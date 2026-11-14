"""Explicit model-graph jobs; GET viewing and export never invoke a model."""

from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends
from fastapi.responses import FileResponse

from src.api.route_guards import ValidatedRoute
from src.api.schemas.common import ok
from src.engine.market.model_graph.generation import availability
from src.engine.market.model_graph.service import GraphResearchService

from .file_previews import require_same_origin

router = APIRouter(
    prefix="/relations/research",
    tags=["Relationship research"],
    route_class=ValidatedRoute,
    dependencies=[Depends(require_same_origin)],
)


@router.get("/providers")
def providers():
    return ok(availability())


@router.post("/runs")
def create(payload: Annotated[dict[str, Any], Body()]):
    return ok(GraphResearchService().start(payload))


@router.get("/runs")
def history():
    return ok({"items": GraphResearchService().store.history()})


@router.get("/runs/{run_id}")
def detail(run_id: str):
    return ok(GraphResearchService().detail(run_id))


@router.get("/runs/{run_id}/events")
def events(run_id: str):
    return ok({"items": GraphResearchService().store.events(run_id)})


@router.get("/runs/{run_id}/graph")
def result(run_id: str, include_inferences: bool = False):
    return ok(GraphResearchService().result(run_id, include_inferences))


@router.post("/runs/{run_id}/cancel")
def cancel(run_id: str):
    return ok(GraphResearchService().store.cancel(run_id))


@router.get("/runs/{run_id}/export")
def export(run_id: str):
    service = GraphResearchService()
    service.store.result(run_id)
    return FileResponse(
        service.store.directory(run_id) / "graph.json", media_type="application/json", filename=run_id + ".json"
    )
