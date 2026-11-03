"""Idea and implementation stages see only discovery evidence, never validation labels."""

from src.core.repository import json_loads
from src.core.timeutil import utc_now_iso

from .agents import AgentSession
from .config import invalid
from .factors import market_panel
from .pit import known_documents
from .store import LOCK, AlphaStore
from .studies import add_candidate


def research_evidence(study: dict) -> dict:
    cfg = study["config"]
    return {
        "purpose": cfg["purpose"],
        "batch_size": cfg["batch_size"],
        "policy": cfg["policy"],
        "discovery_end": cfg["splits"]["train"][-1],
        "validation_and_holdout_labels": "not_available",
    }


def discover(store: AlphaStore, study: dict, session: AgentSession, emit) -> dict:
    cfg = study["config"]
    catalog = {"fields": cfg["fields"], "operators": cfg["operators"], "max_window": cfg["limits"]["max_window"]}
    # Historical runs cannot consult research memories created after discovery time.
    cutoff = cfg["splits"]["train"][-1]
    dataset = store.get("alpha_datasets", study["dataset_id"])
    training_history = {
        symbol: [row for row in rows if row["date"] <= cutoff] for symbol, rows in dataset["payload"]["history"].items()
    }
    training = market_panel(training_history)
    summaries = {
        field: {
            "observations": int(frame.count().sum()),
            "missing": int(frame.isna().sum().sum()),
            "first_date": str(frame.index[0]),
            "last_date": str(frame.index[-1]),
            "median": float(frame.stack().median()) if frame.count().sum() else None,
        }
        for field, frame in training.items()
    }
    research = {
        **research_evidence(study),
        "training_summary": summaries,
        "symbols": sorted(training_history),
        "limitations": dataset["payload"]["limitations"],
    }
    memories = store.repo.db.query(
        "SELECT name,mode,status,created_at FROM alpha_studies WHERE created_at<=? AND id<>? ORDER BY id DESC LIMIT 20",
        (cutoff, study["id"]),
    )
    if cfg.get("memory_dataset_id"):
        memory = store.get("alpha_datasets", cfg["memory_dataset_id"])
        memories.extend(known_documents(memory["payload"]["documents"], cutoff + "T00:00:00+00:00"))
    response = session.run("idea", {"catalog": catalog, "research": research, "memory": memories}, cfg["purpose"])
    ideas = response.get("ideas")
    remaining = cfg["batch_size"] - len(store.list("alpha_candidates", study["id"]))
    if not isinstance(ideas, list) or not 1 <= len(ideas) <= remaining:
        raise invalid("Idea Person返回的假设数量为空或超过剩余预算")
    identifiers = []
    for hypothesis in ideas:
        if not isinstance(hypothesis, dict):
            raise invalid("假设必须为对象")
        try:
            implementation = session.run(
                "implement",
                {"catalog": catalog, "hypothesis": hypothesis, "research": research},
                cfg["purpose"],
            )
        except Exception as exc:
            if session.cancelled():
                raise
            implementation = {"unsupported": str(exc)}
        candidate = add_candidate(store, study["id"], hypothesis, implementation, "ai")
        identifiers.append(candidate["id"])
        emit("implementation", {"candidate_id": candidate["id"], "status": candidate["status"]})
    return {"candidate_ids": identifiers, "validation_visible_to_agents": False}


def reserve_holdout(store: AlphaStore, study_id: int, candidate_id: int) -> dict:
    with LOCK, store.repo.db.transaction():
        study = store.get("alpha_studies", study_id)
        if study["status"] != "validated" or not any(
            row["candidate_id"] == candidate_id and row.get("passed") for row in study["result"].get("validation", [])
        ):
            raise invalid("只有冻结验证通过的候选可以一次性使用留出")
        dataset = store.get("alpha_datasets", study["dataset_id"])
        symbols, days = sorted(dataset["payload"]["history"]), study["config"]["splits"]["holdout"]
        previous = store.repo.db.query(
            "SELECT * FROM alpha_holdouts WHERE market=? AND start_date<=? AND end_date>=?",
            (study["config"]["market"], days[-1], days[0]),
        )
        if any(set(symbols) & set(json_loads(row["symbols"], [])) for row in previous):
            raise invalid("相同证券和重叠留出日期已经消费，换项目或改文件名不能重新解锁")
        store.repo.insert(
            "alpha_holdouts",
            {
                "study_id": study_id,
                "candidate_id": candidate_id,
                "market": study["config"]["market"],
                "symbols": symbols,
                "start_date": days[0],
                "end_date": days[-1],
                "created_at": utc_now_iso(),
            },
        )
        store.event(
            study_id, "holdout_reserved", {"candidate_id": candidate_id, "start_date": days[0], "end_date": days[-1]}
        )
        return store.transition(study_id, {"validated"}, "testing")
