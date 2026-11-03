"""Background UI runs sharing the durable API/CLI runner."""

import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from threading import Event, RLock
from time import monotonic
from typing import Any

from src.core.config import get_settings
from src.core.logger import get_logger
from src.core.security_config import security_config
from src.core.task_control import TaskEvent, cancel_lease
from src.core.timeutil import utc_now_iso
from src.data import DataSourceManager

from .config import backtest_config
from .runner import BacktestRunner

LOCK = RLock()
POOL: ThreadPoolExecutor | None = None
ACTIVE: dict[str, tuple[int, Event]] = {}


def submit(payload: dict[str, Any]) -> dict[str, Any]:
    """Deduplicate active requests, including the isolated database identity."""
    global POOL
    key = hashlib.sha256(json.dumps([str(get_settings().db_path), payload], sort_keys=True).encode()).hexdigest()
    runner, data = BacktestRunner(), DataSourceManager()
    with LOCK:
        if key in ACTIVE:
            return runner.detail(ACTIVE[key][0])
        if len(ACTIVE) >= security_config()["limits"]["backtest_pending"]:
            raise ValueError("回测队列已满，请等待已有任务完成")
        task = runner.create(payload, deferred=True)
        stop = TaskEvent("backtest", task["task_id"], runner.repo, security_config()["limits"]["backtest_pending"])
        try:
            ACTIVE[key] = (task["task_id"], stop)
            if POOL is None:
                POOL = ThreadPoolExecutor(
                    max_workers=backtest_config()["execution"]["workers"], thread_name_prefix="backtest"
                )
            POOL.submit(_execute, runner, task["task_id"], data, stop, key)
        except Exception:
            ACTIVE.pop(key, None)
            stop.close()
            runner.repo.update(
                "backtest_tasks",
                task["task_id"],
                {"status": "failed", "error_msg": "回测执行队列提交失败", "finished_at": utc_now_iso()},
            )
            raise
    return task


def _execute(runner, task_id, data, stop, key) -> None:
    deadline = monotonic() + backtest_config()["execution"]["timeout_seconds"]

    def checkpoint():
        if stop.is_set():
            raise InterruptedError("用户取消；已停止在安全检查点")
        if monotonic() > deadline:
            raise TimeoutError("超过回测时间限制")

    try:
        runner.execute(task_id, checkpoint=checkpoint, data=data, _owned_event=stop)
    except Exception as exc:
        get_logger("backtest.jobs").debug(
            "worker ended | task_id={} error_type={} (runner retains failure)", task_id, type(exc).__name__
        )
    finally:
        if isinstance(stop, TaskEvent):
            stop.close()
        with LOCK:
            ACTIVE.pop(key, None)


def cancel(task_id: int) -> str:
    with LOCK:
        for active_id, stop in ACTIVE.values():
            if active_id == task_id:
                stop.set()
                return "已请求取消，等待当前行情或模型调用结束"
    return "已请求执行进程取消" if cancel_lease("backtest", task_id) else "任务已结束或当前进程没有该运行"


def shutdown() -> None:
    """Drain workers at application shutdown; later isolated app instances can restart."""
    global POOL
    with LOCK:
        for _, stop in ACTIVE.values():
            stop.set()
        pool, POOL = POOL, None
    if pool:
        pool.shutdown(wait=True)
