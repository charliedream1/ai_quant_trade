"""Filter telemetry before SDK construction, including exception and path content."""

import json
import os
import re
from contextlib import contextmanager
from contextvars import ContextVar

from src.core.redaction import SENSITIVE, redact_text, secret_values

from .config import observation_config

SECRET_SNAPSHOT: ContextVar[tuple[str, ...] | None] = ContextVar("observation_secret_snapshot", default=None)


@contextmanager
def privacy_scope(*, refresh=False):
    """Resolve current credential values once per operation; children share its safe snapshot."""
    if SECRET_SNAPSHOT.get() is not None and not refresh:
        yield
        return
    values = set(secret_values())
    values.update(value for key, value in os.environ.items() if key.upper().endswith("_KEY") and len(value) >= 6)
    token = SECRET_SNAPSHOT.set(tuple(sorted(values, key=len, reverse=True)))
    try:
        yield
    finally:
        SECRET_SNAPSHOT.reset(token)


def clean_text(value: str, maximum: int) -> str:
    snapshot = SECRET_SNAPSHOT.get()
    if snapshot is None:
        with privacy_scope():
            return clean_text(value, maximum)
    text = redact_text(value, secrets=snapshot)
    text = re.sub(r"(?i)\b[a-z]:[\\/][^\s\"'<>]+", "<local-path>", text)
    text = re.sub(r"(?<![\w:/])/(?!/)[^\s\"'<>]+", "<local-path>", text)
    text = re.sub(r"\\\\[^\s\"'<>]+", "<local-path>", text)
    text = re.sub(r"(?i)(https?://)[^\s/@]+:[^\s/@]+@", r"\1<credentials>@", text)
    return text[:maximum]


def content(value, *, _depth=0, **_):
    cfg = observation_config()
    maximum = cfg["max_content_chars"]
    if _depth >= cfg["max_content_depth"]:
        return "<depth-limit>"
    if isinstance(value, dict):
        return {
            str(k): "<redacted>" if SENSITIVE.search(str(k)) else content(v, _depth=_depth + 1)
            for k, v in list(value.items())[: cfg["max_collection_items"]]
        }
    if isinstance(value, (list, tuple)):
        return [content(v, _depth=_depth + 1) for v in value[: cfg["max_collection_items"]]]
    if isinstance(value, str):
        return clean_text(value, maximum)
    return value if value is None or isinstance(value, (bool, int, float)) else type(value).__name__


def metadata(value: dict | None) -> dict:
    cfg = observation_config()
    result = {}
    for key, item in (value or {}).items():
        if key not in cfg["metadata_fields"]:
            continue
        if not isinstance(item, (str, bool, int, float, type(None))) and not (
            key == "argument_keys" and isinstance(item, list) and all(isinstance(v, str) for v in item)
        ):
            continue
        safe = content(item)
        encoded = json.dumps(safe, ensure_ascii=False)
        result[key] = (
            safe if len(encoded) <= cfg["max_metadata_chars"] else clean_text(encoded, cfg["max_metadata_chars"] - 2)
        )
    return result


def sdk_mask(*, data, **_):
    """Last SDK-boundary filter; app instrumentation never exports headers or configuration."""
    return content(data)
