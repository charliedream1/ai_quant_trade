"""Viewer policies stay separate from application code."""

import hashlib
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from src.core.config import PROJECT_ROOT
from src.core.exceptions import BusinessError, ErrorCode


@lru_cache(maxsize=1)
def preview_config() -> dict[str, Any]:
    return yaml.safe_load((PROJECT_ROOT / "egs/config/knowledge/file_preview.yaml").read_text(encoding="utf-8"))


def file_kind(name: str) -> str:
    suffix = Path(name).suffix.lower()
    for kind, suffixes in preview_config()["formats"].items():
        if suffix in suffixes:
            return str(kind)
    raise BusinessError(ErrorCode.INVALID_PARAM, "不支持此文件格式")


def digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def decode_text(content: bytes) -> str:
    for encoding in preview_config()["text_encodings"]:
        try:
            return content.decode(encoding)
        except UnicodeError:
            continue
    raise BusinessError(ErrorCode.INVALID_PARAM, "无法识别文本编码，请使用UTF-8")
