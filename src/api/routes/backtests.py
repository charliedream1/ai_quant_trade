"""Backtest routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Query

from src.api.route_guards import ValidatedRoute
from src.api.schemas.common import ok
from src.engine.backtest import BacktestRunner

router = APIRouter(tags=["策略仿真-回测"], route_class=ValidatedRoute)
BACKTEST_BODY = Body(...)
PAGE_QUERY = Query(1, ge=1)
PAGE_SIZE_QUERY = Query(20, ge=1, le=100)


@router.get("/backtest-engines")
def engines():
    return ok(BacktestRunner().engines())


@router.post("/backtests")
def create(payload: dict[str, Any] = BACKTEST_BODY):
    return ok(BacktestRunner().create(payload))


@router.get("/backtests")
def list_tasks(
    strategy_id: int | None = None,
    status: str | None = None,
    page: int = PAGE_QUERY,
    page_size: int = PAGE_SIZE_QUERY,
):
    return ok(BacktestRunner().list(strategy_id=strategy_id, status=status, page=page, page_size=page_size))


@router.get("/backtests/{task_id}")
def detail(task_id: int):
    return ok(BacktestRunner().detail(task_id))


@router.delete("/backtests/{task_id}")
def delete(task_id: int):
    BacktestRunner().delete(task_id)
    return ok(None)


@router.get("/backtests/{task_id}/performance")
def performance(task_id: int):
    return ok(BacktestRunner().performance(task_id))


@router.get("/backtests/{task_id}/equity-curve")
def equity_curve(task_id: int):
    return ok(BacktestRunner().equity_curve(task_id))


@router.get("/backtests/{task_id}/trades")
def trades(task_id: int, page: int = PAGE_QUERY, page_size: int = PAGE_SIZE_QUERY):
    return ok(BacktestRunner().trades(task_id, page=page, page_size=page_size))


@router.get("/backtests/{task_id}/attribution")
def attribution(task_id: int):
    return ok(BacktestRunner().attribution(task_id))
