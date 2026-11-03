"""Persisted Skill reports and actual execution event streams."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from src.api.event_stream import sse_events
from src.api.route_guards import ValidatedRoute
from src.api.schemas.common import ok
from src.engine.insights.service import InsightReportService

router = APIRouter(tags=["Skill 洞察报告"], route_class=ValidatedRoute)


class InsightRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: str
    backend: str | None = None
    market: str = "CN"
    symbol: str = Field(default="", max_length=100)
    model_id: int | None = Field(default=None, gt=0)
    model_name: str = Field(default="", max_length=200)
    reasoning_effort: str = Field(default="", pattern="^(|low|medium|high|xhigh)$")
    timeframe: str | None = None
    end_date: str = ""
    research_snapshot: str = Field(default="", pattern="^([a-f0-9]{64})?$")
    include_fundamentals: bool = False


@router.post("/insights/runs")
def create(payload: InsightRequest):
    return ok(InsightReportService().start(payload.model_dump()))


@router.post("/insights/runs/stream")
def stream(payload: InsightRequest):
    service = InsightReportService()
    run = service.start(payload.model_dump())

    def events():
        for update in service.follow(run["run_id"]):
            for event in update["events"]:
                yield {"type": "progress", "run_id": run["run_id"], "data": event}
            if update["run"]["status"] != "running":
                yield {"type": "result", "run_id": run["run_id"], "data": ok(update["run"])}

    return StreamingResponse(sse_events(events()), media_type="text/event-stream")


@router.get("/insights/runs")
def history():
    service = InsightReportService()
    return ok(service.store.history(service.config["defaults"]["history_limit"]))


@router.get("/insights/runs/{run_id}")
def detail(run_id: str):
    return ok(InsightReportService().detail(run_id))


@router.get("/insights/runs/{run_id}/events")
def events(run_id: str):
    service = InsightReportService()
    service.detail(run_id)
    return ok(service.store.events(run_id))


@router.get("/insights/runs/{run_id}/files/{name}")
def artifact(run_id: str, name: str):
    try:
        path = InsightReportService().store.artifact(run_id, name)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    # Attachments avoid running report JavaScript in the application origin.
    return FileResponse(path, filename=name, headers={"X-Content-Type-Options": "nosniff"})
