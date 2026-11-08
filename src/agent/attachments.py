"""Validate and prepare files selected in the AI composer."""

from __future__ import annotations

import base64
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from uuid import uuid4

import yaml
from loguru import logger

from src.core.config import PROJECT_ROOT, get_settings
from src.core.exceptions import BusinessError, ErrorCode
from src.core.kb_importer import parse_document_bytes
from src.documents.store import PreviewStore

from .image_validation import validate_images

CONFIG_PATH = PROJECT_ROOT / "egs" / "config" / "platform" / "ai_workbench_presets.yaml"


@dataclass(slots=True)
class AttachmentBundle:
    paths: list[Path] = field(default_factory=list)
    image_paths: list[Path] = field(default_factory=list)
    text_context: str = ""
    labels: list[str] = field(default_factory=list)
    image_content: dict[Path, bytes] = field(default_factory=dict, repr=False)
    image_mimes: dict[str, str] = field(default_factory=dict)
    file_content: dict[Path, bytes] = field(default_factory=dict, repr=False)
    preview_records: list[dict[str, Any]] = field(default_factory=list)
    previews_prepared: bool = False

    def metadata(self) -> dict[str, Any]:
        if not self.previews_prepared:
            self.previews_prepared = True
            for path in self.paths:
                try:
                    item = PreviewStore().upload(
                        path.name, self.file_content[path], source="attachment", image_verified=path in self.image_paths
                    )
                    self.preview_records.append({"id": item["id"], "name": path.name})
                except BusinessError as exc:
                    logger.warning("附件保持可用，阅读预览不可用 | file={} reason={}", path.name, exc.message)
        return {
            "files": [path.name for path in self.paths],
            "images": [path.name for path in self.image_paths],
            "count": len(self.paths),
            "documents": self.preview_records,
        }

    def image_data_urls(self) -> list[str]:
        values: list[str] = []
        for path in self.image_paths:
            mime = self.image_mimes[str(path)]
            encoded = base64.b64encode(self.image_content[path]).decode("ascii")
            values.append(f"data:{mime};base64,{encoded}")
        return values

    def cli_image_paths(self) -> list[Path]:
        """Persist validated snapshots so CLI never reopens an unvalidated UI cache file."""
        if not self.image_paths:
            return []
        root = get_settings().data_dir / "ai_workspace" / "validated" / uuid4().hex
        root.mkdir(parents=True)
        paths = []
        for index, original in enumerate(self.image_paths):
            target = root / f"{index}{original.suffix.lower()}"
            with target.open("xb") as stream:
                stream.write(self.image_content[original])
            paths.append(target)
        return paths


def prepare_attachments(value: Any) -> AttachmentBundle:
    items = value if isinstance(value, list | tuple) else [value] if value else []
    limits = _limits()
    if len(items) > int(limits["max_files"]):
        raise BusinessError(ErrorCode.INVALID_PARAM, f"附件最多 {limits['max_files']} 个")
    bundle = AttachmentBundle()
    total_bytes = 0
    text_blocks: list[str] = []
    for item in items:
        path = _path_from_item(item)
        if path is None or not path.exists() or not path.is_file():
            raise BusinessError(ErrorCode.INVALID_PARAM, "附件不存在或不可读取")
        suffix = path.suffix.lower()
        if suffix not in set(limits["text_extensions"]) | set(limits["image_extensions"]):
            raise BusinessError(ErrorCode.INVALID_PARAM, f"不支持的附件类型：{path.name}")
        remaining = int(limits["max_total_bytes"]) - total_bytes
        with path.open("rb") as stream:
            content = stream.read(remaining + 1)
        total_bytes += len(content)
        if total_bytes > int(limits["max_total_bytes"]):
            raise BusinessError(ErrorCode.INVALID_PARAM, "附件总大小超过配置上限")
        bundle.paths.append(path)
        bundle.file_content[path] = content
        bundle.labels.append(f"{path.name} ({len(content)} bytes)")
        if suffix in set(limits["image_extensions"]):
            bundle.image_paths.append(path)
            bundle.image_content[path] = content
            continue
        text = _read_text_attachment(path, content)
        if len(text) > int(limits["max_text_chars"]):
            text = text[: int(limits["max_text_chars"])] + "\n[附件文本已按配置截断]"
        text_blocks.append(f"\n--- 附件：{path.name} ---\n{text}")
    bundle.text_context = "".join(text_blocks)
    bundle.image_mimes = validate_images([(str(path), data) for path, data in bundle.image_content.items()])
    return bundle


def _limits() -> dict[str, Any]:
    try:
        payload = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {}
        configured = payload["attachments"]
        if not isinstance(configured, dict) or any(
            int(configured[key]) <= 0 for key in ("max_files", "max_total_bytes", "max_text_chars")
        ):
            raise ValueError("附件限制必须为正数")
        return configured
    except (OSError, yaml.YAMLError, KeyError, TypeError, ValueError) as exc:
        raise BusinessError(ErrorCode.INVALID_PARAM, "附件配置不可用") from exc


def _path_from_item(item: Any) -> Path | None:
    if isinstance(item, str | Path):
        return Path(item)
    if isinstance(item, dict):
        return Path(str(item.get("path") or item.get("name") or ""))
    return Path(str(getattr(item, "path", "") or getattr(item, "name", "")))


def _read_text_attachment(path: Path, content: bytes) -> str:
    suffix = path.suffix.lower()
    if suffix in {".docx", ".pdf"}:
        parsed = parse_document_bytes(path.name, content)
        return parsed["content"]
    return content.decode("utf-8", errors="replace")
