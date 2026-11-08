"""Versioned research policies and bounded project-contained artifacts."""

import hashlib
import json
from copy import deepcopy
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from src.core.config import PROJECT_ROOT
from src.core.exceptions import BusinessError, ErrorCode


def invalid(reason: str) -> BusinessError:
    return BusinessError(ErrorCode.INVALID_PARAM, reason)


@lru_cache(maxsize=1)
def config() -> dict[str, Any]:
    return yaml.safe_load((PROJECT_ROOT / "egs/config/agents/alpha_mining.yaml").read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def prompts() -> dict[str, Any]:
    return yaml.safe_load((PROJECT_ROOT / "egs/config/agents/alpha_mining_prompts.yaml").read_text(encoding="utf-8"))


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def policy(overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    result = deepcopy(config()["policy"])
    supplied = overrides or {}
    if set(supplied) - set(result):
        raise invalid("研究政策包含未登记字段")
    for key, value in supplied.items():
        default = result[key]
        if isinstance(default, bool):
            valid = isinstance(value, bool)
        elif isinstance(default, int):
            valid = isinstance(value, int) and not isinstance(value, bool) and value >= 0
        elif isinstance(default, float):
            valid = isinstance(value, (float, int)) and not isinstance(value, bool) and 0 <= value <= 1
        else:
            valid = isinstance(value, str) and bool(value.strip())
        if not valid:
            raise invalid("研究政策参数类型或范围不合法：" + key)
        result[key] = value
    if (
        result["train_fraction"] + result["validation_fraction"] >= 1
        or result["train_fraction"] <= 0
        or result["validation_fraction"] <= 0
        or result["horizon"] < 1
        or result["block_sessions"] < result["horizon"]
        or result["embargo_sessions"] < result["horizon"]
        or result["bootstrap_samples"] < 99
        or result["bootstrap_samples"] > config()["limits"]["max_bootstrap_samples"]
        or result["min_train_dates"] < 2
        or result["min_test_dates"] < 2
        or result["min_assets"] < 3
        or result["top_k"] < 1
        or result["max_weight"] <= 0
        or result["significance"] <= 0
    ):
        raise invalid("研究切分、样本或统计预算不合法")
    return result


def contained(path: Path) -> Path:
    resolved = path.resolve()
    if not resolved.is_relative_to(PROJECT_ROOT.resolve()):
        raise invalid("Alpha研究文件必须位于项目目录")
    return resolved


def source_manifest() -> dict[str, str]:
    roots = [
        PROJECT_ROOT / "src" / name
        for name in (
            "alpha_mining",
            "engine/composition",
            "engine/execution",
            "portfolio",
            "risk",
            "strategy/composition",
            "strategy/factors",
            "agent/providers",
        )
    ]
    files = [path for root in roots for path in root.glob("*.py")]
    files.extend(
        [
            PROJECT_ROOT / "egs/config/strategies/execution_costs.yaml",
            PROJECT_ROOT / "egs/config/agents/alpha_mining.yaml",
            PROJECT_ROOT / "egs/config/agents/alpha_mining_prompts.yaml",
            PROJECT_ROOT / "src/agent/llm_client.py",
            PROJECT_ROOT / "egs/config/strategies/factor_research.yaml",
            PROJECT_ROOT / "egs/config/agents/agent_providers.yaml",
        ]
    )
    return {
        path.relative_to(PROJECT_ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(files)
    }
