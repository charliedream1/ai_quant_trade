"""Bounded public-document download using the project's pinned HTTP transport."""

import ipaddress
import socket
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urljoin, urlsplit

from bs4 import BeautifulSoup

from src.core.exceptions import BusinessError, ErrorCode
from src.core.kb_importer import import_uploaded_document
from src.core.network_policy import network_session, validate_url
from src.core.repository import Repository

from .config import knowledge_config, library_name


def public_url(url: str) -> None:
    parsed, _ = validate_url(url, resolve=True)
    addresses = socket.getaddrinfo(
        parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80), type=socket.SOCK_STREAM
    )
    if any(not ipaddress.ip_address(item[4][0]).is_global for item in addresses):
        raise BusinessError(ErrorCode.INVALID_PARAM, "网页下载仅允许公共网络地址")


def download_document(url: str) -> tuple[str, bytes, str]:
    policy = knowledge_config()
    current = str(url).strip()
    with network_session(public_only=True) as session:
        for _ in range(policy["download"]["max_redirects"] + 1):
            public_url(current)
            with session.get(
                current, stream=True, allow_redirects=False, timeout=policy["download"]["timeout_seconds"]
            ) as response:
                if response.is_redirect:
                    current = urljoin(current, response.headers["Location"])
                    continue
                response.raise_for_status()
                content = bytearray()
                for block in response.iter_content(policy["download"]["block_bytes"]):
                    content.extend(block)
                    if len(content) > policy["max_upload_bytes"]:
                        raise BusinessError(ErrorCode.INVALID_PARAM, "下载文档超过大小上限")
                name = Path(unquote(urlsplit(current).path)).name or "webpage.html"
                mime = response.headers.get("Content-Type", "").split(";")[0].lower()
                if bytes(content).lstrip().startswith(b"%PDF-"):
                    name = Path(name).stem + ".pdf"
                elif mime in {"text/html", "application/xhtml+xml"}:
                    name = Path(name).stem + ".html"
                return name, bytes(content), current
    raise BusinessError(ErrorCode.INVALID_PARAM, "网页重定向次数超限")


def import_url(
    url: str,
    *,
    library: str | None = None,
    title: str | None = None,
    chunk_chars: int | None = None,
    source: str | None = None,
    repo: Repository | None = None,
    require_fulltext: bool = False,
    **options: Any,
) -> dict[str, Any]:
    repo = repo or Repository()
    name = library_name(library)
    key = source or url
    existing = repo.db.query_one(
        "SELECT * FROM kb_documents WHERE source = ? AND library_name = ? AND attachment_session = ''", (key, name)
    )
    if existing:
        return {**existing, "doc_id": existing["id"], "imported": False}
    filename, content, final_url = download_document(url)
    if require_fulltext and Path(filename).suffix.lower() in {".html", ".htm"}:
        soup = BeautifulSoup(content, "html.parser")
        candidate = soup.find("meta", attrs={"name": "citation_pdf_url"})
        href = candidate.get("content") if candidate else None
        if not href:
            link = soup.find("link", attrs={"type": "application/pdf"})
            href = link.get("href") if link else None
        if not isinstance(href, str):
            raise BusinessError(ErrorCode.PARSE_ERROR, "未找到可下载的论文全文，不将摘要页作为全文入库")
        filename, content, final_url = download_document(urljoin(final_url, href))
        if Path(filename).suffix.lower() in {".html", ".htm"}:
            raise BusinessError(ErrorCode.PARSE_ERROR, "全文地址返回网页，未导入论文全文")
    row = import_uploaded_document(
        filename=filename,
        content_bytes=content,
        title=title,
        library=name,
        chunk_chars=chunk_chars,
        source=key,
        repo=repo,
        **options,
    )
    return {**row, "imported": True, "download_url": final_url}
