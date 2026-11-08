"""Frozen, project-local settings and recipe validation."""

import math
from copy import deepcopy
from functools import lru_cache
from hashlib import sha256
from pathlib import Path

import yaml

from src.alpha_mining.config import digest
from src.core.config import PROJECT_ROOT

COMPONENTS = {"cn_analysis", "cn_debate", "contest_data", "contest_research"}


@lru_cache(maxsize=1)
def _settings() -> dict:
    return yaml.safe_load((PROJECT_ROOT / "egs/config/agents/agent_strategies.yaml").read_text(encoding="utf-8"))


def settings() -> dict:
    return deepcopy(_settings())


def freeze(recipe: str, options: dict | None = None) -> dict:
    cfg = settings()
    if recipe not in cfg["recipes"]:
        raise ValueError("未知Agent策略方案")
    value = {**cfg["defaults"], **(options or {})}
    if set(value) - set(cfg["defaults"]):
        raise ValueError("未知研究配置")
    if value["depth"] not in cfg["depths"] or value["predictor"] not in {"baseline", "lightgbm"}:
        raise ValueError("未知深度或效用预测器")
    for key in (
        "calls",
        "horizon",
        "min_history",
        "score_window",
        "prediction_horizon",
        "min_training",
        "output_tokens",
    ):
        if type(value[key]) is not int or value[key] < 1:
            raise ValueError("研究预算或窗口不合法：" + key)
    if value["calls"] > cfg["limits"]["max_calls"]:
        raise ValueError("模型调用预算超限")
    if (
        not value["min_history"] <= value["score_window"] <= cfg["limits"]["max_score_window"]
        or value["prediction_horizon"] < 2
    ):
        raise ValueError("成熟成绩窗口不合法")
    for key in ("shrinkage", "ewma_alpha", "max_actor_budget", "similarity_limit"):
        number = value[key]
        if (
            isinstance(number, bool)
            or not isinstance(number, (int, float))
            or not math.isfinite(number)
            or not 0 <= number <= 1
        ):
            raise ValueError("研究比例参数不合法：" + key)
    if value["volatility_floor"] <= 0 or not 0 < value["ewma_alpha"] <= 1 or not 0 < value["max_actor_budget"] <= 1:
        raise ValueError("效用或预算参数不合法")
    if (
        type(value["enable_thinking"]) is not bool
        or not isinstance(value["model_params"], dict)
        or set(value["model_params"]) != set(cfg["defaults"]["model_params"])
    ):
        raise ValueError("模型配置字段不合法")
    if (
        not 1 <= value["model_params"]["n_estimators"] <= cfg["limits"]["max_trees"]
        or value["model_params"]["n_jobs"] != 1
    ):
        raise ValueError("效用模型训练资源超限")
    if not value["feature_windows"] or any(
        type(window) is not int or window < 1 or window > value["min_history"] for window in value["feature_windows"]
    ):
        raise ValueError("效用特征窗口不合法")
    prompts = yaml.safe_load((PROJECT_ROOT / "egs/config/agents/agent_strategy_prompts.yaml").read_text(encoding="utf-8"))
    if not isinstance(value["role_models"], dict):
        raise ValueError("角色模型配置必须为对象")
    for role, selection in value["role_models"].items():
        if (
            role not in prompts["roles"]
            or not isinstance(selection, dict)
            or set(selection) - {"model_id", "backend", "model_name", "reasoning_effort"}
        ):
            raise ValueError("角色或模型配置字段不合法")
        if "model_id" in selection and (type(selection["model_id"]) is not int or selection["model_id"] < 1):
            raise ValueError("角色模型ID必须为正整数")
        if selection.get("backend", "api") not in {"api", "codex", "qoder", "trae", "codebuddy"} or selection.get(
            "reasoning_effort", ""
        ) not in {
            "",
            "low",
            "medium",
            "high",
            "xhigh",
        }:
            raise ValueError("角色后端或推理强度不支持")
    result = {
        "recipe": recipe,
        "definition": cfg["recipes"][recipe],
        "policy": value,
        "depth": cfg["depths"][value["depth"]],
        "limits": cfg["limits"],
        "prompts": prompts,
    }
    if "fundamental" in result["definition"]["required"]:
        if "fundamental" not in result["depth"]["analysts"]:
            result["depth"]["analysts"].append("fundamental")
        if "fundamentals" not in result["depth"]["data_roles"]:
            result["depth"]["data_roles"].append("fundamentals")
    if "sector" in result["definition"]["required"] and "sector" not in result["depth"]["beliefs"]:
        result["depth"]["beliefs"].append("sector")
    files = [*Path(__file__).parent.glob("*.py"), PROJECT_ROOT / "egs/config/strategies/execution_costs.yaml"]
    files += [
        path
        for name in ("engine/composition", "engine/execution", "portfolio", "risk", "agent/providers")
        for path in (PROJECT_ROOT / "src" / name).glob("*.py")
    ]
    files.append(PROJECT_ROOT / "egs/config/agents/agent_providers.yaml")
    result["source_manifest"] = {
        path.relative_to(PROJECT_ROOT).as_posix(): sha256(path.read_bytes()).hexdigest() for path in sorted(files)
    }
    result["version"] = digest(result)
    return result
