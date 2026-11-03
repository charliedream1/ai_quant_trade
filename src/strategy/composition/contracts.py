"""Immutable point-in-time inputs and explicit per-security observations."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any

from .config import fail


@dataclass(frozen=True)
class Observation:
    symbol: str
    value: float | None
    status: str = "pass"
    reason: str = "rule_pass"
    evidence: dict[str, Any] = field(default_factory=dict)
    horizon: int = 1
    semantics: str = "relative_strength"
    family: str = "price"


@dataclass(frozen=True)
class Frame:
    as_of: str
    history: Mapping[str, tuple[Mapping[str, Any], ...]]
    metadata: Mapping[str, Mapping[str, Any]]
    account: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        as_of: str,
        history: dict[str, list[dict[str, Any]]],
        metadata: dict[str, dict[str, Any]] | None = None,
        account: dict[str, Any] | None = None,
    ):
        selected = {}
        for symbol, rows in sorted(history.items()):
            accepted = sorted(
                [dict(row) for row in rows if str(row.get("timestamp") or row.get("date"))[:10] <= as_of],
                key=lambda row: str(row.get("timestamp") or row.get("date")),
            )
            dates = [str(row.get("timestamp") or row.get("date"))[:10] for row in accepted]
            if len(dates) != len(set(dates)):
                raise fail("invalid", symbol)
            selected[symbol] = tuple(
                MappingProxyType({**row, "timestamp": day, "date": day})
                for row, day in zip(accepted, dates, strict=True)
            )
        meta = {
            symbol: MappingProxyType(dict(values))
            for symbol, values in (metadata or {}).items()
            if str(values.get("available_at") or "9999")[:10] <= as_of
        }
        return cls(as_of, MappingProxyType(selected), MappingProxyType(meta), account or {})

    def active(self) -> list[str]:
        return [symbol for symbol, rows in self.history.items() if rows and rows[-1]["date"] == self.as_of]

    def mutable_history(self) -> dict[str, list[dict[str, Any]]]:
        return {symbol: [dict(row) for row in rows] for symbol, rows in self.history.items()}
