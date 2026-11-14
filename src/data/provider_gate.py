"""A bounded cross-process gate coordinates application-owned provider requests."""

import os
from contextlib import contextmanager
from threading import Lock
from time import monotonic, sleep

from filelock import FileLock, Timeout
from requests.exceptions import Timeout as RequestTimeout

from src.core.config import get_settings

THREAD_GATE = Lock()


@contextmanager
def eastmoney_gate(interval, jitter):
    cfg = get_settings()
    root = (cfg.data_dir / "provider_locks").resolve()
    if not root.is_relative_to(cfg.data_dir.resolve()):
        raise ValueError("Provider gate escapes the configured private data directory")
    root.mkdir(parents=True, exist_ok=True)
    stamp = root / "eastmoney.last"
    if not THREAD_GATE.acquire(timeout=cfg.data_timeout_seconds):
        raise RequestTimeout("Provider thread wait exceeded its budget")
    try:
        with FileLock(str(root / "eastmoney.lock"), timeout=cfg.data_timeout_seconds):
            try:
                previous = float(stamp.read_text(encoding="utf-8")) if stamp.exists() else 0
            except (ValueError, OSError):
                previous = 0
            if previous > monotonic():
                previous = 0
            wait = max(interval - (monotonic() - previous), 0) + jitter
            if wait > 0:
                sleep(wait)
            pending = stamp.with_suffix(".pending")
            pending.write_text(str(monotonic()), encoding="utf-8")
            os.replace(pending, stamp)
            yield
    except Timeout as exc:
        raise RequestTimeout("Provider concurrency wait exceeded its budget") from exc
    finally:
        THREAD_GATE.release()
