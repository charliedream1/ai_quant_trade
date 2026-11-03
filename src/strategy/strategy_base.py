"""Unified strategy interface."""

from typing import Any


class StrategyBase:
    name = "UnnamedStrategy"
    version = "v1"
    description = ""
    params_schema: list[dict[str, Any]] = []

    def __init__(self, params: dict[str, Any] | None = None) -> None:
        self.params = params or {}

    def on_start(self, context: dict[str, Any]) -> None:
        pass

    def on_bar(self, bar: dict[str, Any]) -> list[dict[str, Any]]:
        return []

    def on_tick(self, tick: dict[str, Any]) -> list[dict[str, Any]]:
        return []

    def on_stop(self, context: dict[str, Any]) -> None:
        pass
