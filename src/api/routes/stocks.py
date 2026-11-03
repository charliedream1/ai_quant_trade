"""Stock detail routes."""

from fastapi import APIRouter, Query

from src.api.route_guards import ValidatedRoute
from src.api.schemas.common import ok
from src.engine.market import StockAnalyzer

router = APIRouter(tags=["市场分析-个股"], route_class=ValidatedRoute)


@router.get("/stocks/{symbol}/detail")
def detail(
    symbol: str, sections: str | None = None, kline_period: str = "daily", kline_count: int = Query(60, ge=1, le=240)
):
    return ok(
        StockAnalyzer().detail(
            symbol=symbol, sections=sections or "", kline_period=kline_period, kline_count=kline_count
        )
    )
