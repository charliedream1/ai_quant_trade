"""Watchlist routes."""

from typing import Annotated, Any

from fastapi import APIRouter, Body

from src.api.route_guards import ValidatedRoute
from src.api.schemas.common import ok
from src.engine.market import QuoteService

router = APIRouter(tags=["市场分析-自选"], route_class=ValidatedRoute)


@router.get("/watchlist/groups")
def groups():
    return ok(QuoteService().list_watchlist_groups())


@router.post("/watchlist/groups")
def create_group(payload: Annotated[dict[str, Any], Body()]):
    return ok(QuoteService().create_group(payload["name"], int(payload.get("sort_order") or 0)))


@router.put("/watchlist/groups/{group_id}")
def update_group(group_id: int, payload: Annotated[dict[str, Any], Body()]):
    values = {k: v for k, v in payload.items() if k in ("name", "sort_order")}
    return ok(QuoteService().update_group(group_id, values))


@router.delete("/watchlist/groups/{group_id}")
def delete_group(group_id: int, force: bool = False):
    QuoteService().delete_group(group_id, force=force)
    return ok(None)


@router.get("/watchlist/quotes")
def watchlist_quotes(group_id: int | None = None):
    return ok(QuoteService().watchlist_quotes(group_id))


@router.post("/watchlist/groups/{group_id}/symbols")
def add_symbols(group_id: int, payload: Annotated[dict[str, Any], Body()]):
    return ok(QuoteService().add_symbols(group_id, payload.get("symbols") or []))


@router.delete("/watchlist/groups/{group_id}/symbols/{symbol}")
def remove_symbol(group_id: int, symbol: str):
    QuoteService().remove_symbol(group_id, symbol)
    return ok(None)
