"""Shared alpha research contracts and actual persistent process events."""

from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from src.alpha_mining.approvals import approve
from src.alpha_mining.config import config, invalid
from src.alpha_mining.contracts import StudyRequest
from src.alpha_mining.data_io import attest, parse_upload, register_snapshot
from src.alpha_mining.export import export_draft
from src.alpha_mining.service import AlphaService
from src.api.route_guards import ValidatedRoute
from src.core.async_work import blocking_call, read_upload
from src.core.config import PROJECT_ROOT
from src.core.repository import json_loads
from src.core.stream_control import stream_pause

from ..event_stream import sse_events
from ..schemas.common import ok
from .file_previews import require_same_origin

router = APIRouter(
    prefix="/alpha", tags=["Alpha研究"], dependencies=[Depends(require_same_origin)], route_class=ValidatedRoute
)


class DatasetRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=200)
    kind: Literal["market", "documents", "macro"]
    payload: dict[str, Any]


class CandidateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    hypothesis: dict[str, Any]
    implementation: dict[str, Any]


class ActionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: Literal["discover", "validate", "holdout", "run"]
    candidate_id: int | None = Field(default=None, gt=0)


class ReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    candidate_id: int | None = Field(default=None, gt=0)
    track: Literal["economic", "technical"]
    decision: Literal["approve", "reject"]
    reviewer: str = Field(min_length=1, max_length=200)
    evidence: dict[str, Any]


class AttestationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reviewer: str = Field(min_length=1, max_length=200)
    evidence: dict[str, Any]


class ExportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    candidate_id: int | None = Field(default=None, gt=0)
    configuration: int = Field(default=1, ge=1, le=8)


class SnapshotRequest(BaseModel):
    snapshot_id: str = Field(pattern="^[a-f0-9]{64}$")


@router.get("/config")
def configuration():
    return ok(config())


@router.get("/datasets")
def datasets():
    service = AlphaService()
    return ok({"items": [service.dataset_metadata(row) for row in service.store.list("alpha_datasets")]})


@router.post("/datasets")
def dataset(payload: DatasetRequest):
    return ok(AlphaService().register_dataset(payload.name, payload.kind, payload.payload))


@router.post("/datasets/upload")
async def upload(kind: Literal["market", "documents", "macro"], file: Annotated[UploadFile, File()]):
    content = await read_upload(file, config()["limits"]["max_upload_bytes"])
    parsed = await blocking_call(parse_upload, kind, file.filename or "", content)
    return ok(await blocking_call(AlphaService().register_dataset, file.filename or kind, kind, parsed))


@router.post("/datasets/snapshot")
def snapshot(payload: SnapshotRequest):
    return ok(register_snapshot(AlphaService(), payload.snapshot_id))


@router.post("/datasets/{dataset_id}/attest")
def attest_source(dataset_id: int, payload: AttestationRequest):
    return ok(attest(AlphaService(), dataset_id, payload.reviewer, payload.evidence))


@router.get("/templates/{kind}")
def template(kind: Literal["market", "documents", "macro"]):
    return FileResponse(PROJECT_ROOT / "egs/examples/alpha_mining_examples" / (kind + ".csv"), filename=kind + ".csv")


@router.get("/template-info/{kind}")
def template_info(kind: Literal["market", "documents", "macro"]):
    path = PROJECT_ROOT / "egs/examples/alpha_mining_examples" / (kind + ".csv")
    return ok(
        {
            "kind": kind,
            "csv_header": path.read_text(encoding="utf-8").strip(),
            "download_url": "/api/v1/alpha/templates/" + kind,
            "data_rows": 0,
        }
    )


@router.get("/studies")
def studies():
    service = AlphaService()
    return ok(
        {
            "items": [
                {key: row[key] for key in ("id", "name", "mode", "status", "created_at")}
                for row in service.store.list("alpha_studies")
            ]
        }
    )


@router.post("/studies")
def create(payload: StudyRequest):
    return ok(AlphaService().create(payload.model_dump(exclude_none=True)))


@router.get("/studies/{study_id}")
def detail(study_id: int):
    return ok(AlphaService().detail(study_id))


@router.post("/studies/{study_id}/candidates")
def candidate(study_id: int, payload: CandidateRequest):
    return ok(AlphaService().candidate(study_id, payload.hypothesis, payload.implementation))


@router.post("/studies/{study_id}/seal")
def seal(study_id: int):
    return ok(AlphaService().seal(study_id))


@router.post("/studies/{study_id}/actions")
def action(study_id: int, payload: ActionRequest):
    return ok(AlphaService().start(study_id, payload.action, payload.candidate_id))


@router.post("/studies/{study_id}/cancel")
def cancel(study_id: int):
    return ok(AlphaService().cancel(study_id))


def event_rows(service: AlphaService, study_id: int, after: int) -> list[dict]:
    service.store.get("alpha_studies", study_id)
    rows = service.store.repo.db.query(
        "SELECT * FROM alpha_events WHERE study_id=? AND id>? ORDER BY id LIMIT ?",
        (study_id, after, config()["limits"]["event_limit"]),
    )
    return [{**row, "payload": json_loads(row["payload"], {})} for row in rows]


@router.get("/studies/{study_id}/events")
def events(study_id: int, after: int = 0):
    return ok({"items": event_rows(AlphaService(), study_id, after)})


@router.get("/studies/{study_id}/stream")
def stream(study_id: int, after: int = 0):
    service = AlphaService()
    service.store.get("alpha_studies", study_id)

    def actual_events():
        cursor = after
        while True:
            rows = event_rows(service, study_id, cursor)
            for row in rows:
                cursor = row["id"]
                yield {"type": "progress", "data": row}
            study = service.detail(study_id)
            if study["status"] not in {"discovering", "validating", "testing"}:
                if not rows or len(rows) < config()["limits"]["event_limit"]:
                    yield {"type": "result", "data": ok(study)}
                    return
            stream_pause(config()["limits"]["poll_seconds"])

    return StreamingResponse(sse_events(actual_events()), media_type="text/event-stream")


@router.post("/studies/{study_id}/run-stream")
def run_stream(study_id: int, payload: ActionRequest):
    AlphaService().start(study_id, payload.action, payload.candidate_id)
    return stream(study_id)


@router.post("/studies/{study_id}/reviews")
def review(study_id: int, payload: ReviewRequest):
    service = AlphaService()
    return ok(
        approve(
            service.store,
            study_id,
            payload.candidate_id,
            payload.track,
            payload.decision,
            payload.reviewer,
            payload.evidence,
        )
    )


@router.post("/studies/{study_id}/export")
def export(study_id: int, payload: ExportRequest):
    return ok(export_draft(AlphaService().store, study_id, payload.candidate_id, payload.configuration))


@router.get("/studies/{study_id}/files/{name}")
def artifact(study_id: int, name: str):
    path = AlphaService().store.artifact(study_id, name)
    if not path.is_file():
        raise invalid("研究产物尚未生成")
    return FileResponse(
        path,
        filename=name,
        content_disposition_type="inline" if name.endswith(".html") else "attachment",
        headers={"X-Content-Type-Options": "nosniff", "Cache-Control": "no-store"},
    )


@router.get("/studies/{study_id}/artifacts")
def artifacts(study_id: int):
    service = AlphaService()
    folder = service.store.artifact(study_id, "report.html").parent
    return ok(
        {
            "items": [
                {
                    "name": path.name,
                    "bytes": path.stat().st_size,
                    "download_url": f"/api/v1/alpha/studies/{study_id}/files/{path.name}",
                }
                for path in sorted(folder.iterdir())
                if path.is_file() and path.suffix != ".tmp"
            ]
            if folder.is_dir()
            else []
        }
    )


@router.get("/studies/{study_id}/artifact-text/{name}")
def artifact_text(study_id: int, name: str):
    path = AlphaService().store.artifact(study_id, name)
    if not path.is_file() or path.suffix not in {".md", ".py", ".html", ".json"}:
        raise invalid("请选择已生成的文本产物")
    maximum = config()["limits"]["max_response_chars"]
    text = path.read_text(encoding="utf-8")
    return ok(
        {
            "name": name,
            "content": text[:maximum],
            "truncated": len(text) > maximum,
            "download_url": f"/api/v1/alpha/studies/{study_id}/files/{name}",
        }
    )
