"""Use zvec-grep's lexical engine on active, explicitly scoped chunk files."""

import hashlib
import json
import os
import subprocess  # nosec B404
from pathlib import Path
from typing import Any

from src.core.config import PROJECT_ROOT
from src.core.exceptions import BusinessError, ErrorCode
from src.core.kb_chunks import refresh_document_chunks
from src.core.process_control import stop_process_tree
from src.core.process_env import process_environment
from src.core.repository import Repository
from src.core.tool_paths import runtime_path

from .config import knowledge_config
from .files import KnowledgeFiles


class KeywordSearch:
    def __init__(self, repo: Repository | None = None):
        self.repo = repo or Repository()
        self.files = KnowledgeFiles(self.repo)

    def search(
        self,
        keywords: list[str],
        *,
        library: str,
        limit: int,
        session_id: str = "",
        category_id: int | None = None,
        scope: str = "all",
        document_id: int | None = None,
    ) -> list[dict[str, Any]]:
        policy = knowledge_config()["search"]
        active: dict[str, dict[str, Any]] = {}
        for row in self.files.documents(
            library, session_id=session_id, category_id=category_id, scope=scope, document_id=document_id
        ):
            directory = self.files.directory(library) / str(row["id"])
            manifest_path = directory / "manifest.json"
            if not manifest_path.exists():
                refresh_document_chunks(self.repo, row["id"])
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            chunk_ids = {
                item["chunk_index"]: item["id"]
                for item in self.repo.db.query(
                    "SELECT id, chunk_index FROM kb_document_chunks WHERE doc_id = ?", (row["id"],)
                )
            }
            for chunk in manifest["chunks"]:
                path = (directory / chunk["file"]).resolve()
                if not path.is_relative_to(directory.resolve()):
                    raise BusinessError(ErrorCode.STORAGE_ERROR, "分块文件路径越界")
                active[str(path)] = {
                    **row,
                    "chunk_id": chunk_ids.get(chunk["chunk_index"]),
                    "chunk_index": chunk["chunk_index"],
                    "chunk_heading": chunk["heading"],
                    "chunk_path": str(path),
                    "chunk_sha256": chunk.get("sha256"),
                }
        if not active or not keywords:
            return []
        matched: dict[str, dict[str, Any]] = {}
        paths = list(active)
        for offset in range(0, len(paths), policy["path_batch_size"]):
            request = {
                "root": str(self.files.directory(library)),
                "paths": paths[offset : offset + policy["path_batch_size"]],
                "keywords": keywords,
                "module": str(runtime_path(policy["entrypoint"])),
                "limit": policy["path_batch_size"] * policy["matches_per_file"],
                "matches_per_file": policy["matches_per_file"],
            }
            result = self._run(request)
            for hit in result["items"]:
                path = str(Path(hit["file"]["absolutePath"]).resolve())
                if path not in active:
                    continue
                row = active[path]
                content = Path(path).read_text(encoding="utf-8")
                if (
                    row.get("chunk_sha256")
                    and hashlib.sha256(content.encode("utf-8")).hexdigest() != row["chunk_sha256"]
                ):
                    raise BusinessError(ErrorCode.PARSE_ERROR, "分块文件摘要不符，请重新入库")
                matched[path] = {
                    **row,
                    "chunk_content": content,
                    "snippet": content,
                    "line_number": hit["range"]["startLine"],
                    "score": sum(content.casefold().count(term.casefold()) for term in keywords),
                }
        return sorted(matched.values(), key=lambda row: (-row["score"], row["id"], row["chunk_index"]))[:limit]

    def _run(self, request: dict[str, Any]) -> dict[str, Any]:
        policy = knowledge_config()["search"]
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
        try:
            with subprocess.Popen(  # nosec B603
                [policy["node"], str(runtime_path(policy["adapter"]))],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=PROJECT_ROOT,
                env=process_environment("document"),
                creationflags=flags,
                start_new_session=os.name != "nt",
            ) as process:
                try:
                    output, error = process.communicate(
                        json.dumps(request).encode("utf-8"), timeout=policy["timeout_seconds"]
                    )
                except subprocess.TimeoutExpired:
                    stop_process_tree(process)
                    process.communicate()
                    raise BusinessError(ErrorCode.PARSE_ERROR, "zvec-grep检索超时") from None
                if process.returncode or len(output) > policy["max_output_bytes"]:
                    raise BusinessError(ErrorCode.PARSE_ERROR, "zvec-grep检索失败，请检查项目内安装和运行日志")
                return dict(json.loads(output))
        except OSError as exc:
            raise BusinessError(ErrorCode.PARSE_ERROR, "zvec-grep或Node.js未安装") from exc
