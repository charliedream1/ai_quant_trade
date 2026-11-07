"""Knowledge application operations shared by HTTP and Gradio adapters."""

from typing import Any
from uuid import uuid4

from src.core.file_storage import FileStorage
from src.core.kb_chunks import refresh_document_chunks
from src.core.kb_importer import parse_document_tags
from src.core.repository import Repository, json_loads
from src.core.timeutil import utc_now_iso
from src.knowledge.config import chunk_length, library_name
from src.knowledge.sag_sync import auto_sync_document


def delete_document(doc_id: int):
    repo = Repository()
    row = repo.get("kb_documents", doc_id)
    repo.delete("kb_documents", doc_id)
    if row.get("file_path"):
        FileStorage().delete(row["file_path"])
    return None


def _chunk_count(repo: Repository, doc_id: int) -> int:
    return int(repo.db.scalar("SELECT COUNT(*) FROM kb_document_chunks WHERE doc_id = ?", (doc_id,)) or 0)


def create_note(payload: dict[str, Any]):
    return _create_doc(payload, doc_type="note")


def _create_doc(payload: dict[str, Any], doc_type: str) -> dict[str, Any]:
    repo = Repository()
    storage = FileStorage()
    now = utc_now_iso()
    title = payload["title"]
    content = payload.get("content") or ""
    rel = ""
    if doc_type == "note":
        rel = f"knowledge/notes/{storage.safe_filename(title)}_{uuid4().hex}.md"
        storage.write_text(rel, content)
    row = repo.insert(
        "kb_documents",
        {
            "title": title,
            "doc_type": "笔记" if doc_type == "note" else payload.get("doc_type", "文档"),
            "category_id": int(payload.get("category_id") or 0),
            "summary": payload.get("summary") or content[:200],
            "content": content,
            "file_path": rel,
            "source": payload.get("source") or "local",
            "tags": parse_document_tags(payload.get("tags")),
            "status": "ready",
            "imported_at": now,
            "updated_at": now,
            "library_name": library_name(payload.get("library_name")),
            "chunk_chars": chunk_length(payload.get("chunk_chars")),
        },
    )
    row["doc_id"] = row["id"]
    row["tags"] = json_loads(row.get("tags"), [])
    row["chunk_count"] = refresh_document_chunks(repo, int(row["id"]), title=title, content=content)
    auto_sync_document(repo, int(row["id"]))
    return row


def _document_chunks(repo: Repository, doc_id: int, *, include_content: bool) -> list[dict[str, Any]]:
    columns = "chunk_index, heading, char_count"
    if include_content:
        columns += ", content"
    return repo.db.query(
        f"SELECT {columns}\n              FROM kb_document_chunks\n             WHERE doc_id = ?\n             ORDER BY chunk_index ASC\n             LIMIT 20",
        (doc_id,),
    )


def document_detail(doc_id: int, include_content: bool = True):
    repo = Repository()
    row = repo.get("kb_documents", doc_id)
    row["doc_id"] = row["id"]
    row["tags"] = json_loads(row.get("tags"), [])
    row["chunk_count"] = _chunk_count(repo, doc_id)
    row["chunks"] = _document_chunks(repo, doc_id, include_content=include_content)
    if not include_content:
        row.pop("content", None)
    return row


def create_category(payload: dict[str, Any]):
    now = utc_now_iso()
    row = Repository().insert(
        "kb_categories",
        {
            "name": payload["name"],
            "parent_id": int(payload.get("parent_id") or 0),
            "sort_order": int(payload.get("sort_order") or 0),
            "created_at": now,
            "updated_at": now,
        },
    )
    row["category_id"] = row["id"]
    return row
