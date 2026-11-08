"""Project settings and local credentials for explicit telemetry enablement."""

import os
from functools import lru_cache

import yaml

from src.core import env_file
from src.core.config import PROJECT_ROOT
from src.core.env_file import resolve_env_value


@lru_cache(maxsize=1)
def observation_config() -> dict:
    return yaml.safe_load((PROJECT_ROOT / "egs/config/models/observability.yaml").read_text(encoding="utf-8"))["langfuse"]


def enabled() -> bool:
    raw = os.environ.get("ALL_IN_ONE_LANGFUSE_ENABLED")
    if raw is None:
        files = (env_file.ENV_FILE,)
        stamp = tuple((str(p), p.stat().st_mtime_ns if p.is_file() else 0) for p in files)
        raw = _enabled_value(stamp)
    return str(raw).lower() in {"true", "1", "yes", "on"} if raw else bool(observation_config()["enabled"])


@lru_cache(maxsize=8)
def _enabled_value(stamp: tuple) -> str:
    return resolve_env_value("ALL_IN_ONE_LANGFUSE_ENABLED")


def settings() -> dict:
    cfg = dict(observation_config())
    capture = resolve_env_value("ALL_IN_ONE_LANGFUSE_CAPTURE_CONTENT")
    if capture:
        cfg["capture_content"] = capture.lower() in {"true", "1", "yes", "on"}
    cfg["environment"] = resolve_env_value("ALL_IN_ONE_LANGFUSE_ENVIRONMENT") or cfg["environment"]
    cfg["public_key"] = resolve_env_value("LANGFUSE_PUBLIC_KEY")
    cfg["secret_key"] = resolve_env_value("LANGFUSE_SECRET_KEY")
    cfg["base_url"] = resolve_env_value("LANGFUSE_BASE_URL")
    return cfg
