"""SAG indexing is an explicit administrator action, guarded by the existing access boundary."""

from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends

from src.api.route_guards import ValidatedRoute
from src.api.schemas.common import ok
from src.core.async_work import blocking_call
from src.core.exceptions import BusinessError, ErrorCode
from src.knowledge.sag_client import RetrievalUnavailableError
from src.knowledge.sag_service import readiness, sync_documents

from .file_previews import require_same_origin

router = APIRouter(
    tags=["知识库检索后端"], prefix="/kb", dependencies=[Depends(require_same_origin)], route_class=ValidatedRoute
)


@router.get("/retrieval/status")
def status():
    return ok(readiness())


@router.post("/sag/sync")
async def sync(payload: Annotated[dict[str, Any], Body()]):
    try:
        return ok(await blocking_call(sync_documents, payload))
    except RetrievalUnavailableError as exc:
        raise BusinessError(ErrorCode.DOCUMENT_SOURCE_ERROR, str(exc)) from None
