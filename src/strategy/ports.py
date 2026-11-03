"""Standard strategy port data contracts."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol

DEFAULT_SIGNAL_TYPE = "order"
DEFAULT_SIGNAL_QUANTITY = 0.0
SIDE_ALIASES = {
    "buy": "buy",
    "long": "buy",
    "open_long": "buy",
    "sell": "sell",
    "short": "sell",
    "close_long": "sell",
    "hold": "hold",
}


@dataclass(slots=True)
class StrategyContext:
    """Execution context injected by backtest, paper and live engines."""

    params: dict[str, Any] = field(default_factory=dict)
    symbols: list[str] = field(default_factory=list)
    mode: str = "backtest"
    account: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "params": self.params,
            "symbols": self.symbols,
            "mode": self.mode,
            "account": self.account,
            "metadata": self.metadata,
        }


@dataclass(slots=True)
class MarketEvent:
    """Normalized market event delivered to strategies."""

    symbol: str
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0
    raw: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = {
            "symbol": self.symbol,
            "timestamp": self.timestamp,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
        }
        data.update(self.raw)
        return data

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> MarketEvent:
        symbol = str(value.get("symbol") or value.get("code") or "000001")
        return cls(
            symbol=symbol,
            timestamp=str(value.get("timestamp") or value.get("datetime") or value.get("date") or ""),
            open=float(value.get("open") or value.get("open_price") or value.get("close") or 0.0),
            high=float(value.get("high") or value.get("close") or 0.0),
            low=float(value.get("low") or value.get("close") or 0.0),
            close=float(value.get("close") or value.get("price") or 0.0),
            volume=float(value.get("volume") or 0.0),
            raw=dict(value),
        )


@dataclass(slots=True)
class StrategySignal:
    """Normalized strategy signal consumed by execution engines."""

    symbol: str
    side: str
    quantity: float = DEFAULT_SIGNAL_QUANTITY
    signal_type: str = DEFAULT_SIGNAL_TYPE
    price: float | None = None
    reason: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "side": self.side,
            "quantity": self.quantity,
            "signal_type": self.signal_type,
            "price": self.price,
            "reason": self.reason,
            "metadata": self.metadata,
        }

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any], fallback_symbol: str = "") -> StrategySignal:
        side_text = str(value.get("side") or value.get("direction") or value.get("action") or "hold").lower()
        quantity = value.get("quantity", value.get("qty", value.get("volume", DEFAULT_SIGNAL_QUANTITY)))
        quantity_value = DEFAULT_SIGNAL_QUANTITY if quantity is None else quantity
        price_value = value.get("price")
        return cls(
            symbol=str(value.get("symbol") or value.get("code") or fallback_symbol),
            side=SIDE_ALIASES.get(side_text, side_text),
            quantity=float(quantity_value),
            signal_type=str(value.get("signal_type") or value.get("type") or DEFAULT_SIGNAL_TYPE),
            price=_optional_float(price_value),
            reason=str(value.get("reason") or value.get("signal") or ""),
            metadata={key: item for key, item in dict(value).items() if key not in _SIGNAL_CORE_KEYS},
        )


class StrategyPort(Protocol):
    """Runtime interface implemented by all strategy adapters."""

    adapter_type: str
    entry_name: str
    capabilities: list[str]
    params_schema: Any

    def on_start(self, context: StrategyContext) -> None: ...

    def on_bar(self, event: MarketEvent, context: StrategyContext) -> list[StrategySignal]: ...

    def on_tick(self, event: MarketEvent, context: StrategyContext) -> list[StrategySignal]: ...

    def on_stop(self, context: StrategyContext) -> None: ...


_SIGNAL_CORE_KEYS = {
    "symbol",
    "code",
    "side",
    "direction",
    "action",
    "quantity",
    "qty",
    "volume",
    "signal_type",
    "type",
    "price",
    "reason",
    "signal",
}


def normalize_signals(value: Any, fallback_symbol: str = "") -> list[StrategySignal]:
    """Normalize common strategy return shapes to platform signals."""
    if value is None:
        return []
    if isinstance(value, StrategySignal):
        return [value]
    if isinstance(value, Mapping):
        return [StrategySignal.from_mapping(value, fallback_symbol)]
    if isinstance(value, Sequence) and not isinstance(value, str | bytes):
        signals: list[StrategySignal] = []
        for item in value:
            signals.extend(normalize_signals(item, fallback_symbol))
        return signals
    return []


def _optional_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    return float(value)
