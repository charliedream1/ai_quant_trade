"""Bounded background monitoring with real stages and per-session request identity."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from contextvars import copy_context
from threading import RLock
from typing import Any
from uuid import uuid4

from src.core.timeutil import utc_now_iso

from .factor_monitor import FactorMonitorService

_LOCK = RLock()
_JOBS: dict[str, dict[str, Any]] = {}
_ACTIVE: dict[str, str] = {}
_EXECUTOR: ThreadPoolExecutor | None = None


def start_monitor(options: dict[str, Any], owner: str = "", service: FactorMonitorService | None = None) -> str:
    global _EXECUTOR
    service = service or FactorMonitorService()
    config = service._config()
    with _LOCK:
        finished = [key for key, job in _JOBS.items() if job["status"] in {"completed", "failed"}]
        while len(_JOBS) >= config["max_jobs"] and finished:
            _JOBS.pop(finished.pop(0))
        if len(_JOBS) >= config["max_jobs"]:
            raise ValueError("监控任务队列已满，请等待现有任务完成")
        if _EXECUTOR is None:
            _EXECUTOR = ThreadPoolExecutor(max_workers=config["job_workers"], thread_name_prefix="factor-monitor")
        identifier = uuid4().hex
        _JOBS[identifier] = {
            "id": identifier,
            "status": "queued",
            "stage": "等待执行",
            "events": [],
            "result": None,
            "error": "",
            "database": str(service.repo.db.db_path),
            "owner": owner,
        }
        if owner:
            _ACTIVE[owner] = identifier
        _EXECUTOR.submit(copy_context().run, _run, identifier, service, dict(options))
        return identifier


def _run(identifier: str, service: FactorMonitorService, options: dict[str, Any]) -> None:
    def progress(message: str) -> None:
        with _LOCK:
            job = _JOBS[identifier]
            job["stage"] = message
            job["events"].append({"time": utc_now_iso(), "message": message})

    try:
        with _LOCK:
            _JOBS[identifier]["status"] = "running"
        comparisons = list(dict.fromkeys(options.pop("compare_universes", []) or []))
        result = service.monitor(**options, progress=progress)
        result["comparison"] = []
        for selected in [options.get("universe_id", "custom"), *comparisons]:
            if selected == options.get("universe_id", "custom"):
                other = result
            else:
                progress(f"开始对照股票池：{selected}")
                other = service.monitor(
                    **{**options, "universe_id": selected, "membership_version": ""}, progress=progress
                )
            result["comparison"].extend(
                {
                    "universe": other["universe_metadata"]["label"],
                    "factor": row["factor_name"],
                    "rank_ic_mean": row["rank_ic_mean"],
                    "icir": row["icir"],
                    "coverage": row["coverage"],
                    "samples": row["sample_size"],
                    "policy": other["universe_metadata"]["history_policy"],
                }
                for row in other["metrics"]
            )
        progress("分析和对照完成，结果已保存")
        with _LOCK:
            _JOBS[identifier].update(status="completed", result=result)
    except Exception as exc:
        with _LOCK:
            _JOBS[identifier].update(status="failed", error=str(exc), stage="执行失败")


def monitor_job(identifier: str, owner: str = "") -> dict[str, Any]:
    with _LOCK:
        if identifier not in _JOBS:
            raise ValueError("监控任务不存在或已过期，请重新运行")
        job = _JOBS[identifier]
        service = FactorMonitorService()
        if job["database"] != str(service.repo.db.db_path):
            raise ValueError("监控任务不属于当前运行数据库")
        if owner and _ACTIVE.get(owner) != identifier:
            return {"status": "stale"}
        return {**job, "events": list(job["events"])}


def shutdown_monitor_jobs() -> None:
    global _EXECUTOR
    with _LOCK:
        executor, _EXECUTOR = _EXECUTOR, None
    if executor:
        executor.shutdown(wait=True, cancel_futures=True)
