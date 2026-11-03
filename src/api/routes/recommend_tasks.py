"""Recommendation task routes."""

from typing import Annotated, Any

from fastapi import APIRouter, Body

from src.api.route_guards import ValidatedRoute
from src.api.schemas.common import ok
from src.engine.market import Recommender

router = APIRouter(tags=["市场分析-推荐"], route_class=ValidatedRoute)


@router.post("/recommend-tasks")
def create_task(payload: Annotated[dict[str, Any], Body()]):
    return ok(Recommender().create_task(payload))


@router.get("/recommend-tasks/{task_id}")
def task_status(task_id: int):
    return ok(Recommender().status(task_id))


@router.get("/recommend-tasks/{task_id}/result")
def task_result(task_id: int):
    return ok(Recommender().result(task_id))
