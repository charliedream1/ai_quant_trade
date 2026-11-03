"""Market quote routes."""

from fastapi import APIRouter, Query

from src.api.route_guards import ValidatedRoute
from src.api.schemas.common import ok
from src.engine.market import QuoteService

router = APIRouter(tags=["市场分析-行情"], route_class=ValidatedRoute)


@router.get("/market/indices")
def indices(refresh: bool = False):
    return ok(QuoteService().indices(refresh=refresh))


@router.get("/market/sectors")
def sectors(board: str = "industry", sort: str = "涨跌幅", limit: int = Query(20, ge=1, le=100)):
    return ok(QuoteService().sectors(board=board, sort=sort, limit=limit))


@router.get("/market/heatmap")
def heatmap(level: str = "industry", board: str | None = None, threshold: float = 0.0):
    return ok(QuoteService().heatmap(level=level, board=board, threshold=threshold))
