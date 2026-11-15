"""Explicit real-model policy for interactive assistants, independent of market data mode."""

from contextlib import contextmanager
from contextvars import ContextVar
from urllib.parse import urlsplit

from src.core.exceptions import BusinessError, ErrorCode
from src.core.repository import Repository
from src.core.workspace_config import workspace_config

REQUIRE_REAL_MODEL: ContextVar[bool] = ContextVar("require_real_model", default=False)


def real_profile(row: dict) -> bool:
    policy = workspace_config()["assistant"]
    name = str(row.get("model_name") or "").strip().lower()
    scheme = urlsplit(str(row.get("base_url") or "")).scheme.lower()
    return (
        bool(name)
        and not any(name == token or name.startswith(token + "-") for token in policy["excluded_models"])
        and scheme in {"http", "https"}
        and scheme not in policy["excluded_schemes"]
    )


def real_model(name: str = "") -> dict:
    rows = Repository().db.query("SELECT * FROM llm_models WHERE enabled=1 ORDER BY is_default DESC,id DESC")
    selected = next((row for row in rows if real_profile(row) and (not name or row["model_name"] == name)), None)
    if selected is None:
        raise BusinessError(ErrorCode.LLM_ERROR, workspace_config()["assistant"]["messages"]["model_missing"])
    return selected


@contextmanager
def require_real_model():
    token = REQUIRE_REAL_MODEL.set(True)
    try:
        yield
    finally:
        REQUIRE_REAL_MODEL.reset(token)
