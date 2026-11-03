"""Project-local SQLite cache of scalar factors, never labels or Python objects."""

import math
import sqlite3
from contextlib import closing
from hashlib import sha256
from pathlib import Path

from src.core.config import PROJECT_ROOT, get_settings

from .config import factor_config, factor_error


class FactorCache:
    def __init__(self, path: Path | None = None):
        cfg = factor_config()
        self.path = (path or get_settings().data_dir / cfg["cache"]["relative_path"]).resolve()
        if not self.path.is_relative_to(PROJECT_ROOT.resolve()):
            raise factor_error("cache_invalid")
        self.timeout = cfg["limits"]["cache_timeout_seconds"]
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as db, db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS factor_values (key TEXT PRIMARY KEY, value REAL, checksum TEXT NOT NULL)"
            )

    def _connect(self):
        return sqlite3.connect(self.path, timeout=self.timeout)

    def get(self, keys: list[str]) -> dict[str, float | None]:
        result = {}
        with closing(self._connect()) as db:
            for key in keys:
                row = db.execute("SELECT value, checksum FROM factor_values WHERE key = ?", (key,)).fetchone()
                if row is None:
                    continue
                value, checksum = row
                if (value is not None and not math.isfinite(value)) or checksum != self._checksum(key, value):
                    raise factor_error("cache_invalid")
                result[key] = value
        return result

    def put(self, values: dict[str, float | None]) -> None:
        if not values:
            return
        with closing(self._connect()) as db, db:
            db.executemany(
                "INSERT OR REPLACE INTO factor_values(key, value, checksum) VALUES (?, ?, ?)",
                [(key, value, self._checksum(key, value)) for key, value in values.items()],
            )

    @staticmethod
    def _checksum(key: str, value: float | None) -> str:
        canonical = None if value is None else (0.0 if value == 0 else float(value))
        return sha256(f"{key}:{canonical!r}".encode()).hexdigest()
