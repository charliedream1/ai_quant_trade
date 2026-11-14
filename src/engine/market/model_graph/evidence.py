"""Authorized original passages and public reads, never model-supplied source text."""

import re
from datetime import date, timedelta
from hashlib import sha256
from urllib.parse import parse_qs, unquote, urlsplit

from bs4 import BeautifulSoup

from src.core.kb_importer import parse_document_bytes
from src.core.network_policy import network_session
from src.core.repository import Repository
from src.core.timeutil import utc_now_iso
from src.knowledge.download import download_document
from src.knowledge.files import KnowledgeFiles
from src.knowledge.sag2_retrieval import SAG2Retrieval

from .config import config


class EvidenceCorpus:
    def __init__(self, request):
        self.request = request
        self.sources = []
        self.candidates = []

    def add(self, title, text, *, url="", published_at=None, provenance="public_original", document_id=None):
        limits = config()["limits"]
        if len(self.sources) >= limits["sources"]:
            raise ValueError("Graph source budget exhausted")
        if sum(len(row["text"]) for row in self.sources) >= limits["total_source_chars"]:
            raise ValueError("Graph source-text budget exhausted")
        if published_at and published_at[:10] > self.request["as_of"]:
            raise ValueError("Source publication is after the requested as-of date")
        if (
            published_at
            and published_at[:10]
            < (
                date.fromisoformat(self.request["as_of"])
                - timedelta(days=self.request.get("lookback_days", limits["lookback_days"]))
            ).isoformat()
        ):
            raise ValueError("Source publication is outside the selected lookback")
        digest = sha256(text.encode("utf-8")).hexdigest()
        existing = next((row for row in self.sources if row["sha256"] == digest), None)
        if existing:
            return existing
        maximum = min(
            limits["source_chars"], limits["total_source_chars"] - sum(len(row["text"]) for row in self.sources)
        )
        row = {
            "id": f"E{len(self.sources) + 1}",
            "title": title,
            "text": text[:maximum],
            "sha256": digest,
            "url": url,
            "published_at": published_at,
            "first_seen_at": utc_now_iso(),
            "coverage": "excerpt" if len(text) > maximum else "parsed_original",
            "provenance": provenance,
            "document_id": document_id,
            "date_verified": bool(published_at),
        }
        row["quote_spans"] = quote_spans(row["id"], row["text"], limits["quote_span_chars"])
        self.sources.append(row)
        return row

    def prompt_sources(self):
        # Span text replaces the duplicated full original in prompts; storage retains both.
        return [{key: value for key, value in row.items() if key != "text"} for row in self.sources]

    def load_local(self):
        library = self.request.get("library_name")
        if not library:
            return
        documents = KnowledgeFiles(Repository()).documents(library, session_id=self.request.get("session_id", ""))
        selected = self.request.get("document_ids") or []
        if selected and set(selected) - {row["id"] for row in documents}:
            raise ValueError("Graph document is outside the selected library/session")
        if not selected and documents:
            passages = SAG2Retrieval(Repository()).search(
                self.request["company_name"] + " " + self.request["symbol"],
                documents,
                "bm25",
                config()["limits"]["sources"],
                rounds=1,
            )[0]
            for passage in passages:
                self.add(
                    passage["title"],
                    passage["chunk_content"],
                    provenance="authorized_local_passage",
                    document_id=passage["id"],
                )
            return
        for row in documents:
            if selected and row["id"] not in selected:
                continue
            self.add(row["title"], row["content"], provenance="authorized_local_document", document_id=row["id"])

    def read(self, url):
        if len(url) > config()["limits"]["url_chars"]:
            raise ValueError("Graph source URL exceeds budget")
        name, content, final_url = download_document(url)
        parsed = parse_document_bytes(name, content)
        published = None
        if name.lower().endswith((".html", ".htm")):
            soup = BeautifulSoup(content, "html.parser")
            metadata = soup.find("meta", attrs={"property": "article:published_time"}) or next(
                (
                    soup.find("meta", attrs={"name": key})
                    for key in ("pubdate", "publishdate", "date")
                    if soup.find("meta", attrs={"name": key})
                ),
                None,
            )
            if metadata and metadata.get("content"):
                try:
                    published = date.fromisoformat(str(metadata["content"])[:10]).isoformat()
                except ValueError:
                    pass
        return self.add(name, parsed["content"], url=final_url, published_at=published)

    def search(self, query):
        # Search discovers public candidates; snippets never enter the evidence corpus.
        policy = config()["search"]
        with network_session(public_only=True) as session:
            response = session.get(policy["url"], params={"q": query}, timeout=policy["timeout_seconds"], stream=True)
            try:
                response.raise_for_status()
                content = bytearray()
                for chunk in response.iter_content(chunk_size=policy["chunk_bytes"]):
                    content.extend(chunk)
                    if len(content) > policy["max_response_bytes"]:
                        raise ValueError("Graph search response exceeds the configured limit")
            finally:
                response.close()
        soup = BeautifulSoup(bytes(content), "html.parser")
        rows = []
        for link in soup.select(config()["search"]["selector"])[: config()["limits"]["sources"]]:
            url = str(link.get("href") or "")
            values = parse_qs(urlsplit(url).query)
            if values.get("uddg"):
                url = unquote(values["uddg"][0])
            if url.startswith("//"):
                url = "https:" + url
            if urlsplit(url).scheme in {"http", "https"}:
                rows.append({"title": link.get_text(" ", strip=True), "url": url, "evidence": False})
        self.candidates.extend(rows)
        return rows


def quote_spans(identifier, text, maximum):
    """Partition frozen text without rewriting punctuation or PDF word boundaries."""
    spans: dict[str, str] = {}
    start = 0
    while start < len(text):
        end = min(start + maximum, len(text))
        if end < len(text):
            boundaries = list(re.finditer(r"\n\s*\n|[.!?。！？]\s+", text[start:end]))
            if boundaries and boundaries[-1].end() >= maximum // 2:
                end = start + boundaries[-1].end()
        spans[f"{identifier}:{len(spans) + 1}"] = text[start:end]
        start = end
    return spans
