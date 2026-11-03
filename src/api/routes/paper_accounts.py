"""Paper trading routes."""

from typing import Annotated, Any

from fastapi import APIRouter, Body, Query

from src.api.route_guards import ValidatedRoute
from src.api.schemas.common import ok
from src.engine.paper import PaperAccountService

router = APIRouter(tags=["策略仿真-模拟盘"], route_class=ValidatedRoute)
PAGE_QUERY = Query(1, ge=1)
PAGE_SIZE_QUERY = Query(20, ge=1, le=100)


@router.get("/paper-accounts")
def list_accounts(page: int = PAGE_QUERY, page_size: int = PAGE_SIZE_QUERY):
    return ok(PaperAccountService().list(page, page_size))


@router.post("/paper-accounts")
def create(payload: Annotated[dict[str, Any], Body()]):
    return ok(PaperAccountService().create(payload))


@router.post("/paper-accounts/{account_id}/reset")
def reset(account_id: int, payload: Annotated[dict[str, Any] | None, Body()] = None):
    return ok(PaperAccountService().reset(account_id, payload.get("initial_capital") if payload else None))


@router.get("/paper-accounts/{account_id}/overview")
def overview(account_id: int):
    return ok(PaperAccountService().overview(account_id))


@router.post("/paper-accounts/{account_id}/orders")
def order(account_id: int, payload: Annotated[dict[str, Any], Body()]):
    return ok(PaperAccountService().order(account_id, payload))


@router.post("/paper-accounts/{account_id}/orders/match")
def match_orders(account_id: int):
    return ok(PaperAccountService().match_orders(account_id))


@router.delete("/paper-accounts/{account_id}/orders/{order_id}")
def cancel(account_id: int, order_id: int):
    return ok(PaperAccountService().cancel(account_id, order_id))


@router.get("/paper-accounts/{account_id}/orders")
def orders(
    account_id: int, status: str | None = None, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100)
):
    return ok(PaperAccountService().orders(account_id, status=status, page=page, page_size=page_size))


@router.get("/paper-accounts/{account_id}/fills")
def fills(
    account_id: int, symbol: str | None = None, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100)
):
    return ok(PaperAccountService().fills(account_id, symbol=symbol, page=page, page_size=page_size))


@router.get("/paper-accounts/{account_id}/positions")
def positions(account_id: int):
    return ok(PaperAccountService().positions(account_id))


@router.get("/paper-accounts/{account_id}/equity-history")
def equity_history(account_id: int, start_date: str | None = None, end_date: str | None = None):
    return ok(PaperAccountService().equity_history(account_id))
