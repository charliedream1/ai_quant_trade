"""Knowledge policy shared by importers, file storage and retrieval."""

from functools import lru_cache
from typing import Any

import yaml

from src.core.config import PROJECT_ROOT
from src.core.exceptions import BusinessError, ErrorCode


@lru_cache(maxsize=1)
def knowledge_config() -> dict[str, Any]:
    return dict(yaml.safe_load((PROJECT_ROOT / "egs/config/knowledge/knowledge.yaml").read_text(encoding="utf-8")))


def library_name(value: Any = None) -> str:
    name = str(value or knowledge_config()["default_library"]).strip()
    if not name or len(name) > knowledge_config()["library_name_chars"] or any(ord(c) < 32 for c in name):
        raise BusinessError(ErrorCode.INVALID_PARAM, "知识库名称为空、过长或包含控制字符")
    return name


def chunk_length(value: Any = None) -> int:
    policy = knowledge_config()
    try:
        size = int(value if value not in (None, "", 0) else policy["chunk_chars"])
    except (ValueError, TypeError) as exc:
        raise BusinessError(ErrorCode.INVALID_PARAM, "切分长度必须是整数") from exc
    if not policy["minimum_chunk_chars"] <= size <= policy["maximum_chunk_chars"]:
        raise BusinessError(ErrorCode.INVALID_PARAM, "切分长度超出配置范围")
    return size
