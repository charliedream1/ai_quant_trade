"""YAML configuration for the bundled model strategies."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml

from src.strategy.factors.config import factor_set

CONFIG_PATH = Path(__file__).resolve().parents[3] / "egs" / "model_strategies.yaml"
BACKEND_MODULES = {
    "lightgbm": "src.strategy.models.lightgbm_backend",
    "xgboost": "src.strategy.models.xgboost_backend",
    "mlp": "src.strategy.models.neural_backend",
}


def model_config(profile: str, overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    if profile not in payload["profiles"]:
        raise ValueError(f"未知模型策略配置：{profile}")
    config = deepcopy(payload["defaults"])
    config.update(deepcopy(payload["profiles"][profile]))
    for key, value in (overrides or {}).items():
        if key not in config:
            raise ValueError(f"模型策略不支持参数：{key}")
        if key == "model_params":
            if not isinstance(value, dict):
                raise ValueError("model_params 必须为对象")
            config[key].update(value)
        else:
            config[key] = value
    if config["backend"] not in BACKEND_MODULES:
        raise ValueError("模型后端未注册")
    if not isinstance(config["feature_set"], str) or not isinstance(config["feature_preprocess"], str):
        raise ValueError("特征集及预处理必须为字符串")
    if config["feature_set"]:
        factor_set(config["feature_set"])
    if config["feature_preprocess"] not in {"rank", "zscore"}:
        raise ValueError("特征预处理仅支持rank或zscore")
    positive = (
        "short_window",
        "long_window",
        "volatility_window",
        "volume_window",
        "horizon",
        "train_window",
        "min_train_dates",
        "min_train_samples",
        "retrain_interval",
        "history_limit",
        "top_n",
        "quantity",
    )
    if any(int(config[key]) <= 0 for key in positive):
        raise ValueError("窗口、训练规模、持仓数量和交易数量必须为正整数")
    if not config["lag_windows"] or any(int(value) <= 0 for value in config["lag_windows"]):
        raise ValueError("lag_windows 必须包含正整数")
    if not 0 < float(config["validation_fraction"]) < 0.5:
        raise ValueError("验证集比例必须在 0 与 0.5 之间")
    if int(config["history_limit"]) <= int(config["long_window"]) + int(config["min_train_dates"]):
        raise ValueError("history_limit 不足以覆盖预热和最小训练窗口")
    return config
