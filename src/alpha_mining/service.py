"""One asynchronous research lifecycle for Gradio, REST and the command line."""

import json
from threading import Event, Thread
from time import monotonic

from loguru import logger

from src.core.task_control import TaskEvent, cancel_lease, lease_alive
from src.core.timeutil import utc_now_iso

from .agents import AgentSession
from .config import config, digest, invalid, source_manifest
from .datasets import validate_dataset
from .discovery import discover, reserve_holdout
from .evaluation import evaluate_holdout, validate_family
from .families import check_unseen_validation
from .regime import run_regime
from .report import render
from .store import LOCK, AlphaStore
from .studies import add_candidate, create_study
from .theme import run_theme

ACTIVE: dict[tuple[str, int], tuple[Event, Thread]] = {}


class AlphaService:
    def __init__(self, store: AlphaStore | None = None, llm=None):
        self.store = store or AlphaStore()
        self.llm = llm

    def register_dataset(self, name: str, kind: str, payload: dict, provenance: dict | None = None) -> dict:
        if len(json.dumps(payload, ensure_ascii=False).encode()) > config()["limits"]["max_upload_bytes"]:
            raise invalid("研究数据超过导入大小上限")
        normalized = validate_dataset(kind, payload)
        row = self.store.insert(
            "alpha_datasets",
            {
                "name": name[:200],
                "kind": kind,
                "payload": normalized,
                "digest": digest(normalized),
                "provenance": provenance or {"verified": False, "method": "user_import_requires_source_review"},
                "created_at": utc_now_iso(),
            },
        )
        return self.dataset_metadata(row)

    @staticmethod
    def dataset_metadata(row: dict) -> dict:
        payload = row["payload"]
        return {
            key: value
            for key, value in {
                **row,
                "payload": None,
                "assets": len(payload.get("history", {})),
                "observations": len(payload.get("documents") or payload.get("observations") or []),
                "source": payload.get("source"),
                "is_mock": payload.get("is_mock"),
            }.items()
            if key != "payload"
        }

    def create(self, request: dict) -> dict:
        return create_study(self.store, request)

    def candidate(self, study_id: int, hypothesis: dict, implementation: dict) -> dict:
        return add_candidate(self.store, study_id, hypothesis, implementation, "human")

    def seal(self, study_id: int) -> dict:
        with LOCK, self.store.repo.db.transaction():
            study = self.store.get("alpha_studies", study_id)
            if study["config"]["source_manifest"] != source_manifest():
                raise invalid("研究实现或政策文件已改变，请登记新版本，不在旧版本上覆盖结果")
            rows = self.store.list("alpha_candidates", study_id)
            if study["mode"] != "alpha" or not rows:
                raise invalid("冻结家族需要至少一个已登记候选")
            return self.store.transition(
                study_id,
                {"draft", "discovered"},
                "sealed",
                {**study["result"], "sealed_candidates": [{"id": row["id"], "digest": row["digest"]} for row in rows]},
            )

    def start(self, study_id: int, action: str, candidate_id: int | None = None) -> dict:
        key = str(self.store.root), study_id
        with LOCK:
            if key in ACTIVE:
                raise invalid("该研究正在运行，不能重复提交")
            if len(ACTIVE) >= config()["limits"]["max_jobs"]:
                raise invalid("研究队列已满")
            cancel = TaskEvent("alpha", study_id, self.store.repo, config()["limits"]["max_jobs"])
            try:
                study = self.store.get("alpha_studies", study_id)
                stages = {
                    "discover": ({"draft", "discovered"}, "discovering"),
                    "validate": ({"sealed"}, "validating"),
                    "run": ({"draft"}, "discovering"),
                }
                if action == "holdout":
                    study = reserve_holdout(self.store, study_id, int(candidate_id or 0))
                elif action in stages:
                    if (action == "run") == (study["mode"] == "alpha"):
                        raise invalid("研究流程与操作不匹配")
                    allowed, state = stages[action]
                    if action == "validate":
                        check_unseen_validation(self.store, study)
                    study = self.store.transition(study_id, allowed, state)
                else:
                    raise invalid("未知研究操作")
                thread = Thread(
                    target=self._execute,
                    args=(study, action, candidate_id, cancel, key),
                    daemon=True,
                    name="alpha-" + str(study_id),
                )
                ACTIVE[key] = cancel, thread
                thread.start()
                return study
            except Exception:
                ACTIVE.pop(key, None)
                cancel.close()
                raise

    def _execute(self, study: dict, action: str, candidate_id: int | None, cancel: Event, key: tuple) -> None:
        started = monotonic()

        def emit(kind, data=None, extra=None):
            if cancel.is_set():
                raise invalid("研究已取消")
            if monotonic() - started > study["config"]["limits"]["timeout_seconds"]:
                raise invalid("研究达到总耗时预算")
            self.store.event(study["id"], kind, {"data": data, "details": extra} if extra is not None else data or {})

        session = None
        try:
            session = AgentSession(self.store, study, self.llm, cancel.is_set)
            if action == "discover":
                result, target = discover(self.store, study, session, emit), "discovered"
            elif action == "validate":
                result, target = validate_family(self.store, study, session, emit, cancel.is_set), "validated"
            elif action == "holdout":
                candidate = self.store.get("alpha_candidates", int(candidate_id or 0))
                result, target = (
                    evaluate_holdout(self.store, study, candidate, session, emit, cancel.is_set),
                    "reviewed",
                )
            elif study["mode"] == "theme":
                result, target = run_theme(self.store, study, session, emit), "completed"
            else:
                result, target = run_regime(self.store, study, session, emit), "completed"
            if cancel.is_set():
                raise invalid("研究已取消")
            result["duration_ms"] = round((monotonic() - started) * 1000)
            self.store.write(study["id"], action + "-result.json", result)
            render(self.store, study["id"], {**study, "status": target, "result": result})
            self.store.transition(study["id"], {study["status"]}, target, result)
            self.store.event(study["id"], "finished", {"action": action, "duration_ms": result["duration_ms"]})
        except Exception as exc:
            logger.warning("Alpha研究结束 | study={} action={} error={}", study["id"], action, exc)
            current = self.store.get("alpha_studies", study["id"])
            self.store.transition(
                study["id"],
                {current["status"]},
                "cancelled" if cancel.is_set() else "failed",
                {**current["result"], "error": str(exc), "action": action},
            )
            render(self.store, study["id"])
        finally:
            try:
                transport = getattr(session.llm, "session", None) if session is not None and self.llm is None else None
                if transport is not None:
                    transport.close()
            finally:
                if isinstance(cancel, TaskEvent):
                    cancel.close()
                with LOCK:
                    ACTIVE.pop(key, None)

    def cancel(self, study_id: int) -> dict:
        self.store.get("alpha_studies", study_id)
        with LOCK:
            job = ACTIVE.get((str(self.store.root), study_id))
            remote = cancel_lease("alpha", study_id, self.store.repo)
            if not job and not remote:
                raise invalid("研究没有正在运行的任务")
            if job:
                job[0].set()
        self.store.event(study_id, "cancel_requested", {"network_request": "stops_after_current_bounded_request"})
        return {"study_id": study_id, "cancel_requested": True}

    def detail(self, study_id: int) -> dict:
        study = self.store.get("alpha_studies", study_id)
        with LOCK:
            running = (str(self.store.root), study_id) in ACTIVE
            if (
                study["status"] in {"discovering", "validating", "testing"}
                and not running
                and not lease_alive("alpha", study_id, self.store.repo)
            ):
                study = self.store.transition(
                    study_id,
                    {study["status"]},
                    "failed",
                    {**study["result"], "error": "运行进程已中断；保留已有候选/试验，不自动重跑或重新解锁留出"},
                )
        return {
            **study,
            "candidates": self.store.list("alpha_candidates", study_id),
            "trials": self.store.list("alpha_trials", study_id),
            "reviews": self.store.list("alpha_reviews", study_id),
            "event_chain_valid": self.store.verify_events(study_id),
        }


def shutdown() -> None:
    with LOCK:
        jobs = list(ACTIVE.values())
        for cancel, _ in jobs:
            cancel.set()
    for _, thread in jobs:
        thread.join()
