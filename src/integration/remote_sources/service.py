"""Remote knowledge source persistence, synchronization and local import."""

from __future__ import annotations

import json
from hashlib import sha256
from typing import Any

from loguru import logger

from src.core.exceptions import BusinessError, ErrorCode
from src.core.file_storage import FileStorage
from src.core.kb_chunks import refresh_document_chunks
from src.core.repository import Repository, json_loads
from src.core.timeutil import utc_now_iso
from src.integration.remote_sources.base import (
    RemoteSourceAdapter,
    normalize_document,
    normalize_documents,
)
from src.knowledge.config import chunk_length, library_name

DEFAULT_REMOTE_SYNC_LIMIT = 20
MAX_REMOTE_SYNC_LIMIT = 100


class RemoteSourceService:
    def __init__(self, repo: Repository | None = None) -> None:
        self.repo = repo or Repository()

    def list(self) -> list[dict[str, Any]]:
        rows = self.repo.list("remote_sources", order_by="id DESC")
        return [self._shape(row) for row in rows]

    def create(self, payload: dict[str, Any]) -> dict[str, Any]:
        name = str(payload.get("name") or "").strip()
        if not name:
            raise BusinessError(ErrorCode.MISSING_PARAM, "远程知识源名称不能为空。")
        now = utc_now_iso()
        row = self.repo.insert(
            "remote_sources",
            {
                "source_type": payload.get("type") or payload.get("source_type") or "custom",
                "name": name,
                "conn_config": json.dumps(payload, ensure_ascii=False),
                "enabled": 1 if payload.get("enabled", True) else 0,
                "status": "disconnected",
                "last_sync_at": None,
                "created_at": now,
                "updated_at": now,
            },
        )
        logger.info("远程知识源已创建：source_id={} type={}", row["id"], row["source_type"])
        return self._shape(row)

    def update(self, source_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        current = self.repo.get("remote_sources", source_id)
        values: dict[str, Any] = {"updated_at": utc_now_iso(), "status": "disconnected"}
        if "name" in payload:
            name = str(payload["name"] or "").strip()
            if not name:
                raise BusinessError(ErrorCode.MISSING_PARAM, "远程知识源名称不能为空。")
            values["name"] = name
        if "type" in payload or "source_type" in payload:
            values["source_type"] = payload.get("type") or payload.get("source_type")
        if "enabled" in payload:
            values["enabled"] = 1 if payload["enabled"] else 0
        config = dict(json_loads(current.get("conn_config"), {}) or {})
        config.update(payload)
        values["conn_config"] = json.dumps(config, ensure_ascii=False)
        row = self.repo.update("remote_sources", source_id, values)
        logger.info("远程知识源配置已更新：source_id={}", source_id)
        return self._shape(row)

    def delete(self, source_id: int) -> None:
        self.repo.delete("remote_sources", source_id)
        logger.info("远程知识源已删除：source_id={}", source_id)

    def test(self, source_id: int) -> dict[str, Any]:
        row = self.repo.get("remote_sources", source_id)
        checked_at = utc_now_iso()
        try:
            adapter = RemoteSourceAdapter(row)
            probe = adapter.probe()
            capabilities = adapter.capabilities(probe)
            success = bool(probe.get("success"))
            self._set_status(source_id, "connected" if success else "failed")
            result = {
                "source_id": source_id,
                "server_id": adapter.server_id,
                "success": success,
                "latency_ms": probe.get("latency_ms"),
                "capabilities": capabilities,
                "tools": probe.get("tools", []),
                "error": str(probe.get("error") or ""),
                "checked_at": checked_at,
            }
        except BusinessError as exc:
            self._set_status(source_id, "failed")
            result = {
                "source_id": source_id,
                "success": False,
                "capabilities": [],
                "tools": [],
                "error": exc.message,
                "checked_at": checked_at,
            }
        logger.info(
            "远程知识源测试完成：source_id={} success={} capabilities={}",
            source_id,
            result["success"],
            result["capabilities"],
        )
        return result

    def documents(
        self,
        source_id: int,
        folder: str | None = None,
        keyword: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        row = self.repo.get("remote_sources", source_id)
        adapter = RemoteSourceAdapter(row)
        action = "search" if keyword else "list"
        if keyword:
            values = {"query": keyword, "folder": folder, "page": page, "page_size": page_size}
        else:
            values = {"folder": folder, "page": page, "page_size": page_size}
        payload, call_result = adapter.call(action, values)
        normalized = normalize_documents(payload)
        items = []
        for item in normalized["items"]:
            self._cache_metadata(source_id, item)
            item["imported"] = self._is_imported(source_id, item["remote_doc_id"])
            items.append(item)
        self._set_status(source_id, "connected")
        logger.info(
            "远程知识源文档列表完成：source_id={} action={} count={} latency_ms={}",
            source_id,
            action,
            len(items),
            call_result.get("latency_ms"),
        )
        return {
            "items": items,
            "page": page,
            "page_size": page_size,
            "total": normalized["total"],
            "next_cursor": normalized["next_cursor"],
        }

    def pull(self, source_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        remote_doc_id = str(payload.get("remote_doc_id") or payload.get("document_id") or "").strip()
        if not remote_doc_id:
            raise BusinessError(ErrorCode.MISSING_PARAM, "远程文档 ID 不能为空。")
        row = self.repo.get("remote_sources", source_id)
        adapter = RemoteSourceAdapter(row)
        document_payload, call_result = adapter.call(
            "fetch",
            {
                "remote_doc_id": remote_doc_id,
                "folder": payload.get("folder"),
            },
        )
        document = normalize_document(document_payload, remote_doc_id)
        category_id = int(payload.get("category_id") or 0)
        local_result = self._import_document(
            row, document, category_id, payload.get("library_name"), payload.get("chunk_chars")
        )
        self._set_status(source_id, "connected", sync=True)
        logger.info(
            "远程知识源文档导入完成：source_id={} remote_doc_id={} local_doc_id={} latency_ms={}",
            source_id,
            document["remote_doc_id"],
            local_result["local_doc_id"],
            call_result.get("latency_ms"),
        )
        return {
            "success_count": 1 if local_result["changed"] else 0,
            "skipped_count": 0 if local_result["changed"] else 1,
            "failed_count": 0,
            "failures": [],
            "source_id": source_id,
            "remote_doc_id": document["remote_doc_id"],
            "local_doc_id": local_result["local_doc_id"],
            "local_path": local_result["local_path"],
            "chunk_count": local_result["chunk_count"],
            "changed": local_result["changed"],
        }

    def sync(self, source_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        folder = str(payload.get("folder") or "").strip() or None
        keyword = str(payload.get("keyword") or payload.get("query") or "").strip() or None
        category_id = int(payload.get("category_id") or 0)
        limit = _sync_limit(payload.get("limit") or payload.get("page_size"))
        listed = self.documents(
            source_id,
            folder=folder,
            keyword=keyword,
            page=1,
            page_size=limit,
        )
        items = list(listed.get("items") or [])[:limit]
        success_count = 0
        skipped_count = 0
        failures: list[dict[str, Any]] = []
        imported: list[dict[str, Any]] = []
        for item in items:
            remote_doc_id = str(item.get("remote_doc_id") or "").strip()
            if not remote_doc_id:
                continue
            try:
                result = self.pull(
                    source_id,
                    {
                        "remote_doc_id": remote_doc_id,
                        "folder": folder,
                        "category_id": category_id,
                        "library_name": payload.get("library_name"),
                        "chunk_chars": payload.get("chunk_chars"),
                    },
                )
            except BusinessError as exc:
                failures.append(
                    {
                        "remote_doc_id": remote_doc_id,
                        "title": item.get("title") or remote_doc_id,
                        "error": exc.message,
                    }
                )
                continue
            success_count += int(result.get("success_count") or 0)
            skipped_count += int(result.get("skipped_count") or 0)
            imported.append(
                {
                    "remote_doc_id": remote_doc_id,
                    "title": item.get("title") or remote_doc_id,
                    "local_doc_id": result.get("local_doc_id"),
                    "local_path": result.get("local_path"),
                    "chunk_count": result.get("chunk_count"),
                    "changed": bool(result.get("changed")),
                }
            )
        failed_count = len(failures)
        status = "failed" if items and failed_count == len(items) else "connected"
        self._set_status(source_id, status, sync=True)
        logger.info(
            "远程知识源批量同步完成：source_id={} scanned={} success={} skipped={} failed={}",
            source_id,
            len(items),
            success_count,
            skipped_count,
            failed_count,
        )
        return {
            "source_id": source_id,
            "action": "search" if keyword else "list",
            "folder": folder or "",
            "keyword": keyword or "",
            "category_id": category_id,
            "limit": limit,
            "scanned_count": len(items),
            "success_count": success_count,
            "skipped_count": skipped_count,
            "failed_count": failed_count,
            "failures": failures,
            "imported": imported,
            "total": listed.get("total"),
            "next_cursor": listed.get("next_cursor") or "",
        }

    def _import_document(
        self,
        source_row: dict[str, Any],
        document: dict[str, Any],
        category_id: int,
        library: str | None = None,
        chunk_chars: int | None = None,
    ) -> dict[str, Any]:
        source_id = int(source_row["id"])
        remote_id = str(document["remote_doc_id"])
        source_key = f"remote:{source_id}:{remote_id}"
        name = library_name(library)
        existing = self.repo.db.query_one(
            "SELECT * FROM kb_documents WHERE source = ? AND library_name = ?", (source_key, name)
        )
        now = utc_now_iso()
        title = str(document["title"])
        content = str(document["content"])
        summary = str(document.get("summary") or content[:200])
        changed = not existing or any(
            existing.get(key) != value
            for key, value in {
                "title": title,
                "summary": summary,
                "content": content,
                "category_id": category_id,
            }.items()
        )
        local_path = str(existing.get("file_path") or "") if existing else ""
        if not local_path:
            fingerprint = sha256(name.encode("utf-8")).hexdigest()[:8]
            filename = FileStorage().safe_filename(f"remote_{fingerprint}_{source_id}_{remote_id}_{title}", ".md")
            local_path = f"knowledge/remote/{filename}"
        FileStorage().write_text(local_path, content)
        values = {
            "title": title,
            "doc_type": str(document.get("type") or "远程文档"),
            "category_id": category_id,
            "summary": summary,
            "content": content,
            "file_path": local_path,
            "source": source_key,
            "library_name": name,
            "chunk_chars": chunk_length(chunk_chars),
            "tags": ["remote", str(source_row.get("source_type") or "custom")],
            "status": "ready",
            "imported_at": now,
            "updated_at": now,
        }
        if existing:
            local_row = self.repo.update("kb_documents", int(existing["id"]), values)
        else:
            local_row = self.repo.insert("kb_documents", values)
        chunk_count = refresh_document_chunks(
            self.repo,
            int(local_row["id"]),
            title=title,
            content=content,
        )
        self._cache_document(source_id, document, local_path)
        return {
            "local_doc_id": int(local_row["id"]),
            "local_path": local_path,
            "chunk_count": chunk_count,
            "changed": changed,
        }

    def _cache_metadata(self, source_id: int, item: dict[str, Any]) -> None:
        existing = self._cache_row(source_id, item["remote_doc_id"])
        now = utc_now_iso()
        values = {
            "source_id": source_id,
            "remote_id": item["remote_doc_id"],
            "title": item["title"],
            "summary": item.get("summary") or "",
            "content": existing.get("content") if existing else None,
            "local_path": existing.get("local_path") if existing else None,
            "fetched_at": existing.get("fetched_at") if existing else now,
            "created_at": existing.get("created_at") if existing else now,
            "updated_at": now,
        }
        if existing:
            self.repo.update("remote_docs_cache", int(existing["id"]), values)
        else:
            self.repo.insert("remote_docs_cache", values)

    def _cache_document(self, source_id: int, document: dict[str, Any], local_path: str) -> None:
        existing = self._cache_row(source_id, document["remote_doc_id"])
        now = utc_now_iso()
        values = {
            "source_id": source_id,
            "remote_id": document["remote_doc_id"],
            "title": document["title"],
            "summary": document.get("summary") or "",
            "content": document["content"],
            "local_path": local_path,
            "fetched_at": now,
            "created_at": existing.get("created_at") if existing else now,
            "updated_at": now,
        }
        if existing:
            self.repo.update("remote_docs_cache", int(existing["id"]), values)
        else:
            self.repo.insert("remote_docs_cache", values)

    def _cache_row(self, source_id: int, remote_id: str) -> dict[str, Any] | None:
        return self.repo.db.query_one(
            "SELECT * FROM remote_docs_cache WHERE source_id = ? AND remote_id = ?",
            (source_id, remote_id),
        )

    def _is_imported(self, source_id: int, remote_id: str) -> bool:
        source_key = f"remote:{source_id}:{remote_id}"
        return bool(self.repo.db.scalar("SELECT COUNT(*) FROM kb_documents WHERE source = ?", (source_key,)))

    def _set_status(self, source_id: int, status: str, sync: bool = False) -> None:
        values: dict[str, Any] = {"status": status, "updated_at": utc_now_iso()}
        if sync:
            values["last_sync_at"] = utc_now_iso()
        self.repo.update("remote_sources", source_id, values)

    def _shape(self, row: dict[str, Any]) -> dict[str, Any]:
        adapter = None
        try:
            adapter = RemoteSourceAdapter(row)
        except BusinessError:
            pass
        row["source_id"] = row["id"]
        row["type"] = row["source_type"]
        row["config"] = adapter.public_config() if adapter else {}
        row["conn_config"] = row["config"]
        row["mcp_server_id"] = adapter.server_id if adapter else None
        row["enabled"] = bool(row.get("enabled"))
        return row


def _sync_limit(value: Any) -> int:
    try:
        limit = int(value or DEFAULT_REMOTE_SYNC_LIMIT)
    except (TypeError, ValueError):
        limit = DEFAULT_REMOTE_SYNC_LIMIT
    return min(max(limit, 1), MAX_REMOTE_SYNC_LIMIT)
