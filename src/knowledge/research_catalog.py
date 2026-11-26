"""Build an immutable, source-backed list of research documents."""

import hashlib
import json
import re
from collections.abc import Callable
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from src.core.page_work import check
from src.core.repository import Repository
from src.data import DataSourceManager, resolve_security_symbol

from .research_classification import policy


def publication_year(value):
    match = re.match(r"^([0-9]{4})(?:$|[-/T])", str(value or ""))
    limits = policy()["limits"]
    if match and limits["min_year"] <= int(match[1]) <= limits["max_year"]:
        return int(match[1])
    return None


def _identity(kind, row, url):
    if row.get("doi"):
        return re.sub(r"^https?://(?:dx\.)?doi\.org/", "", str(row["doi"]).lower())
    parts = urlsplit(url)
    path = parts.path.removesuffix(".pdf")
    if parts.hostname in {"arxiv.org", "export.arxiv.org", "www.arxiv.org"}:
        path = re.sub(r"^/(?:abs|pdf)/", "", path)
        return f"arxiv:{path}"
    return f"{kind}:{urlunsplit((parts.scheme, parts.netloc, parts.path, parts.query, ''))}"


def _manifest(kind, row):
    url = str(row.get("pdf_url") or row.get("url") or "")
    origin = str(row.get("url") or url)
    if not origin:
        identity = (kind, row.get("source", ""), row.get("id"), row.get("title"))
        key = json.dumps(identity, ensure_ascii=False)
    else:
        key = _identity(kind, row, origin)
    institutions = row.get("institutions") or ([row["org"]] if row.get("org") else [])
    return {
        "key": hashlib.sha256(key.encode()).hexdigest(),
        "kind": kind,
        "url": url,
        "landing_url": str(row.get("landing_url") or ""),
        "title": str(row.get("title") or ""),
        "abstract": str(row.get("abstract") or row.get("summary") or "")[: policy()["limits"]["text_chars"]],
        "provider": str(row.get("source") or ""),
        "published": row.get("publish_date") or row.get("published_at") or "",
        "institutions": institutions,
    }


def collect(kind, filters):
    if kind not in {"report", "paper"}:
        raise ValueError("Unknown research document type")
    keyword = str(filters[0] or "").strip()
    data = DataSourceManager()
    size, pages = (policy()["limits"][name] for name in ("page_size", "pages"))
    filter_count = 2 if kind == "report" else 4
    window = int(filters[filter_count] or 1) if len(filters) > filter_count else 1
    if window < 1:
        raise ValueError("Source window must be positive")
    first_page = (window - 1) * pages
    get_page: Callable[[int], list[dict[str, Any]]] | None = None
    local = []
    if kind == "report":
        symbol = str(filters[1] or "").strip()
        resolved = resolve_security_symbol(symbol, market=data.market) if symbol else ""
        if symbol and not resolved:
            raise ValueError("Unknown security code or name")
        report_loader = getattr(data, "research_report_page", None)
        get_page = (lambda page: report_loader(resolved, page + 1, size)) if report_loader else None
        if not report_loader and window == 1:
            local = data.reports(keyword=keyword or None, symbol=resolved or None)

        def matching(row):
            return (
                not keyword
                or keyword.casefold()
                in " ".join(str(row.get(key) or "") for key in ("title", "org", "analyst")).casefold()
            )
    else:
        source, start, end = filters[1:4]
        start, end = int(start) if start else None, int(end) if end else None
        if start and end and start > end:
            raise ValueError("Start year must precede end year")
        paper_loader = getattr(data, "research_paper_page", None)
        get_page = (
            (lambda page: paper_loader(keyword, page * size, size))
            if paper_loader and source in (None, "", "arXiv")
            else None
        )
        local = Repository().db.query(
            """SELECT * FROM papers WHERE (?='' OR source=?)
               AND (?='' OR instr(lower(title),lower(?))>0 OR instr(lower(abstract),lower(?))>0)
               AND (? IS NULL OR published_at>=?) AND (? IS NULL OR published_at<=?)
               AND (? OR url NOT LIKE 'https://example.local/%')
               ORDER BY published_at DESC, id DESC LIMIT ? OFFSET ?""",
            (
                source or "",
                source or "",
                keyword,
                keyword,
                keyword,
                start,
                f"{start}-01-01",
                end,
                f"{end}-12-31",
                data.is_mock,
                size * pages + 1,
                first_page * size,
            ),
        )
        if not get_page and data.is_mock and not local and window == 1:
            local = data.paper_search(keyword=keyword, year_from=start, year_to=end)

        def matching(row):
            year = publication_year(row.get("published_at"))
            return (
                (not source or source == row.get("source"))
                and (not start or year is not None and year >= start)
                and (not end or year is not None and year <= end)
            )

    gathered: dict[str, dict[str, Any]] = {}
    complete = get_page is not None
    upstream_ids: set[str] = set()
    reason = "source_window" if get_page is None else ""
    if get_page:
        for page in range(first_page, first_page + pages):
            check()
            try:
                rows = get_page(page)
            except (ValueError, OSError, RuntimeError):
                if not gathered and not local:
                    raise
                complete, reason = False, "source_error"
                break
            manifests = [_manifest(kind, row) for row in rows]
            ids = {item["key"] for item in manifests}
            if ids and ids <= upstream_ids:
                complete, reason = False, "repeated_source_page"
                break
            upstream_ids.update(ids)
            for row, item in zip(rows, manifests, strict=True):
                if matching(row):
                    gathered[item["key"]] = item
            if len(rows) < size:
                break
        else:
            complete, reason = False, "page_limit"
    if len(local) > size * pages:
        complete = False
        reason = reason or "result_limit"
    for row in local[: size * pages]:
        if matching(row):
            item = _manifest(kind, row)
            gathered.setdefault(item["key"], item)
    scope = {
        "kind": kind,
        "market": data.market,
        "filters": filters,
        "complete": complete,
        "reason": reason,
        "window": window,
    }
    return list(gathered.values()), scope
