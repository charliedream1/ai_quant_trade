"""SQLite leases establish task ownership across independent Web/CLI processes."""

import os
import sqlite3
import time
from threading import Event, Thread
from uuid import uuid4

from src.core.logger import get_logger
from src.core.repository import Repository
from src.core.security_config import security_config


class TaskLease:
    def __init__(self, kind: str, key, repo=None, limit: int | None = None):
        self.repo = repo or Repository()
        self.kind, self.key = kind, str(key)
        self.owner = str(os.getpid()) + ":" + uuid4().hex
        self.policy = security_config()["tasks"]
        self.stop = Event()
        self.poll_at, self.was_cancelled = 0.0, False
        now = time.time()
        with self.repo.db.transaction():
            previous = self.repo.db.query_one("SELECT * FROM task_leases WHERE kind=? AND task_key=?", (kind, self.key))
            if previous and previous["status"] == "running" and previous["expires"] > now:
                raise ValueError("该任务已有活动执行进程")
            if (
                limit is not None
                and self.repo.db.scalar(
                    "SELECT COUNT(*) FROM task_leases WHERE kind=? AND status='running' AND expires>?", (kind, now)
                )
                >= limit
            ):
                raise ValueError("任务队列已满，请等待现有任务完成")
            self.repo.db.execute(
                "INSERT INTO task_leases(kind,task_key,owner,expires,cancel_requested,status) VALUES(?,?,?,?,0,'running') "
                "ON CONFLICT(kind,task_key) DO UPDATE SET owner=excluded.owner,expires=excluded.expires,cancel_requested=0,status='running'",
                (kind, self.key, self.owner, now + self.policy["lease_seconds"]),
            )
        self.thread = Thread(target=self._heartbeat, daemon=True, name="task-lease-" + kind)
        try:
            self.thread.start()
        except Exception:
            self.repo.db.execute(
                "UPDATE task_leases SET status='finished',expires=? WHERE kind=? AND task_key=? AND owner=?",
                (time.time(), self.kind, self.key, self.owner),
            )
            raise

    def _heartbeat(self):
        while not self.stop.wait(self.policy["heartbeat_seconds"]):
            try:
                cursor = self.repo.db.execute(
                    "UPDATE task_leases SET expires=? WHERE kind=? AND task_key=? AND owner=? AND status='running'",
                    (time.time() + self.policy["lease_seconds"], self.kind, self.key, self.owner),
                )
                if cursor.rowcount != 1:
                    self.was_cancelled = True
                    return
            except (RuntimeError, OSError, sqlite3.Error):
                self.was_cancelled = True
                return

    def cancelled(self):
        if time.monotonic() >= self.poll_at:
            row = self.repo.db.query_one(
                "SELECT cancel_requested,owner FROM task_leases WHERE kind=? AND task_key=?", (self.kind, self.key)
            )
            self.was_cancelled = (
                self.was_cancelled or not row or row["owner"] != self.owner or bool(row["cancel_requested"])
            )
            self.poll_at = time.monotonic() + self.policy["cancel_poll_seconds"]
        return self.was_cancelled

    def close(self):
        self.stop.set()
        try:
            self.repo.db.execute(
                "UPDATE task_leases SET status='finished',expires=? WHERE kind=? AND task_key=? AND owner=?",
                (time.time(), self.kind, self.key, self.owner),
            )
        except (RuntimeError, OSError, sqlite3.Error) as exc:
            get_logger("task.lease").warning(
                "任务租约释放失败，将按到期时间回收 | kind={} error_type={}", self.kind, type(exc).__name__
            )
        finally:
            self.thread.join(timeout=self.policy["heartbeat_seconds"])


def lease_alive(kind: str, key, repo=None) -> bool:
    database = (repo or Repository()).db
    return bool(
        database.scalar(
            "SELECT COUNT(*) FROM task_leases WHERE kind=? AND task_key=? AND status='running' AND expires>?",
            (kind, str(key), time.time()),
        )
    )


def cancel_lease(kind: str, key, repo=None) -> bool:
    return (repo or Repository()).db.execute(
        "UPDATE task_leases SET cancel_requested=1 WHERE kind=? AND task_key=? AND status='running' AND expires>?",
        (kind, str(key), time.time()),
    ).rowcount > 0


class TaskEvent(Event):
    """Event-compatible cancellation backed by a cross-process lease."""

    def __init__(self, kind: str, key, repo=None, limit=None, lease=None):
        super().__init__()
        self.lease = lease or TaskLease(kind, key, repo, limit)

    def is_set(self):
        return super().is_set() or self.lease.cancelled()

    def set(self):
        super().set()
        cancel_lease(self.lease.kind, self.lease.key, self.lease.repo)

    def close(self):
        self.lease.close()
