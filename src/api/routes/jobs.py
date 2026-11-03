"""Scheduler routes."""

from typing import Annotated, Any

from fastapi import APIRouter, Body, Query

from src.api.route_guards import ValidatedRoute
from src.api.schemas.common import ok
from src.scheduler import SchedulerService

router = APIRouter(tags=["定时任务"], route_class=ValidatedRoute)


@router.get("/jobs")
def list_jobs(
    job_type: str | None = None,
    enabled: bool | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    return ok(SchedulerService().list(job_type=job_type, enabled=enabled, page=page, page_size=page_size))


@router.post("/jobs")
def create_job(payload: Annotated[dict[str, Any], Body()]):
    return ok(SchedulerService().create(payload))


@router.get("/jobs/{job_id}")
def detail(job_id: int):
    return ok(SchedulerService().detail(job_id))


@router.put("/jobs/{job_id}")
def update(job_id: int, payload: Annotated[dict[str, Any], Body()]):
    return ok(SchedulerService().update(job_id, payload))


@router.delete("/jobs/{job_id}")
def delete(job_id: int):
    SchedulerService().delete(job_id)
    return ok(None)


@router.post("/jobs/{job_id}/enable")
def enable(job_id: int):
    return ok(SchedulerService().enable(job_id, True))


@router.post("/jobs/{job_id}/disable")
def disable(job_id: int):
    return ok(SchedulerService().enable(job_id, False))


@router.post("/jobs/{job_id}/trigger")
def trigger(job_id: int):
    return ok(SchedulerService().trigger(job_id))


@router.get("/jobs/{job_id}/histories")
def histories(
    job_id: int,
    status: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    return ok(SchedulerService().histories(job_id, status=status, page=page, page_size=page_size))
