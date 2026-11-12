"""Scoped local SAG2 indexing under the existing administrator access boundary."""

from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends

from src.api.route_guards import ValidatedRoute
from src.api.schemas.common import ok
from src.core.async_work import blocking_call
from src.core.exceptions import BusinessError, ErrorCode
from src.knowledge.sag2_service import prepare_index, readiness

from .file_previews import require_same_origin

router = APIRouter(
    tags=["知识库检索后端"], prefix="/kb", dependencies=[Depends(require_same_origin)], route_class=ValidatedRoute
)


@router.get("/retrieval/status")
def status():
    return ok(readiness())


@router.post("/sag/sync")
async def sync(payload: Annotated[dict[str, Any], Body()]):
    raise BusinessError(ErrorCode.INVALID_PARAM, "Original SAG is retired; use /kb/sag2/index")


@router.post("/sag2/index")
async def index(payload: Annotated[dict[str, Any], Body()]):
    return ok(await blocking_call(prepare_index, payload))
