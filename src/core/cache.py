"""Small in-process TTL cache."""

import time
from threading import RLock
from typing import Any

from src.core.security_config import security_config


class TTLCache:
    def __init__(self) -> None:
        self._items: dict[str, tuple[float, Any]] = {}
        self._lock = RLock()

    def get(self, key: str) -> Any | None:
        with self._lock:
            item = self._items.get(key)
            if item is None:
                return None
            expires_at, value = item
            if expires_at < time.time():
                self._items.pop(key, None)
                return None
            return value

    def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        with self._lock:
            expired = [name for name, (deadline, _) in self._items.items() if deadline <= time.time()]
            for name in expired:
                self._items.pop(name, None)
            if key not in self._items and len(self._items) >= security_config()["limits"]["cache_items"]:
                self._items.pop(next(iter(self._items)))
            self._items[key] = (time.time() + ttl_seconds, value)

    def clear(self) -> None:
        with self._lock:
            self._items.clear()
