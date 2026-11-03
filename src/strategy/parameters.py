"""Resolve strategy parameters once for previews and every backtest entry point."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from src.core.exceptions import BusinessError, ErrorCode
from src.core.repository import Repository, json_loads

from .models.config import model_config
from .parameter_profiles import ParameterProfiles, parameter_mapping
from .strategy_store import StrategyStore


def merge_parameters(base: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge objects; replace lists and scalar values in full."""
    result = deepcopy(base)
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = merge_parameters(result[key], value)
        else:
            result[key] = deepcopy(value)
    return result


def schema_defaults(schema: Any) -> dict[str, Any]:
    if isinstance(schema, list):
        schema = {
            str(item["name"]): item["default"]
            for item in schema
            if isinstance(item, dict) and item.get("name") and "default" in item
        }
    return parameter_mapping(schema, "策略默认参数")


def validate_declared_parameters(params: dict[str, Any], schema: Any) -> None:
    """Reject invalid declared values rather than displaying silently clamped values."""
    if not isinstance(schema, list):
        return
    types = {"int": (int,), "float": (int, float), "bool": (bool,), "str": (str,)}
    for item in schema:
        if not isinstance(item, dict) or item.get("name") not in params:
            continue
        name = str(item["name"])
        value = params[name]
        kind = str(item.get("type") or "")
        expected = types.get(kind)
        if expected and (not isinstance(value, expected) or (kind in {"int", "float"} and isinstance(value, bool))):
            raise BusinessError(ErrorCode.INVALID_PARAM, f"参数 {name} 必须为 {kind} 类型")
        if kind in {"int", "float"}:
            if "min" in item and value < item["min"]:
                raise BusinessError(ErrorCode.INVALID_PARAM, f"参数 {name} 不能小于 {item['min']}")
            if "max" in item and value > item["max"]:
                raise BusinessError(ErrorCode.INVALID_PARAM, f"参数 {name} 不能大于 {item['max']}")


class StrategyParameters:
    def __init__(self, repo: Repository | None = None, profiles: ParameterProfiles | None = None) -> None:
        self.store = StrategyStore(repo=repo)
        self.profiles = profiles or ParameterProfiles()

    def _source(self, strategy_id: int) -> tuple[dict[str, Any], str, dict[str, Any], dict[str, Any]]:
        row = self.store.repo.get("strategies", strategy_id)
        source = self.store.storage.read_text(row["file_path"])
        validation = self.store.validator.validate_source(source)
        entry = str(validation.get("entry_class") or validation.get("entry_func") or "")
        return row, source, validation, self.profiles.family(entry)

    def options(self, strategy_id: int) -> list[dict[str, Any]]:
        _, _, _, family = self._source(strategy_id)
        return self.profiles.options(family)

    def resolve(self, strategy_id: int, overrides: Any = None, profile_id: str | None = None) -> dict[str, Any]:
        row, source, validation, family = self._source(strategy_id)
        selected = self.profiles.select(family, profile_id)
        source_defaults = schema_defaults(validation.get("params_schema"))
        model_profile = family.get("model_profile")
        model_defaults: dict[str, Any] = {}
        if model_profile:
            # Model dependencies remain lazy: this reads YAML without fitting a model.
            model_defaults = model_config(str(model_profile))
        saved_defaults = schema_defaults(json_loads(row.get("param_schema"), {}))
        runtime = parameter_mapping(overrides, "本次参数覆盖")
        layers = [model_defaults, source_defaults, saved_defaults, selected.get("params", {}), runtime]
        resolved: dict[str, Any] = {}
        for layer in layers:
            resolved = merge_parameters(resolved, layer)
        validate_declared_parameters(resolved, validation.get("params_schema"))
        for constraint in family.get("constraints", []):
            greater, smaller = constraint["greater"], constraint["than"]
            if resolved[greater] <= resolved[smaller]:
                raise BusinessError(ErrorCode.INVALID_PARAM, f"参数 {greater} 必须大于 {smaller}")
        if model_profile:
            try:
                resolved = model_config(str(model_profile), resolved)
            except (ValueError, TypeError, KeyError) as exc:
                raise BusinessError(ErrorCode.INVALID_PARAM, f"模型参数不合法：{exc}") from exc
        return {
            "strategy": {key: row.get(key) for key in ("id", "name", "version", "updated_at", "file_path")},
            "source": source,
            "entry": validation.get("entry_class") or validation.get("entry_func"),
            "profile": selected,
            "profile_file": {key: family[key] for key in ("file", "sha256") if key in family},
            "model_profile": model_profile,
            "layers": {
                "model_defaults": model_defaults,
                "source_defaults": source_defaults,
                "saved_defaults": saved_defaults,
                "profile_params": selected.get("params", {}),
                "overrides": runtime,
            },
            "resolved_params": resolved,
        }
