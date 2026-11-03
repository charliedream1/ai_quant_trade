"""Shared durable AI workspace sessions, attachments and native event streams."""

from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, File, Query, UploadFile
from fastapi.responses import StreamingResponse

from src.agent.attachments import _limits
from src.agent.composer_config import validate_selection
from src.agent.workspace import AIWorkspaceService
from src.api.event_stream import sse_events
from src.api.route_guards import ValidatedRoute
from src.api.schemas.common import ok
from src.core.async_work import blocking_call, read_upload

from .file_previews import require_same_origin

router = APIRouter(tags=["AI工作台会话"], dependencies=[Depends(require_same_origin)], route_class=ValidatedRoute)
JsonBody = Annotated[dict[str, Any], Body()]
PAGE = Query(1, ge=1)
PAGE_SIZE = Query(20, ge=1, le=100)


@router.get("/ai-workspace/sessions")
def sessions(page: int = PAGE, page_size: int = PAGE_SIZE):
    return ok(AIWorkspaceService().list_sessions(page, page_size))


@router.post("/ai-workspace/sessions")
def create_session(payload: JsonBody):
    return ok(
        AIWorkspaceService().create_session(
            str(payload.get("title") or ""), str(payload.get("project_name") or "") or None
        )
    )


@router.get("/ai-workspace/sessions/{session_id}")
def session_detail(session_id: int):
    return ok(AIWorkspaceService().detail(session_id))


@router.post("/ai-workspace/sessions/{session_id}/messages")
def message(session_id: int, payload: JsonBody):
    return ok(AIWorkspaceService().send(session_id, payload))


@router.post("/ai-workspace/sessions/{session_id}/messages/stream")
def message_stream(session_id: int, payload: JsonBody):
    payload = validate_selection(payload)
    return StreamingResponse(
        sse_events(AIWorkspaceService().send_stream(session_id, payload)), media_type="text/event-stream"
    )


@router.post("/ai-workspace/attachments")
async def attachment(file: Annotated[UploadFile, File()]):
    maximum = int(_limits()["max_total_bytes"])
    content = await read_upload(file, maximum)
    return ok(await blocking_call(AIWorkspaceService().upload, file.filename or "", content))
