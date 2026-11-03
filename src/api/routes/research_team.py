"""Multi-agent research review endpoints; no order execution capability."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from src.agent.providers.contracts import ModelSelection
from src.agent.research_team import ResearchTeam
from src.api.event_stream import sse_events
from src.api.route_guards import ValidatedRoute
from src.api.schemas.common import ok

router = APIRouter(tags=["多Agent投研"], route_class=ValidatedRoute)


class TeamRequest(BaseModel):
    backtest_id: int = Field(gt=0)
    objective: str = Field(min_length=1, max_length=2000)
    model_id: int | None = Field(default=None, gt=0)
    workflow: str = Field(default="backtest_review", pattern="^(backtest_review|etf_review)$")
    provider: ModelSelection | None = None
    role_models: dict[str, ModelSelection] = Field(default_factory=dict)


@router.post("/research-team/runs")
def create_run(payload: TeamRequest):
    return ok(
        ResearchTeam().run(
            payload.backtest_id,
            payload.objective,
            payload.model_id,
            payload.workflow,
            payload.provider.model_dump(exclude_none=True) if payload.provider else None,
            {
                role: value.model_dump(exclude_unset=True, exclude_none=True)
                for role, value in payload.role_models.items()
            },
        )
    )


@router.get("/research-team/runs/{run_id}")
def detail(run_id: str):
    return ok(ResearchTeam().detail(run_id))


@router.post("/research-team/runs/stream")
def stream_run(payload: TeamRequest):
    def events():
        for report in ResearchTeam().run_stream(
            payload.backtest_id,
            payload.objective,
            payload.model_id,
            payload.workflow,
            payload.provider.model_dump(exclude_none=True) if payload.provider else None,
            {
                role: value.model_dump(exclude_unset=True, exclude_none=True)
                for role, value in payload.role_models.items()
            },
        ):
            yield {
                "type": "result" if report["status"] != "running" else "status",
                "run_id": report["run_id"],
                "data": ok(report)
                if report["status"] != "running"
                else {"status": report["status"], "roles": report["roles"], "events": report["events"]},
            }

    return StreamingResponse(sse_events(events()), media_type="text/event-stream")
