"""Example custom scheduled job handlers."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from src.core.timeutil import utc_now_iso


def echo_task(params: dict[str, Any], job: dict[str, Any]) -> dict[str, Any]:
    message = str(params.get("message") or params.get("topic") or job.get("name") or "自定义任务").strip()
    return {
        "status": "成功",
        "summary": f"自定义执行体完成：{message}",
        "details": {
            "message": message,
            "job_id": job.get("job_id") or job.get("id"),
            "executed_at": utc_now_iso(),
        },
    }


def sleep_task(params: dict[str, Any], _job: dict[str, Any]) -> dict[str, Any]:
    seconds = float(params.get("sleep_seconds") or 1)
    time.sleep(max(seconds, 0))
    marker_path = str(params.get("marker_path") or "").strip()
    if marker_path:
        Path(marker_path).write_text("done", encoding="utf-8")
    return {
        "status": "成功",
        "summary": f"睡眠任务完成：{seconds:g} 秒",
        "details": {"sleep_seconds": seconds, "executed_at": utc_now_iso()},
    }
