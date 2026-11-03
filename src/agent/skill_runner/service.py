"""Foreground local research with inspectable IDs and explicit interruption semantics."""

import html
import json
import os
from threading import Event, Thread
from time import monotonic
from uuid import uuid4

from loguru import logger

from src.core.timeutil import utc_now_iso

from .catalog import preview, settings
from .store import SkillRunStore
from .workflows import HANDLERS, import_data


class LocalSkillService:
    def __init__(self, store=None):
        self.store = store or SkillRunStore()

    def register(self, payload: dict) -> dict:
        if int(os.environ.get("ALL_IN_ONE_PROVIDER_DEPTH", "0")) > 0:
            raise ValueError(settings()["messages"]["recursion"])
        plan = preview(payload)
        return self.store.save(
            {
                "run_id": uuid4().hex,
                "status": "registered",
                "created_at": utc_now_iso(),
                "plan": plan,
                "pid": os.getpid(),
                "outer_cli_usage": None,
                "process_lifetime": "foreground",
            }
        )

    def run(self, payload: dict, emit=None) -> dict:
        return self.execute(self.register(payload)["run_id"], emit=emit)

    def execute(self, run_id: str, emit=None) -> dict:
        row = self.store.get(run_id)
        if row["status"] != "registered":
            raise ValueError("Skill运行不能重复执行")
        row.update(status="running", pid=os.getpid(), started_at=utc_now_iso())
        self.store.heartbeat(run_id)
        self.store.save(row)
        started = monotonic()
        heartbeat_stop = Event()

        def heartbeat():
            while not heartbeat_stop.wait(settings()["limits"]["heartbeat_seconds"]):
                self.store.heartbeat(run_id)

        heartbeat_thread = Thread(target=heartbeat, daemon=True)
        heartbeat_thread.start()

        def event(kind, payload):
            self.store.event(run_id, kind, payload)
            if emit:
                emit(kind, payload)

        def cancelled():
            return self.store.cancelled(run_id) or monotonic() - started > settings()["limits"]["deadline_seconds"]

        event("started", {"run_id": run_id, "digest": row["plan"]["digest"]})
        try:
            plan = row["plan"]
            request = import_data(plan)
            result, report = HANDLERS[plan["family"]](request, plan["provider"], cancelled, event)
            row.update(result=result, status=result["status"])
            if cancelled():
                row["status"] = "cancelled"
            if report and report.is_file():
                (self.store.directory(run_id) / "report.html").write_bytes(report.read_bytes())
                row["domain_report"] = str(report)
        except (Exception, KeyboardInterrupt) as exc:
            interrupted = isinstance(exc, KeyboardInterrupt) or cancelled()
            self.store.cancel(run_id)
            row.update(status="cancelled" if interrupted else "failed", error=str(exc))
            logger.warning("local skill stopped | run={} error_type={}", run_id, type(exc).__name__)
            event("error", {"type": type(exc).__name__, "message": str(exc)})
        finally:
            heartbeat_stop.set()
            heartbeat_thread.join(timeout=settings()["limits"]["heartbeat_seconds"])
            row.update(finished_at=utc_now_iso(), duration_ms=round((monotonic() - started) * 1000))
            self.store.save(row)
            (self.store.directory(run_id) / "result.json").write_text(
                json.dumps(row, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            self._report(row)
            event("finished", {"status": row["status"], "duration_ms": row["duration_ms"]})
        return row

    def _report(self, row):
        path = self.store.directory(row["run_id"]) / "report.html"
        if path.exists():
            return
        text = html.escape(json.dumps(row.get("result") or {"error": row.get("error")}, ensure_ascii=False, indent=2))
        path.write_text(
            '<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>研究Skill报告</title>'
            "<body><h1>"
            + html.escape(row["plan"]["skill"])
            + "</h1><p>"
            + html.escape(row["status"])
            + "</p><pre>"
            + text
            + "</pre></body></html>",
            encoding="utf-8",
        )
