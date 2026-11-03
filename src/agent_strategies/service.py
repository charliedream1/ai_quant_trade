"""Frozen shared service for graph stages and bounded background research runs."""

from datetime import date
from threading import Event, Thread

from loguru import logger

from src.agent.llm_client import LLMClient
from src.agent.providers import provider_snapshot
from src.alpha_mining.config import digest
from src.alpha_mining.store import AlphaStore
from src.core.task_control import TaskEvent, cancel_lease
from src.engine.execution.config import resolve_costs
from src.strategy.composition.contracts import Frame
from src.strategy.composition.validation import settings as execution_settings

from .config import freeze, settings
from .contest import data_team, research_team
from .debate import analyze, debate
from .evidence import assemble
from .report import render
from .scores import mature
from .session import Session
from .store import LOCK, StrategyStore

ACTIVE: dict[tuple[str, int], Event] = {}


class AgentStrategyService:
    def __init__(self, store=None, llm=None):
        self.store = store or StrategyStore()
        self.llm = llm

    def prepare(self, request: dict, frame: Frame) -> dict:
        cfg = freeze(request["recipe"], request.get("options"))
        mode = request.get("validation_mode", "current_research")
        if mode not in {"current_research", "historical_research"}:
            raise ValueError("未知研究验证模式")
        if frame.as_of != date.today().isoformat() and mode != "historical_research":
            raise ValueError("历史生成必须显式选择historical_research，不能冒充当时决定")
        candidates = request.get("symbols") or frame.active()
        candidates = sorted(set(candidates))
        if not candidates:
            raise ValueError("研究没有有效候选；请明确选择股票池或有当期数据的证券")
        if not set(candidates) <= set(frame.history):
            raise ValueError("研究证券超出行情母池")
        evidence = assemble(frame, candidates, cfg, request.get("documents_dataset_id"))
        safe = {
            key: request[key]
            for key in (
                "recipe",
                "market_dataset_id",
                "documents_dataset_id",
                "backend",
                "model_id",
                "model_name",
                "reasoning_effort",
                "scope",
                "market",
                "validation_mode",
                "execution_costs",
                "execution_cost_snapshot",
                "execution",
                "risk",
            )
            if key in request
        }
        safe.update(as_of=frame.as_of, symbols=sorted(candidates))
        safe["execution"] = execution_settings("execution", safe.get("execution"))
        safe["risk"] = execution_settings("risk", safe.get("risk"))
        safe["execution_cost_snapshot"] = safe.get("execution_cost_snapshot") or resolve_costs(
            safe.get("execution_costs"), safe["execution"]
        )
        if not self.llm:
            client = LLMClient(repo=self.store.repo)
            try:
                cfg["provider_snapshot"] = provider_snapshot(
                    safe, client=client, probe=safe.get("backend", "api") != "api"
                )
                if safe.get("backend", "api") == "api":
                    profile = client._select_config(safe.get("model_id"))
                    cfg["model_snapshot"] = {
                        key: profile.get(key) for key in ("id", "model_name", "base_url", "api_key_env")
                    }
                    safe["model_id"] = profile["id"]
                cfg["role_model_snapshots"] = {}
                for role, selection in cfg["policy"]["role_models"].items():
                    cfg["role_model_snapshots"][role] = provider_snapshot(
                        {**safe, **selection},
                        client=client,
                        probe=selection.get("backend", safe.get("backend", "api")) != "api",
                    )
            finally:
                client.session.close()
        lineage = digest(
            [
                cfg,
                sorted(frame.history),
                {
                    key: value
                    for key, value in safe.items()
                    if key not in {"as_of", "symbols", "market_dataset_id", "documents_dataset_id"}
                },
            ]
        )
        run = self.store.create(safe, cfg, evidence, lineage)
        self.store.event(
            run["id"],
            "registered",
            {"digest": run["digest"], "calls_budget": cfg["policy"]["calls"], "missing": evidence["missing"]},
        )
        return run

    def save(self, run: dict, status: str, result: dict) -> dict:
        self.store.write(
            run["id"], "report.html", render({**run, "status": status, "result": result}, self.all_events(run["id"]))
        )
        self.store.write(run["id"], "result.json", result)
        return self.store.update(run["id"], status, result)

    def all_events(self, run_id: int) -> list[dict]:
        result: list[dict] = []
        after = 0
        while True:
            page = self.store.events(run_id, after)
            if not page:
                return result
            result.extend(page)
            after = page[-1]["id"]

    def phase(self, run_id: int, final: bool, frame: Frame, emit=None, cancelled=None, budget=None) -> dict:
        run = self.store.get(run_id)
        expected = "prepared" if final else "created"
        with LOCK:
            if run["status"] != expected:
                raise ValueError("研究阶段不允许重复执行")
            self.store.update(run_id, "running", run["result"])
        session = None
        try:
            session = Session(self.store, run, emit, cancelled, self.llm, budget)
            evidence, result = run["evidence"], run["result"]
            if not final:
                updates = mature(self.store, run, frame) if run["config"]["definition"]["kind"] == "contest" else []
                stage = (
                    data_team(session, evidence)
                    if run["config"]["definition"]["kind"] == "contest"
                    else analyze(session, evidence)
                )
                result = {**stage, "shadow_updates": updates}
            else:
                result = (
                    research_team(session, evidence, result)
                    if run["config"]["definition"]["kind"] == "contest"
                    else debate(session, evidence, result)
                )
            result["validation_mode"] = run["request"].get("validation_mode", "current_research")
            status = "prepared" if not final else "partial" if evidence["missing"] else "completed"
            session.event("phase_completed", {"status": status, "final": final})
            return self.save(run, status, result)
        except Exception as exc:
            status = "cancelled" if cancelled and cancelled() else "failed"
            self.save(run, status, {**run["result"], "error": str(exc), "can_allocate": False})
            raise
        finally:
            if session is not None and not self.llm:
                transport = getattr(session.llm, "session", None)
                if transport is not None:
                    transport.close()

    def start(self, request: dict) -> dict:
        dataset = AlphaStore(self.store.repo).get("alpha_datasets", request["market_dataset_id"])
        if dataset["kind"] != "market":
            raise ValueError("必须选择真实日期行情数据集")
        frame = Frame.create(request["as_of"], dataset["payload"]["history"], dataset["payload"].get("metadata"))
        with LOCK:
            if len(ACTIVE) >= settings()["limits"]["max_jobs"]:
                raise ValueError("研究并发预算已满")
            run = self.prepare(request, frame)
            key, cancel = (
                (str(self.store.root), run["id"]),
                TaskEvent("agent_strategy", run["id"], self.store.repo, settings()["limits"]["max_jobs"]),
            )
            ACTIVE[key] = cancel
            try:
                Thread(target=self._execute, args=(run["id"], frame, key, cancel), daemon=True).start()
            except Exception:
                ACTIVE.pop(key, None)
                cancel.close()
                self.store.update(run["id"], "failed", {"error": "研究执行线程启动失败", "can_allocate": False})
                raise
        return run

    def _execute(self, run_id: int, frame: Frame, key, cancel: Event):
        try:
            self.phase(run_id, False, frame, cancelled=cancel.is_set)
            self.phase(run_id, True, frame, cancelled=cancel.is_set)
        except Exception as exc:
            logger.warning("Agent策略异步任务已结束 | run_id={} error_type={}", run_id, type(exc).__name__)
        finally:
            if isinstance(cancel, TaskEvent):
                cancel.close()
            with LOCK:
                ACTIVE.pop(key, None)

    def cancel(self, run_id: int) -> dict:
        self.store.get(run_id)
        with LOCK:
            remote = cancel_lease("agent_strategy", run_id, self.store.repo)
            cancel = ACTIVE.get((str(self.store.root), run_id))
            if cancel:
                cancel.set()
        self.store.event(run_id, "cancel_requested", {"active": cancel is not None})
        return {"requested": cancel is not None or remote, "run_id": run_id}


def shutdown():
    with LOCK:
        for cancel in ACTIVE.values():
            cancel.set()
