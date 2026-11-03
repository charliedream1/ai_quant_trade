"""Process-isolated scheduled job execution."""

from __future__ import annotations

import multiprocessing as mp
import queue
import traceback
from concurrent.futures import TimeoutError
from typing import Any

PROCESS_TERMINATE_GRACE_SECONDS = 2.0


def execute_scheduled_job_in_process(job: dict[str, Any], timeout_seconds: float) -> dict[str, Any]:
    ctx = mp.get_context("spawn")
    result_queue: mp.Queue[dict[str, Any]] = ctx.Queue(maxsize=1)
    process = ctx.Process(
        target=_process_entrypoint,
        args=(job, result_queue),
        name=f"scheduled-job-{job.get('job_id') or job.get('id') or 'custom'}",
    )
    process.start()
    process.join(timeout_seconds)
    try:
        if process.is_alive():
            _terminate_process(process)
            raise TimeoutError()
        return _read_process_result(process, result_queue)
    finally:
        result_queue.close()
        result_queue.join_thread()


def _process_entrypoint(job: dict[str, Any], result_queue: mp.Queue[dict[str, Any]]) -> None:
    try:
        from src.scheduler.jobs import execute_scheduled_job

        result_queue.put({"ok": True, "result": execute_scheduled_job(job)})
    except Exception as exc:  # pragma: no cover - child process branch
        result_queue.put(
            {
                "ok": False,
                "error_type": type(exc).__name__,
                "error_msg": str(exc),
                "traceback": traceback.format_exc(limit=12),
            }
        )


def _read_process_result(process: Any, result_queue: mp.Queue[dict[str, Any]]) -> dict[str, Any]:
    try:
        payload = result_queue.get_nowait()
    except queue.Empty as exc:
        raise RuntimeError(f"调度子进程未返回结果，退出码 {process.exitcode}") from exc
    if payload.get("ok"):
        result = payload.get("result")
        return result if isinstance(result, dict) else {"summary": str(result or "")}
    message = payload.get("error_msg") or "未知错误"
    error_type = payload.get("error_type") or "Error"
    raise RuntimeError(f"调度子进程执行失败：{error_type}: {message}")


def _terminate_process(process: Any) -> None:
    process.terminate()
    process.join(PROCESS_TERMINATE_GRACE_SECONDS)
    if process.is_alive() and hasattr(process, "kill"):
        process.kill()
        process.join(PROCESS_TERMINATE_GRACE_SECONDS)
