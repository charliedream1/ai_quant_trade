"""Shared model row contract independent from feature construction."""

from dataclasses import dataclass


@dataclass(slots=True)
class FeatureRow:
    symbol: str
    date: str
    values: list[float]
    target: float | None = None
    target_date: str = ""
