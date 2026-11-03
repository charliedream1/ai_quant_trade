"""System settings routes."""

from pathlib import Path
from typing import Annotated, Any
from uuid import uuid4

from fastapi import APIRouter, Body, File, UploadFile

from src.api.route_guards import ValidatedRoute
from src.api.schemas.common import ok
from src.core.async_work import blocking_call, read_upload
from src.core.env_file import delete_env_value, env_status, import_env_file, masked_env_rows
from src.core.security_config import security_config
from src.core.system_settings import global_settings_payload, save_global_settings

router = APIRouter(tags=["模型配置-系统设置"], route_class=ValidatedRoute)


@router.get("/settings")
def get_settings():
    return ok(global_settings_payload())


@router.put("/settings")
def save_settings(payload: Annotated[dict[str, Any], Body()]):
    return ok(save_global_settings(payload))


@router.get("/settings/environment")
def environment_variables():
    return ok(masked_env_rows())


@router.post("/settings/environment/check")
def check_environment_variable(payload: Annotated[dict[str, Any], Body()]):
    return ok(env_status(str(payload.get("name") or "")))


@router.delete("/settings/environment/{name}")
def delete_environment_variable(name: str):
    return ok({**delete_env_value(name), "variables": masked_env_rows()})


@router.post("/settings/environment/import")
async def import_environment_file(
    file: Annotated[UploadFile, File()],
    overwrite: bool = False,
):
    suffix = Path(file.filename or ".env").suffix or ".env"
    temporary = Path(get_settings_path()) / f"env-upload-{uuid4().hex}{suffix}"
    content = await read_upload(file, security_config()["uploads"]["environment_bytes"])
    await blocking_call(temporary.write_bytes, content)
    try:
        result = await blocking_call(import_env_file, temporary, overwrite=overwrite, restricted=True)
    finally:
        temporary.unlink(missing_ok=True)
    return ok({**result, "variables": masked_env_rows()})


def get_settings_path() -> str:
    from src.core.config import get_settings as runtime_settings

    path = runtime_settings().data_dir / "tmp"
    path.mkdir(parents=True, exist_ok=True)
    return str(path)
