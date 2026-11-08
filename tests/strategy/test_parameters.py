"""Parameter precedence and validation, independent of model fitting."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.core.exceptions import BusinessError
from src.strategy import StrategyStore
from src.strategy.parameter_profiles import ParameterProfiles, parameter_mapping
from src.strategy.parameters import StrategyParameters, merge_parameters


def test_nested_overrides_preserve_siblings_and_explicit_zero_false():
    base = {"model_params": {"depth": 4, "seed": 7}, "windows": [1, 5], "enabled": True, "cost": 0.1}
    combined = merge_parameters(base, {"model_params": {"depth": 3}, "windows": [2], "enabled": False, "cost": 0})
    assert combined == {"model_params": {"depth": 3, "seed": 7}, "windows": [2], "enabled": False, "cost": 0}
    assert base["model_params"]["depth"] == 4


@pytest.mark.parametrize("value", [[], "{}", {"a": float("nan")}, {"_experiment": {}}, {"_backtest": {}}])
def test_invalid_parameters_fail_before_execution(value):
    with pytest.raises(BusinessError):
        parameter_mapping(value, "参数")


def test_saved_schema_list_and_empty_override_inherit_defaults(client):
    store = StrategyStore()
    item = store.import_example("egs/examples/strategy_examples/dual_ma_strategy.py", {"name": "params_list"})
    store.repo.update("strategies", item["id"], {"param_schema": [{"name": "fast_window", "default": 9}]})
    resolver = StrategyParameters()
    assert resolver.resolve(item["id"], {})["resolved_params"] == {"fast_window": 9, "slow_window": 20}
    assert resolver.resolve(item["id"], None)["resolved_params"] == {"fast_window": 9, "slow_window": 20}
    selected = resolver.resolve(item["id"], {"slow_window": 45}, "dual_ma.yaml:slow")
    assert selected["resolved_params"] == {"fast_window": 10, "slow_window": 45}
    assert selected["layers"]["saved_defaults"] == {"fast_window": 9}


def test_model_layers_and_nested_profile_overrides_need_no_training(client):
    store = StrategyStore()
    item = store.import_example(
        "egs/examples/strategy_examples/lightgbm_rank_strategy.py",
        {"name": "model_params", "default_params": {"top_n": 2, "model_params": {"reg_lambda": 3.0}}},
    )
    resolution = StrategyParameters().resolve(
        item["id"], {"model_params": {"n_estimators": 12}}, "lightgbm_rank.yaml:slower_fit"
    )
    params = resolution["resolved_params"]
    assert params["top_n"] == 2
    assert params["retrain_interval"] == 20
    assert params["model_params"]["n_estimators"] == 12
    assert params["model_params"]["learning_rate"] == 0.03
    assert params["model_params"]["reg_lambda"] == 3.0
    assert params["model_params"]["random_state"] == 7
    assert resolution["profile_file"]["sha256"]


@pytest.mark.parametrize("profile", ["../config.yaml:x", "rsi.yaml:strict", "dual_ma.yaml:missing"])
def test_profiles_cannot_cross_strategy_or_escape_directory(client, profile):
    item = StrategyStore().import_example("egs/examples/strategy_examples/dual_ma_strategy.py", {"name": "profile_guard"})
    with pytest.raises(BusinessError, match="不属于当前策略"):
        StrategyParameters().resolve(item["id"], {}, profile)


def test_all_bundled_strategies_have_two_compatible_yaml_schemes(client):
    store = StrategyStore()
    resolver = StrategyParameters()
    paths = sorted(Path("egs/examples/strategy_examples").glob("*_strategy.py"))
    assert len(paths) == 13
    for path in paths:
        item = store.import_example(path.as_posix(), {"name": f"schemes_{path.stem}"})
        options = resolver.options(item["id"])
        assert len(options) == 2, path
        for option in options:
            assert resolver.resolve(item["id"], {}, option["id"])["resolved_params"], path


def test_custom_strategy_without_scheme_uses_its_declared_defaults(client, tmp_path):
    store = StrategyStore()
    item = store.import_example("egs/examples/strategy_examples/dual_ma_strategy.py", {"name": "custom_defaults"})
    resolver = StrategyParameters(profiles=ParameterProfiles(tmp_path))
    assert resolver.options(item["id"]) == []
    assert resolver.resolve(item["id"])["resolved_params"]["slow_window"] == 20


@pytest.mark.parametrize(
    "params", [{"fast_window": 1}, {"fast_window": "5"}, {"fast_window": True}, {"fast_window": 30, "slow_window": 20}]
)
def test_invalid_declared_values_are_rejected_in_preview(client, params):
    item = StrategyStore().import_example("egs/examples/strategy_examples/dual_ma_strategy.py", {"name": "typed_params"})
    with pytest.raises(BusinessError):
        StrategyParameters().resolve(item["id"], params)
