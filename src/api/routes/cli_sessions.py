"""CLI builder session routes."""

from typing import Annotated, Any

from fastapi import APIRouter, Body, Query

from src.api.route_guards import ValidatedRoute
from src.api.schemas.common import ok
from src.strategy import StrategyStore
from src.strategy.cli_builder import CliBuilder

router = APIRouter(tags=["策略构建-CLI"], route_class=ValidatedRoute)


@router.post("/cli-sessions")
def create(payload: Annotated[dict[str, Any], Body()]):
    return ok(CliBuilder().create_session(payload))


@router.get("/cli-sessions/{session_id}")
def status(session_id: int):
    return ok(CliBuilder().status(session_id))


@router.get("/cli-sessions/{session_id}/logs")
def logs(session_id: int, offset: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=500)):
    return ok(CliBuilder().logs(session_id, offset=offset, limit=limit))


@router.post("/cli-sessions/{session_id}/import")
def import_artifact(session_id: int, payload: Annotated[dict[str, Any], Body()]):
    return ok(
        CliBuilder().import_artifact(
            session_id, payload["file"], payload["name"], payload.get("description") or "", StrategyStore()
        )
    )
