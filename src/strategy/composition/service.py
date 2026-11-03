"""Bounded asynchronous runs, shared by Gradio, REST, CLI and paper monitors."""

import json
from copy import deepcopy
from datetime import date, timedelta
from threading import Event, RLock, Thread
from time import monotonic
from typing import Any
from uuid import uuid4

from loguru import logger

from src.agent.providers import provider_snapshot
from src.core.stream_control import stream_pause
from src.core.task_control import TaskEvent, TaskLease, cancel_lease, lease_alive
from src.core.timeutil import utc_now_iso
from src.engine.composition.data import load_snapshot
from src.engine.composition.preflight import preflight
from src.engine.composition.report import render
from src.engine.composition.simulation import CompositionSimulation
from src.engine.execution.runtime import prepare_execution
from src.engine.market.resource_pool import ResourcePoolService

from .accounts import PipelineAccounts
from .config import config, fail, merge, template
from .store import PipelineStore
from .validation import compile_plan, digest

JOB_LOCK = RLock()
ACTIVE: dict[str, Event] = {}
ACTIVE_KEYS: dict[str, str] = {}


def today() -> str:
    return date.today().isoformat()


def component_catalog() -> list[dict[str, Any]]:
    cfg = config()
    return (
        [{"id": key, **row} for key, row in cfg["components"].items()]
        + [
            {"id": key, "kind": "portfolio", "label": label, "defaults": cfg["defaults"]["portfolio"]}
            for key, label in cfg["portfolios"].items()
        ]
        + [
            {
                "id": key,
                "kind": "risk",
                "label": value["label"],
                "status": value.get("status", "available"),
                "defaults": {field: cfg["defaults"]["risk"][field] for field in value["fields"]},
            }
            for key, value in cfg["risk_components"].items()
        ]
    )


def validation_summary(diagnostics: dict[str, Any]) -> dict[str, Any]:
    models = list((diagnostics.get("model_diagnostics") or {}).values())
    for child in (diagnostics.get("children") or {}).values():
        child_result = validation_summary(child)
        models.extend(child_result["models"])
    return {"models": models, "unexercised_models": sum(not model.get("predictions") for model in models)}


class PipelineService:
    def __init__(self, store: PipelineStore | None = None):
        self.store = store or PipelineStore()
        self.cfg = config()

    def preview(
        self, definition: dict[str, Any], overrides: dict[str, Any] | None = None, variant: str = "baseline"
    ) -> dict[str, Any]:
        plan = compile_plan(definition, overrides, variant)
        return {"compiled": plan, "digest": digest(plan), "training_started": False, "model_called": False}

    def _normalize(self, payload: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
        request = dict(payload)
        mode = request.get("mode") or "screen"
        if mode not in {"screen", "targets", "backtest", "replay", "paper"}:
            raise fail("invalid", "mode")
        request["mode"] = mode
        if mode == "paper" and request.get("execution_costs"):
            raise fail("invalid", "本次执行费用覆盖用于研究回测；模拟账户沿用发布方案，调整后请创建新版本和账户")
        request["end_date"] = str(request.get("end_date") or today())
        request["start_date"] = str(
            request.get("start_date")
            or (
                date.fromisoformat(request["end_date"]) - timedelta(days=self.cfg["defaults"]["default_backtest_days"])
            ).isoformat()
        )
        if (
            date.fromisoformat(request["end_date"]) > date.fromisoformat(today())
            or request["start_date"] > request["end_date"]
        ):
            raise fail("invalid", "dates")
        request["market"] = str(request.get("market") or "CN").upper()
        if request["market"] not in {"CN", "US"}:
            raise fail("invalid", "market")
        if request.get("resource_pool_id"):
            request["symbols"] = [
                row["symbol"] for row in ResourcePoolService().list_items(int(request["resource_pool_id"]))
            ]
            if not request["symbols"]:
                raise fail("invalid", "resource pool is empty")
        request["agent_mode"] = request.get("agent_mode") or (
            "off" if mode == "backtest" else "replay" if mode == "replay" else "live"
        )
        if request.get("risk_only") and mode != "paper":
            raise fail("invalid", "risk_only mode")
        if request["agent_mode"] not in {"off", "live", "replay", "research"}:
            raise fail("invalid", "agent_mode")
        if request["agent_mode"] == "research" and mode in {"paper", "replay"}:
            raise fail("invalid", "历史研究生成不能冒充前向模拟或当时决定回放")
        if request["agent_mode"] == "live" and (mode in {"backtest", "replay"} or request["end_date"] != today()):
            raise fail("live_history")
        if mode == "paper" and request["end_date"] != today():
            raise fail("lookahead", "paper date")
        if request.get("backend") not in {None, "api", "codex", "qoder", "trae", "codebuddy"}:
            raise fail("invalid_backend")
        if request.get("account_id") and not request.get("version_id"):
            request["version_id"] = PipelineAccounts(self.store).detail(int(request["account_id"]))["version_id"]
        if request.get("version_id"):
            version = self.store.version(int(request["version_id"]), True)
            parent = self.store.repo.get("strategy_pipelines", version["pipeline_id"])
            if parent["status"] == "disabled" and not request.get("risk_only"):
                raise fail("invalid", "pipeline disabled; risk-only monitoring remains available")
            if request.get("overrides") or request.get("variant") not in {None, "baseline"}:
                raise fail("immutable")
            return request, version
        definition = request.get("definition") or template(
            str(request.get("template") or self.cfg["defaults"]["default_template"])
        )
        compiled = compile_plan(definition, request.get("overrides"), request.get("variant") or "baseline")
        # Save the resolved definition, so runtime has no hidden parameter layer.
        request["resolved_digest"] = digest(compiled)
        return request, {"definition": definition, "compiled": compiled, "_unpublished": True}

    def start(self, payload: dict[str, Any]) -> dict[str, Any]:
        request, version = self._normalize(payload)
        if request["agent_mode"] in {"live", "research"}:
            request["_provider_snapshot"] = provider_snapshot(request, probe=request.get("backend", "api") != "api")
            if request["_provider_snapshot"].get("model_id"):
                request["model_id"] = request["_provider_snapshot"]["model_id"]
        key = digest({"root": str(self.store.root), "request": request, "plan": version["compiled"]})
        with JOB_LOCK:
            if key in ACTIVE_KEYS:
                return self.store.run(ACTIVE_KEYS[key])
            if len(ACTIVE) >= self.cfg["defaults"]["max_jobs"]:
                raise fail("busy")
            if version.pop("_unpublished", False):
                raw = merge(
                    version["definition"],
                    (version["definition"].get("variants") or {}).get(request.get("variant") or "baseline", {}),
                )
                raw = merge(raw, request.get("overrides") or {})
                raw["variants"] = {"baseline": {}}
                draft = self.store.save_draft(raw)
                version = self.store.publish(draft["id"])
            request["version_id"] = version["id"]
            run_id = uuid4().hex
            lease = TaskLease("pipeline", run_id, self.store.repo, self.cfg["defaults"]["max_jobs"])
            try:
                self.store.repo.db.execute(
                    "INSERT INTO strategy_pipeline_runs(id,version_id,status,request,created_at) VALUES(?,?,?,?,?)",
                    (
                        run_id,
                        version["id"],
                        "running",
                        json.dumps(request, ensure_ascii=False, allow_nan=False),
                        utc_now_iso(),
                    ),
                )
                self.store.append(
                    run_id,
                    "status",
                    self.cfg["messages"]["submitted"],
                    {"mode": request["mode"], "version_id": version["id"]},
                )
                cancel = TaskEvent("pipeline", run_id, lease=lease)
                ACTIVE[run_id] = cancel
                ACTIVE_KEYS[key] = run_id
                Thread(
                    target=self._execute,
                    args=(run_id, request, version, cancel, key),
                    daemon=True,
                    name="pipeline-" + run_id,
                ).start()
                return self.store.run(run_id)
            except Exception:
                ACTIVE.pop(run_id, None)
                ACTIVE_KEYS.pop(key, None)
                lease.close()
                raise

    def _execute(self, run_id: str, request: dict[str, Any], version: dict[str, Any], cancel: Event, key: str) -> None:
        started = monotonic()
        result: dict[str, Any] = {}
        account = None
        simulation = None

        def emit(kind: str, text: str, data: Any = None):
            if cancel.is_set():
                raise fail("cancelled")
            if monotonic() - started > self.cfg["defaults"]["deadline_seconds"]:
                raise fail("timeout")
            self.store.append(run_id, kind, text, data)

        try:
            plan = deepcopy(version["compiled"])
            instrument = self.cfg["defaults"]["instruments"][request["market"]]
            for field in ("lot_size", "settlement_sessions"):
                if field not in version["definition"].get("execution", {}):
                    plan["execution"][field] = instrument[field]
            plan = prepare_execution(plan, request)
            self.store.write(run_id, "request.json", request)
            self.store.write(run_id, "definition.json", version)
            snapshot = load_snapshot(request, plan, emit)
            warnings = preflight(plan, snapshot, request)
            self.store.write(run_id, "snapshot.json", snapshot)
            request_runtime = {**request, "_cancelled": cancel.is_set}
            if request["mode"] == "paper":
                accounts = PipelineAccounts(self.store)
                account = (
                    accounts.detail(int(request["account_id"]))
                    if request.get("account_id")
                    else accounts.create(version["id"], plan["name"])
                )
                if account["version_id"] != version["id"]:
                    raise fail("invalid", "account version")
                saved = account["state"]
                current_state = digest({k: saved.get(k) for k in ("book", "risk", "pending", "pending_due")})
                expired = (
                    saved.get("pending_due")
                    and saved.get("pending_valid_until")
                    and request["end_date"] > saved["pending_valid_until"]
                )
                if (
                    request.get("risk_only")
                    and saved.get("source_snapshot_id") == digest(snapshot)
                    and saved.get("monitor_state_digest") == current_state
                    and not expired
                ):
                    self.store.append(
                        run_id, "monitor", "unchanged", {"account_id": account["id"], "snapshot_id": digest(snapshot)}
                    )
                    self._finish(
                        run_id,
                        "finished",
                        {
                            "account_id": account["id"],
                            "monitor_no_change": True,
                            "report_reference": saved.get("last_run_id"),
                            "source": snapshot["source"],
                            "is_mock": snapshot["is_mock"],
                        },
                    )
                    return
            simulation = CompositionSimulation(
                plan, snapshot, request_runtime, self.store, emit, account["state"] if account else None, cancel.is_set
            )
            result = simulation.run()
            validation = validation_summary(result["diagnostics"])
            if validation["unexercised_models"]:
                warnings.append("model_not_exercised")
            result.update(
                version_id=version["id"],
                pipeline_id=version["pipeline_id"],
                source_manifest=version["manifest"],
                definition_digest=version["digest"],
                agent_mode=request["agent_mode"],
                warnings=warnings,
                duration_ms=round((monotonic() - started) * 1000),
                snapshot_id=digest(snapshot),
                execution_policy=plan["execution"],
                instrument_assumption=instrument["policy"],
                validation={
                    "model_count": len(validation["models"]),
                    "unexercised_models": validation["unexercised_models"],
                },
            )
            status = "failed" if result["decision_errors"] else "finished"
            if account:
                state = {
                    **account["state"],
                    **result["ledger"],
                    "last_run_id": run_id,
                    "monitor_request": {
                        k: v
                        for k, v in request.items()
                        if k not in {"definition", "overrides", "template", "snapshot_id"}
                    },
                }
                state["source_snapshot_id"] = digest(snapshot)
                state["monitor_state_digest"] = digest(
                    {k: state.get(k) for k in ("book", "risk", "pending", "pending_due")}
                )
                self.store.save_account(account["id"], account["version"], state, simulation.book.last_day)
                result["account_id"] = account["id"]
            self.store.write(run_id, "ledger.json", result.pop("ledger"))
            self.store.write(run_id, "result.json", result)
            row = {"id": run_id, "status": status, "request": request}
            (self.store.directory(run_id) / "report.html").write_text(render(row, result), encoding="utf-8")
            self.store.append(
                run_id, "artifact", self.cfg["messages"]["saved"], {"name": "report.html", "status": status}
            )
            self._finish(run_id, status, result)
        except Exception as exc:
            status = "cancelled" if cancel.is_set() else "failed"
            result.update(error=str(exc), duration_ms=round((monotonic() - started) * 1000))
            self.store.append(run_id, "error", str(exc), {"status": status})
            self._finish(run_id, status, result)
            logger.warning("pipeline run failed | id={} status={} error={}", run_id, status, exc)
        finally:
            if isinstance(cancel, TaskEvent):
                cancel.close()
            with JOB_LOCK:
                ACTIVE.pop(run_id, None)
                ACTIVE_KEYS.pop(key, None)

    def _finish(self, run_id: str, status: str, result: dict[str, Any]) -> None:
        self.store.repo.db.execute(
            "UPDATE strategy_pipeline_runs SET status=?,result=?,finished_at=? WHERE id=?",
            (status, json.dumps(result, ensure_ascii=False, allow_nan=False), utc_now_iso(), run_id),
        )

    def detail(self, run_id: str) -> dict[str, Any]:
        with JOB_LOCK:
            row = self.store.run(run_id)
            if (
                row["status"] in {"running", "cancelling"}
                and row["id"] not in ACTIVE
                and not lease_alive("pipeline", run_id, self.store.repo)
            ):
                self._finish(row["id"], "failed", {"error": self.cfg["messages"]["interrupted"]})
                row = self.store.run(run_id)
            return row

    def follow(self, run_id: str):
        cursor = 0
        while True:
            row = self.detail(run_id)
            events = self.store.events(run_id)
            if len(events) > cursor or row["status"] not in {"running", "cancelling"}:
                yield {"run": row, "events": events[cursor:]}
                cursor = len(events)
            if row["status"] not in {"running", "cancelling"}:
                return
            stream_pause(self.cfg["defaults"]["poll_seconds"])

    def cancel(self, run_id: str) -> dict[str, Any]:
        with JOB_LOCK:
            row = self.detail(run_id)
            cancel_lease("pipeline", run_id, self.store.repo)
            if row["id"] in ACTIVE:
                ACTIVE[row["id"]].set()
                self.store.repo.db.execute(
                    "UPDATE strategy_pipeline_runs SET status='cancelling' WHERE id=?", (row["id"],)
                )
            return self.store.run(run_id)
