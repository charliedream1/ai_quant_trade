"""Independent configuration experiments see lagged, date-anonymized macro evidence only."""

from datetime import timedelta

import pandas as pd

from src.core.timeutil import utc_now_iso

from .agents import AgentSession
from .backtest import paired_results, plan_definition, simulate
from .config import config, invalid
from .pit import macro_snapshot, timestamp
from .store import AlphaStore


def anonymous_inputs(rows: list[dict], cutoff: str, framework: dict) -> tuple[list[dict], dict]:
    selected = [row for row in rows if row["series"] in {framework["growth_series"], framework["inflation_series"]}]
    values, mapping = macro_snapshot(selected, cutoff, framework["lag_days"])
    aliases = {framework["growth_series"]: "growth", framework["inflation_series"]: "inflation"}
    result = []
    for source, alias in aliases.items():
        matching = [row for row in values if row["series"] == source][-framework["window_observations"] :]
        result.extend(
            [{**row, "series": alias, "series_period": index - len(matching) + 1} for index, row in enumerate(matching)]
        )
    return result, {row["id"]: mapping[row["id"]] for row in result}


def rule_regime(values: list[dict]) -> str:
    series = {key: [row for row in values if row["series"] == key] for key in ("growth", "inflation")}
    if any(len(rows) < 2 for rows in series.values()):
        return "unknown"
    growth = series["growth"][-1]["value"] - series["growth"][-2]["value"]
    inflation = series["inflation"][-1]["value"] - series["inflation"][-2]["value"]
    if growth == 0 or inflation == 0:
        return "unknown"
    return (
        ("Reflation" if inflation > 0 else "Goldilocks")
        if growth > 0
        else ("Stagflation" if inflation > 0 else "Risk_Off")
    )


def classify(session: AgentSession, values: list[dict], framework: dict, selected: dict) -> dict:
    if any(
        sum(row["series"] == key for row in values) < framework["min_observations"] for key in ("growth", "inflation")
    ):
        return {"regime": "unknown", "status": "insufficient_pit", "confidence": 0.0, "evidence_ids": []}
    prompt_framework = {
        "states": config()["regimes"],
        "definition": framework["definition"],
        "insufficient_evidence": "unknown",
        "dates": "relative_periods_only",
        "allowed_evidence_ids": [row["id"] for row in values],
        "comparison": "compare_each_series_own_latest_two_observations_not_same_period_intersection",
    }
    result = session.run("regime", {"macro": values, "framework": prompt_framework}, framework["objective"], selected)
    names = set(config()["regimes"]) | {"unknown"}
    if (
        result.get("regime") not in names
        or type(result.get("confidence")) not in {float, int}
        or not 0 <= result["confidence"] <= 1
    ):
        raise invalid("体制或置信度不合法")
    references = result.get("evidence_ids")
    if not isinstance(references, list) or set(references) - {row["id"] for row in values}:
        raise invalid("体制判断引用不存在的证据")
    if result["regime"] != "unknown" and {row["series"] for row in values if row["id"] in references} != {
        "growth",
        "inflation",
    }:
        raise invalid("体制判断必须引用增长与通胀的实际资料")
    if any(term.casefold() in str(result.get("rationale", "")).casefold() for term in framework["leak_terms"]):
        raise invalid("体制输出包含未提供的历史事件线索")
    if result["confidence"] < framework["min_confidence"]:
        result["regime"] = "unknown"
    expected = rule_regime(values)
    if result["regime"] != "unknown" and expected != "unknown" and result["regime"] != expected:
        raise invalid("模型体制字段与冻结增长/通胀定义不一致，拒绝配置资金")
    return {**result, "status": "classified"}


def run_regime(store: AlphaStore, study: dict, session: AgentSession, emit) -> dict:
    cfg = study["config"]
    dataset = store.get("alpha_datasets", study["dataset_id"])
    decisions, failures = [], []
    for index, selected in enumerate(cfg["configurations"], 1):
        for cutoff in cfg["decision_dates"]:
            if timestamp(cutoff) > timestamp(utc_now_iso()):
                raise invalid("不能把未来时点标记为已经完成的前向观察")
            values, mapping = anonymous_inputs(dataset["payload"]["observations"], cutoff, cfg["regime"])
            try:
                result = classify(session, values, cfg["regime"], selected)
            except Exception as exc:
                if session.cancelled():
                    raise
                result = {"regime": "unknown", "confidence": 0.0, "status": "failed", "error": str(exc)}
                failures.append({"configuration": index, "cutoff": cutoff, "error": str(exc)})
            allocation = cfg["regime"]["allocations"].get(result["regime"], {})
            weights = {cfg["asset_mapping"][key]: value for key, value in allocation.items()}
            decision = {
                **result,
                "configuration": index,
                "model_id": selected["model_id"],
                "cutoff": cutoff,
                "generated_at": utc_now_iso(),
                "weights": weights,
                "server_only_time_mapping": mapping,
                "rule_regime": rule_regime(values),
                "input_mode": "lagged_anonymous_pit",
                "validation_mode": "historical_replay"
                if timestamp(cutoff) < timestamp(study["created_at"])
                else "prospective_snapshot",
            }
            decisions.append(decision)
            emit(
                "regime_decision", {key: value for key, value in decision.items() if key != "server_only_time_mapping"}
            )
    result = {
        "decisions": decisions,
        "configurations": cfg["configurations"],
        "failures": failures,
        "configured_count": len(cfg["configurations"]),
        "historical_model_memory_risk": True,
        "ensemble_voting": False,
        "automatic_live_trading": False,
        "export_ready": not failures
        and any(row["regime"] != "unknown" for row in decisions)
        and bool(dataset["provenance"].get("verified"))
        and not dataset["payload"]["is_mock"],
    }
    if cfg.get("market_dataset_id"):
        result["comparisons"] = regime_backtests(store, study, decisions, emit, session.cancelled)
    else:
        result["comparison_status"] = "missing_market_dataset"
    return result


def weights_panel(days: list[str], decisions: list[dict], names: list[str], validity_days: int) -> pd.DataFrame:
    output = []
    for day in days:
        eligible = [row for row in decisions if row["cutoff"][:10] <= day]
        current = max(eligible, key=lambda row: row["cutoff"]) if eligible else {}
        valid = current and timestamp(current["cutoff"]) + timedelta(days=validity_days) >= timestamp(
            day + "T00:00:00+00:00"
        )
        weights = current.get("weights", {}) if valid else {}
        output.append({name: weights.get(name, 0.0) for name in names})
    return pd.DataFrame(output, index=days)


def regime_backtests(store: AlphaStore, study: dict, decisions: list[dict], emit, cancelled) -> dict:
    cfg = study["config"]
    snapshot = store.get("alpha_datasets", cfg["market_dataset_id"])["payload"]
    names = list(cfg["asset_mapping"].values())
    if set(names) - set(snapshot["history"]):
        raise invalid("股债基准资产不在行情归档，不能暗中替换代理")
    snapshot = {**snapshot, "history": {name: snapshot["history"][name] for name in names}}
    days = sorted(
        {
            row["date"]
            for rows in snapshot["history"].values()
            for row in rows
            if cfg["decision_dates"][0][:10] <= row["date"] <= cfg["cutoff"][:10]
        }
    )
    if len(days) < cfg["policy"]["min_test_dates"]:
        return {"status": "insufficient_forward_market_dates"}
    definition = plan_definition(study, 1, names)
    definition["nodes"][0].update(
        component="alpha_regime", params={"study_id": study["id"], "configuration": 1, "artifact_digest": ""}
    )
    definition["portfolio"] = {
        "component": "regime_fixed",
        "params": {"top_k": len(names), "max_weight": cfg["policy"]["max_weight"]},
    }
    baseline_weights = {cfg["asset_mapping"][key]: value for key, value in cfg["regime"]["benchmark_weights"].items()}
    baseline_panel = pd.DataFrame([baseline_weights] * len(days), index=days).reindex(columns=names)
    baseline = simulate(study, snapshot, days, definition, baseline_panel, 1, emit, cancelled, targets=True)
    results = {}
    for index, _ in enumerate(cfg["configurations"], 1):
        selected = [row for row in decisions if row["configuration"] == index]
        values = weights_panel(days, selected, names, cfg["regime"]["validity_days"])
        actual = simulate(study, snapshot, days, definition, values, 1, emit, cancelled, targets=True)
        results[str(index)] = paired_results(actual, baseline, cfg["policy"])
    rules = [
        {
            **row,
            "weights": {
                cfg["asset_mapping"][key]: value
                for key, value in cfg["regime"]["allocations"].get(row["rule_regime"], {}).items()
            },
        }
        for row in decisions
        if row["configuration"] == 1
    ]
    rule_values = weights_panel(days, rules, names, cfg["regime"]["validity_days"])
    rule_actual = simulate(study, snapshot, days, definition, rule_values, 1, emit, cancelled, targets=True)
    return {
        "status": "historical_replay_not_claimed_unseen_model_oos",
        "configurations": results,
        "rule_based": paired_results(rule_actual, baseline, cfg["policy"]),
        "baseline_label": "same_tradeable_assets_static_60_40_with_same_costs_and_risk",
    }
