"""Strategy library routes."""

from typing import Any

from fastapi import APIRouter, Body, Query
from pydantic import BaseModel, Field

from src.api.route_guards import ValidatedRoute
from src.api.schemas.common import ok
from src.strategy import StrategyStore
from src.strategy.parameters import StrategyParameters

router = APIRouter(tags=["策略构建-策略库"], route_class=ValidatedRoute)
STRATEGY_BODY = Body(...)
PAGE_QUERY = Query(1, ge=1)
PAGE_SIZE_QUERY = Query(20, ge=1, le=100)


class SourceReview(BaseModel):
    source_sha256: str = Field(pattern="^[a-f0-9]{64}$")
    reviewer: str = Field(min_length=1, max_length=200)


@router.post("/strategies/{strategy_id}/source-review")
def source_review(strategy_id: int, payload: SourceReview):
    return ok(StrategyStore().review(strategy_id, payload.source_sha256, payload.reviewer))


@router.get("/strategies")
def list_strategies(
    keyword: str | None = None,
    status: str | None = None,
    tag: str | None = None,
    page: int = PAGE_QUERY,
    page_size: int = PAGE_SIZE_QUERY,
):
    return ok(StrategyStore().list(keyword=keyword, status=status, tag=tag, page=page, page_size=page_size))


@router.get("/strategies/{strategy_id}/params")
def params(strategy_id: int):
    return ok(StrategyStore().params(strategy_id))


@router.get("/strategies/{strategy_id}/parameter-profiles")
def parameter_profiles(strategy_id: int):
    return ok(StrategyParameters().options(strategy_id))


@router.post("/strategies/{strategy_id}/resolve-params")
def resolve_params(strategy_id: int, payload: dict[str, Any] = STRATEGY_BODY):
    resolution = StrategyParameters().resolve(strategy_id, payload.get("params"), payload.get("parameter_profile"))
    return ok({key: value for key, value in resolution.items() if key != "source"})


@router.get("/strategies/{strategy_id}")
def detail(strategy_id: int, include_code: bool = True):
    return ok(StrategyStore().get(strategy_id, include_code=include_code))


@router.post("/strategies")
def create(payload: dict[str, Any] = STRATEGY_BODY):
    return ok(StrategyStore().create(payload))


@router.put("/strategies/{strategy_id}")
def update(strategy_id: int, payload: dict[str, Any] = STRATEGY_BODY):
    return ok(StrategyStore().update(strategy_id, payload))


@router.delete("/strategies/{strategy_id}")
def delete(strategy_id: int):
    StrategyStore().delete(strategy_id)
    return ok(None)


@router.post("/strategies/{strategy_id}/enable")
def enable(strategy_id: int):
    return ok(StrategyStore().set_status(strategy_id, "可用"))


@router.post("/strategies/{strategy_id}/disable")
def disable(strategy_id: int):
    return ok(StrategyStore().set_status(strategy_id, "停用"))
