"""Safe import and masked inspection for local environment files."""

from __future__ import annotations

import os
import re
from io import StringIO
from pathlib import Path
from typing import Any
from uuid import uuid4

from dotenv import dotenv_values

from src.core.config import PROJECT_ROOT
from src.core.crypto import mask_secret
from src.core.file_lock import file_lock
from src.core.security_config import security_config

ENV_FILE = PROJECT_ROOT / ".env"
ENV_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
MAX_ENV_FILE_BYTES = 128 * 1024


def read_env_values(path: Path | None = None) -> dict[str, str]:
    path = path or ENV_FILE
    if not path.exists():
        return {}
    return _parse_env(path.read_text(encoding="utf-8-sig"))


def import_env_file(
    upload_path: str | Path, overwrite: bool = False, target: Path | None = None, *, restricted: bool = False
) -> dict[str, Any]:
    target = target or ENV_FILE
    source = Path(upload_path)
    if source.suffix.lower() not in {".env", ".llm_env", ".secrets", ".txt"}:
        raise ValueError("仅支持 .env、.llm_env、.secrets 或 .txt 文件")
    if source.stat().st_size > MAX_ENV_FILE_BYTES:
        raise ValueError("环境变量文件不能超过 128 KB")

    incoming = _parse_env(source.read_text(encoding="utf-8-sig"))
    if not incoming:
        raise ValueError("文件中没有有效的环境变量")
    if restricted:
        for key in incoming:
            validate_import_name(key)
    with file_lock(target):
        return _merge_environment(target, incoming, overwrite)


def _merge_environment(target: Path, incoming: dict[str, str], overwrite: bool) -> dict[str, Any]:
    current = read_env_values(target)
    imported = []
    skipped = []
    for key, value in incoming.items():
        if key in current and not overwrite:
            skipped.append(key)
            continue
        current[key] = value
        imported.append(key)

    _write_env(target, current)
    for key in imported:
        os.environ[key] = current[key]
    return {"imported": imported, "skipped": skipped, "total": len(current), "path": target.name}


def save_env_value(name: str, value: str, target: Path | None = None) -> None:
    target = target or ENV_FILE
    key = str(name or "").strip()
    validate_env_name(key)
    with file_lock(target):
        values = read_env_values(target)
        values[key] = str(value)
        _write_env(target, values)
        os.environ[key] = str(value)


def delete_env_value(name: str, target: Path | None = None) -> dict[str, Any]:
    target = target or ENV_FILE
    key = validate_env_name(name)
    with file_lock(target):
        return _delete_value(key, target)


def _delete_value(key: str, target: Path) -> dict[str, Any]:
    values = read_env_values(target)
    existed_in_file = key in values
    if existed_in_file:
        values.pop(key, None)
        _write_env(target, values)
    existed_in_process = key in os.environ
    os.environ.pop(key, None)
    return {
        "name": key,
        "deleted": existed_in_file or existed_in_process,
        "file_deleted": existed_in_file,
        "process_deleted": existed_in_process,
        "path": target.name,
    }


def validate_env_name(name: str) -> str:
    key = str(name or "").strip()
    if not ENV_NAME.fullmatch(key):
        raise ValueError("环境变量名格式无效")
    return key


def validate_import_name(name: str) -> str:
    key = validate_env_name(name)
    cfg = security_config()["uploads"]
    if any(key.startswith(prefix) for prefix in cfg["environment_blocked_prefixes"]) or not (
        key in cfg["environment_allowed_names"] or key.endswith(tuple(cfg["environment_allowed_suffixes"]))
    ):
        raise ValueError(security_config()["messages"]["environment"])
    return key


def env_status(name: str, target: Path | None = None) -> dict[str, Any]:
    target = target or ENV_FILE
    key = validate_env_name(name)
    file_values = read_env_values(target)
    locations = []
    if key in os.environ:
        locations.append("process")
    if key in file_values:
        locations.append(target.name)
    resolved = os.environ[key] if key in os.environ else file_values.get(key) or ""
    return {
        "name": key,
        "configured": bool(resolved),
        "masked_value": mask_secret(resolved),
        "locations": locations,
        "source": locations[0] if locations else "",
    }


def default_key_name(name: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9]+", "_", str(name or "MODEL")).strip("_").upper() or "MODEL"
    return f"LLM_{normalized}_API_KEY"


def masked_env_rows(path: Path | None = None) -> list[dict[str, str]]:
    path = path or ENV_FILE
    return [
        {"name": key, "value": mask_secret(value), "source": path.name}
        for key, value in sorted(read_env_values(path).items())
    ]


def resolve_env_value(name: str) -> str:
    key = validate_env_name(name)
    if key in os.environ:
        return os.environ[key]
    llm_values = read_env_values()
    if key in llm_values:
        return llm_values[key]
    return ""


def _parse_env(text: str) -> dict[str, str]:
    if "\x00" in text:
        raise ValueError("环境变量文件包含无效字符")
    parsed = dotenv_values(stream=StringIO(text))
    values: dict[str, str] = {}
    for raw_key, raw_value in parsed.items():
        key = str(raw_key or "").strip()
        if not ENV_NAME.fullmatch(key):
            raise ValueError(f"无效的环境变量名：{key or '(空)'}")
        if raw_value is None:
            raise ValueError(f"环境变量 {key} 缺少值")
        values[key] = str(raw_value)
    return values


def _quote(value: str) -> str:
    return "'" + value.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n") + "'"


def _write_env(target: Path, values: dict[str, str]) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name + "." + uuid4().hex + ".tmp")
    descriptor = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        stream.write("".join(f"{key}={_quote(value)}\n" for key, value in sorted(values.items())))
    temporary.replace(target)
    if os.name != "nt":
        target.chmod(0o600)
