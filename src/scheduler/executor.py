"""Scheduled job CRUD, trigger execution and runtime reload service."""

from __future__ import annotations

import json
import time
from concurrent.futures import Future, ThreadPoolExecutor, TimeoutError
from threading import Lock
from typing import Any

from src.core.exceptions import BusinessError, ErrorCode
from src.core.logger import get_logger
from src.core.repository import Repository, json_loads
from src.core.task_control import TaskLease
from src.core.timeutil import utc_now_iso
from src.scheduler.cron import next_run_iso, normalize_cron
from src.scheduler.jobs import SKIPPED_STATUS, SUCCESS_STATUS, execute_scheduled_job
from src.scheduler.policies import (
    PROCESS_TIMEOUT_MODE,
    mutex_group_from_params,
    retry_policy_from_params,
    timeout_mode_from_params,
    timeout_seconds_from_params,
    trading_day_skip_summary,
)
from src.scheduler.process_runner import execute_scheduled_job_in_process

FAILED_STATUS = "失败"
RUNNING_STATUS = "运行中"
TIMED_OUT_STATUS = "超时"
MANUAL_TRIGGER = "manual"
CRON_TRIGGER = "cron"
_RUNNING_JOB_IDS: set[int] = set()


class SoftTaskTimeoutError(TimeoutError):
    def __init__(self, future: Future):
        super().__init__("线程执行超过软时限，等待实际停止后释放互斥")
        self.pending_future = future


_RUNNING_MUTEX_GROUPS: set[str] = set()
_RUNNING_LOCK = Lock()


class SchedulerService:
    def __init__(self, repo: Repository | None = None) -> None:
        self.repo = repo or Repository()
        self.log = get_logger("scheduler.executor")

    def list(
        self,
        job_type: str | None = None,
        enabled: bool | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        where: list[str] = []
        params: list[Any] = []
        if job_type:
            where.append("job_type = ?")
            params.append(job_type)
        if enabled is not None:
            where.append("enabled = ?")
            params.append(1 if enabled else 0)
        result = self.repo.page(
            "scheduled_jobs",
            page,
            page_size,
            " AND ".join(where),
            params,
            order_by="created_at DESC",
        )
        result["items"] = [self._public_job(item) for item in result["items"]]
        return result

    def create(self, payload: dict[str, Any]) -> dict[str, Any]:
        now = utc_now_iso()
        cron_expr = normalize_cron(payload.get("cron") or payload.get("cron_expr") or "0 16 * * 1-5")
        enabled = bool(payload.get("enabled", True))
        row = self.repo.insert(
            "scheduled_jobs",
            {
                "name": _required_text(payload.get("name"), "任务名称"),
                "cron_expr": cron_expr,
                "job_type": _required_text(payload.get("job_type"), "任务类型"),
                "job_params": json.dumps(_normalize_job_params(payload), ensure_ascii=False),
                "enabled": 1 if enabled else 0,
                "last_run_at": None,
                "next_run_at": next_run_iso(cron_expr) if enabled else None,
                "created_at": now,
                "updated_at": now,
            },
        )
        _reload_runtime_jobs()
        return self.detail(int(row["id"]))

    def detail(self, job_id: int) -> dict[str, Any]:
        row = self._public_job(self.repo.get("scheduled_jobs", job_id))
        row["recent_execution"] = self.repo.db.query_one(
            "SELECT * FROM job_executions WHERE job_id = ? ORDER BY triggered_at DESC LIMIT 1",
            (job_id,),
        )
        return row

    def update(self, job_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        current = self.repo.get("scheduled_jobs", job_id)
        values: dict[str, Any] = {"updated_at": utc_now_iso()}
        for key in ("name", "job_type"):
            if key in payload:
                values[key] = _required_text(payload[key], key)
        enabled_value = current.get("enabled")
        if "enabled" in payload:
            enabled_value = 1 if payload["enabled"] else 0
            values["enabled"] = enabled_value
        cron_expr = str(current.get("cron_expr") or "")
        if "cron" in payload or "cron_expr" in payload:
            cron_expr = normalize_cron(payload.get("cron") or payload.get("cron_expr"))
            values["cron_expr"] = cron_expr
        if "target" in payload or "job_params" in payload:
            values["job_params"] = json.dumps(_normalize_job_params(payload), ensure_ascii=False)
        if "cron_expr" in values or "enabled" in values:
            values["next_run_at"] = next_run_iso(cron_expr) if int(enabled_value or 0) else None
        self.repo.update("scheduled_jobs", job_id, values)
        _reload_runtime_jobs()
        return self.detail(job_id)

    def delete(self, job_id: int) -> None:
        self.repo.delete("scheduled_jobs", job_id)
        _reload_runtime_jobs()

    def enable(self, job_id: int, enabled: bool) -> dict[str, Any]:
        row = self.repo.get("scheduled_jobs", job_id)
        self.repo.update(
            "scheduled_jobs",
            job_id,
            {
                "enabled": 1 if enabled else 0,
                "next_run_at": next_run_iso(str(row.get("cron_expr") or "")) if enabled else None,
                "updated_at": utc_now_iso(),
            },
        )
        _reload_runtime_jobs()
        return self.detail(job_id)

    def trigger(self, job_id: int, trigger_type: str = MANUAL_TRIGGER) -> dict[str, Any]:
        job = self._public_job(self.repo.get("scheduled_jobs", job_id))
        params = job.get("target") or {}
        if trigger_type == CRON_TRIGGER:
            skip_summary = trading_day_skip_summary(params)
            if skip_summary:
                return self._record_skipped(job_id, trigger_type, skip_summary, job)
        mutex_group = mutex_group_from_params(params)
        skip_summary = _mark_running(job_id, mutex_group)
        if skip_summary:
            return self._record_skipped(job_id, trigger_type, skip_summary, job)
        leases = []
        try:
            leases.append(TaskLease("scheduler_job", job_id, self.repo))
            if mutex_group:
                leases.append(TaskLease("scheduler_mutex", mutex_group, self.repo))
        except ValueError:
            for lease in leases:
                lease.close()
            _unmark_running(job_id, mutex_group)
            return self._record_skipped(job_id, trigger_type, "其他执行进程仍持有该任务互斥", job)
        started_at = utc_now_iso()
        started = time.perf_counter()
        execution = self.repo.insert(
            "job_executions",
            {
                "job_id": job_id,
                "triggered_at": started_at,
                "trigger_type": trigger_type or MANUAL_TRIGGER,
                "status": RUNNING_STATUS,
                "duration_ms": None,
                "result_summary": "",
                "error_msg": "",
                "created_at": started_at,
            },
        )
        status = SUCCESS_STATUS
        summary = ""
        error_msg = ""
        attempt_count = 0
        pending_future = None
        retry_policy = retry_policy_from_params(params)
        timeout_seconds = timeout_seconds_from_params(params)
        timeout_mode = timeout_mode_from_params(params)
        self.log.info(
            "scheduled job execution started | job_id={} job_name={} job_type={} trigger_type={} "
            "timeout_seconds={} timeout_mode={} max_attempts={} mutex_group={}",
            job_id,
            job.get("name") or "-",
            job.get("job_type") or "-",
            trigger_type or MANUAL_TRIGGER,
            timeout_seconds or "-",
            timeout_mode,
            retry_policy.max_attempts,
            mutex_group or "-",
        )
        try:
            for attempt in range(1, retry_policy.max_attempts + 1):
                attempt_count = attempt
                delay_seconds = retry_policy.delay_seconds(attempt)
                if delay_seconds > 0:
                    time.sleep(delay_seconds)
                try:
                    result = _execute_with_timeout(job, timeout_seconds, timeout_mode)
                    status = str(result.get("status") or SUCCESS_STATUS)
                    summary = str(result.get("summary") or "")
                    error_msg = str(result.get("error_msg") or "")
                    if status != FAILED_STATUS:
                        break
                    if attempt < retry_policy.max_attempts:
                        self.log.warning(
                            "scheduled job attempt returned failure | job_id={} attempt={}/{} summary={}",
                            job_id,
                            attempt,
                            retry_policy.max_attempts,
                            summary,
                        )
                except TimeoutError as timeout_error:
                    pending_future = getattr(timeout_error, "pending_future", None)
                    status = TIMED_OUT_STATUS
                    summary = f"任务执行超时，超过 {timeout_seconds:g} 秒未完成。"
                    error_msg = summary
                    self.log.warning(
                        "scheduled job timeout | job_id={} trigger_type={} timeout_seconds={} timeout_mode={}",
                        job_id,
                        trigger_type,
                        timeout_seconds,
                        timeout_mode,
                    )
                except Exception as exc:
                    status = FAILED_STATUS
                    summary = "任务执行失败"
                    error_msg = str(exc)
                    if attempt < retry_policy.max_attempts:
                        self.log.warning(
                            "scheduled job attempt failed | job_id={} attempt={}/{} error={}",
                            job_id,
                            attempt,
                            retry_policy.max_attempts,
                            exc,
                        )
                    else:
                        self.log.exception("scheduled job failed | job_id={} trigger_type={}", job_id, trigger_type)
                if status != FAILED_STATUS:
                    break
            if attempt_count > 1:
                summary = f"{summary}；已重试 {attempt_count - 1} 次。"
        finally:

            def release(_=None):
                _unmark_running(job_id, mutex_group)
                for lease in leases:
                    lease.close()

            if pending_future is not None and not pending_future.done():
                error_msg += "；线程执行仍在结束中，互斥在真正停止后释放，不会自动重试"
                pending_future.add_done_callback(release)
            else:
                release()
        finished_at = utc_now_iso()
        duration_ms = int((time.perf_counter() - started) * 1000)
        row = self.repo.update(
            "job_executions",
            int(execution["id"]),
            {
                "status": status,
                "duration_ms": duration_ms,
                "result_summary": summary,
                "error_msg": error_msg,
            },
        )
        self.repo.update(
            "scheduled_jobs",
            job_id,
            {
                "last_run_at": finished_at,
                "next_run_at": next_run_iso(str(job.get("cron_expr") or "")) if int(job.get("enabled") or 0) else None,
                "updated_at": finished_at,
            },
        )
        _reload_runtime_jobs()
        row["history_id"] = row["id"]
        log_message = (
            "scheduled job execution finished | job_id={} job_name={} job_type={} trigger_type={} status={} "
            "history_id={} duration_ms={} attempts={} summary={}"
        )
        log_args = (
            job_id,
            job.get("name") or "-",
            job.get("job_type") or "-",
            trigger_type or MANUAL_TRIGGER,
            status,
            row["history_id"],
            duration_ms,
            attempt_count,
            summary[:240],
        )
        if status == SUCCESS_STATUS:
            self.log.info(log_message, *log_args)
        elif status == SKIPPED_STATUS:
            self.log.warning(log_message, *log_args)
        else:
            self.log.error(log_message, *log_args)
        _publish_job_event(job, row)
        return row

    def histories(
        self,
        job_id: int,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        where = "job_id = ?"
        params: list[Any] = [job_id]
        if status:
            where += " AND status = ?"
            params.append(status)
        result = self.repo.page("job_executions", page, page_size, where, params, order_by="triggered_at DESC")
        for item in result["items"]:
            item["history_id"] = item["id"]
        return result

    @staticmethod
    def _public_job(row: dict[str, Any]) -> dict[str, Any]:
        item = dict(row)
        item["job_id"] = item["id"]
        item["target"] = json_loads(item.get("job_params"), {})
        return item

    def _record_skipped(
        self, job_id: int, trigger_type: str, summary: str, job: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        now = utc_now_iso()
        row = self.repo.insert(
            "job_executions",
            {
                "job_id": job_id,
                "triggered_at": now,
                "trigger_type": trigger_type or MANUAL_TRIGGER,
                "status": SKIPPED_STATUS,
                "duration_ms": 0,
                "result_summary": summary,
                "error_msg": "",
                "created_at": now,
            },
        )
        if trigger_type == CRON_TRIGGER:
            job = job or self._public_job(self.repo.get("scheduled_jobs", job_id))
            self.repo.update(
                "scheduled_jobs",
                job_id,
                {
                    "last_run_at": now,
                    "next_run_at": next_run_iso(str(job.get("cron_expr") or ""))
                    if int(job.get("enabled") or 0)
                    else None,
                    "updated_at": now,
                },
            )
            _reload_runtime_jobs()
        row["history_id"] = row["id"]
        job = job or self._public_job(self.repo.get("scheduled_jobs", job_id))
        self.log.warning(
            "scheduled job execution skipped | job_id={} job_name={} job_type={} trigger_type={} history_id={} "
            "summary={}",
            job_id,
            job.get("name") or "-",
            job.get("job_type") or "-",
            trigger_type or MANUAL_TRIGGER,
            row["history_id"],
            summary[:240],
        )
        _publish_job_event(job, row)
        return row


def _required_text(value: Any, label: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise BusinessError(ErrorCode.MISSING_PARAM, f"{label}不能为空")
    return text


def _normalize_job_params(payload: dict[str, Any]) -> dict[str, Any]:
    value = payload.get("target") if "target" in payload else payload.get("job_params")
    if value in (None, ""):
        return {}
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError as exc:
            raise BusinessError(ErrorCode.INVALID_PARAM, "任务参数必须是合法 JSON 对象") from exc
        if isinstance(parsed, dict):
            return parsed
    raise BusinessError(ErrorCode.INVALID_PARAM, "任务参数必须是 JSON 对象")


def _mark_running(job_id: int, mutex_group: str | None) -> str | None:
    with _RUNNING_LOCK:
        if job_id in _RUNNING_JOB_IDS:
            return "上一次执行仍未结束，本次触发已跳过。"
        if mutex_group and mutex_group in _RUNNING_MUTEX_GROUPS:
            return f"互斥组 {mutex_group} 已有任务正在执行，本次触发已跳过。"
        _RUNNING_JOB_IDS.add(job_id)
        if mutex_group:
            _RUNNING_MUTEX_GROUPS.add(mutex_group)
        return None


def _unmark_running(job_id: int, mutex_group: str | None) -> None:
    with _RUNNING_LOCK:
        _RUNNING_JOB_IDS.discard(job_id)
        if mutex_group:
            _RUNNING_MUTEX_GROUPS.discard(mutex_group)


def _reload_runtime_jobs() -> None:
    from src.scheduler.runtime import scheduler_runtime

    scheduler_runtime.reload_jobs()


def _execute_with_timeout(job: dict[str, Any], timeout_seconds: float | None, timeout_mode: str) -> dict[str, Any]:
    if timeout_seconds is None:
        return execute_scheduled_job(job)
    if timeout_mode == PROCESS_TIMEOUT_MODE:
        return execute_scheduled_job_in_process(job, timeout_seconds)
    executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix=f"scheduled-job-{job.get('job_id')}")
    future = executor.submit(execute_scheduled_job, job)
    try:
        return future.result(timeout=timeout_seconds)
    except TimeoutError as exc:
        raise SoftTaskTimeoutError(future) from exc
    finally:
        executor.shutdown(wait=False, cancel_futures=True)


def _publish_job_event(job: dict[str, Any], execution: dict[str, Any]) -> None:
    from src.api.ws_hub import ws_hub

    status = str(execution.get("status") or "")
    event_type = "scheduler_skipped"
    if status == SUCCESS_STATUS:
        event_type = "task_done"
    elif status in {FAILED_STATUS, TIMED_OUT_STATUS}:
        event_type = "task_failed"
    payload = {
        "task_type": "scheduler",
        "job_id": job.get("job_id") or job.get("id"),
        "job_name": job.get("name"),
        "job_type": job.get("job_type"),
        "history_id": execution.get("history_id") or execution.get("id"),
        "status": status,
        "summary": execution.get("result_summary") or "",
        "error_msg": execution.get("error_msg") or "",
        "duration_ms": execution.get("duration_ms"),
        "trigger_type": execution.get("trigger_type"),
    }
    ws_hub.broadcast_nowait("notify", event_type, payload)
