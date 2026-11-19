"""Private daily metadata reuse with cancellable cross-process discovery ownership."""

import hashlib
import json
import os
import re
from datetime import datetime
from uuid import uuid4
from zoneinfo import ZoneInfo

from filelock import FileLock, Timeout

from src.core.config import get_settings
from src.core.logger import get_logger
from src.core.page_work import check
from src.core.redaction import redact
from src.core.stream_control import stream_cancelled


def day(policy):
    return datetime.now(ZoneInfo(policy["timezone"])).date().isoformat()


def uncached(backend, policy, load):
    get_logger("ui.catalog").warning("CLI catalogue cache storage unavailable | backend={}", backend)
    check()
    if stream_cancelled():
        raise InterruptedError("Metadata request cancelled")
    result = safe_result(load(), policy)
    check()
    if stream_cancelled():
        raise InterruptedError("Metadata request cancelled")
    return {**result, "cache_reused": False}


def safe_result(value, policy):
    """Keep only discovery fields and scrub credential values and local paths."""
    fields = ("backend", "rows", "status", "source", "updated", "available", "stale", "last_attempt")
    result = {key: value[key] for key in fields if key in value}
    result["rows"] = [
        {key: row[key] for key in ("id", "name", "billing", "source", "efforts") if key in row} for row in value["rows"]
    ]
    encoded = json.dumps(redact(result), ensure_ascii=False)
    # Paths can occur inside labels, not just as an entire field value.
    encoded = re.sub(r"[A-Za-z]:[\\/][^\s\"<>]+|/(?:home|Users)/[^\s\"<>]+", policy["local_path_label"], encoded)
    return json.loads(encoded)


def read(path, backend, policy):
    try:
        if path.stat().st_size > policy["max_bytes"]:
            return None
        entry = json.loads(path.read_text(encoding="utf-8"))
        value = entry["result"]
        if (
            entry["version"] != policy["version"]
            or value["backend"] != backend
            or value["status"] not in {"ready", "failed", "empty", "missing", "unsupported"}
            or not isinstance(value["rows"], list)
            or len(value["rows"]) > policy["max_models"]
            or any(
                not isinstance(row, dict)
                or any(not isinstance(row.get(key), str) for key in ("id", "name", "billing"))
                or (
                    row.get("efforts") is not None
                    and (
                        not isinstance(row["efforts"], list)
                        or any(not isinstance(item, str) for item in row["efforts"])
                    )
                )
                for row in value["rows"]
            )
            or any(not isinstance(value.get(key), str) for key in ("source", "updated"))
            or not isinstance(entry["attempt"], str)
            or not isinstance(entry["day"], str)
        ):
            return None
        entry["result"] = safe_result(value, policy)
        return entry
    except (OSError, ValueError, KeyError, TypeError):
        return None


def reuse(scope, backend, refresh, policy, load):
    key = hashlib.sha256(json.dumps(scope, sort_keys=True).encode()).hexdigest()
    directory = get_settings().data_dir / policy["directory"]
    try:
        directory.mkdir(parents=True, exist_ok=True)
    except OSError:
        return uncached(backend, policy, load)
    path = directory / (key + ".json")
    initial = read(path, backend, policy)

    def cached(entry):
        return {**entry["result"], "cache_reused": True}

    check()
    if stream_cancelled():
        raise InterruptedError("Metadata request cancelled")
    if initial and not refresh and initial["day"] == day(policy):
        return cached(initial)
    lock = FileLock(str(directory / (key + ".lock")))
    # FileLock owns both thread and process coordination; short waits retain cancellation.
    waited = 0.0
    while True:
        check()
        if stream_cancelled():
            raise InterruptedError("Metadata wait cancelled")
        try:
            lock.acquire(timeout=policy["poll_seconds"])
            break
        except Timeout:
            waited += policy["poll_seconds"]
            if waited >= policy["wait_seconds"]:
                raise TimeoutError("Metadata discovery is still running; retry shortly") from None
        except OSError:
            return uncached(backend, policy, load)
    try:
        check()
        current = read(path, backend, policy)
        initial_attempt = initial["attempt"] if initial else None
        if current and current["day"] == day(policy) and (not refresh or current["attempt"] != initial_attempt):
            return cached(current)
        result = safe_result(load(), policy)
        check()
        if stream_cancelled():
            raise InterruptedError("Metadata request cancelled")
        if result["status"] == "failed" and current and current["result"]["rows"]:
            result = {**current["result"], "status": "failed", "stale": True, "last_attempt": result["updated"]}
        entry = {"version": policy["version"], "day": day(policy), "attempt": uuid4().hex, "result": result}
        data = json.dumps(entry, ensure_ascii=False)
        if len(data.encode()) <= policy["max_bytes"]:
            try:
                temporary = path.with_suffix(".tmp")
                temporary.write_text(data, encoding="utf-8")
                os.replace(temporary, path)
            except OSError:
                get_logger("ui.catalog").warning("CLI catalogue cache write unavailable | backend={}", backend)
        return {**result, "cache_reused": False}
    finally:
        lock.release()
