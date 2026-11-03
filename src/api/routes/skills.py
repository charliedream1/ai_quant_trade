"""Skill routes."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Body

from src.api.route_guards import ValidatedRoute
from src.api.schemas.common import ok
from src.integration.skill_manager import SkillManager

router = APIRouter(tags=["模型配置-Skill"], route_class=ValidatedRoute)
JsonBody = Annotated[dict[str, Any], Body()]
OptionalJsonBody = Annotated[dict[str, Any] | None, Body()]


@router.get("/skills")
def list_skills():
    return ok(SkillManager().list())


@router.post("/skills")
def create_skill(payload: JsonBody):
    return ok(SkillManager().create(payload))


@router.post("/skills/{skill_id}/enable")
def enable(skill_id: int):
    return ok(SkillManager().enable(skill_id, True))


@router.post("/skills/{skill_id}/disable")
def disable(skill_id: int):
    return ok(SkillManager().enable(skill_id, False))


@router.put("/skills/{skill_id}/params")
def params(skill_id: int, payload: JsonBody):
    return ok(SkillManager().params(skill_id, payload.get("params") or payload))


@router.post("/skills/{skill_id}/run")
def run(skill_id: int, payload: OptionalJsonBody = None):
    data = payload or {}
    nested_params = data.get("params")
    params = nested_params if isinstance(nested_params, dict) else data
    return ok(SkillManager().run(skill_id, params))
