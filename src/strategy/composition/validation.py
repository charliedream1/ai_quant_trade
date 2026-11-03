"""No-execution compilation of bounded, typed acyclic strategy plans."""

import hashlib
import json
import math
import re
from copy import deepcopy
from typing import Any

from src.agent_strategies.config import freeze as agent_strategy_config
from src.agent_strategies.ports import COMPONENTS as AGENT_STRATEGY_COMPONENTS
from src.strategy.factors.config import factor_config, factor_set
from src.strategy.factors.validation import validate_connections, validate_parameters
from src.strategy.models.config import model_config

from .config import config, fail, merge, template

IDENTIFIER = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,63}$")
PLAN_KEYS = {
    "name",
    "description",
    "schema_version",
    "universe",
    "nodes",
    "output",
    "portfolio",
    "risk",
    "execution",
    "rebalance_sessions",
    "sleeves",
    "variants",
    "budget_fallback",
}


def digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode("utf-8")
    ).hexdigest()


def _finite(value: Any) -> None:
    if isinstance(value, dict):
        for child in value.values():
            _finite(child)
    elif isinstance(value, list):
        for child in value:
            _finite(child)
    elif isinstance(value, float) and not math.isfinite(value):
        raise fail("invalid", "NaN/Inf")


def settings(kind: str, override: dict[str, Any] | None) -> dict[str, Any]:
    defaults = config()["defaults"][kind]
    value = override or {}
    if not isinstance(value, dict) or set(value) - set(defaults):
        raise fail("invalid", kind)
    result = merge(defaults, value)
    for key, item in result.items():
        expected = defaults[key]
        if isinstance(expected, bool):
            valid = isinstance(item, bool)
        elif isinstance(expected, (float, int)):
            valid = not isinstance(item, bool) and isinstance(item, (float, int)) and math.isfinite(item) and item >= 0
            if isinstance(expected, int):
                valid = valid and isinstance(item, int)
        else:
            valid = isinstance(item, type(expected))
        if not valid:
            raise fail("invalid", f"{kind}.{key}")
    if kind == "risk":
        if not 0 <= result["max_exposure"] <= 1 or not 0 <= result["max_weight"] <= 1 or result["max_positions"] < 0:
            raise fail("invalid", kind)
        if any(
            not 0 <= result[key] <= 1
            for key in (
                "stop_loss",
                "trailing_stop",
                "max_drawdown",
                "daily_loss",
                "max_sector_weight",
                "max_cluster_weight",
                "max_asset_class_weight",
            )
        ):
            raise fail("invalid", kind)
        steps = result["drawdown_steps"]
        if any(
            not isinstance(row, list) or len(row) != 2 or not 0 <= row[0] <= 1 or not 0 <= row[1] <= 1 for row in steps
        ):
            raise fail("invalid", "drawdown_steps")
    if kind == "portfolio":
        if (
            not 0 < result["exposure"] <= 1
            or not 0 < result["max_weight"] <= 1
            or result["top_k"] < 1
            or result["window"] < result["min_observations"]
            or result["min_observations"] < 2
        ):
            raise fail("invalid", kind)
        if result["fallback"] not in {"none", "equal", "inverse_volatility"} or not 0 <= result["shrinkage"] <= 1:
            raise fail("invalid", kind)
    if kind == "execution":
        if (
            result["initial_capital"] <= 0
            or result["lot_size"] < 1
            or any(
                not 0 <= result[key] <= 1
                for key in (
                    "commission_rate",
                    "slippage_rate",
                    "max_participation",
                    "turnover_limit",
                    "rebalance_band",
                    "max_gap",
                )
            )
        ):
            raise fail("invalid", kind)
    return result


def _node(node: dict[str, Any], known: dict[str, str]) -> dict[str, Any]:
    cfg = config()
    if set(node) - {"id", "component", "inputs", "params", "family"}:
        raise fail("invalid", "node fields")
    key, component = node.get("id"), node.get("component")
    if (
        not isinstance(key, str)
        or not IDENTIFIER.fullmatch(key)
        or key in known
        or not isinstance(component, str)
        or component not in cfg["components"]
    ):
        raise fail("invalid", key)
    entry = cfg["components"][component]
    parents = node.get("inputs") or ["universe"]
    if (
        not isinstance(parents, list)
        or not parents
        or any(not isinstance(parent, str) for parent in parents)
        or len(parents) != len(set(parents))
        or any(parent not in known for parent in parents)
    ):
        raise fail("invalid", key)
    if entry["kind"] != "ensemble" and len(parents) != 1:
        raise fail("invalid", key)
    if entry["kind"] == "ensemble" and component != "merge" and any(known[parent] == "agent" for parent in parents):
        raise fail("invalid", key)
    override = node.get("params") or {}
    if not isinstance(override, dict):
        raise fail("invalid", key)
    if component in cfg["defaults"]["model_profiles"]:
        base = model_config(cfg["defaults"]["model_profiles"][component])
        if not isinstance(override.get("model_params", {}), dict) or set(override.get("model_params", {})) - set(
            base["model_params"]
        ):
            raise fail("invalid", "unregistered model parameters")
        params = model_config(cfg["defaults"]["model_profiles"][component], override)
        if params["backend"] != component:
            raise fail("invalid", "model backend cannot change component identity")
        limits = cfg["defaults"]["model_limits"]
        model = params["model_params"]
        if any(not isinstance(value, (int, float, bool, list, str)) for value in model.values()):
            raise fail("invalid", "model parameter type")
        if (
            int(model.get("n_estimators", 1)) > limits["max_trees"]
            or int(model.get("epochs", 1)) > limits["max_epochs"]
            or int(model.get("n_jobs", model.get("threads", 1))) not in range(1, limits["max_threads"] + 1)
        ):
            raise fail("invalid", "model resource budget")
        if "hidden_sizes" in model and (
            not isinstance(model["hidden_sizes"], list)
            or len(model["hidden_sizes"]) > limits["max_hidden_layers"]
            or any(
                not isinstance(width, int) or width < 1 or width > limits["max_hidden_width"]
                for width in model["hidden_sizes"]
            )
        ):
            raise fail("invalid", "network budget")
        if "seeds" in model and (
            not isinstance(model["seeds"], list)
            or not model["seeds"]
            or len(model["seeds"]) > limits["max_members"]
            or any(not isinstance(seed, int) for seed in model["seeds"])
        ):
            raise fail("invalid", "ensemble budget")
    else:
        if set(override) - set(entry["defaults"]):
            raise fail("invalid", key)
        params = merge(entry["defaults"], override)
        for parameter, default in entry["defaults"].items():
            value = params[parameter]
            if isinstance(default, bool):
                valid = isinstance(value, bool)
            elif isinstance(default, (float, int)):
                valid = (
                    isinstance(value, (int, float))
                    and not isinstance(value, bool)
                    and math.isfinite(value)
                    and value >= 0
                )
                if isinstance(default, int):
                    valid = valid and isinstance(value, int) and (value > 0 or parameter == "min_amount")
            else:
                valid = isinstance(value, type(default))
            if not valid:
                raise fail("invalid", f"{key}.{parameter}")
    if "long" in params and params.get("short", 0) >= params["long"]:
        raise fail("invalid", key)
    if component == "macd" and params["fast"] >= params["slow"]:
        raise fail("invalid", key)
    if component in {"rank", "vote"}:
        weights = params.get("weights") or []
        if weights and (
            len(weights) != len(parents)
            or any(not isinstance(w, (int, float)) or w < 0 for w in weights)
            or sum(weights) <= 0
        ):
            raise fail("invalid", key)
        if params["minimum"] > len(parents):
            raise fail("invalid", key)
        params["weights"] = [float(weight) for weight in weights]
    if component == "merge" and params["method"] not in {"union", "intersection", "k_n"}:
        raise fail("invalid", key)
    if component == "merge" and params["minimum"] > len(parents):
        raise fail("invalid", key)
    if (
        component == "regime"
        and params["mode"] not in {"trend", "range"}
        or component == "bollinger"
        and params["mode"] not in {"breakout", "reversion"}
    ):
        raise fail("invalid", key)
    if component == "agent" and params["workflow"] not in cfg["prompts"]["roles"]:
        raise fail("invalid", key)
    if component in AGENT_STRATEGY_COMPONENTS:
        recipe = agent_strategy_config(
            params["recipe"], {name: params[name] for name in ("depth", "predictor", "calls")}
        )
        expected_kind = "contest" if component.startswith("contest") else "debate"
        if recipe["definition"]["kind"] != expected_kind or (
            params["documents_dataset"] and not params["documents_dataset"].isdigit()
        ):
            raise fail("invalid", "Agent方案类型或资料ID不合法")
    if component == "low_volatility" and not 0 <= params["percentile"] <= 1:
        raise fail("invalid", key)
    validate_parameters(component, params)
    known[key] = entry["kind"]
    factor_name = params.get("set_name") if component == "factor_set" else params.get("feature_set")
    contract = (
        {"factor_contract": {"definitions": factor_set(factor_name), "preprocess": factor_config()["preprocess"]}}
        if factor_name
        else {}
    )
    return {
        **contract,
        "id": key,
        "component": component,
        "kind": entry["kind"],
        "inputs": parents,
        "params": params,
        "family": node.get("family") or entry.get("family") or ("model" if entry["kind"] == "scorer" else "price"),
    }


def compile_plan(
    definition: dict[str, Any],
    overrides: dict[str, Any] | None = None,
    variant: str = "baseline",
    parents: tuple[str, ...] = (),
) -> dict[str, Any]:
    cfg = config()
    if (
        not isinstance(definition, dict)
        or not isinstance(overrides or {}, dict)
        or len(parents) > cfg["defaults"]["max_depth"]
    ):
        raise fail("invalid")
    variants = definition.get("variants") or {"baseline": {}}
    if variant not in variants:
        raise fail("invalid", variant)
    value = merge(merge(definition, variants[variant]), overrides or {})
    if set(value) - PLAN_KEYS or not str(value.get("name") or "").strip():
        raise fail("invalid", "plan fields/name")
    value.pop("variants", None)
    nodes = value.get("nodes") or []
    if not isinstance(nodes, list) or len(nodes) > cfg["defaults"]["max_nodes"]:
        raise fail("invalid", "nodes")
    known = {"universe": "filter"}
    pending = deepcopy(nodes)
    compiled = []
    while pending:
        ready = [
            node
            for node in pending
            if isinstance(node, dict) and all(parent in known for parent in node.get("inputs", ["universe"]))
        ]
        if not ready:
            raise fail("invalid", "cycle/missing dependency")
        for node in ready:
            compiled.append(_node(node, known))
            pending.remove(node)
    output = value.get("output") or "universe"
    if output not in known:
        raise fail("invalid", "output")
    validate_connections(compiled, output)
    used = {output}
    for node in reversed(compiled):
        if node["id"] in used:
            used.update(node["inputs"])
    if any(node["id"] not in used for node in compiled):
        raise fail("invalid", "unreachable node")
    if any(node["kind"] == "agent" and node["id"] != output for node in compiled):
        raise fail("invalid", "agent must be terminal")
    portfolio = value.get("portfolio") or {"component": "equal"}
    component = portfolio.get("component")
    if component not in cfg["portfolios"] or set(portfolio) - {"component", "params"}:
        raise fail("invalid", "portfolio")
    output_component = next((node["component"] for node in compiled if node["id"] == output), "")
    lookup = {node["id"]: node for node in compiled}
    for node in compiled:
        predecessor = {"cn_debate": "cn_analysis", "contest_research": "contest_data"}.get(node["component"])
        if predecessor and lookup.get(node["inputs"][0], {}).get("component") != predecessor:
            raise fail("invalid", "研究终阶段必须连接对应证据阶段")
        if node["component"] == "contest_research" and node["id"] != output:
            raise fail("invalid", "资金预算不能混入评分投票；并行组合请使用子策略预算")
    if (component == "agent_budget") != (output_component == "contest_research"):
        raise fail("invalid", "研究预算端口必须配套agent_budget")
    if (component == "regime_fixed") != (output_component == "alpha_regime"):
        raise fail("invalid", "frozen regime weights require a terminal alpha_regime and regime_fixed portfolio")
    if any(node["component"] == "alpha_regime" and node["id"] != output for node in compiled):
        raise fail("invalid", "regime allocations cannot be mixed into score voting")
    sleeves: list[dict[str, Any]] = []
    for sleeve in value.get("sleeves") or []:
        key = sleeve.get("id", "")
        if (
            not IDENTIFIER.fullmatch(key)
            or key in {item["id"] for item in sleeves}
            or not 0 < sleeve.get("budget", 0) <= 1
        ):
            raise fail("invalid", "sleeve")
        source = sleeve.get("template")
        if source in parents:
            raise fail("invalid", "sleeve cycle")
        child = sleeve.get("definition") or template(source)
        child_plan = compile_plan(
            child, sleeve.get("overrides"), sleeve.get("variant", "baseline"), (*parents, str(source))
        )
        sleeves.append({"id": key, "budget": sleeve["budget"], "definition": child_plan})
    if (
        bool(sleeves) != (component in {"fixed_budget", "strategy_risk_budget"})
        or sum(item["budget"] for item in sleeves) > 1
    ):
        raise fail("invalid", "budgets")
    if sleeves and nodes:
        raise fail("invalid", "sleeves/nodes")
    universe = value.get("universe") or {"symbols": []}
    symbols = universe.get("symbols") or []
    if (
        not isinstance(symbols, list)
        or len(symbols) > cfg["defaults"]["max_symbols"]
        or any(not isinstance(s, str) or not re.fullmatch(r"[A-Za-z0-9._-]{1,20}", s) for s in symbols)
    ):
        raise fail("invalid", "universe")
    plan = {
        **value,
        "nodes": compiled,
        "output": output,
        "sleeves": sleeves,
        "universe": {**universe, "symbols": sorted(set(symbols))},
        "portfolio": {"component": component, "params": settings("portfolio", portfolio.get("params"))},
        "risk": settings("risk", value.get("risk")),
        "execution": settings("execution", value.get("execution")),
    }
    if not isinstance(plan.get("rebalance_sessions", 1), int) or plan.get("rebalance_sessions", 1) < 1:
        raise fail("invalid", "rebalance_sessions")
    _finite(plan)
    return plan
