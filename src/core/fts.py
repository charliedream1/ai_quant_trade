"""FTS5 helpers with LIKE fallback."""

from typing import Any

from .database import Database
from .kb_chunks import ensure_document_chunks

REMOTE_SOURCE_PREFIX = "remote:"
KB_SCOPE_LOCAL = "local"
KB_SCOPE_REMOTE = "remote"
KB_SCOPE_ALL = "all"
KB_SCOPES = {KB_SCOPE_LOCAL, KB_SCOPE_REMOTE, KB_SCOPE_ALL}


def normalize_kb_scope(scope: str | None, *, default: str = KB_SCOPE_ALL) -> str:
    """Normalize knowledge search scope."""
    normalized = (scope or default).strip().lower()
    if normalized in KB_SCOPES:
        return normalized
    return default


def kb_document_source_scope(row: dict[str, Any]) -> str:
    source = str(row.get("source") or "")
    if source.startswith(REMOTE_SOURCE_PREFIX):
        return KB_SCOPE_REMOTE
    return KB_SCOPE_LOCAL


def kb_remote_source_id(row: dict[str, Any]) -> str | None:
    source = str(row.get("source") or "")
    if not source.startswith(REMOTE_SOURCE_PREFIX):
        return None
    parts = source.split(":", 2)
    if len(parts) < 2 or not parts[1]:
        return None
    return parts[1]


def _scope_filter(scope: str, *, prefix: str) -> tuple[str | None, list[Any]]:
    source_column = f"{prefix}source"
    if scope == KB_SCOPE_REMOTE:
        return f"{source_column} LIKE ?", [f"{REMOTE_SOURCE_PREFIX}%"]
    if scope == KB_SCOPE_LOCAL:
        return (
            f"({source_column} IS NULL OR {source_column} = '' OR {source_column} NOT LIKE ?)",
            [f"{REMOTE_SOURCE_PREFIX}%"],
        )
    return None, []


def _annotate_source_scope(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    for row in rows:
        row["source_scope"] = kb_document_source_scope(row)
    return rows


class FTSService:
    def __init__(self, db: Database | None = None) -> None:
        self.db = db or Database()

    def search_news(self, keyword: str, limit: int = 20) -> list[dict[str, Any]]:
        if not keyword:
            return []
        try:
            rows = self.db.query(
                """SELECT n.*, snippet(news_items_fts, 1, '<mark>', '</mark>', '...', 16) AS snippet
                   FROM news_items_fts f JOIN news_items n ON f.rowid = n.id
                   WHERE news_items_fts MATCH ?
                   ORDER BY rank LIMIT ?""",
                (keyword, limit),
            )
            if rows:
                return rows
        except Exception:
            pass
        like = f"%{keyword}%"
        return self.db.query(
            """SELECT *, summary AS snippet FROM news_items
               WHERE title LIKE ? OR summary LIKE ?
               ORDER BY published_at DESC LIMIT ?""",
            (like, like, limit),
        )

    def search_kb(
        self,
        keyword: str,
        limit: int = 20,
        category_id: int | None = None,
        doc_type: str | None = None,
        scope: str | None = None,
    ) -> list[dict[str, Any]]:
        if not keyword:
            return []
        normalized_scope = normalize_kb_scope(scope)
        ensure_document_chunks(self.db)
        filters = []
        params: list[Any] = []
        if category_id is not None:
            filters.append("d.category_id = ?")
            params.append(category_id)
        if doc_type:
            filters.append("d.doc_type = ?")
            params.append(doc_type)
        source_filter, source_params = _scope_filter(normalized_scope, prefix="d.")
        if source_filter:
            filters.append(source_filter)
            params.extend(source_params)
        suffix = (" AND " + " AND ".join(filters)) if filters else ""
        try:
            rows = self.db.query(
                f"""SELECT d.*,
                          c.id AS chunk_id,
                          c.chunk_index AS chunk_index,
                          c.heading AS chunk_heading,
                          c.content AS chunk_content,
                          snippet(kb_document_chunks_fts, 2, '<mark>', '</mark>', '...', 24) AS snippet
                   FROM kb_document_chunks_fts f
                   JOIN kb_document_chunks c ON f.rowid = c.id
                   JOIN kb_documents d ON c.doc_id = d.id
                   WHERE kb_document_chunks_fts MATCH ?{suffix}
                   ORDER BY rank LIMIT ?""",
                [keyword] + params + [limit],
            )
            if rows:
                return _annotate_source_scope(rows)
        except Exception:
            pass
        rows = self._search_kb_chunks_like(
            keyword,
            limit=limit,
            category_id=category_id,
            doc_type=doc_type,
            scope=normalized_scope,
        )
        if rows:
            return _annotate_source_scope(rows)
        try:
            rows = self.db.query(
                f"""SELECT d.*, snippet(kb_documents_fts, 2, '<mark>', '</mark>', '...', 24) AS snippet
                   FROM kb_documents_fts f JOIN kb_documents d ON f.rowid = d.id
                   WHERE kb_documents_fts MATCH ?{suffix}
                   ORDER BY rank LIMIT ?""",
                [keyword] + params + [limit],
            )
            if rows:
                return _annotate_source_scope(rows)
        except Exception:
            pass
        like = f"%{keyword}%"
        where = "(title LIKE ? OR summary LIKE ? OR content LIKE ?)"
        like_params: list[Any] = [like, like, like]
        fallback_filters = []
        fallback_params: list[Any] = []
        if category_id is not None:
            fallback_filters.append("category_id = ?")
            fallback_params.append(category_id)
        if doc_type:
            fallback_filters.append("doc_type = ?")
            fallback_params.append(doc_type)
        fallback_source_filter, fallback_source_params = _scope_filter(normalized_scope, prefix="")
        if fallback_source_filter:
            fallback_filters.append(fallback_source_filter)
            fallback_params.extend(fallback_source_params)
        if fallback_filters:
            where += " AND " + " AND ".join(fallback_filters)
            like_params.extend(fallback_params)
        like_params.append(limit)
        rows = self.db.query(
            f"SELECT *, content AS snippet FROM kb_documents WHERE {where} ORDER BY updated_at DESC LIMIT ?",
            like_params,
        )
        return _annotate_source_scope(rows)

    def _search_kb_chunks_like(
        self,
        keyword: str,
        *,
        limit: int,
        category_id: int | None,
        doc_type: str | None,
        scope: str,
    ) -> list[dict[str, Any]]:
        like = f"%{keyword}%"
        where = "(d.title LIKE ? OR d.summary LIKE ? OR c.heading LIKE ? OR c.content LIKE ?)"
        params: list[Any] = [like, like, like, like]
        filters: list[str] = []
        if category_id is not None:
            filters.append("d.category_id = ?")
            params.append(category_id)
        if doc_type:
            filters.append("d.doc_type = ?")
            params.append(doc_type)
        source_filter, source_params = _scope_filter(scope, prefix="d.")
        if source_filter:
            filters.append(source_filter)
            params.extend(source_params)
        if filters:
            where += " AND " + " AND ".join(filters)
        params.append(limit)
        return self.db.query(
            f"""SELECT d.*,
                      c.id AS chunk_id,
                      c.chunk_index AS chunk_index,
                      c.heading AS chunk_heading,
                      c.content AS chunk_content,
                      c.content AS snippet
                 FROM kb_document_chunks c
                 JOIN kb_documents d ON c.doc_id = d.id
                WHERE {where}
                ORDER BY d.updated_at DESC, c.chunk_index ASC
                LIMIT ?""",
            params,
        )
