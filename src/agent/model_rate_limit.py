"""Atomic rolling quotas and bounded in-flight leases shared by project processes."""

import hashlib
import os
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

from loguru import logger

from src.core.exceptions import BusinessError, ErrorCode
from src.core.llm_config import llm_config

from .model_budget import CallBudget
from .model_options import quota_identity


class ModelRateLimiter:
    def __init__(self, db_path: Path, config: dict):
        self.db_path = db_path
        self.config = config
        self.scope = hashlib.sha256(quota_identity(config).encode("utf-8")).hexdigest()

    @contextmanager
    def permit(self, budget: CallBudget):
        rpm, concurrency = int(self.config["rpm"]), int(self.config["max_concurrency"])
        if not rpm and not concurrency:
            yield 0.0
            return
        started = time.monotonic()
        token = uuid4().hex
        while True:
            remaining = budget.remaining()
            delay = self._try_acquire(token, remaining)
            if delay is None:
                break
            if not self.config["wait_on_limit"]:
                raise BusinessError(ErrorCode.LLM_ERROR, "本地模型请求限流", {"status": "local_rate_limited"})
            budget.wait(delay)
        wait_ms = (time.monotonic() - started) * 1000
        if wait_ms > llm_config()["rate_limit"]["poll_seconds"] * 1000:
            logger.info("模型配额等待 | model_id={} wait_ms={:.1f}", self.config.get("id"), wait_ms)
        try:
            budget.remaining()
            yield wait_ms
        finally:
            connection = self._connect()
            try:
                with connection:
                    connection.execute("UPDATE llm_request_slots SET lease_until=0 WHERE token=?", (token,))
            finally:
                connection.close()

    def _connect(self, remaining: float | None = None):
        timeout = llm_config()["rate_limit"]["database_busy_seconds"]
        if remaining is not None:
            timeout = min(timeout, remaining, llm_config()["rate_limit"]["poll_seconds"])
        return sqlite3.connect(self.db_path, timeout=timeout)

    def _try_acquire(self, token: str, remaining: float) -> float | None:
        policy = llm_config()["rate_limit"]
        now = time.time()
        cutoff = now - policy["window_seconds"]
        connection = self._connect(remaining)
        try:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("DELETE FROM llm_request_slots WHERE admitted_at<=? AND lease_until<=?", (cutoff, now))
            rows = connection.execute(
                "SELECT admitted_at, lease_until, owner_pid FROM llm_request_slots WHERE scope=?", (self.scope,)
            ).fetchall()
            recent = [row[0] for row in rows if row[0] > cutoff]
            active = sum(row[1] > now for row in rows)
            rpm = self.config["rpm"]
            concurrency = self.config["max_concurrency"]
            if rpm and len(recent) >= rpm:
                return min(policy["poll_seconds"], max(0, min(recent) + policy["window_seconds"] - now))
            if concurrency and active >= concurrency:
                return policy["poll_seconds"]
            lease = now + remaining + policy["lease_grace_seconds"]
            connection.execute(
                "INSERT INTO llm_request_slots(token,scope,admitted_at,lease_until,owner_pid) VALUES(?,?,?,?,?)",
                (token, self.scope, now, lease, os.getpid()),
            )
            return None
        except sqlite3.OperationalError as exc:
            if "locked" in str(exc).lower() or "busy" in str(exc).lower():
                return policy["poll_seconds"]
            raise
        finally:
            connection.commit()
            connection.close()
