"""Research report routes."""

from typing import Annotated, Any

from fastapi import APIRouter, Body, Query

from src.api.route_guards import ValidatedRoute
from src.api.schemas.common import ok
from src.core.exceptions import BusinessError, ErrorCode
from src.data import DataSourceManager
from src.knowledge.research_import import import_research_document

router = APIRouter(tags=["市场分析-研报"], route_class=ValidatedRoute)


@router.post("/reports/import")
def import_report(payload: Annotated[dict[str, Any], Body()]):
    return ok(
        import_research_document(
            "report", int(payload["report_id"]), payload.get("library_name"), payload.get("chunk_chars")
        )
    )


@router.get("/reports")
def reports(
    keyword: str | None = None,
    symbol: str | None = None,
    org: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    items = DataSourceManager().reports(keyword=keyword, symbol=symbol)
    if org:
        items = [item for item in items if item["org"] == org]
    start = (page - 1) * page_size
    return ok({"items": items[start : start + page_size], "page": page, "page_size": page_size, "total": len(items)})


@router.get("/reports/{report_id}")
def report_detail(report_id: int, include_body: bool = True):
    item = DataSourceManager().report_detail(report_id)
    if not item:
        raise BusinessError(ErrorCode.NOT_FOUND, "研报不存在")
    if not include_body:
        item.pop("body", None)
    return ok(item)
