"""Project-local component configuration, independent from model imports."""

from copy import deepcopy
from functools import lru_cache
from typing import Any

import yaml

from src.core.config import PROJECT_ROOT

CONFIG_PATH = PROJECT_ROOT / "egs" / "strategy_components.yaml"
TEMPLATE_ROOT = PROJECT_ROOT / "egs" / "strategy_pipelines"


@lru_cache(maxsize=1)
def _config() -> dict[str, Any]:
    return dict(yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")))


def config() -> dict[str, Any]:
    return deepcopy(_config())


def fail(code: str, detail: Any = "") -> ValueError:
    return ValueError(f"{_config()['messages'].get(code, code)}: {detail}".rstrip(": "))


def merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(base)
    for key, value in override.items():
        result[key] = (
            merge(result[key], value)
            if isinstance(value, dict) and isinstance(result.get(key), dict)
            else deepcopy(value)
        )
    return result


def templates() -> list[dict[str, Any]]:
    return [
        {"id": path.stem, "definition": yaml.safe_load(path.read_text(encoding="utf-8"))}
        for path in sorted(TEMPLATE_ROOT.glob("*.yaml"))
    ]


def template(name: str) -> dict[str, Any]:
    return next((row["definition"] for row in templates() if row["id"] == name), {})
