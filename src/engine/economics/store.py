"""Content-addressed observations preserve first-seen times and raw revisions."""

import hashlib
import json
import os
import re
from pathlib import Path
from threading import RLock
from uuid import uuid4

from filelock import FileLock

from src.core.config import get_settings

from .config import economics_config

LOCK = RLock()


def digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()).hexdigest()


class EconomicStore:
    def __init__(self, root: Path | None = None):
        self.root = root or Path(get_settings().data_dir) / "economics"

    def read(self, identifier: str) -> dict:
        if not re.fullmatch(r"[a-f0-9]{64}", identifier):
            raise ValueError("Invalid economic snapshot identifier")
        try:
            value = json.loads((self.root / "snapshots" / (identifier + ".json")).read_text(encoding="utf-8"))
        except OSError:
            raise ValueError("Economic snapshot not found") from None
        if (
            value.get("snapshot_id") != identifier
            or digest({key: item for key, item in value.items() if key != "snapshot_id"}) != identifier
        ):
            raise ValueError("Economic snapshot integrity check failed")
        return value

    def save(self, value: dict) -> dict:
        value = {key: item for key, item in value.items() if key != "snapshot_id"}
        identifier = digest(value)
        result = {**value, "snapshot_id": identifier}
        with LOCK:
            path = self.root / "snapshots" / (identifier + ".json")
            if not path.exists():
                self._write(path, result)
        return result

    def cached(self, key: str) -> dict | None:
        path = self.root / "cache" / (key + ".json")
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None

    def cache(self, key: str, value: dict) -> None:
        with LOCK:
            self._write(self.root / "cache" / (key + ".json"), value)

    def first_seen(self, revision: str, observed_at: str) -> str:
        self.root.mkdir(parents=True, exist_ok=True)
        key = digest({"revision": revision})
        with FileLock(
            str(self.root / ".revision.lock"), timeout=economics_config()["defaults"]["revision_lock_seconds"]
        ):
            record = self.cached(key)
            if record is None:
                record = {"first_seen_at": observed_at}
                self.cache(key, record)
            return str(record["first_seen_at"])

    @staticmethod
    def _write(path: Path, value: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(path.name + "." + uuid4().hex + ".tmp")
        temporary.write_text(json.dumps(value, ensure_ascii=False, allow_nan=False), encoding="utf-8")
        os.replace(temporary, path)
