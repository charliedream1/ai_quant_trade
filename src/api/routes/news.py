"""News routes."""

from fastapi import APIRouter, Query

from src.api.route_guards import ValidatedRoute
from src.api.schemas.common import ok
from src.engine.market import NewsAggregator

router = APIRouter(tags=["市场分析-新闻"], route_class=ValidatedRoute)


@router.get("/news")
def list_news(
    category: str | None = None,
    keyword: str | None = None,
    source: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    refresh: bool = False,
):
    return ok(NewsAggregator().list_news(category, keyword, source, page, page_size, refresh=refresh))


@router.get("/news/keyword-cloud")
def keyword_cloud(scope: str = "day", category: str | None = None, top_n: int = Query(50, ge=1, le=200)):
    return ok(NewsAggregator().keyword_cloud(scope, category, top_n))
