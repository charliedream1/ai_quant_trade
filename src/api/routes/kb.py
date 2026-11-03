"""Knowledge base routes."""

from typing import Annotated, Any

from fastapi import APIRouter, Body, Query, Request

from src.agent import RAGService
from src.api.route_guards import ValidatedRoute
from src.api.schemas.common import ok
from src.core.async_work import blocking_call, read_upload
from src.core.exceptions import BusinessError, ErrorCode
from src.core.fts import kb_document_source_scope, kb_remote_source_id
from src.core.kb_importer import MAX_UPLOAD_BYTES, import_uploaded_document
from src.core.repository import Repository, json_loads
from src.core.timeutil import utc_now_iso
from src.documents import knowledge
from src.documents.knowledge import _chunk_count, _create_doc
from src.integration.remote_sources.service import RemoteSourceService
from src.knowledge.config import library_name
from src.knowledge.download import import_url
from src.knowledge.files import KnowledgeFiles
from src.knowledge.search import KeywordSearch

router = APIRouter(tags=["知识库"], route_class=ValidatedRoute)
JsonBody = Annotated[dict[str, Any], Body()]


@router.get("/kb/libraries")
def libraries():
    return ok({"items": KnowledgeFiles().libraries()})


@router.post("/kb/libraries")
def create_library(payload: JsonBody):
    return ok({"name": KnowledgeFiles().create_library(library_name(payload.get("name")))})


@router.post("/kb/urls")
async def import_webpage(payload: JsonBody):
    return ok(
        await blocking_call(
            import_url,
            payload["url"],
            library=payload.get("library_name"),
            chunk_chars=payload.get("chunk_chars"),
            title=payload.get("title"),
        )
    )


@router.get("/kb/categories")
def categories():
    repo = Repository()
    rows = repo.list("kb_categories", order_by="parent_id ASC, sort_order ASC, id ASC")
    by_parent: dict[int, list[dict[str, Any]]] = {}
    for row in rows:
        row["category_id"] = row["id"]
        row["document_count"] = (
            repo.db.scalar("SELECT COUNT(*) AS cnt FROM kb_documents WHERE category_id = ?", (row["id"],)) or 0
        )
        row["children"] = []
        by_parent.setdefault(row["parent_id"], []).append(row)
    for row in rows:
        row["children"] = by_parent.get(row["id"], [])
    return ok(by_parent.get(0, []))


@router.post("/kb/categories")
def create_category(payload: JsonBody):
    return ok(knowledge.create_category(payload))


@router.put("/kb/categories/{category_id}")
def update_category(category_id: int, payload: JsonBody):
    values = {k: payload[k] for k in ("name", "parent_id", "sort_order") if k in payload}
    values["updated_at"] = utc_now_iso()
    row = Repository().update("kb_categories", category_id, values)
    row["category_id"] = row["id"]
    return ok(row)


@router.delete("/kb/categories/{category_id}")
def delete_category(category_id: int):
    Repository().delete("kb_categories", category_id)
    return ok(None)


@router.post("/kb/documents")
async def create_document(request: Request):
    content_type = request.headers.get("content-type", "")
    if "multipart/form-data" in content_type:
        form = await request.form()
        file_value = form.get("file")
        if file_value is None or not hasattr(file_value, "read"):
            raise BusinessError(ErrorCode.MISSING_PARAM, "请上传文档文件")
        content = await read_upload(file_value, MAX_UPLOAD_BYTES)
        row = await blocking_call(
            import_uploaded_document,
            filename=str(getattr(file_value, "filename", "") or "document.md"),
            content_bytes=content,
            title=str(form.get("title") or "").strip() or None,
            category_id=_form_int(form.get("category_id"), "分类 ID"),
            tags=form.get("tags"),
            library=str(form.get("library_name") or "") or None,
            chunk_chars=_form_int(form.get("chunk_chars"), "切分长度") or None,
            attachment_session=str(form.get("attachment_session") or ""),
        )
        return ok(row)
    payload = await request.json()
    if not isinstance(payload, dict):
        raise BusinessError(ErrorCode.INVALID_PARAM, "请求体必须是 JSON 对象")
    return ok(await blocking_call(_create_doc, payload, doc_type=payload.get("doc_type") or "document"))


@router.post("/kb/notes")
def create_note(payload: JsonBody):
    return ok(knowledge.create_note(payload))


@router.get("/kb/documents")
def list_documents(
    category_id: int | None = None,
    keyword: str | None = None,
    doc_type: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    library: str | None = Query(None, alias="library_name"),
):
    where: list[str] = ["library_name = ?", "attachment_session = ''"]
    params: list[Any] = [library_name(library)]
    if category_id:
        where.append("category_id = ?")
        params.append(category_id)
    if keyword:
        where.append("title LIKE ?")
        params.append(f"%{keyword}%")
    if doc_type and doc_type != "all":
        where.append("doc_type = ?")
        params.append(doc_type)
    repo = Repository()
    result = repo.page("kb_documents", page, page_size, " AND ".join(where), params, order_by="updated_at DESC")
    for item in result["items"]:
        item["doc_id"] = item["id"]
        item["tags"] = json_loads(item.get("tags"), [])
        item["chunk_count"] = _chunk_count(repo, int(item["id"]))
    return ok(result)


@router.get("/kb/documents/{doc_id}")
def document_detail(doc_id: int, include_content: bool = True):
    return ok(knowledge.document_detail(doc_id, include_content))


@router.delete("/kb/documents/{doc_id}")
def delete_document(doc_id: int):
    return ok(knowledge.delete_document(doc_id))


@router.get("/kb/search")
def search(
    keyword: str,
    category_id: int | None = None,
    doc_type: str | None = None,
    scope: str = "local",
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    library: str | None = Query(None, alias="library_name"),
):
    repo = Repository()
    items = KeywordSearch(repo).search(
        [keyword], library=library_name(library), limit=page * page_size, category_id=category_id, scope=scope
    )
    if doc_type and doc_type != "all":
        items = [item for item in items if item["doc_type"] == doc_type]
    total = len(items)
    items = items[(page - 1) * page_size : page * page_size]
    for item in items:
        item["doc_id"] = item["id"]
        item["source_scope"] = kb_document_source_scope(item)
        item["source_name"] = _source_name(item, repo)
        item["score"] = 1.0
    return ok({"items": items, "page": page, "page_size": page_size, "total": total})


@router.post("/kb/qa")
def qa(payload: JsonBody):
    return ok(RAGService().ask(payload))


@router.post("/kb/qa/clear")
def clear_qa_history(payload: JsonBody):
    return ok(RAGService().clear_history(payload))


@router.get("/kb/qa/sessions")
def qa_sessions(limit: int = Query(50, ge=1, le=100)):
    return ok({"items": RAGService().list_sessions(limit=limit)})


@router.put("/kb/qa/sessions")
def update_qa_session(payload: JsonBody):
    return ok(RAGService().update_session(payload))


@router.get("/kb/remote-sources")
def remote_sources():
    return ok(RemoteSourceService().list())


@router.post("/kb/remote-sources")
def create_remote_source(payload: JsonBody):
    return ok(RemoteSourceService().create(payload))


@router.put("/kb/remote-sources/{source_id}")
def update_remote_source(source_id: int, payload: JsonBody):
    return ok(RemoteSourceService().update(source_id, payload))


@router.delete("/kb/remote-sources/{source_id}")
def delete_remote_source(source_id: int):
    RemoteSourceService().delete(source_id)
    return ok(None)


@router.post("/kb/remote-sources/{source_id}/test")
def test_remote_source(source_id: int):
    return ok(RemoteSourceService().test(source_id))


@router.get("/kb/remote-sources/{source_id}/documents")
def remote_documents(
    source_id: int,
    folder: str | None = None,
    keyword: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    return ok(
        RemoteSourceService().documents(source_id, folder=folder, keyword=keyword, page=page, page_size=page_size)
    )


@router.post("/kb/remote-sources/{source_id}/pull")
def pull_remote(source_id: int, payload: JsonBody):
    return ok(RemoteSourceService().pull(source_id, payload))


@router.post("/kb/remote-sources/{source_id}/sync")
def sync_remote(source_id: int, payload: JsonBody):
    return ok(RemoteSourceService().sync(source_id, payload))


def _source_name(row: dict[str, Any], repo: Repository) -> str:
    if kb_document_source_scope(row) != "remote":
        return "本地知识库"
    source_id = kb_remote_source_id(row)
    if source_id:
        source = repo.db.query_one("SELECT name FROM remote_sources WHERE id = ?", (source_id,))
        if source:
            return str(source.get("name") or "远程知识源")
    return "远程知识源"


def _form_int(value: Any, label: str) -> int:
    if value in (None, ""):
        return 0
    try:
        return int(str(value))
    except ValueError as exc:
        raise BusinessError(ErrorCode.INVALID_PARAM, f"{label}必须是整数") from exc
