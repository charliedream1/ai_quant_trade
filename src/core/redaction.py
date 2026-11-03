"""Recursive public representations; never return credential-bearing configuration."""

import os
import re
from functools import lru_cache
from urllib.parse import urlsplit, urlunsplit

from dotenv import dotenv_values

from src.core.config import PROJECT_ROOT

SENSITIVE = re.compile(
    r"(?:api.?key|(?:token|secret|password|authorization|credential|cookie)$|(?:^|[_.-])(?:token|secret|password|authorization|credential|cookie)[_.-])",
    re.I,
)
MASK = "<configured>"


@lru_cache(maxsize=8)
def _file_secrets(stamp: tuple) -> tuple[str, ...]:
    values = {}
    for name in (".env", ".llm_env"):
        values.update(dotenv_values(PROJECT_ROOT / name))
    return tuple(str(value) for key, value in values.items() if value and len(value) >= 6 and SENSITIVE.search(key))


def secret_values() -> tuple[str, ...]:
    stamps = tuple(
        (PROJECT_ROOT / name).stat().st_mtime_ns if (PROJECT_ROOT / name).exists() else 0
        for name in (".env", ".llm_env")
    )
    environment = tuple(value for key, value in os.environ.items() if len(value) >= 6 and SENSITIVE.search(key))
    values = {*_file_secrets(stamps), *environment}
    values.update(value.split(" ", 1)[1] for value in tuple(values) if value.lower().startswith("bearer "))
    return tuple(sorted(values, key=len, reverse=True))


def redact_text(value: str) -> str:
    text = str(value)
    for secret in secret_values():
        text = text.replace(secret, MASK)
    text = re.sub(r"(?i)(bearer\s+)[\w.\-~+/=]+", r"\1<configured>", text)
    text = re.sub(r"(?i)((?:api[_-]?key|token|password|secret)=)[^\s&\"']+", r"\1<configured>", text)
    return text


def redact(value, key: str = ""):
    if SENSITIVE.search(key) and not key.lower().endswith(("_env", "_configured", "_name")):
        return MASK if value else value
    if isinstance(value, dict):
        return {str(name): redact(item, str(name)) for name, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [redact(item) for item in value]
    if isinstance(value, str):
        text = redact_text(value)
        if "://" in text:
            try:
                parsed = urlsplit(text)
                if parsed.username or parsed.password:
                    text = urlunsplit(
                        (parsed.scheme, parsed.netloc.rsplit("@", 1)[-1], parsed.path, parsed.query, parsed.fragment)
                    )
            except ValueError:
                pass
        return text
    return value if isinstance(value, (int, float, bool, type(None))) else str(value)
