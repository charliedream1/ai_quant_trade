"""Thin HTTP adapters for the shared model catalog."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Body

from src.agent import model_catalog
from src.api.route_guards import ValidatedRoute
from src.api.schemas.common import ok

router = APIRouter(tags=["模型配置-LLM"], route_class=ValidatedRoute)


@router.get("/llm-models")
def list_models():
    return ok(model_catalog.list_models())


@router.get("/llm-models/{model_id}")
def get_model(model_id: int):
    return ok(model_catalog.get_model(model_id))


@router.post("/llm-models")
def create_model(payload: Annotated[dict[str, Any], Body()]):
    return ok(model_catalog.create_model(payload))


@router.put("/llm-models/{model_id}")
def update_model(model_id: int, payload: Annotated[dict[str, Any], Body()]):
    return ok(model_catalog.update_model(model_id, payload))


@router.delete("/llm-models/{model_id}")
def delete_model(model_id: int):
    return ok(model_catalog.delete_model(model_id))


@router.post("/llm-models/{model_id}/set-default")
def set_default(model_id: int, payload: Annotated[dict[str, Any], Body()]):
    return ok(model_catalog.set_default(model_id, payload))


@router.post("/llm-models/{model_id}/test")
def test_model(model_id: int):
    return ok(model_catalog.test_model(model_id))


@router.post("/llm/chat")
def chat(payload: Annotated[dict[str, Any], Body()]):
    return ok(model_catalog.chat(payload))
