"""Versioned strategy workshop, actual streams and local paper account controls."""

from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.routing import APIRoute
from pydantic import BaseModel, ConfigDict, Field

from src.api.event_stream import sse_events
from src.api.schemas.common import ok
from src.core.exceptions import BusinessError, ErrorCode
from src.strategy.composition.accounts import PipelineAccounts
from src.strategy.composition.config import merge, templates
from src.strategy.composition.evidence_view import evidence
from src.strategy.composition.layouts import GraphLayouts
from src.strategy.composition.service import PipelineService, component_catalog
from src.strategy.composition.validation import compile_plan


class PipelineRoute(APIRoute):
    def get_route_handler(self):
        handler = super().get_route_handler()

        async def guarded(request):
            try:
                return await handler(request)
            except ValueError as exc:
                raise BusinessError(ErrorCode.INVALID_PARAM, str(exc)) from exc

        return guarded


router = APIRouter(tags=["策略工坊"], route_class=PipelineRoute)


class PlanRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    definition: dict[str, Any]
    overrides: dict[str, Any] = Field(default_factory=dict)
    variant: str = "baseline"


class LayoutRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    definition_digest: str = Field(pattern="^[0-9a-f]{64}$")
    layout: dict[str, Any]
    revision: int = Field(ge=0)


@router.get("/strategy-pipelines/{pipeline_id}/layout")
def graph_layout(pipeline_id: int):
    PipelineService().store.repo.get("strategy_pipelines", pipeline_id)
    return ok(GraphLayouts().load(f"pipeline:{pipeline_id}"))


@router.put("/strategy-pipelines/{pipeline_id}/layout")
def save_graph_layout(pipeline_id: int, payload: LayoutRequest):
    PipelineService().store.repo.get("strategy_pipelines", pipeline_id)
    return ok(
        GraphLayouts().save(f"pipeline:{pipeline_id}", payload.definition_digest, payload.layout, payload.revision)
    )


@router.get("/strategy-pipeline-runs/{run_id}/nodes")
def graph_nodes(run_id: str, after: int = 0):
    return ok(evidence(run_id, after))


class RunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version_id: int | None = Field(default=None, gt=0)
    template: str | None = None
    definition: dict[str, Any] | None = None
    overrides: dict[str, Any] = Field(default_factory=dict)
    variant: str = "baseline"
    symbols: list[str] | None = None
    resource_pool_id: int | None = Field(default=None, gt=0)
    mode: str = Field(default="screen", pattern="^(screen|targets|backtest|replay|paper)$")
    market: str = Field(default="CN", pattern="^(CN|US)$")
    start_date: str = ""
    end_date: str = ""
    agent_mode: str | None = None
    backend: str = Field(default="api", pattern="^(api|codex|qoder|trae|codebuddy)$")
    model_id: int | None = Field(default=None, gt=0)
    model_name: str = Field(default="", max_length=200)
    reasoning_effort: str = Field(default="", pattern="^(|low|medium|high|xhigh)$")
    snapshot_id: str | None = None
    agent_replay: list[str] = Field(default_factory=list)
    account_id: int | None = Field(default=None, gt=0)
    refresh_decision: bool = False
    require_real: bool = False
    risk_only: bool = False
    execution_costs: dict[str, Any] | None = None
    agent_documents_dataset_id: int | None = Field(default=None, gt=0)
    agent_strategy_options: dict[str, Any] = Field(default_factory=dict)


@router.get("/strategy-components")
def components():
    return ok(component_catalog())


@router.get("/strategy-pipeline-templates")
def presets():
    return ok(templates())


@router.post("/strategy-pipelines/preview")
def preview(payload: PlanRequest):
    return ok(PipelineService().preview(payload.definition, payload.overrides, payload.variant))


@router.post("/strategy-pipelines")
def create(payload: PlanRequest):
    service = PipelineService()
    compile_plan(payload.definition, payload.overrides, payload.variant)
    resolved = merge(
        merge(payload.definition, (payload.definition.get("variants") or {"baseline": {}})[payload.variant]),
        payload.overrides,
    )
    resolved["variants"] = {"baseline": {}}
    return ok(service.store.save_draft(resolved))


@router.get("/strategy-pipelines")
def list_plans():
    return ok(PipelineService().store.catalog())


@router.put("/strategy-pipelines/{pipeline_id}")
def update(pipeline_id: int, payload: PlanRequest):
    compile_plan(payload.definition, payload.overrides, payload.variant)
    resolved = merge(
        merge(payload.definition, (payload.definition.get("variants") or {"baseline": {}})[payload.variant]),
        payload.overrides,
    )
    resolved["variants"] = {"baseline": {}}
    return ok(PipelineService().store.save_draft(resolved, pipeline_id))


@router.get("/strategy-pipelines/{pipeline_id}")
def plan_detail(pipeline_id: int):
    store = PipelineService().store
    store.repo.get("strategy_pipelines", pipeline_id)
    return ok(next(row for row in store.catalog() if row["id"] == pipeline_id))


@router.post("/strategy-pipelines/{pipeline_id}/enabled")
def enabled(pipeline_id: int, enabled: bool):
    return ok(PipelineService().store.set_enabled(pipeline_id, enabled))


@router.post("/strategy-pipelines/{pipeline_id}/publish")
def publish(pipeline_id: int):
    return ok(PipelineService().store.publish(pipeline_id))


@router.get("/strategy-pipelines/{pipeline_id}/versions")
def versions(pipeline_id: int):
    return ok(PipelineService().store.versions(pipeline_id))


@router.post("/strategy-pipeline-runs")
def run(payload: RunRequest):
    return ok(PipelineService().start(payload.model_dump(exclude_none=True)))


@router.post("/strategy-pipeline-runs/stream")
def stream(payload: RunRequest):
    service = PipelineService()
    started = service.start(payload.model_dump(exclude_none=True))

    def events():
        for update in service.follow(started["id"]):
            for event in update["events"]:
                yield {"type": "progress", "run_id": started["id"], "data": event}
            if update["run"]["status"] not in {"running", "cancelling"}:
                yield {"type": "result", "run_id": started["id"], "data": ok(update["run"])}

    return StreamingResponse(sse_events(events()), media_type="text/event-stream")


@router.get("/strategy-pipeline-runs")
def runs():
    service = PipelineService()
    return ok(service.store.runs(service.cfg["defaults"]["history_limit_runs"]))


@router.get("/strategy-pipeline-runs/{run_id}")
def detail(run_id: str):
    return ok(PipelineService().detail(run_id))


@router.get("/strategy-pipeline-runs/{run_id}/events")
def events(run_id: str):
    service = PipelineService()
    service.detail(run_id)
    return ok(service.store.events(run_id))


@router.get("/strategy-pipeline-runs/{run_id}/result")
def result(run_id: str):
    return ok(PipelineService().detail(run_id)["result"])


@router.post("/strategy-pipeline-runs/{run_id}/cancel")
def cancel(run_id: str):
    return ok(PipelineService().cancel(run_id))


@router.get("/strategy-pipeline-runs/{run_id}/files/{name}")
def artifact(run_id: str, name: str):
    try:
        path = PipelineService().store.artifact(run_id, name)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
    return FileResponse(path, filename=name, headers={"X-Content-Type-Options": "nosniff"})


@router.get("/strategy-pipeline-accounts")
def accounts():
    return ok(PipelineAccounts().list())


@router.get("/strategy-pipeline-accounts/{account_id}")
def account(account_id: int):
    return ok(PipelineAccounts().detail(account_id))


@router.post("/strategy-pipeline-accounts/{account_id}/monitor")
def monitor(account_id: int, enabled: bool):
    return ok(PipelineAccounts().monitor(account_id, enabled))


@router.post("/strategy-pipeline-accounts/{account_id}/risk-reset")
def reset(account_id: int):
    return ok(PipelineAccounts().reset_risk(account_id))
