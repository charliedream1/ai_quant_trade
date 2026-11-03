"""Factor research and monitoring routes."""

from __future__ import annotations

from fastapi import APIRouter, Query

from src.api.route_guards import ValidatedRoute
from src.api.schemas.common import ok
from src.engine.research import FactorMonitorService
from src.engine.research.monitor_jobs import monitor_job, start_monitor
from src.engine.research.monitor_universe import MonitorUniverses

router = APIRouter(tags=["投研-因子监控"], route_class=ValidatedRoute)
UNIVERSE_QUERY = Query(default="")


@router.get("/factors/definitions")
def definitions():
    return ok(FactorMonitorService().definitions())


@router.get("/factors/monitor")
def monitor(
    universe: str | None = UNIVERSE_QUERY,
    universe_id: str = "custom",
    resource_id: int | None = None,
    backend: str = "builtin",
    as_of: str = "",
    membership_version: str = "",
    force_refresh: bool = False,
):
    return ok(
        FactorMonitorService().monitor(
            universe_text=universe or "",
            universe_id=universe_id,
            resource_id=resource_id,
            backend=backend,
            as_of=as_of,
            membership_version=membership_version,
            force_refresh=force_refresh,
        )
    )


@router.get("/factors/qlib-status")
def qlib_status():
    return ok(FactorMonitorService().qlib_status())


@router.get("/factors/universes")
def universes():
    return ok(FactorMonitorService().universes())


@router.post("/factors/universes/memberships")
def memberships(payload: dict):
    service = FactorMonitorService()
    return ok(MonitorUniverses(service.repo, service.data, service._config()).save_memberships(payload))


@router.post("/factors/jobs")
def start(payload: dict):
    allowed = {
        "universe_text",
        "universe_id",
        "resource_id",
        "backend",
        "as_of",
        "membership_version",
        "force_refresh",
        "compare_universes",
    }
    if set(payload) - allowed:
        raise ValueError("包含未知监控参数")
    return ok({"job_id": start_monitor(payload), "status": "queued"})


@router.get("/factors/jobs/{job_id}")
def job_status(job_id: str):
    result = monitor_job(job_id)
    return ok({key: value for key, value in result.items() if key not in {"database", "owner"}})
