"""Scheduler runtime lifecycle with APScheduler first and thread fallback."""

from __future__ import annotations

import time
from datetime import UTC, datetime
from threading import Event, RLock, Thread
from typing import Any

from src.core.logger import get_logger
from src.core.repository import Repository
from src.core.task_control import TaskLease
from src.core.timeutil import utc_now_iso
from src.scheduler.cron import APSCHEDULER_AVAILABLE, build_cron_trigger

if APSCHEDULER_AVAILABLE:
    from apscheduler.schedulers.background import BackgroundScheduler  # type: ignore[import-not-found]
else:
    BackgroundScheduler = None  # type: ignore[assignment,misc]

JOB_ID_PREFIX = "scheduled-job-"
DEFAULT_POLL_SECONDS = 5.0


class SchedulerRuntime:
    """Owns the in-process scheduler instance."""

    def __init__(self) -> None:
        self._scheduler: Any = None
        self._thread: Thread | None = None
        self._stop_event = Event()
        self._lock = RLock()
        self.log = get_logger("scheduler.runtime")
        self._leader: TaskLease | None = None

    def start(self) -> None:
        with self._lock:
            if self.running:
                return
            self._stop_event.clear()
            try:
                self._leader = TaskLease("leader", "scheduler")
            except ValueError:
                self._thread = Thread(target=self._standby, name="scheduler-standby", daemon=True)
                self._thread.start()
                return
            self._activate()

    def _activate(self):
        with self._lock:
            if self._stop_event.is_set():
                return
            if BackgroundScheduler is not None:
                self._scheduler = BackgroundScheduler(timezone=UTC)
                self._scheduler.start(paused=False)
                self.reload_jobs()
                self.log.info("scheduler runtime started | backend=apscheduler jobs={}", self.job_count)
                self._thread = Thread(target=self._refresh, name="scheduler-refresh", daemon=True)
                self._thread.start()
                return
            self._thread = Thread(target=self._poll_loop, name="scheduler-runtime", daemon=True)
            self._thread.start()
            self.log.warning("scheduler runtime started | backend=thread-fallback apscheduler=missing")

    def _standby(self):
        while not self._stop_event.wait(DEFAULT_POLL_SECONDS):
            try:
                self._leader = TaskLease("leader", "scheduler")
            except ValueError:
                continue
            self._activate()
            return

    def _refresh(self):
        previous = None
        while not self._stop_event.wait(DEFAULT_POLL_SECONDS):
            try:
                current = Repository().db.query_one(
                    "SELECT COUNT(*) AS n,MAX(updated_at) AS stamp,SUM(enabled) AS active FROM scheduled_jobs"
                )
                if current != previous:
                    self.reload_jobs()
                    previous = current
            except (RuntimeError, OSError):
                return

    def stop(self) -> None:
        with self._lock:
            self._stop_event.set()
            if self._scheduler and self._scheduler.running:
                self._scheduler.shutdown(wait=False)
                self.log.info("scheduler runtime stopped | backend=apscheduler")
            if self._thread and self._thread.is_alive():
                self._thread.join(timeout=2.0)
                self.log.info("scheduler runtime stopped | backend=thread-fallback")
            self._scheduler = None
            self._thread = None
            if self._leader:
                self._leader.close()
                self._leader = None

    def reload_jobs(self) -> None:
        with self._lock:
            if not self._scheduler or not self._scheduler.running:
                return
            for job in list(self._scheduler.get_jobs()):
                if job.id.startswith(JOB_ID_PREFIX):
                    self._scheduler.remove_job(job.id)
            rows = Repository().list(
                "scheduled_jobs",
                where="enabled = ?",
                params=(1,),
                order_by="id ASC",
            )
            for row in rows:
                self._add_job(row)
            self.log.debug("scheduler jobs reloaded | jobs={}", self.job_count)

    @property
    def running(self) -> bool:
        return bool(
            (self._scheduler and self._scheduler.running)
            or (self._thread and self._thread.is_alive() and not self._stop_event.is_set())
        )

    @property
    def backend(self) -> str:
        if self._leader is None:
            return "standby"
        return "apscheduler" if self._scheduler else "thread-fallback"

    @property
    def job_count(self) -> int:
        if self._scheduler:
            return len([job for job in self._scheduler.get_jobs() if job.id.startswith(JOB_ID_PREFIX)])
        return int(Repository().db.scalar("SELECT COUNT(*) FROM scheduled_jobs WHERE enabled = 1") or 0)

    def status(self) -> dict[str, Any]:
        return {"running": self.running, "backend": self.backend, "job_count": self.job_count}

    def run_due_once(self) -> int:
        return self._run_due_jobs()

    def _add_job(self, row: dict[str, Any]) -> None:
        try:
            trigger = build_cron_trigger(str(row.get("cron_expr") or ""))
            if trigger is None:
                return
            self._scheduler.add_job(
                self._run_job,
                trigger=trigger,
                id=f"{JOB_ID_PREFIX}{row['id']}",
                name=str(row.get("name") or row["id"]),
                args=[int(row["id"])],
                max_instances=1,
                coalesce=True,
                replace_existing=True,
            )
        except Exception as exc:
            self.log.warning(
                "scheduler job skipped during reload | job_id={} cron={} error={}",
                row.get("id"),
                row.get("cron_expr"),
                exc,
            )

    def _poll_loop(self) -> None:
        while not self._stop_event.wait(DEFAULT_POLL_SECONDS):
            try:
                self._run_due_jobs()
            except Exception as exc:
                self.log.exception("scheduler fallback loop failed | error={}", exc)

    def _run_due_jobs(self) -> int:
        now_iso = utc_now_iso()
        rows = Repository().list(
            "scheduled_jobs",
            where="enabled = ? AND next_run_at IS NOT NULL AND next_run_at <= ?",
            params=(1, now_iso),
            order_by="next_run_at ASC, id ASC",
            limit=20,
        )
        for row in rows:
            self._run_job(int(row["id"]))
        return len(rows)

    def _run_job(self, job_id: int) -> None:
        from src.scheduler.executor import CRON_TRIGGER, SchedulerService

        job = Repository().get_optional("scheduled_jobs", job_id) or {}
        started = time.perf_counter()
        self.log.info(
            "scheduler cron trigger started | job_id={} job_name={} job_type={}",
            job_id,
            job.get("name") or "-",
            job.get("job_type") or "-",
        )
        result = SchedulerService().trigger(job_id, trigger_type=CRON_TRIGGER)
        self.log.info(
            "scheduler cron trigger finished | job_id={} job_name={} job_type={} status={} history_id={} "
            "duration_ms={:.0f} summary={}",
            job_id,
            job.get("name") or "-",
            job.get("job_type") or "-",
            result.get("status"),
            result.get("history_id"),
            (time.perf_counter() - started) * 1000,
            str(result.get("result_summary") or "")[:240],
        )


def parse_scheduler_iso(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


scheduler_runtime = SchedulerRuntime()
