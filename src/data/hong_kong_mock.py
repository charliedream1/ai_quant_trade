"""Explicit HK-only development fixture without mainland fallback or network calls."""

from datetime import date, timedelta
from typing import Any

import yaml

from src.core.config import PROJECT_ROOT

from .hong_kong import HongKongDataSource, hk_symbol
from .hong_kong_calendar import sessions


class HongKongMockSource(HongKongDataSource):
    source_name = "mock-local-hk"

    def __init__(self):
        super().__init__()
        self.fixtures = yaml.safe_load(
            (PROJECT_ROOT / "egs/examples/data/hong_kong_mock.yaml").read_text(encoding="utf-8")
        )

    def stock_quote(self, symbol):
        canonical = hk_symbol(symbol)
        row = self.fixtures["quotes"].get(canonical)
        if row is None:
            raise ValueError("No explicitly configured HK development fixture for this security")
        return {
            **row,
            "symbol": canonical,
            "market": "HK",
            "currency": "HKD",
            "data_source": self.source_name,
            "volume_unit": "shares",
            "is_mock": True,
        }

    def history(self, symbol, start_date="", end_date="", count=240, period="daily", adjustment="none"):
        quote = self.stock_quote(symbol)
        config = self.fixtures["history"]
        current = date.fromisoformat(start_date or config["start"])
        rows: list[dict[str, Any]] = []
        while len(rows) < min(count, config["sessions"]):
            if end_date and current.isoformat() > end_date:
                break
            if current.weekday() < 5 and sessions(current.isoformat(), current.isoformat()) != []:
                price = quote["price"] + config["price_increment"] * len(rows)
                rows.append(
                    {
                        "date": current.isoformat(),
                        "open": price,
                        "high": price,
                        "low": price,
                        "close": price,
                        "volume": config["volume"],
                        "data_source": self.source_name,
                        "market": "HK",
                        "currency": "HKD",
                        "volume_unit": "shares",
                        "adjust": adjustment,
                    }
                )
            current += timedelta(days=1)
        return rows

    def indices(self, refresh=False):
        return []

    def paper_search(self, keyword="", year_from=None, year_to=None):
        return []
