"""Bounded background jobs shared by browser and HTTP clients."""

import json
from collections.abc import Iterator
from datetime import date
from threading import RLock, Thread
from typing import Any
from uuid import uuid4

from src.core.stream_control import stream_pause
from src.core.task_control import TaskEvent, lease_alive
from src.core.timeutil import utc_now_iso

from .config import insight_config
from .execution import execute
from .store import InsightStore

JOB_LOCK = RLock()
ACTIVE: dict[str, dict[str, Any]] = {}


class InsightReportService:
    def __init__(self, store: InsightStore | None = None):
        self.store = store or InsightStore()
        self.config = insight_config()

    def normalize(self, payload: dict[str, Any]) -> dict[str, Any]:
        result = dict(payload)
        messages, defaults = self.config["messages"], self.config["defaults"]
        if result.get("kind") not in self.config["tasks"]:
            raise ValueError(messages["invalid_kind"])
        result["backend"] = result.get("backend") or defaults["backend"]
        if result["backend"] not in {row["id"] for row in self.config["backends"]}:
            raise ValueError(messages["invalid_backend"])
        result["market"] = str(result.get("market") or "CN").upper()
        if result["market"] not in {"CN", "US"}:
            raise ValueError(messages["no_data"])
        result["timeframe"] = result.get("timeframe") or defaults["timeframe"]
        if result["timeframe"] not in {row["id"] for row in self.config["ui"]["timeframe_choices"]}:
            raise ValueError(messages["invalid_kind"])
        result["end_date"] = str(result.get("end_date") or date.today().isoformat()).strip()
        try:
            if date.fromisoformat(result["end_date"]) > date.today():
                raise ValueError(messages["invalid_date"])
        except ValueError as exc:
            raise ValueError(messages["invalid_date"]) from exc
        result["symbol"] = str(result.get("symbol") or "").strip()
        if result["kind"] == "single_stock_analysis" and not result["symbol"]:
            raise ValueError(messages["invalid_symbol"])
        return result

    def start(self, payload: dict[str, Any], cancelled=None) -> dict[str, Any]:
        payload = self.normalize(payload)
        key = str(self.store.root) + json.dumps(payload, sort_keys=True, ensure_ascii=False)
        with JOB_LOCK:
            if key in ACTIVE and ACTIVE[key]["status"] == "running":
                return dict(ACTIVE[key])
            ACTIVE.pop(key, None)
            if len(ACTIVE) >= self.config["defaults"]["max_concurrent_jobs"]:
                raise ValueError(self.config["messages"]["busy"])
            run: dict[str, Any] = {
                "run_id": uuid4().hex,
                "request": payload,
                "status": "running",
                "created_at": utc_now_iso(),
            }
            stop = TaskEvent("insight", run["run_id"], limit=self.config["defaults"]["max_concurrent_jobs"])
            try:
                self.store.save(run)
                self.store.append(run["run_id"], "status", self.config["messages"]["submitted"], payload)
                ACTIVE[key] = run
                Thread(
                    target=self._execute,
                    args=(key, run, lambda: stop.is_set() or bool(cancelled and cancelled()), stop),
                    daemon=True,
                    name=f"insight-{run['run_id']}",
                ).start()
            except Exception:
                ACTIVE.pop(key, None)
                stop.close()
                raise
            return dict(run)

    def _execute(self, key: str, run: dict[str, Any], cancelled=None, stop=None) -> None:
        try:
            execute(run, self.store, self.config, cancelled=cancelled)
        finally:
            if stop:
                stop.close()
            with JOB_LOCK:
                if ACTIVE.get(key, {}).get("run_id") == run["run_id"]:
                    ACTIVE.pop(key, None)

    def detail(self, run_id: str) -> dict[str, Any]:
        with JOB_LOCK:
            run = self.store.detail(run_id)
            if (
                run["status"] == "running"
                and not any(item["run_id"] == run_id for item in ACTIVE.values())
                and not lease_alive("insight", run_id)
            ):
                run.update(status="failed", error=self.config["messages"]["incomplete"])
                self.store.save(run)
            return run

    def follow(self, run_id: str) -> Iterator[dict[str, Any]]:
        cursor = 0
        while True:
            run = self.detail(run_id)
            events = self.store.events(run_id)
            if len(events) > cursor or run["status"] != "running":
                yield {"run": run, "events": events[cursor:]}
                cursor = len(events)
            if run["status"] != "running":
                return
            stream_pause(self.config["defaults"]["poll_seconds"])
