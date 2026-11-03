"""Knowledge document chunking helpers."""

from __future__ import annotations

import re
from typing import Any

from src.core.database import Database
from src.core.repository import Repository
from src.core.timeutil import utc_now_iso
from src.knowledge.config import chunk_length
from src.knowledge.files import KnowledgeFiles

DEFAULT_CHUNK_CHARS = chunk_length()
DEFAULT_OVERLAP_CHARS = 160
MIN_CHUNK_CHARS = 120
BACKFILL_LIMIT = 100


def split_knowledge_chunks(
    content: str,
    *,
    title: str = "",
    max_chars: int = DEFAULT_CHUNK_CHARS,
    overlap_chars: int = DEFAULT_OVERLAP_CHARS,
) -> list[dict[str, Any]]:
    """Split Markdown-like text into stable chunks for FTS/RAG retrieval."""
    text = _normalize_content(content)
    if not text:
        return []
    max_chars = max(max_chars, MIN_CHUNK_CHARS)
    overlap_chars = min(max(overlap_chars, 0), max_chars // 3)
    paragraphs = _paragraphs(text)
    chunks: list[dict[str, Any]] = []
    current_parts: list[str] = []
    current_heading = title.strip() or "正文"

    def flush() -> None:
        nonlocal current_parts
        chunk_text = "\n\n".join(part for part in current_parts if part.strip()).strip()
        if chunk_text:
            chunks.append(
                {
                    "chunk_index": len(chunks),
                    "heading": current_heading,
                    "content": chunk_text,
                    "char_count": len(chunk_text),
                }
            )
        current_parts = []

    for paragraph in paragraphs:
        heading = _heading(paragraph)
        if heading:
            if current_parts:
                flush()
            current_heading = heading
        if len(paragraph) > max_chars:
            flush()
            for piece in _split_long_text(paragraph, max_chars=max_chars, overlap_chars=overlap_chars):
                current_parts = [piece]
                flush()
            continue
        candidate_len = _joined_len([*current_parts, paragraph])
        if current_parts and candidate_len > max_chars:
            overlap = _tail_overlap(current_parts, overlap_chars)
            flush()
            if overlap:
                current_parts.append(overlap)
        current_parts.append(paragraph)
    flush()
    return chunks


def refresh_document_chunks(
    repo: Repository,
    doc_id: int,
    *,
    title: str | None = None,
    content: str | None = None,
) -> int:
    row = repo.get("kb_documents", doc_id)
    document_title = title if title is not None else str(row.get("title") or "")
    document_content = content if content is not None else str(row.get("content") or "")
    chunks = split_knowledge_chunks(
        document_content, title=document_title, max_chars=chunk_length(row.get("chunk_chars")), overlap_chars=0
    )
    KnowledgeFiles(repo).write_document({**row, "content": document_content, "title": document_title}, chunks)
    now = utc_now_iso()
    repo.db.execute("DELETE FROM kb_document_chunks WHERE doc_id = ?", (doc_id,))
    if not chunks:
        return 0
    repo.db.executemany(
        """INSERT INTO kb_document_chunks
           (doc_id, chunk_index, heading, content, char_count, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        [
            (
                doc_id,
                int(chunk["chunk_index"]),
                str(chunk["heading"]),
                str(chunk["content"]),
                int(chunk["char_count"]),
                now,
                now,
            )
            for chunk in chunks
        ],
    )
    return len(chunks)


def ensure_document_chunks(db: Database, *, limit: int = BACKFILL_LIMIT) -> int:
    """Backfill chunks for legacy documents that predate the chunk table."""
    rows = db.query(
        """SELECT d.id
             FROM kb_documents d
            WHERE COALESCE(d.content, '') <> ''
              AND NOT EXISTS (
                    SELECT 1 FROM kb_document_chunks c WHERE c.doc_id = d.id
                  )
            ORDER BY d.updated_at DESC, d.id DESC
            LIMIT ?""",
        (limit,),
    )
    if not rows:
        return 0
    repo = Repository(db)
    created = 0
    for row in rows:
        created += refresh_document_chunks(repo, int(row["id"]))
    return created


def _normalize_content(content: str) -> str:
    return re.sub(r"\n{3,}", "\n\n", str(content or "").replace("\r\n", "\n").replace("\r", "\n")).strip()


def _paragraphs(text: str) -> list[str]:
    # Blank lines and hash-prefixed code inside fences are not section boundaries.
    parts: list[str] = []
    current: list[str] = []
    fenced = False
    for line in text.splitlines():
        heading = not fenced and re.match(r"^#{1,6}\s+", line)
        if not fenced and (not line.strip() or heading) and current:
            parts.append("\n".join(current).strip())
            current = []
        if line.strip() or fenced:
            current.append(line)
        if re.match(r"^\s*(```|~~~)", line):
            fenced = not fenced
        if heading:
            parts.append("\n".join(current))
            current = []
    if current:
        parts.append("\n".join(current).strip())
    return parts or [text]


def _heading(paragraph: str) -> str:
    first_line = paragraph.splitlines()[0].strip()
    if first_line.startswith("#"):
        return first_line.lstrip("#").strip()[:120] or "正文"
    return ""


def _joined_len(parts: list[str]) -> int:
    return len("\n\n".join(parts))


def _tail_overlap(parts: list[str], overlap_chars: int) -> str:
    if overlap_chars <= 0:
        return ""
    text = "\n\n".join(parts).strip()
    if len(text) <= overlap_chars:
        return text
    return text[-overlap_chars:].lstrip()


def _split_long_text(text: str, *, max_chars: int, overlap_chars: int) -> list[str]:
    pieces: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        piece = text[start:end].strip()
        if piece:
            pieces.append(piece)
        if end >= len(text):
            break
        start = max(end - overlap_chars, start + 1)
    return pieces
