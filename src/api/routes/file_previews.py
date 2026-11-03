"""Read-only file previews and optimistic Markdown updates by registered identity."""

from typing import Annotated

from fastapi import APIRouter, Depends, File, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, ConfigDict

from src.api.route_guards import ValidatedRoute
from src.core.async_work import blocking_call, read_upload
from src.core.exceptions import BusinessError, ErrorCode
from src.documents.config import preview_config
from src.documents.service import FilePreviewService
from src.documents.store import PreviewStore
from src.documents.view import viewer_html

from ..schemas.common import ok


def require_same_origin(request: Request) -> None:
    origin = request.headers.get("origin")
    expected = f"{request.url.scheme}://{request.url.netloc}"
    if request.method not in {"GET", "HEAD", "OPTIONS"} and origin and origin.rstrip("/") != expected:
        raise BusinessError(ErrorCode.INVALID_PARAM, "文件写入和登记仅接受同站点网页请求")


router = APIRouter(
    tags=["文件阅读与Markdown编辑"], dependencies=[Depends(require_same_origin)], route_class=ValidatedRoute
)


class FileLocation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    path: str


class MarkdownUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    revision: str
    content: str


@router.post("/file-previews/project")
def open_project(payload: FileLocation):
    record = PreviewStore().register_project(payload.path)
    return ok(FilePreviewService().detail(record["id"]))


@router.post("/file-previews/uploads")
async def upload_preview(file: Annotated[UploadFile, File()]):
    maximum = preview_config()["limits"]["max_bytes"]
    content = await read_upload(file, maximum)
    record = await blocking_call(PreviewStore().upload, file.filename or "", content)
    return ok(await blocking_call(FilePreviewService().detail, record["id"]))


@router.post("/file-previews/knowledge/{doc_id}")
def open_knowledge(doc_id: int):
    return ok(FilePreviewService().knowledge(doc_id))


@router.get("/file-previews/{identifier}")
def detail(identifier: str):
    return ok(FilePreviewService().detail(identifier))


@router.get("/file-previews/{identifier}/view", response_class=HTMLResponse)
def view(identifier: str):
    PreviewStore().read(identifier)
    return HTMLResponse(
        viewer_html(identifier),
        headers={
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "frame-ancestors 'self'; object-src 'none'; base-uri 'none'",
        },
    )


@router.get("/file-previews/{identifier}/raw")
def raw(identifier: str, download: bool = False):
    service = FilePreviewService()
    row = service.detail(identifier)
    path = service.store.path(service.store.read(identifier))
    mime = {"pdf": "application/pdf", "html": "text/plain", "text": "text/plain", "markdown": "text/plain"}.get(
        row["kind"]
    )
    return FileResponse(
        path,
        media_type=mime,
        filename=row["name"],
        content_disposition_type="attachment" if download or row["kind"] == "office" else "inline",
        headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"},
    )


@router.post("/file-previews/{identifier}/conversion")
def conversion(identifier: str):
    value = FilePreviewService().convert(identifier)
    return ok({key: item for key, item in value.items() if key != "path"})


@router.get("/file-previews/{identifier}/pdf")
def pdf(identifier: str):
    value = FilePreviewService().convert(identifier)
    if value["status"] != "completed":
        raise BusinessError(ErrorCode.TASK_NOT_FINISHED, value.get("error") or "Office预览仍在转换中")
    return FileResponse(
        value["path"],
        media_type="application/pdf",
        headers={"Cache-Control": "private", "X-Content-Type-Options": "nosniff"},
    )


@router.put("/file-previews/{identifier}/markdown")
def save_markdown(identifier: str, payload: MarkdownUpdate):
    return ok(FilePreviewService().save_markdown(identifier, payload.revision, payload.content))


@router.get("/file-previews/{identifier}/assets/{relative:path}")
def asset(identifier: str, relative: str):
    path = FilePreviewService().asset(identifier, relative)
    return FileResponse(path, headers={"X-Content-Type-Options": "nosniff", "Cache-Control": "private"})
