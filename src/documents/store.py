"""Durable UUID file records; clients never choose the stored path or write permission."""

import json
import os
import zipfile
from io import BytesIO
from pathlib import Path
from threading import RLock
from typing import Any
from uuid import UUID, uuid4

from src.agent.image_validation import validate_images
from src.core.config import get_settings
from src.core.exceptions import BusinessError, ErrorCode
from src.core.timeutil import utc_now_iso

from .access import bounded_read, can_edit_project, compact_path, project_file
from .config import decode_text, digest, file_kind, preview_config

FILE_LOCK = RLock()


def validate_content(name: str, content: bytes) -> str:
    kind = file_kind(name)
    limits = preview_config()["limits"]
    if (not content and kind not in {"markdown", "text"}) or len(content) > limits["max_bytes"]:
        raise BusinessError(ErrorCode.INVALID_PARAM, "文件为空或超过大小上限")
    if kind in {"markdown", "html", "text"}:
        text = decode_text(content)
        if "\x00" in text:
            raise BusinessError(ErrorCode.INVALID_PARAM, "文本中包含二进制数据")
    elif kind == "image":
        validate_images([(name, content)])
    elif kind == "pdf" and b"%PDF-" not in content[:1024]:
        raise BusinessError(ErrorCode.INVALID_PARAM, "文件内容不是PDF")
    elif kind == "office":
        _validate_office(name, content)
    return kind


def _validate_office(name: str, content: bytes) -> None:
    suffix = Path(name).suffix.lower()
    if suffix in {".doc", ".xls", ".ppt"}:
        if not content.startswith(bytes.fromhex("d0cf11e0a1b11ae1")):
            raise BusinessError(ErrorCode.INVALID_PARAM, "旧版Office文件头不正确")
        return
    required = {".docx": "word/document.xml", ".xlsx": "xl/workbook.xml", ".pptx": "ppt/presentation.xml"}
    try:
        with zipfile.ZipFile(BytesIO(content)) as archive:
            entries = archive.infolist()
            limits = preview_config()["limits"]
            if (
                len(entries) > limits["max_zip_entries"]
                or sum(item.file_size for item in entries) > limits["max_zip_bytes"]
            ):
                raise ValueError("解包资源超过上限")
            names = {item.filename for item in entries}
            if suffix in required and "[Content_Types].xml" not in names:
                raise ValueError("缺少Office类型声明")
            if any(
                Path(name.replace("\\", "/")).is_absolute() or ".." in Path(name.replace("\\", "/")).parts
                for name in names
            ):
                raise ValueError("压缩文件包含越界条目")
            if required.get(suffix, "mimetype") not in names or any("vbaproject" in item.lower() for item in names):
                raise ValueError("格式不符或包含宏项目")
    except (zipfile.BadZipFile, ValueError) as exc:
        raise BusinessError(ErrorCode.INVALID_PARAM, f"Office文件校验失败：{exc}") from exc


class PreviewStore:
    def __init__(self) -> None:
        settings = get_settings()
        self.root = (settings.data_dir / "file_previews").resolve()
        if not self.root.is_relative_to(Path(settings.data_dir).resolve()):
            raise BusinessError(ErrorCode.INVALID_PARAM, "File preview storage must stay inside the configured data directory")
        self.root.mkdir(parents=True, exist_ok=True)
        self.root = compact_path(self.root)

    def directory(self, identifier: str) -> Path:
        try:
            key = UUID(str(identifier)).hex
        except ValueError as exc:
            raise BusinessError(ErrorCode.INVALID_PARAM, "文件ID格式无效") from exc
        return self.root / "records" / key

    def read(self, identifier: str) -> dict[str, Any]:
        path = self.directory(identifier) / "record.json"
        try:
            row = json.loads(path.read_text(encoding="utf-8"))
            if row["id"] != UUID(identifier).hex:
                raise ValueError("记录身份不符")
            return dict(row)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise BusinessError(ErrorCode.NOT_FOUND, "文件记录不存在") from exc

    def save(self, row: dict[str, Any]) -> None:
        root = self.directory(row["id"])
        root.mkdir(parents=True, exist_ok=True)
        temporary = root / (uuid4().hex + ".json.tmp")
        temporary.write_text(json.dumps(row, ensure_ascii=False), encoding="utf-8")
        os.replace(temporary, root / "record.json")

    def upload(
        self,
        name: str,
        content: bytes,
        *,
        source: str = "upload",
        knowledge_id: int | None = None,
        image_verified: bool = False,
    ) -> dict:
        name = Path(name.replace("\\", "/")).name
        if (
            image_verified
            and file_kind(name) == "image"
            and 0 < len(content) <= preview_config()["limits"]["max_bytes"]
        ):
            kind = "image"
        else:
            kind = validate_content(name, content)
        key = uuid4().hex
        directory = self.directory(key)
        directory.mkdir(parents=True)
        path = directory / ("original" + Path(name).suffix.lower())
        path.write_bytes(content)
        row = {
            "id": key,
            "name": name,
            "kind": kind,
            "source": source,
            "editable": kind == "markdown",
            "knowledge_id": knowledge_id,
            "revision": digest(content),
            "created_at": utc_now_iso(),
        }
        self.save(row)
        return row

    def register_project(self, name: str) -> dict:
        path = project_file(name)
        content = bounded_read(path)
        kind = validate_content(path.name, content)
        row = {
            "id": uuid4().hex,
            "name": path.name,
            "kind": kind,
            "source": "project",
            "relative": path.relative_to(get_settings().project_root.resolve()).as_posix(),
            "editable": can_edit_project(path),
            "revision": digest(content),
            "created_at": utc_now_iso(),
        }
        self.save(row)
        return row

    def path(self, row: dict) -> Path:
        if row["source"] == "project":
            return project_file(row["relative"])
        path = self.directory(row["id"]) / ("original" + Path(row["name"]).suffix.lower())
        if not path.resolve().is_relative_to(self.directory(row["id"]).resolve()) or not path.is_file():
            raise BusinessError(ErrorCode.NOT_FOUND, "原文件缺失")
        return path
