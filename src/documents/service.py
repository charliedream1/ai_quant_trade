"""Resolve original documents and update only explicitly editable Markdown sources."""

import os
from contextlib import nullcontext
from pathlib import Path
from uuid import uuid4

from loguru import logger

from src.core.config import PROJECT_ROOT, get_settings
from src.core.exceptions import BusinessError, ErrorCode
from src.core.file_storage import FileStorage
from src.core.kb_chunks import refresh_document_chunks
from src.core.repository import Repository
from src.core.timeutil import utc_now_iso
from src.knowledge.files import KnowledgeFiles

from .access import bounded_read, can_edit_project, project_file
from .config import decode_text, digest, preview_config
from .conversion import request_pdf
from .store import FILE_LOCK, PreviewStore, validate_content


def _atomic_write(path: Path, content: bytes) -> None:
    if not path.resolve().is_relative_to(PROJECT_ROOT.resolve()):
        raise BusinessError(ErrorCode.INVALID_PARAM, "禁止修改项目目录外的文件")
    temporary = path.with_name(path.name + "." + uuid4().hex + ".tmp")
    temporary.write_bytes(content)
    os.replace(temporary, path)


class FilePreviewService:
    def __init__(self) -> None:
        self.store = PreviewStore()

    def knowledge(self, doc_id: int) -> dict:
        row = Repository().get("kb_documents", int(doc_id))
        if row.get("original_file_id"):
            return self.detail(row["original_file_id"])
        if not row.get("file_path"):
            content = str(row.get("content") or "").encode("utf-8")
        else:
            content = bounded_read(FileStorage().resolve(row["file_path"]), text=True)
        record = self.store.upload(
            str(row["title"]) + ".md", content, source="knowledge_text", knowledge_id=int(doc_id)
        )
        record.update(editable=row.get("doc_type") in {"note", "笔记"}, legacy=True)
        if record["editable"]:
            record["legacy"] = False
            Repository().update("kb_documents", int(doc_id), {"original_file_id": record["id"]})
        self.store.save(record)
        return self.detail(record["id"])

    def detail(self, identifier: str) -> dict:
        row = self.store.read(identifier)
        if row.get("knowledge_id"):
            Repository().get("kb_documents", int(row["knowledge_id"]))
        path = self.store.path(row)
        content = bounded_read(path)
        row.update(revision=digest(content), bytes=len(content))
        if row["source"] == "project":
            row["editable"] = can_edit_project(path)
        result = {key: value for key, value in row.items() if key != "relative"}
        result.update(
            url=f"{get_settings().api_prefix}/file-previews/{row['id']}/view",
            ui=preview_config()["ui"],
            limits=preview_config()["limits"],
        )
        if row["kind"] in {"markdown", "text", "html"}:
            maximum = preview_config()["limits"]["max_text_bytes"]
            utf8 = decode_text(content).encode("utf-8")
            result["preview_truncated"] = len(utf8) > maximum
            result["content"] = utf8[:maximum].decode("utf-8", errors="ignore")
            if result["preview_truncated"]:
                result["editable"] = False
        return result

    def convert(self, identifier: str) -> dict:
        row = self.detail(identifier)
        if row["kind"] != "office":
            raise BusinessError(ErrorCode.INVALID_PARAM, "只有Office文件需要转换")
        return request_pdf(row)

    def save_markdown(self, identifier: str, revision: str, text: str) -> dict:
        with FILE_LOCK:
            row = self.detail(identifier)
            if row["kind"] != "markdown" or not row["editable"]:
                raise BusinessError(ErrorCode.INVALID_PARAM, "该文件只读，仅允许修改Markdown原件")
            if row["revision"] != revision:
                raise BusinessError(
                    ErrorCode.CONSTRAINT_CONFLICT, "文件已被其他窗口修改，请重新载入后合并，未覆盖原文件"
                )
            content = text.encode("utf-8")
            if len(content) > preview_config()["limits"]["max_text_bytes"]:
                raise BusinessError(ErrorCode.INVALID_PARAM, "Markdown超过编辑大小上限，未保存")
            validate_content(row["name"], content)
            path = self.store.path(self.store.read(identifier))
            previous = bounded_read(path, text=True)
            if digest(previous) != revision:
                raise BusinessError(ErrorCode.CONSTRAINT_CONFLICT, "文件刚被其他进程修改，未覆盖原件")
            history = self.store.directory(identifier) / "versions"
            history.mkdir(exist_ok=True)
            backup = history / (revision + ".md")
            if not backup.exists():
                backup.write_bytes(previous)
            self._commit_markdown(row, path, previous, content, text)
            logger.info(
                "Markdown已保存 | file={} revision={} knowledge={}",
                identifier,
                digest(content),
                row.get("knowledge_id"),
            )
            return self.detail(identifier)

    def _commit_markdown(self, row: dict, path: Path, previous: bytes, content: bytes, text: str) -> None:
        repo = Repository() if row.get("knowledge_id") else None
        current = repo.get("kb_documents", int(row["knowledge_id"])) if repo is not None else None
        derived = FileStorage().resolve(current["file_path"]) if current and current.get("file_path") else None
        previous_derived = bounded_read(derived) if derived is not None else None
        manifest = self.store.directory(row["id"]) / "record.json"
        previous_manifest = manifest.read_bytes()
        try:
            with repo.db.transaction() if repo is not None else nullcontext():
                _atomic_write(path, content)
                if repo is not None and current is not None:
                    repo.update(
                        "kb_documents",
                        current["id"],
                        {"content": text, "summary": text[:200], "updated_at": utc_now_iso()},
                    )
                    refresh_document_chunks(repo, current["id"], title=current["title"], content=text)
                if derived is not None:
                    _atomic_write(derived, content)
                record = self.store.read(row["id"])
                record.update(revision=digest(content), updated_at=utc_now_iso())
                self.store.save(record)
        except Exception:
            _atomic_write(path, previous)
            if derived is not None and previous_derived is not None:
                _atomic_write(derived, previous_derived)
            _atomic_write(manifest, previous_manifest)
            if repo is not None and current is not None:
                chunks = repo.db.query(
                    "SELECT chunk_index, heading, content, char_count FROM kb_document_chunks WHERE doc_id = ? ORDER BY chunk_index",
                    (current["id"],),
                )
                KnowledgeFiles(repo).write_document(current, chunks)
            raise

    def asset(self, identifier: str, relative: str) -> Path:
        row = self.store.read(identifier)
        self.detail(identifier)
        if row["source"] != "project":
            raise BusinessError(ErrorCode.NOT_FOUND, "此上传文件没有独立图片附件")
        base = self.store.path(row).parent
        target = (base / relative).resolve()
        root = PROJECT_ROOT.resolve()
        if not target.is_relative_to(root):
            raise BusinessError(ErrorCode.INVALID_PARAM, "图片路径越界")
        path = project_file(target.relative_to(root).as_posix())
        if path.suffix.lower() not in preview_config()["formats"]["image"]:
            raise BusinessError(ErrorCode.INVALID_PARAM, "只支持受控图片资源")
        validate_content(path.name, bounded_read(path))
        return path
