"""Atomic file projections; only catalogued current chunks participate in retrieval."""

import hashlib
import json
import os
from pathlib import Path
from typing import Any
from uuid import uuid4

from src.core.config import get_settings
from src.core.exceptions import BusinessError, ErrorCode
from src.core.repository import Repository

from .config import knowledge_config, library_name


def atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(uuid4().hex + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)


class KnowledgeFiles:
    def __init__(self, repo: Repository | None = None):
        self.repo = repo or Repository()
        settings = get_settings()
        self.root = (settings.data_dir / knowledge_config()["storage_directory"]).resolve()
        if not self.root.is_relative_to(settings.project_root.resolve()):
            raise BusinessError(ErrorCode.STORAGE_ERROR, "知识库文件必须保存在项目内")

    def directory(self, name: str) -> Path:
        key = hashlib.sha256(library_name(name).encode("utf-8")).hexdigest()[: knowledge_config()["library_hash_chars"]]
        return self.root / key

    def create_library(self, name: str) -> str:
        name = library_name(name)
        atomic_text(self.directory(name) / "library.json", json.dumps({"name": name}, ensure_ascii=False))
        return name

    def libraries(self) -> list[str]:
        names = {knowledge_config()["default_library"]}
        names.update(
            row["library_name"]
            for row in self.repo.db.query(
                "SELECT DISTINCT library_name FROM kb_documents WHERE attachment_session = ''"
            )
        )
        if self.root.exists():
            for path in self.root.glob("*/library.json"):
                names.add(json.loads(path.read_text(encoding="utf-8"))["name"])
        return sorted(names)

    def write_document(self, row: dict[str, Any], chunks: list[dict[str, Any]]) -> None:
        name = library_name(row.get("library_name"))
        self.create_library(name)
        directory = self.directory(name) / str(row["id"])
        atomic_text(directory / "document.md", str(row.get("content") or ""))
        revision = hashlib.sha256(json.dumps(chunks, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()[
            : knowledge_config()["revision_hash_chars"]
        ]
        records = []
        for chunk in chunks:
            filename = f"chunks/{revision}/{int(chunk['chunk_index'])}.md"
            atomic_text(directory / filename, chunk["content"])
            records.append(
                {key: value for key, value in chunk.items() if key != "content"}
                | {"file": filename, "sha256": hashlib.sha256(chunk["content"].encode("utf-8")).hexdigest()}
            )
        metadata = {
            key: row.get(key)
            for key in (
                "id",
                "title",
                "source",
                "original_file_id",
                "library_name",
                "attachment_session",
                "chunk_chars",
                "updated_at",
            )
        }
        atomic_text(directory / "manifest.json", json.dumps({**metadata, "chunks": records}, ensure_ascii=False))

    def documents(
        self,
        name: str,
        *,
        session_id: str = "",
        category_id: int | None = None,
        scope: str = "all",
        document_id: int | None = None,
    ) -> list[dict[str, Any]]:
        rows = self.repo.db.query(
            "SELECT * FROM kb_documents WHERE library_name = ? AND status = 'ready'", (library_name(name),)
        )
        result = []
        for row in rows:
            if document_id is not None and row["id"] != document_id:
                continue
            if row.get("attachment_session") and row["attachment_session"] != session_id:
                continue
            if category_id and row["category_id"] != category_id:
                continue
            remote = str(row.get("source") or "").startswith("remote:")
            if (scope == "local" and remote) or (scope == "remote" and not remote):
                continue
            result.append(row)
        return result
