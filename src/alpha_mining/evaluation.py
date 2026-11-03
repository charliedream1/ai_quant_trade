"""Deterministic numerical and ledger evidence precedes any LLM verdict."""

from copy import deepcopy
from typing import Any

from src.core.timeutil import utc_now_iso

from .agents import AgentSession
from .backtest import paired_backtest
from .factors import causal_checks, evaluate_expression, market_panel
from .novelty import reference_overlap
from .research import factor_statistics
from .statistics import holm
from .store import AlphaStore


def numerical_evidence(store: AlphaStore, study: dict, candidate: dict, split: str, emit, cancelled=None) -> dict:
    cfg = study["config"]
    dataset = store.get("alpha_datasets", study["dataset_id"])
    days = cfg["splits"][split]
    snapshot = deepcopy(dataset["payload"])
    snapshot["history"] = {
        symbol: [row for row in rows if row["date"] <= days[-1]] for symbol, rows in snapshot["history"].items()
    }
    panel = market_panel(snapshot["history"])
    expression = candidate["implementation"]["expression"]
    training = {key: frame.loc[frame.index <= cfg["splits"]["train"][-1]] for key, frame in panel.items()}
    checks = causal_checks(expression, training)
    values = evaluate_expression(expression, panel) * candidate["hypothesis"]["direction"]
    stats = factor_statistics(values, panel["open"], days, cfg["policy"])
    overlap = reference_overlap(
        snapshot["history"], values, days, cfg["reference_factors"], cfg["policy"]["min_assets"]
    )
    paired = paired_backtest(study, candidate, snapshot, values, days, emit, cancelled)
    name = f"candidate-{candidate['id']}-{split}.json"
    evidence = {
        "candidate_id": candidate["id"],
        "candidate_digest": candidate["digest"],
        "split": split,
        "technical": checks,
        "reference_overlap": overlap,
        "statistics": stats,
        "backtest": paired,
        "source": dataset["provenance"],
        "data_is_mock": snapshot["is_mock"],
        "data_digest": dataset["digest"],
        "limitations": snapshot["limitations"],
        "artifact": name,
    }
    store.write(study["id"], name, evidence)
    return evidence


def summarize(evidence: dict) -> dict[str, Any]:
    paired, stats = evidence["backtest"], evidence["statistics"]
    return {
        "candidate_id": evidence["candidate_id"],
        "candidate_digest": evidence["candidate_digest"],
        "split": evidence["split"],
        "technical": evidence["technical"],
        "reference_overlap": evidence["reference_overlap"],
        "source": evidence["source"],
        "data_is_mock": evidence["data_is_mock"],
        "artifact": evidence["artifact"],
        "rank_ic": stats["mean_rank_ic"],
        "coverage": stats["mean_coverage"],
        "ic_inference": stats["inference"],
        "net_excess_return": paired["net_excess_return"],
        "strategy_baseline_return_correlation": paired["strategy_baseline_return_correlation"],
        "net_inference": paired["excess_inference"],
        "metrics": {key: value for key, value in paired["strategy"]["metrics"].items() if key != "execution_orders"},
        "baseline_metrics": {
            key: value for key, value in paired["baseline"]["metrics"].items() if key != "execution_orders"
        },
        "limitations": evidence["limitations"],
        "historical_model_memory_risk": True,
    }


def gates(summary: dict, policy: dict, ic_p: float, net_p: float) -> dict[str, bool]:
    return {
        "causal_implementation": summary["technical"]["passed"],
        "real_data": not policy["require_real_data"] or not summary["data_is_mock"],
        "verified_data": not policy["require_verified_data"] or bool(summary["source"].get("verified")),
        "sufficient_dates": summary["ic_inference"]["status"] == "evaluated"
        and summary["net_inference"]["status"] == "evaluated",
        "coverage": summary["coverage"] >= policy["min_coverage"],
        "ic_positive": summary["rank_ic"] is not None and summary["rank_ic"] > policy["min_rank_ic"],
        "ic_significant": ic_p <= policy["significance"],
        "net_significant": net_p <= policy["significance"],
        "net_positive": summary["net_excess_return"] > policy["min_net_excess"],
        "risk": abs(summary["metrics"]["max_drawdown"]) <= policy["maximum_drawdown"],
        "trades": summary["metrics"]["trade_count"] >= policy["min_trades"],
        "execution_capabilities": not summary["metrics"].get("execution_gaps"),
    }


def evaluator(session: AgentSession, study: dict, candidate: dict, summary: dict) -> dict:
    result = session.run(
        "evaluate",
        {"hypothesis": candidate["hypothesis"], "implementation": candidate["implementation"], "evidence": summary},
        study["config"]["purpose"],
    )
    if result.get("verdict") not in {"approve", "watch", "reject"} or not result.get("rationale"):
        raise ValueError("Evaluator没有返回有效结论")
    if not set(result.get("citations") or []).issubset({"hypothesis", "implementation", "evidence"}):
        raise ValueError("Evaluator引用不存在的证据")
    return result


def validate_family(store: AlphaStore, study: dict, session: AgentSession, emit, cancelled=None) -> dict:
    trials, summaries = [], []
    candidates = sorted(store.list("alpha_candidates", study["id"]), key=lambda row: row["id"])
    for candidate in candidates:
        trial = store.insert(
            "alpha_trials",
            {
                "study_id": study["id"],
                "candidate_id": candidate["id"],
                "split": "validation",
                "status": "running",
                "evidence": {"candidate_digest": candidate["digest"]},
                "created_at": utc_now_iso(),
            },
        )
        trials.append(trial)
        try:
            if candidate["status"] != "implemented":
                raise ValueError("候选实现未通过技术契约")
            summary = summarize(numerical_evidence(store, study, candidate, "validation", emit, cancelled))
        except Exception as exc:
            if cancelled and cancelled():
                raise
            summary = {"candidate_id": candidate["id"], "error": str(exc), "passed": False}
        summaries.append(summary)
        emit("candidate_evaluated", {"candidate_id": candidate["id"], "error": summary.get("error")})
    raw = [
        value
        for summary in summaries
        for value in (
            summary.get("ic_inference", {}).get("p_value", 1.0),
            summary.get("net_inference", {}).get("p_value", 1.0),
        )
    ]
    adjusted = holm(raw, 2 * study["config"]["batch_size"])
    for index, (candidate, trial, summary) in enumerate(zip(candidates, trials, summaries, strict=True)):
        if not summary.get("error"):
            summary["adjusted_ic_p"], summary["adjusted_net_p"] = adjusted[index * 2 : index * 2 + 2]
            summary["gates"] = gates(
                summary, study["config"]["policy"], summary["adjusted_ic_p"], summary["adjusted_net_p"]
            )
            try:
                summary["evaluator"] = evaluator(session, study, candidate, summary)
            except Exception as exc:
                summary["evaluator"] = {"verdict": "reject", "error": str(exc)}
            summary["passed"] = all(summary["gates"].values()) and summary["evaluator"]["verdict"] == "approve"
        store.repo.update(
            "alpha_trials", trial["id"], {"status": "finished", "evidence": summary, "finished_at": utc_now_iso()}
        )
        emit("candidate_verdict", {"candidate_id": candidate["id"], "passed": summary["passed"]})
    return {
        "validation": summaries,
        "registered_candidates": len(candidates),
        "planned_candidate_slots": study["config"]["batch_size"],
        "family_tests": 2 * study["config"]["batch_size"],
        "correction": "Holm_two_pre_registered_tests_per_candidate",
        "holdout_consumed": False,
    }


def evaluate_holdout(
    store: AlphaStore, study: dict, candidate: dict, session: AgentSession, emit, cancelled=None
) -> dict:
    trial = store.insert(
        "alpha_trials",
        {
            "study_id": study["id"],
            "candidate_id": candidate["id"],
            "split": "holdout",
            "status": "running",
            "evidence": {"candidate_digest": candidate["digest"]},
            "created_at": utc_now_iso(),
        },
    )
    try:
        summary = summarize(numerical_evidence(store, study, candidate, "holdout", emit, cancelled))
        summary["gates"] = gates(
            summary, study["config"]["policy"], summary["ic_inference"]["p_value"], summary["net_inference"]["p_value"]
        )
        summary["evaluator"] = evaluator(session, study, candidate, summary)
        summary["passed"] = all(summary["gates"].values()) and summary["evaluator"]["verdict"] == "approve"
    except Exception as exc:
        summary = {"candidate_id": candidate["id"], "error": str(exc), "passed": False}
    store.repo.update(
        "alpha_trials", trial["id"], {"status": "finished", "evidence": summary, "finished_at": utc_now_iso()}
    )
    return {**study["result"], "final": summary, "holdout_consumed": True, "automatic_live_trading": False}
