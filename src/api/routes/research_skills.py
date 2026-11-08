"""The same local executor is optional over REST; local CLI never calls this route."""

from threading import RLock, Thread

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from src.agent.providers import provider_catalog
from src.agent.skill_runner.catalog import preview, settings
from src.agent.skill_runner.service import LocalSkillService
from src.api.schemas.common import ok

from .file_previews import require_same_origin
from .strategy_pipelines import PipelineRoute

router = APIRouter(
    tags=["Agent后端与研究Skills"], dependencies=[Depends(require_same_origin)], route_class=PipelineRoute
)
ACTIVE: set[str] = set()
LOCK = RLock()


@router.get("/agent-providers")
def providers(probe: bool = False):
    return ok({"providers": provider_catalog(probe=probe)})


@router.get("/research-skills")
def catalog():
    return ok({"workflows": settings()["workflows"], "local_entrypoint": "egs/entrypoints/skills.py"})


@router.post("/research-skills/preview")
def inspect(payload: dict):
    try:
        return ok(preview(payload))
    except (ValueError, OSError, KeyError) as exc:
        raise HTTPException(422, str(exc)) from exc


@router.post("/research-skills/runs")
def start(payload: dict):
    if payload.get("imports"):
        raise HTTPException(422, "远程模式须先通过已有数据导入接口上传数据，再提供ID")
    service = LocalSkillService()
    with LOCK:
        if len(ACTIVE) >= settings()["limits"]["max_active_runs"]:
            raise HTTPException(429, "研究Skill并发预算已满")
        row = service.register(payload)
        ACTIVE.add(row["run_id"])

    def execute():
        try:
            service.execute(row["run_id"])
        finally:
            with LOCK:
                ACTIVE.discard(row["run_id"])

    Thread(target=execute, daemon=True, name="research-skill-" + row["run_id"]).start()
    return ok(row)


@router.get("/research-skills/runs/{run_id}")
def detail(run_id: str):
    return ok(LocalSkillService().store.get(run_id))


@router.get("/research-skills/runs/{run_id}/events")
def events(run_id: str):
    return ok({"items": LocalSkillService().store.events(run_id)})


@router.post("/research-skills/runs/{run_id}/cancel")
def cancel(run_id: str):
    return ok(LocalSkillService().store.cancel(run_id))


@router.get("/research-skills/runs/{run_id}/files")
def files(run_id: str):
    return ok({"items": LocalSkillService().store.files(run_id)})


@router.get("/research-skills/runs/{run_id}/files/{name}")
def artifact(run_id: str, name: str):
    entries = LocalSkillService().store.files(run_id)
    entry = next((row for row in entries if row["name"] == name), None)
    if entry is None:
        raise HTTPException(404, "产物不存在")
    return FileResponse(
        entry["path"],
        headers={
            "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; frame-ancestors 'self'",
            "X-Content-Type-Options": "nosniff",
        },
    )
