"""Model market analysis report routes."""

from typing import Annotated, Any

from fastapi import APIRouter, Body, Query

from src.api.route_guards import ValidatedRoute
from src.api.schemas.common import ok
from src.engine.market import MarketReportGenerator

router = APIRouter(tags=["市场分析-模型报告"], route_class=ValidatedRoute)


@router.post("/market-analysis-reports")
def create(payload: Annotated[dict[str, Any], Body(default_factory=dict)]):
    return ok(MarketReportGenerator().create(payload or {}))


@router.get("/market-analysis-reports")
def list_reports(
    report_type: str | None = None,
    status: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    return ok(MarketReportGenerator().list(page=page, page_size=page_size, report_type=report_type, status=status))


@router.get("/market-analysis-reports/{report_id}")
def detail(report_id: int):
    return ok(MarketReportGenerator().detail(report_id))
