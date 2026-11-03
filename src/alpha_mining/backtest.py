"""Pair research signals and explicit baselines through the existing physical ledger."""

from typing import Any

import numpy as np
import pandas as pd

from src.engine.composition.simulation import CompositionSimulation
from src.strategy.composition.validation import compile_plan
from src.strategy.factors.statistics import correlation

from .config import invalid
from .contracts import ResearchPermit
from .statistics import block_test


def plan_definition(study: dict, candidate_id: int, symbols: list[str], benchmark: bool = False) -> dict:
    policy = study["config"]["policy"]
    return {
        "schema_version": 1,
        "name": study["name"],
        "description": "冻结Alpha研究；配对基准同费用与风险",
        "universe": {"symbols": symbols},
        "nodes": [
            {
                "id": "signal",
                "component": "eligibility" if benchmark else "alpha_factor",
                "inputs": ["universe"],
                "params": {}
                if benchmark
                else {"study_id": study["id"], "candidate_id": candidate_id, "artifact_digest": ""},
            }
        ],
        "output": "signal",
        "portfolio": {
            "component": "equal",
            "params": {"top_k": len(symbols) if benchmark else policy["top_k"], "max_weight": policy["max_weight"]},
        },
        "risk": {"max_weight": policy["max_weight"], "max_drawdown": policy["maximum_drawdown"]},
        "execution": study["config"].get("execution") or {},
        "rebalance_sessions": policy["rebalance_sessions"],
        "variants": {"baseline": {}},
    }


def simulate(
    study: dict,
    snapshot: dict,
    days: list[str],
    definition: dict,
    scores: pd.DataFrame | None,
    candidate_id: int,
    emit,
    cancelled=None,
    targets=False,
) -> dict[str, Any]:
    plan = compile_plan(definition)
    request = {
        "mode": "backtest",
        "start_date": days[0],
        "end_date": days[-1],
        "agent_mode": "off",
        "market": study["config"]["market"],
        "execution_cost_snapshot": study["config"].get("execution_costs"),
    }
    if scores is not None:
        request["_alpha_permit"] = ResearchPermit(study["id"], candidate_id, scores, targets=targets)
    simulation = CompositionSimulation(plan, snapshot, request, None, emit, cancelled=cancelled)
    return simulation.run()


def paired_backtest(
    study: dict, candidate: dict, snapshot: dict, scores: pd.DataFrame, days: list[str], emit, cancelled=None
) -> dict[str, Any]:
    names = sorted(snapshot["history"])
    active = plan_definition(study, candidate["id"], names)
    baseline = plan_definition(study, candidate["id"], names, benchmark=True)
    actual = simulate(study, snapshot, days, active, scores, candidate["id"], emit, cancelled)
    reference = simulate(study, snapshot, days, baseline, None, candidate["id"], emit, cancelled)
    return paired_results(actual, reference, study["config"]["policy"])


def paired_results(actual: dict, reference: dict, policy: dict) -> dict:
    if actual["curve"]["dates"] != reference["curve"]["dates"]:
        raise invalid("策略与基准交易日期没有对齐")
    equity, baseline = np.asarray(actual["curve"]["equity"]), np.asarray(reference["curve"]["equity"])
    # Both physical books start from the same explicitly frozen capital.
    initial = float(equity[-1] - actual["metrics"]["total_pnl"])
    prior = np.concatenate(([initial], equity[:-1]))
    baseline_prior = np.concatenate(([initial], baseline[:-1]))
    excess = (equity / prior - baseline / baseline_prior).tolist()
    return {
        "strategy": actual,
        "baseline": reference,
        "net_excess_return": actual["metrics"]["total_return"] - reference["metrics"]["total_return"],
        "excess_inference": block_test(excess, policy),
        "strategy_baseline_return_correlation": correlation(
            (equity / prior - 1).tolist(), (baseline / baseline_prior - 1).tolist()
        ),
        "comparison": "same_dates_universe_execution_costs_and_risk_equal_weight_baseline",
    }
