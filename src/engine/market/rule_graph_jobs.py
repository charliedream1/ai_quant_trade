"""Owned process boundaries give rule graphs hard cancellation and total deadlines."""

import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime
from functools import partial
from pathlib import Path
from threading import RLock, Thread
from time import monotonic, sleep, time
from uuid import uuid4
from zoneinfo import ZoneInfo

from src.core.config import PROJECT_ROOT, get_settings
from src.core.diagnostics_config import diagnostics_config
from src.core.logger import get_logger
from src.core.page_work import finish_run, own_run
from src.core.process_control import stop_process_tree
from src.core.repository import Repository
from src.core.task_control import TaskEvent, lease_alive
from src.core.timeutil import utc_now_iso
from src.data import current_market, normalize_market

from .model_graph.store import GraphStore
from .rule_graph_worker import write_json

LOCK = RLock()
ACTIVE: dict[str, Path] = {}


def shutdown():
    with LOCK:
        owned = dict(ACTIVE)
        for folder in owned.values():
            (folder / "cancel").touch()
    deadline = monotonic() + diagnostics_config()["rules"]["shutdown_seconds"]
    while monotonic() < deadline:
        with LOCK:
            if not set(owned).intersection(ACTIVE):
                return
        sleep(diagnostics_config()["rules"]["poll_seconds"])


class RuleGraphJobs:
    def __init__(self):
        self.store = GraphStore("rule_graph_runs")

    def start(self, symbol, depth=1, relation_types=None, market=None):
        value = str(symbol or "").strip()
        if not value or len(value) > 100 or any(ord(char) < 32 for char in value):
            raise ValueError("Enter a stock code or company name")
        selected = normalize_market(market or current_market())
        if selected not in {"CN", "HK"}:
            raise ValueError("Rule graph research supports CN/HK")
        request = {
            "symbol": value,
            "market": selected,
            "depth": max(1, min(int(depth), 5)),
            "relation_types": sorted(set(relation_types or [])),
            "data_mode": get_settings().data_mode,
            "date": datetime.now(ZoneInfo("Asia/Shanghai")).date().isoformat(),
        }
        fingerprint = hashlib.sha256(json.dumps(request, sort_keys=True).encode()).hexdigest()
        with LOCK:
            active = Repository().db.query(
                "SELECT task_key FROM task_leases WHERE kind=? AND status='running' AND expires>?",
                ("rule_graph", time()),
            )
            for lease_row in active:
                try:
                    existing = self.store.get(lease_row["task_key"])
                except ValueError:
                    continue
                if existing.get("fingerprint") == fingerprint and existing["status"] in {"queued", "running"}:
                    own_run("rule_graph", existing["run_id"], partial(self.store.cancel, existing["run_id"]))
                    return existing
            key = uuid4().hex
            lease = TaskEvent("rule_graph", key, limit=diagnostics_config()["rules"]["active_runs"])
            row = {
                "run_id": key,
                "status": "queued",
                "request": request,
                "fingerprint": fingerprint,
                "created_at": utc_now_iso(),
            }
            try:
                self.store.save(row)
                write_json(self.store.directory(key) / "request.json", request)
                ACTIVE[key] = self.store.directory(key)
                Thread(target=self._execute, args=(row, lease), daemon=True, name="rule-graph-" + key).start()
                own_run("rule_graph", key, lambda: self.store.cancel(key))
            except Exception:
                ACTIVE.pop(key, None)
                lease.close()
                raise
        return row

    def _execute(self, row, lease):
        key, started = row["run_id"], monotonic()
        folder, policy = self.store.directory(key), diagnostics_config()["rules"]
        process = None
        reason = ""
        try:
            row.update(status="running", started_at=utc_now_iso())
            self.store.save(row)
            environment = os.environ.copy()
            environment.update(
                ALL_IN_ONE_DATA_MODE=row["request"]["data_mode"],
                ALL_IN_ONE_DATA_DIR=str(get_settings().data_dir),
                ALL_IN_ONE_DB_PATH=str(get_settings().db_path),
                PYTHONUTF8="1",
            )
            process = subprocess.Popen(
                [sys.executable, "-m", "src.engine.market.rule_graph_worker", str(folder)],
                cwd=PROJECT_ROOT,
                env=environment,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=sys.platform != "win32",
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            while process.poll() is None:
                if (folder / "completed.json").exists():
                    break
                if (folder / "failure.json").exists():
                    failure = json.loads((folder / "failure.json").read_text(encoding="utf-8"))
                    reason = failure.get("message") or failure["error"]
                    break
                if lease.is_set() or self.store.cancelled(key):
                    reason = "cancelled"
                    break
                if monotonic() - started >= policy["timeout_seconds"]:
                    reason = "deadline"
                    break
                sleep(policy["poll_seconds"])
            if not (folder / "completed.json").exists() and not reason:
                reason = (
                    json.loads((folder / "failure.json").read_text(encoding="utf-8"))["error"]
                    if (folder / "failure.json").exists()
                    else "Worker stopped before completion"
                )
        except Exception as exc:
            reason = type(exc).__name__
        finally:
            try:
                if process is not None and process.poll() is None:
                    stop_process_tree(process)
                    process.wait(timeout=policy["shutdown_seconds"])
                graph_path = (
                    folder / "completed.json" if (folder / "completed.json").exists() else folder / "checkpoint.json"
                )
                if reason == "cancelled":
                    row["status"] = "cancelled"
                elif graph_path.exists():
                    graph = json.loads(graph_path.read_text(encoding="utf-8"))
                    row["status"] = (
                        "completed"
                        if graph_path.name == "completed.json" and not reason and not graph.get("source_partial")
                        else "partial"
                    )
                    graph.update(
                        request=row["request"],
                        run_id=key,
                        status=row["status"],
                        elapsed_ms=round((monotonic() - started) * 1000),
                        partial_reason=reason or ("Source branches incomplete" if row["status"] == "partial" else ""),
                    )
                    write_json(folder / "graph.json", graph)
                else:
                    row["status"] = "failed"
                row.update(reason=reason, finished_at=utc_now_iso(), duration_ms=round((monotonic() - started) * 1000))
                self.store.save(row)
                if row["status"] in {"failed", "partial"}:
                    get_logger("rule_graph").warning(
                        "Rule graph stopped | run={} status={} reason={}",
                        key,
                        row["status"],
                        reason or "Source coverage incomplete",
                    )
            finally:
                finish_run("rule_graph", key)
                lease.close()
                with LOCK:
                    ACTIVE.pop(key, None)

    def detail(self, key):
        row = self.store.get(key)
        if row["status"] in {"queued", "running"} and key not in ACTIVE and not lease_alive("rule_graph", key):
            row.update(status="interrupted", reason="Worker owner stopped; restart explicitly")
            self.store.save(row)
        checkpoint = self.store.directory(key) / "checkpoint.json"
        if checkpoint.exists():
            row["stage"] = json.loads(checkpoint.read_text(encoding="utf-8"))["stage"]
        return row
