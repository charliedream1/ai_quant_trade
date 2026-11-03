"""Quant paper routes."""

from typing import Annotated, Any

from fastapi import APIRouter, Body, Query

from src.api.route_guards import ValidatedRoute
from src.api.schemas.common import ok
from src.engine.market import PaperSearchService
from src.knowledge.research_import import import_research_document

router = APIRouter(tags=["市场分析-论文"], route_class=ValidatedRoute)


@router.get("/papers/search")
def search(
    keyword: str = "",
    source: str | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
    sort: str = "relevance",
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    refresh: bool = False,
):
    return ok(
        PaperSearchService().search(
            keyword=keyword,
            source=source,
            year_from=year_from,
            year_to=year_to,
            page=page,
            page_size=page_size,
            refresh=refresh,
        )
    )


@router.post("/papers/favorites")
def favorite(payload: Annotated[dict[str, Any], Body()]):
    return ok(PaperSearchService().favorite(int(payload["paper_id"]), payload.get("note") or ""))


@router.delete("/papers/favorites/{paper_id}")
def unfavorite(paper_id: int):
    PaperSearchService().unfavorite(paper_id)
    return ok(None)


@router.post("/papers/import")
def import_to_kb(payload: Annotated[dict[str, Any], Body()]):
    if payload.get("download_fulltext"):
        return ok(
            import_research_document(
                "paper", int(payload["paper_id"]), payload.get("library_name"), payload.get("chunk_chars")
            )
        )
    return ok(
        PaperSearchService().import_to_kb(
            int(payload["paper_id"]),
            category_id=int(payload.get("category_id") or 0),
            tags=payload.get("tags"),
        )
    )
