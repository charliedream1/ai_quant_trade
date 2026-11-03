"""Expose existing research services to both UI and command-line clients."""

import json
from collections.abc import Callable
from typing import Annotated, Any

from fastapi import APIRouter, Body, File, Query, UploadFile
from fastapi.responses import FileResponse, Response

from src.api.route_guards import ValidatedRoute
from src.api.schemas.common import ok
from src.core.async_work import blocking_call, read_upload
from src.core.exceptions import BusinessError, ErrorCode
from src.data.security_master import SecurityMasterService
from src.engine.market.resource_import import import_config, template_path
from src.engine.market.resource_pool import ResourcePoolService
from src.engine.market.resource_transfer import ResourceImportService, errors_csv
from src.frontend.common.chart_help import catalog
from src.frontend.common.runtime_loader import runtime_source
from src.strategy import StrategyStore

router = APIRouter(tags=["研究资源"], route_class=ValidatedRoute)
JsonBody = Annotated[dict[str, Any], Body()]
LIMIT_QUERY = Query(20, ge=1, le=100)


@router.get("/ui/runtime.js", include_in_schema=False)
def ui_runtime():
    return Response(runtime_source(), media_type="text/javascript", headers={"Cache-Control": "public, max-age=3600"})


@router.get("/ui/chart-explanations")
def chart_explanations():
    return Response(
        content=json.dumps(ok(catalog()), ensure_ascii=False),
        media_type="application/json",
        headers={"Cache-Control": "public, max-age=300"},
    )


@router.get("/securities/search")
def search(query: str = "", market: str | None = None, limit: int = LIMIT_QUERY):
    return ok(SecurityMasterService().search(query, market, limit))


@router.get("/strategy-examples")
def examples():
    return ok(StrategyStore().examples())


@router.get("/strategy-examples/detail")
def example_detail(example: str):
    return ok(StrategyStore().example_detail(example))


@router.post("/strategy-examples/import")
def import_example(payload: JsonBody):
    example = str(payload.get("example") or "")
    if not example:
        raise BusinessError(ErrorCode.MISSING_PARAM, "请指定示例相对路径 example")
    return ok(
        StrategyStore().import_example(example, {key: value for key, value in payload.items() if key != "example"})
    )


@router.get("/resource-pools")
def pools():
    return ok(ResourcePoolService().list_pools())


@router.post("/resource-pools")
def create_pool(payload: JsonBody):
    return ok(ResourcePoolService().create_pool(str(payload.get("name") or ""), str(payload.get("description") or "")))


@router.get("/resource-pools/{pool_id}/items")
def pool_items(pool_id: int):
    if pool_id <= 0:
        raise BusinessError(ErrorCode.INVALID_PARAM, "资源池 ID 必须为正数")
    return ok(ResourcePoolService().list_items(pool_id))


@router.post("/resource-pools/{pool_id}/symbols")
def add_symbols(pool_id: int, payload: JsonBody):
    symbols = payload.get("symbols") or ""
    if isinstance(symbols, list):
        symbols = ",".join(str(symbol) for symbol in symbols)
    return ok(
        ResourcePoolService().add_symbols(
            pool_id,
            str(symbols),
            remark=str(payload.get("remark") or ""),
            weight=float(payload.get("weight", 1.0)),
        )
    )


@router.post("/resource-pools/{pool_id}/import")
async def import_pool(
    pool_id: int,
    file: Annotated[UploadFile, File()],
    mode: str = "merge",
    preview_hash: str = "",
    allow_partial: bool = False,
):
    content = await _upload(file)
    return await blocking_call(
        _validated,
        lambda: ResourceImportService(ResourcePoolService().repo).commit(
            pool_id,
            file.filename or "",
            content,
            mode=mode,
            preview_hash=preview_hash,
            allow_partial=allow_partial,
        ),
    )


@router.post("/resource-pools/{pool_id}/import/preview")
async def preview_pool(pool_id: int, file: Annotated[UploadFile, File()], mode: str = "merge"):
    content = await _upload(file)
    return await blocking_call(
        _validated,
        lambda: ResourceImportService(ResourcePoolService().repo).preview(pool_id, file.filename or "", content, mode),
    )


@router.post("/resource-pools/{pool_id}/import/errors")
async def pool_import_errors(pool_id: int, file: Annotated[UploadFile, File()]):
    report = await blocking_call(
        ResourceImportService(ResourcePoolService().repo).preview, pool_id, file.filename or "", await _upload(file)
    )
    return Response(
        errors_csv(report),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="import-errors.csv"'},
    )


@router.get("/resource-pools/templates/{kind}")
def pool_template(kind: str):
    path = template_path(kind)
    return FileResponse(path, filename=path.name)


async def _upload(file: UploadFile) -> bytes:
    content = await read_upload(file, import_config()["limits"]["file_bytes"])
    if len(content) > import_config()["limits"]["file_bytes"]:
        raise BusinessError(ErrorCode.INVALID_PARAM, "文件超过资源池上传大小限制")
    return content


def _validated(action: Callable[[], Any]) -> dict[str, Any]:
    try:
        return ok(action())
    except ValueError as exc:
        raise BusinessError(ErrorCode.INVALID_PARAM, str(exc)) from exc
