"""Quant paper search, favorites, and knowledge-base import."""

import json
from typing import Any
from uuid import uuid4

from src.core.file_storage import FileStorage
from src.core.kb_chunks import refresh_document_chunks
from src.core.kb_importer import parse_document_tags
from src.core.logger import get_logger
from src.core.repository import Repository, json_loads
from src.core.timeutil import utc_now_iso
from src.data import DataSourceManager


class PaperSearchService:
    def __init__(self, repo: Repository | None = None, data: DataSourceManager | None = None) -> None:
        self.repo = repo or Repository()
        self.data = data or DataSourceManager()
        self.log = get_logger("market.paper_search")

    def search(
        self,
        keyword: str,
        source: str | None = None,
        year_from: int | None = None,
        year_to: int | None = None,
        page: int = 1,
        page_size: int = 20,
        refresh: bool = False,
    ) -> dict[str, Any]:
        if not self.data.is_mock:
            self.repo.db.execute(
                "DELETE FROM papers WHERE url LIKE ?",
                ("https://example.local/%",),
            )
        local_count = self.repo.db.scalar("SELECT COUNT(*) AS cnt FROM papers") or 0
        if not local_count or refresh:
            now = utc_now_iso()
            for item in self.data.paper_search(keyword=keyword, year_from=year_from, year_to=year_to):
                if self.repo.db.scalar(
                    "SELECT COUNT(*) AS cnt FROM papers WHERE url = ?",
                    (item["url"],),
                ):
                    continue
                self.repo.insert(
                    "papers",
                    {
                        "title": item["title"],
                        "authors": json.dumps(item["authors"], ensure_ascii=False),
                        "abstract": item["abstract"],
                        "source": item["source"],
                        "url": item["url"],
                        "pdf_path": "",
                        "published_at": item["published_at"],
                        "is_favorite": 0,
                        "favorite_note": "",
                        "fetched_at": now,
                    },
                )
        where: list[str] = []
        params: list[Any] = []
        if keyword:
            where.append("(title LIKE ? OR abstract LIKE ?)")
            params.extend([f"%{keyword}%", f"%{keyword}%"])
        if source:
            where.append("source = ?")
            params.append(source)
        if year_from:
            where.append("published_at >= ?")
            params.append(f"{year_from}-01-01")
        if year_to:
            where.append("published_at <= ?")
            params.append(f"{year_to}-12-31")
        result = self.repo.page("papers", page, page_size, " AND ".join(where), params, order_by="published_at DESC")
        for item in result["items"]:
            item["authors"] = json.loads(item["authors"] or "[]")
            item["is_favorite"] = bool(item["is_favorite"])
        return result

    def favorite(self, paper_id: int, note: str = "") -> dict[str, Any]:
        row = self.repo.update("papers", paper_id, {"is_favorite": 1, "favorite_note": note})
        row["is_favorite"] = True
        return {"favorite_id": row["id"], "paper_id": row["id"], "favorited_at": utc_now_iso(), "note": note}

    def unfavorite(self, paper_id: int) -> None:
        self.repo.update("papers", paper_id, {"is_favorite": 0, "favorite_note": ""})

    def import_to_kb(self, paper_id: int, category_id: int | None = 0, tags: Any = None) -> dict[str, Any]:
        """Import paper metadata and abstract into the local knowledge base."""
        paper = self.repo.get("papers", paper_id)
        authors = _paper_authors(paper)
        content = _paper_markdown(paper, authors)
        tag_values = parse_document_tags(tags) or ["论文", "市场分析"]
        source_key = f"paper:{paper_id}"
        now = utc_now_iso()
        existing = self.repo.db.query_one("SELECT * FROM kb_documents WHERE source = ?", (source_key,))
        storage = FileStorage()
        relative_path = str(existing.get("file_path") or "") if existing else ""
        if not relative_path:
            filename = storage.safe_filename(f"{paper.get('title') or f'paper_{paper_id}'}_{uuid4().hex[:8]}", ".md")
            relative_path = f"knowledge/papers/{filename}"
        storage.write_text(relative_path, content)
        values = {
            "title": str(paper.get("title") or f"论文 {paper_id}"),
            "doc_type": "论文",
            "category_id": int(category_id or 0),
            "summary": str(paper.get("abstract") or "")[:200],
            "content": content,
            "file_path": relative_path,
            "source": source_key,
            "tags": tag_values,
            "status": "ready",
            "updated_at": now,
        }
        if existing:
            row = self.repo.update("kb_documents", int(existing["id"]), values)
            imported = False
        else:
            row = self.repo.insert("kb_documents", {**values, "imported_at": now})
            imported = True
        row["doc_id"] = row["id"]
        row["tags"] = json_loads(row.get("tags"), [])
        row["paper_id"] = paper_id
        row["imported"] = imported
        row["chunk_count"] = refresh_document_chunks(
            self.repo,
            int(row["id"]),
            title=str(row.get("title") or ""),
            content=content,
        )
        self.log.info(
            "论文已导入知识库：paper_id={} doc_id={} imported={} chunks={}",
            paper_id,
            row["doc_id"],
            imported,
            row["chunk_count"],
        )
        return row


def _paper_authors(row: dict[str, Any]) -> list[str]:
    authors = json_loads(row.get("authors"), [])
    if isinstance(authors, list):
        return [str(item).strip() for item in authors if str(item).strip()]
    if authors:
        return [str(authors).strip()]
    return []


def _paper_markdown(row: dict[str, Any], authors: list[str]) -> str:
    url = str(row.get("url") or "").strip()
    pdf_path = str(row.get("pdf_path") or "").strip()
    lines = [
        f"# {row.get('title') or '未命名论文'}",
        "",
        f"- 作者：{', '.join(authors) if authors else '-'}",
        f"- 来源：{row.get('source') or '-'}",
        f"- 发布时间：{row.get('published_at') or '-'}",
        f"- 原文链接：{url or '-'}",
        f"- PDF路径：{pdf_path or '-'}",
        "",
        "## 摘要",
        "",
        str(row.get("abstract") or "暂无摘要").strip(),
    ]
    return "\n".join(lines).strip() + "\n"
