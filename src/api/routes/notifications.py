"""Read local notifications and change only this client's display state."""

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from src.api.route_guards import ValidatedRoute
from src.api.schemas.common import ok
from src.notifications.service import NotificationService, public_config

from .file_previews import require_same_origin

router = APIRouter(
    tags=["提醒中心"], prefix="/notifications", dependencies=[Depends(require_same_origin)], route_class=ValidatedRoute
)


class Action(BaseModel):
    client_id: UUID
    action: Literal["read", "dismiss"]


@router.get("/config")
def settings():
    return ok(public_config())


@router.get("")
def feed(client_id: UUID, after: int = Query(0, ge=0), before: int = Query(0, ge=0), initial: bool = False):
    return ok(NotificationService().feed(str(client_id), after, before, initial))


@router.post("/{identifier}/state")
def action(identifier: int, payload: Action):
    NotificationService().store.action(str(payload.client_id), identifier, payload.action)
    return ok({"id": identifier, "action": payload.action})


@router.post("/read-all")
def read_all(payload: Action):
    NotificationService().store.read_all(str(payload.client_id))
    return ok({"read": True})
