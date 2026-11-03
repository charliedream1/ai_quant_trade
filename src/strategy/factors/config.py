"""Allowlisted factor definitions stored separately from their implementation."""

from copy import deepcopy
from functools import lru_cache
from typing import Any

import yaml

from src.core.config import PROJECT_ROOT


@lru_cache(maxsize=1)
def _configuration() -> dict[str, Any]:
    return yaml.safe_load((PROJECT_ROOT / "egs/factor_research.yaml").read_text(encoding="utf-8"))


def factor_config() -> dict[str, Any]:
    return deepcopy(_configuration())


def factor_error(code: str, detail: Any = "") -> ValueError:
    return ValueError(f"{_configuration()['messages'].get(code, code)}: {detail}".rstrip(": "))


def factor_set(name: str) -> dict[str, dict[str, Any]]:
    cfg = _configuration()
    if name not in cfg["sets"]:
        raise factor_error("invalid", name)
    names = cfg["sets"][name]["factors"]
    if not names or len(names) != len(set(names)) or len(names) > cfg["limits"]["max_factors"]:
        raise factor_error("invalid", name)
    definitions = {key: deepcopy(cfg["factors"][key]) for key in names}
    for key, row in definitions.items():
        if (
            row["operator"]
            not in {"momentum", "volatility", "volume_ratio", "mean_distance", "range_position", "amount", "intraday"}
            or not isinstance(row["window"], int)
            or not 0 < row["window"] <= cfg["limits"]["max_window"]
            or row["direction"] not in {-1, 1}
            or row["operator"] == "volume_ratio"
            and not 0 < row["short"] <= row["window"]
        ):
            raise factor_error("invalid", key)
    return definitions
