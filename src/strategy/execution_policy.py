"""Unreviewed Python never executes; reviewed custom sources use a bounded worker."""

import hashlib
import json
import os
from functools import lru_cache
from pathlib import Path

import yaml

from src.core.config import PROJECT_ROOT, get_settings
from src.core.exceptions import BusinessError, ErrorCode
from src.core.timeutil import utc_now_iso


@lru_cache(maxsize=1)
def execution_config() -> dict:
    return yaml.safe_load((PROJECT_ROOT / "egs/strategy_execution.yaml").read_text(encoding="utf-8"))


def source_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bundled_source(path: Path, source: bytes | None = None) -> bool:
    content = (path.read_bytes() if source is None else source).decode("utf-8").replace("\r\n", "\n")
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    prior = yaml.safe_load((PROJECT_ROOT / "egs/trusted_strategy_sources.yaml").read_text(encoding="utf-8"))["sources"]
    if digest in prior:
        return True
    return any(
        hashlib.sha256(item.read_text(encoding="utf-8").encode("utf-8")).hexdigest() == digest
        for folder in ("strategy_examples", "strategy_entrypoints")
        for item in (PROJECT_ROOT / "egs" / folder).glob("*.py")
    )


def review_path(digest: str) -> Path:
    if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
        raise ValueError("非法源码SHA256")
    path = get_settings().data_dir / "strategies/reviews" / (digest + ".json")
    if os.name == "nt":
        # Keep the complete SHA256 while supporting deeply nested Windows roots.
        absolute = str(path.resolve())
        if not absolute.startswith("\\\\?\\"):
            absolute = "\\\\?\\UNC\\" + absolute[2:] if absolute.startswith("\\\\") else "\\\\?\\" + absolute
        return Path(absolute)
    return path


def review_source(path: Path, expected: str, reviewer: str, *, generated=False) -> dict:
    digest = source_digest(path)
    if digest != expected or not reviewer.strip():
        raise BusinessError(ErrorCode.STRATEGY_INVALID, execution_config()["messages"]["changed"])
    record = {
        "sha256": digest,
        "reviewer": reviewer.strip(),
        "created_at": utc_now_iso(),
        "execution": "platform_generated" if generated else "reviewed_worker",
        "untrusted_sandbox": False,
    }
    target = review_path(digest)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
    return record


def execution_kind(path: Path, source: bytes | None = None) -> str:
    content = path.read_bytes() if source is None else source
    if bundled_source(path, content):
        return "bundled"
    digest = hashlib.sha256(content).hexdigest()
    record_path = review_path(digest)
    if not record_path.is_file():
        raise BusinessError(ErrorCode.STRATEGY_INVALID, execution_config()["messages"]["review"])
    record = json.loads(record_path.read_text(encoding="utf-8"))
    if record.get("sha256") != digest:
        raise BusinessError(ErrorCode.STRATEGY_INVALID, execution_config()["messages"]["changed"])
    return str(record["execution"])
