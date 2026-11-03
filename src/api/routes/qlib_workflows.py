"""Qlib workflow configuration and run routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Query

from src.api.route_guards import ValidatedRoute
from src.api.schemas.common import ok
from src.engine.research import QlibWorkflowService

router = APIRouter(tags=["投研-Qlib实验"], route_class=ValidatedRoute)
QLIB_BODY = Body(default={})
PAGE_QUERY = Query(1, ge=1)
PAGE_SIZE_QUERY = Query(20, ge=1, le=100)


@router.get("/qlib-workflows/status")
def status():
    return ok(QlibWorkflowService().status())


@router.post("/qlib-workflows/runs")
def create_run(payload: dict[str, Any] = QLIB_BODY):
    return ok(QlibWorkflowService().create_run(payload))


@router.get("/qlib-workflows/runs")
def list_runs(
    run_type: str | None = None,
    page: int = PAGE_QUERY,
    page_size: int = PAGE_SIZE_QUERY,
):
    return ok(QlibWorkflowService().list_runs(run_type=run_type or None, page=page, page_size=page_size))


@router.get("/qlib-workflows/runs/{run_id}")
def detail(run_id: int):
    return ok(QlibWorkflowService().detail(run_id))
