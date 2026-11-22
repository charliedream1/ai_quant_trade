"""JSON-only cross-process observations; OS locks are released by cancelled workers."""

import hashlib
import json
import os
from time import time
from uuid import uuid4

from filelock import FileLock

from src.core.config import get_settings
from src.core.logger import get_logger
from src.core.page_work import policy
from src.data import current_market

from .view_primitives import _today_key


def observation_path(key):
    settings = get_settings()
    cfg = policy()
    scope = [
        str(settings.db_path.resolve()),
        settings.data_mode,
        current_market(),
        _today_key(),
        os.environ.get("ALL_IN_ONE_PAGE_CACHE_EPOCH", str(os.getpid())),
        key,
    ]
    digest = hashlib.sha256(json.dumps(scope, sort_keys=True).encode()).hexdigest()
    root = settings.data_dir / cfg["source_cache_directory"]
    root.mkdir(parents=True, exist_ok=True)
    return root / (digest + ".json")


def cached_observation(key):
    path = observation_path(key)
    try:
        if path.exists() and path.stat().st_size <= policy()["source_cache_max_bytes"]:
            return json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        pass
    return None


def shared_observation(key, loader, refresh=False, *, max_age_seconds=None):
    cfg = policy()
    path = observation_path(key)
    requested = time()
    with FileLock(str(path.with_suffix(".lock")), timeout=cfg["source_cache_lock_seconds"]):
        stamp = path.stat().st_mtime if path.exists() else 0
        fresh = max_age_seconds is None or requested - stamp <= max_age_seconds
        if stamp and fresh and (not refresh or stamp >= requested or max_age_seconds is not None):
            try:
                if path.stat().st_size <= cfg["source_cache_max_bytes"]:
                    return json.loads(path.read_text(encoding="utf-8"))
            except (ValueError, OSError):
                pass
        get_logger("frontend.services").debug("UI snapshot load | key={} refresh={}", json.dumps(key), refresh)
        result = loader()
        content = json.dumps(result, ensure_ascii=False, allow_nan=False)
        if len(content.encode()) <= cfg["source_cache_max_bytes"]:
            temporary = path.parent / (uuid4().hex + ".pending")
            temporary.write_text(content, encoding="utf-8")
            os.replace(temporary, path)
        return result
