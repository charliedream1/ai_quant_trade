"""Shared backend capabilities; no process or network work during page construction."""

from functools import lru_cache

import yaml

from src.core.config import PROJECT_ROOT
from src.core.exceptions import BusinessError, ErrorCode


@lru_cache(maxsize=1)
def composer_config() -> dict:
    return yaml.safe_load((PROJECT_ROOT / "egs/ai_composer.yaml").read_text(encoding="utf-8"))


def normalize_backend(value: str | None) -> str:
    value = str(value or "generic_agent").lower().replace("-", "_").replace(" ", "_")
    for key, profile in composer_config()["backends"].items():
        if value == key or value in profile["aliases"]:
            return key
    return value


def validate_selection(payload: dict) -> dict:
    backend = normalize_backend(payload.get("backend"))
    permission = payload.get("access_mode") or "read-only"
    effort = payload.get("reasoning_effort") or ""
    profile = composer_config()["backends"].get(backend)
    if permission not in composer_config()["permissions"] or (profile and permission not in profile["permissions"]):
        raise BusinessError(ErrorCode.INVALID_PARAM, "所选后端不支持此访问权限")
    if profile and effort not in profile["efforts"]:
        raise BusinessError(ErrorCode.INVALID_PARAM, "所选后端不支持此思考强度")
    return {**payload, "backend": backend, "access_mode": permission, "reasoning_effort": effort}
