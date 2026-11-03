"""Explicit full-document imports for research reports and papers."""

from typing import Any
from urllib.parse import urlsplit, urlunsplit

from src.core.exceptions import BusinessError, ErrorCode
from src.core.repository import Repository
from src.data import DataSourceManager

from .config import knowledge_config
from .download import import_url


def import_research_document(
    kind: str, identifier: int, library: str | None = None, chunk_chars: int | None = None
) -> dict[str, Any]:
    if kind == "paper":
        row = Repository().get("papers", identifier)
    else:
        row = DataSourceManager().report_detail(identifier)
    if not row:
        raise BusinessError(ErrorCode.NOT_FOUND, "研报或论文不存在")
    url = str(row.get("pdf_url") or row.get("url") or "")
    if not url:
        raise BusinessError(ErrorCode.INVALID_PARAM, "当前资料没有可下载的原文地址")
    if kind == "paper":
        parts = urlsplit(url)
        for rule in knowledge_config()["paper_download_rules"]:
            if parts.hostname in rule["hosts"] and parts.path.startswith(rule["from_path"]):
                url = urlunsplit(
                    ("https", parts.netloc, parts.path.replace(rule["from_path"], rule["to_path"], 1), "", "")
                )
                break
    result = import_url(
        url,
        library=library,
        title=row["title"],
        chunk_chars=chunk_chars,
        source=f"{kind}:full:{identifier}",
        require_fulltext=kind == "paper",
        doc_type="论文" if kind == "paper" else "研报",
    )
    return {**result, "research_id": identifier, "research_kind": kind}
