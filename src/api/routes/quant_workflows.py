"""Quant workflow routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Query

from src.api.route_guards import ValidatedRoute
from src.api.schemas.common import ok
from src.engine.research import QuantWorkflowService

router = APIRouter(tags=["量化闭环"], route_class=ValidatedRoute)
RUN_BODY = Body(default_factory=dict)
PAGE_QUERY = Query(1, ge=1)
PAGE_SIZE_QUERY = Query(20, ge=1, le=100)


@router.get("/quant-workflows/modes")
def modes():
    return ok(QuantWorkflowService().modes())


@router.get("/quant-workflows/sops")
def sops(mode: str | None = None):
    return ok(QuantWorkflowService().sops(mode))


@router.get("/quant-workflows/snapshot")
def snapshot(
    mode: str = Query("simulation"),
    sop_id: str | None = None,
    strategy_id: int | None = None,
    backtest_id: int | None = None,
    account_id: int | None = None,
    live_run_id: int | None = None,
):
    return ok(
        QuantWorkflowService().snapshot(
            mode=mode,
            sop_id=sop_id,
            strategy_id=strategy_id,
            backtest_id=backtest_id,
            account_id=account_id,
            live_run_id=live_run_id,
        )
    )


@router.post("/quant-workflows/runs")
def create_run(payload: dict[str, Any] = RUN_BODY):
    return ok(QuantWorkflowService().create_run(payload))


@router.get("/quant-workflows/runs")
def list_runs(
    mode: str | None = None,
    page: int = PAGE_QUERY,
    page_size: int = PAGE_SIZE_QUERY,
):
    return ok(QuantWorkflowService().list_runs(mode=mode, page=page, page_size=page_size))


@router.get("/quant-workflows/runs/{run_id}")
def detail(run_id: int):
    return ok(QuantWorkflowService().detail(run_id))
