"""One service for recipe discovery, actual runs, matured scores and read-only reports."""

from typing import Any, Literal

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from src.agent_strategies.config import settings
from src.agent_strategies.scores import records
from src.agent_strategies.service import AgentStrategyService
from src.api.event_stream import sse_events
from src.api.schemas.common import ok
from src.core.stream_control import stream_pause

from .file_previews import require_same_origin
from .strategy_pipelines import PipelineRoute

router = APIRouter(
    prefix="/agent-strategies",
    tags=["Agent策略"],
    route_class=PipelineRoute,
    dependencies=[Depends(require_same_origin)],
)


class RunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    recipe: str
    market_dataset_id: int = Field(gt=0)
    documents_dataset_id: int | None = Field(default=None, gt=0)
    as_of: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    symbols: list[str] | None = None
    backend: Literal["api", "codex", "qoder", "trae", "codebuddy"] = "api"
    model_id: int | None = Field(default=None, gt=0)
    model_name: str = ""
    reasoning_effort: Literal["", "low", "medium", "high", "xhigh"] = ""
    scope: str = Field(default="default", max_length=200)
    market: Literal["CN", "US"] = "CN"
    validation_mode: Literal["current_research", "historical_research"] = "current_research"
    options: dict[str, Any] = Field(default_factory=dict)
    execution_costs: dict[str, Any] | None = None
    execution: dict[str, Any] | None = None
    risk: dict[str, Any] | None = None


@router.get("/recipes")
def recipes():
    cfg = settings()
    return ok(
        {"recipes": cfg["recipes"], "depths": cfg["depths"], "limits": cfg["limits"], "defaults": cfg["defaults"]}
    )


@router.get("/runs")
def history():
    return ok({"items": AgentStrategyService().store.history()})


@router.post("/runs")
def start(payload: RunRequest):
    return ok(AgentStrategyService().start(payload.model_dump(exclude_none=True)))


@router.get("/runs/{run_id}")
def detail(run_id: int):
    return ok(AgentStrategyService().store.get(run_id))


@router.post("/runs/{run_id}/cancel")
def cancel(run_id: int):
    return ok(AgentStrategyService().cancel(run_id))


@router.get("/runs/{run_id}/events")
def events(run_id: int, after: int = 0):
    store = AgentStrategyService().store
    store.get(run_id)
    return ok({"items": store.events(run_id, after)})


@router.get("/runs/{run_id}/stream")
def stream(run_id: int, after: int = 0):
    service = AgentStrategyService()
    service.store.get(run_id)

    def follow():
        cursor = after
        while True:
            page = service.store.events(run_id, cursor)
            for event in page:
                cursor = event["id"]
                yield {"type": "process", "data": event}
            if page:
                continue
            run = service.store.get(run_id)
            if run["status"] in {"completed", "partial", "failed", "cancelled"}:
                yield {"type": "result", "data": ok(run)}
                return
            stream_pause(settings()["limits"]["poll_seconds"])

    return StreamingResponse(sse_events(follow()), media_type="text/event-stream")


@router.get("/runs/{run_id}/scores")
def scores(run_id: int):
    service = AgentStrategyService()
    run = service.store.get(run_id)
    return ok(
        {channel: records(service.store, run["lineage"], channel, run["as_of"]) for channel in ("data", "research")}
    )


@router.get("/runs/{run_id}/files/{name}")
def artifact(run_id: int, name: str):
    return FileResponse(
        AgentStrategyService().store.artifact(run_id, name),
        headers={"Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; frame-ancestors 'self'"},
    )


@router.get("/runs/{run_id}/file-info/{name}")
def file_info(run_id: int, name: str):
    service = AgentStrategyService()
    path = service.store.artifact(run_id, name)
    return ok(
        {
            "name": name,
            "text": path.read_text(encoding="utf-8")[: settings()["limits"]["max_response_chars"]],
            "download_url": f"/api/v1/agent-strategies/runs/{run_id}/files/{name}",
        }
    )
