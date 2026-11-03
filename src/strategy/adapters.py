"""Adapters that expose different strategy shapes through the standard port."""

from __future__ import annotations

from collections.abc import Callable
from inspect import Parameter, signature
from typing import Any

from .ports import MarketEvent, StrategyContext, StrategySignal, normalize_signals

BAR_METHODS = ("on_bar", "handle_bar", "generate_signal", "generate_signals")
TICK_METHODS = ("on_tick", "handle_tick")
START_METHODS = ("on_start", "on_init", "initialize", "init")
STOP_METHODS = ("on_stop", "finish", "teardown")
RISK_METHODS = ("on_risk_check", "risk_check")
CONTEXT_PARAM_NAMES = {"context", "ctx", "strategy_context", "state"}


class ObjectStrategyAdapter:
    """Adapter for class-based strategies."""

    def __init__(self, instance: Any, adapter_type: str, entry_name: str) -> None:
        self.instance = instance
        self.adapter_type = adapter_type
        self.entry_name = entry_name
        self.capabilities = _capabilities(instance)
        self.params_schema = getattr(instance, "params_schema", [])

    def on_start(self, context: StrategyContext) -> None:
        callback = _first_callable(self.instance, START_METHODS)
        if callback:
            _call_strategy(callback, None, context)

    def on_bar(self, event: MarketEvent, context: StrategyContext) -> list[StrategySignal]:
        callback = _first_callable(self.instance, BAR_METHODS)
        if not callback:
            return []
        return normalize_signals(_call_strategy(callback, event, context), event.symbol)

    def on_tick(self, event: MarketEvent, context: StrategyContext) -> list[StrategySignal]:
        callback = _first_callable(self.instance, TICK_METHODS)
        if not callback:
            return []
        return normalize_signals(_call_strategy(callback, event, context), event.symbol)

    def on_stop(self, context: StrategyContext) -> None:
        callback = _first_callable(self.instance, STOP_METHODS)
        if callback:
            _call_strategy(callback, None, context)


class FunctionStrategyAdapter:
    """Adapter for function-based strategies."""

    def __init__(
        self, callback: Callable[..., Any], adapter_type: str, entry_name: str, capability: str = "bar"
    ) -> None:
        self.callback = callback
        self.adapter_type = adapter_type
        self.entry_name = entry_name
        self.capabilities = [capability]
        self.params_schema: list[dict[str, Any]] = []

    def on_start(self, context: StrategyContext) -> None:
        return None

    def on_bar(self, event: MarketEvent, context: StrategyContext) -> list[StrategySignal]:
        return normalize_signals(_call_strategy(self.callback, event, context), event.symbol)

    def on_tick(self, event: MarketEvent, context: StrategyContext) -> list[StrategySignal]:
        return []

    def on_stop(self, context: StrategyContext) -> None:
        return None


def _first_callable(instance: Any, names: tuple[str, ...]) -> Callable[..., Any] | None:
    for name in names:
        callback = getattr(instance, name, None)
        if callable(callback):
            return callback
    return None


def _capabilities(instance: Any) -> list[str]:
    capabilities: list[str] = []
    for capability, names in (
        ("start", START_METHODS),
        ("bar", BAR_METHODS),
        ("tick", TICK_METHODS),
        ("risk_check", RISK_METHODS),
        ("stop", STOP_METHODS),
    ):
        if _first_callable(instance, names):
            capabilities.append(capability)
    return capabilities


def _call_strategy(callback: Callable[..., Any], event: MarketEvent | None, context: StrategyContext) -> Any:
    params = [
        param
        for param in signature(callback).parameters.values()
        if param.kind in (Parameter.POSITIONAL_ONLY, Parameter.POSITIONAL_OR_KEYWORD)
    ]
    if any(param.kind == Parameter.VAR_POSITIONAL for param in signature(callback).parameters.values()):
        if event is None:
            return callback(context.to_dict())
        return callback(event.to_dict(), context.to_dict())

    if not params:
        return callback()

    if event is None:
        return callback(context.to_dict())

    event_payload = event.to_dict()
    context_payload = context.to_dict()
    if len(params) == 1:
        if params[0].name in CONTEXT_PARAM_NAMES:
            return callback(context_payload)
        return callback(event_payload)

    if params[0].name in CONTEXT_PARAM_NAMES:
        return callback(context_payload, event_payload)
    return callback(event_payload, context_payload)
