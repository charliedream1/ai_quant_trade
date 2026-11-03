"""Live trading routes."""

from typing import Annotated, Any

from fastapi import APIRouter, Body, Query

from src.api.route_guards import ValidatedRoute
from src.api.schemas.common import ok
from src.engine.live import LiveBrokerEventService, LiveTradingService

router = APIRouter(tags=["实盘"], route_class=ValidatedRoute)


@router.get("/live-configs")
def list_configs(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100)):
    return ok(LiveTradingService().list_configs(page=page, page_size=page_size))


@router.post("/live-configs")
def create_config(payload: Annotated[dict[str, Any], Body(...)]):
    return ok(LiveTradingService().create_config(payload))


@router.get("/live-configs/{config_id}")
def detail_config(config_id: int):
    return ok(LiveTradingService().detail_config(config_id))


@router.get("/live-configs/{config_id}/validation")
def validation_checks(config_id: int):
    return ok(LiveTradingService().validation_checks(config_id))


@router.put("/live-configs/{config_id}")
def update_config(config_id: int, payload: Annotated[dict[str, Any], Body(...)]):
    return ok(LiveTradingService().update_config(config_id, payload))


@router.delete("/live-configs/{config_id}")
def delete_config(config_id: int):
    LiveTradingService().delete_config(config_id)
    return ok(None)


@router.patch("/live-configs/{config_id}/risk-controls")
def patch_risk(config_id: int, payload: Annotated[dict[str, Any], Body(...)]):
    return ok(LiveTradingService().patch_risk(config_id, payload.get("risk_controls") or payload))


@router.get("/live-broker-adapters")
def broker_adapters():
    return ok(LiveBrokerEventService().adapters())


@router.post("/live-runs")
def start_run(payload: Annotated[dict[str, Any], Body(...)]):
    return ok(LiveTradingService().start_run(payload))


@router.post("/live-runs/{run_id}/stop")
def stop_run(run_id: int, payload: Annotated[dict[str, Any] | None, Body()] = None):
    return ok(LiveTradingService().stop_run(run_id, graceful=bool((payload or {}).get("graceful", True))))


@router.post("/live-runs/{run_id}/pause")
def pause_run(run_id: int):
    return ok(LiveTradingService().pause_run(run_id))


@router.post("/live-runs/{run_id}/resume")
def resume_run(run_id: int):
    return ok(LiveTradingService().resume_run(run_id))


@router.post("/live-runs/{run_id}/mark-error")
def mark_error(run_id: int, payload: Annotated[dict[str, Any] | None, Body()] = None):
    return ok(LiveTradingService().mark_error(run_id, message=str((payload or {}).get("message") or "")))


@router.post("/live-runs/{run_id}/broker-events")
def broker_event(run_id: int, payload: Annotated[dict[str, Any] | None, Body()] = None):
    return ok(LiveBrokerEventService().handle_event(run_id, payload or {}))


@router.get("/live-runs/{run_id}/status")
def status(run_id: int):
    return ok(LiveTradingService().status(run_id))


@router.get("/live-runs/{run_id}/orders")
def orders(
    run_id: int, status: str | None = None, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100)
):
    return ok(LiveTradingService().orders(run_id, status=status, page=page, page_size=page_size))


@router.get("/live-runs/{run_id}/positions")
def positions(run_id: int):
    return ok(LiveTradingService().positions(run_id))
