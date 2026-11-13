"""HKD cash-equity quotes and original historical observations from public sources."""

import math
import re
from copy import deepcopy
from datetime import date
from functools import lru_cache
from threading import RLock
from time import monotonic, sleep
from typing import Any

import requests
import yaml
from loguru import logger

from src.core.config import PROJECT_ROOT
from src.core.exceptions import BusinessError, ErrorCode
from src.core.network_policy import network_session
from src.core.timeutil import utc_now_iso

from .symbols import parse_symbol


@lru_cache(maxsize=1)
def hk_config():
    return yaml.safe_load((PROJECT_ROOT / "egs/config/data/hong_kong.yaml").read_text(encoding="utf-8"))


def hk_symbol(value):
    parsed = parse_symbol(value)
    if parsed.market != "HK":
        raise ValueError("HK requests require a Hong Kong code, such as 00700.HK")
    if parsed.code.startswith(tuple(hk_config()["excluded_counter_prefixes"])):
        raise ValueError("Non-HKD dual counters are not supported by this HKD workflow")
    return parsed.code + ".HK"


def numeric(value):
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("Non-finite Hong Kong market observation")
    return result


class HongKongDataSource:
    source_name = "hong-kong-public"
    market = "HK"
    _cache: dict[tuple, tuple[float, Any]] = {}
    _lock = RLock()

    def __init__(self, timeout_seconds=None):
        self.policy = hk_config()
        self.timeout = timeout_seconds or self.policy["timeout_seconds"]

    def _get(self, endpoint, params=None):
        for attempt in range(self.policy["request_attempts"]):
            try:
                with network_session() as session:
                    response = session.get(
                        endpoint,
                        params=params,
                        timeout=self.timeout,
                        headers={"Referer": self.policy["endpoints"]["referer"]},
                    )
                    response.raise_for_status()
                    return response
            except requests.RequestException as exc:
                if attempt + 1 == self.policy["request_attempts"]:
                    raise
                logger.debug("HK public source transient failure | error_type={}", type(exc).__name__)
                sleep(self.policy["backoff_seconds"])
        raise RuntimeError("HK request attempts must be positive")

    def _cached(self, key, loader):
        key = ("HK", *key)
        with self._lock:
            cached = self._cache.get(key)
            if cached and monotonic() - cached[0] < self.policy["cache_seconds"]:
                return deepcopy(cached[1])
        try:
            value = loader()
        except BusinessError:
            raise
        except Exception as exc:
            raise BusinessError(
                ErrorCode.DATA_SOURCE_ERROR,
                "Hong Kong public source unavailable",
                {"market": "HK", "error_type": type(exc).__name__},
            ) from None
        with self._lock:
            self._cache[key] = (monotonic(), deepcopy(value))
        return value

    def health(self):
        return {
            "market": "HK",
            "currency": "HKD",
            "network_checked": False,
            "capabilities": self.policy["capabilities"],
            "quotes": {"status": "not_probed", "active_source": self.source_name, "market": "HK"},
            "news": {"status": "unavailable", "market": "HK"},
            "reports": {"status": "unavailable", "market": "HK"},
        }

    def stock_quote(self, symbol):
        canonical = hk_symbol(symbol)
        return self._cached(("quote", canonical), lambda: self._quote(canonical))

    def _quote(self, symbol):
        code = parse_symbol(symbol).code
        response = self._get(self.policy["endpoints"]["quote"] + "hk" + code)
        response.encoding = "gbk"
        match = re.search(r'="([^"]+)"', response.text)
        if not match:
            raise ValueError("HK quote response missing")
        fields = match.group(1).split("~")
        columns = self.policy["quote_fields"]
        if len(fields) <= max(columns.values()) or fields[columns["code"]].zfill(5) != code:
            raise ValueError("HK quote identity mismatch")
        if fields[columns["currency"]] != self.policy["currency"]:
            raise ValueError("This workflow requires an HKD quote")
        price, previous = numeric(fields[columns["close"]]), numeric(fields[columns["previous_close"]])
        return {
            "symbol": symbol,
            "name": fields[columns["name"]],
            "market": "HK",
            "currency": "HKD",
            "price": price,
            "latest_price": price,
            "previous_close": previous,
            "open": numeric(fields[columns["open"]]),
            "volume": numeric(fields[columns["volume"]]),
            "volume_unit": "shares",
            "change_pct": (price / previous - 1) * 100 if previous else None,
            "data_source": "tencent-hk",
            "updated_at": utc_now_iso(),
            "provider_timestamp": fields[columns["timestamp"]],
            "quote_delay": "public feed; no real-time entitlement guarantee",
        }

    def stock_quotes(self, symbols):
        if len(symbols) > self.policy["max_quotes"]:
            raise ValueError("HK batch exceeds configured quote limit")
        return [self.stock_quote(symbol) for symbol in symbols]

    def history(self, symbol, start_date="", end_date="", count=240, period="daily", adjustment="none"):
        canonical = hk_symbol(symbol)
        if period not in self.policy["periods"] or adjustment not in self.policy["adjustments"]:
            raise ValueError("Unsupported HK period or adjustment")
        count = max(1, min(int(count), self.policy["max_history_bars"]))
        key = ("history", canonical, start_date, end_date, count, period, adjustment)
        return self._cached(key, lambda: self._history(canonical, start_date, end_date, count, period, adjustment))

    def _history(self, symbol, start, end, count, period, adjustment):
        code = "hk" + parse_symbol(symbol).code
        frequency = self.policy["periods"][period]
        try:
            payload = self._get(
                self.policy["endpoints"]["history"],
                {"param": f"{code},{frequency},{start},{end},{count},{self.policy['adjustments'][adjustment]}"},
            ).json()
            values = payload["data"][code]
            raw = values.get(self.policy["adjustments"][adjustment] + frequency) or []
            rows = [
                {
                    "date": item[0],
                    "open": numeric(item[1]),
                    "close": numeric(item[2]),
                    "high": numeric(item[3]),
                    "low": numeric(item[4]),
                    "volume": numeric(item[5]),
                    "data_source": "tencent-hk-history",
                }
                for item in raw
            ]
            if not rows:
                raise ValueError("Empty HK history")
        except Exception:
            response = self._get(
                self.policy["endpoints"]["eastmoney_history"],
                {
                    "secid": parse_symbol(symbol).secid,
                    "klt": self.policy["eastmoney_periods"][period],
                    "fqt": self.policy["eastmoney_adjustments"][adjustment],
                    "beg": start.replace("-", "") or "0",
                    "end": end.replace("-", "") or "20500101",
                    "lmt": count,
                    "fields1": "f1,f2,f3,f4,f5,f6",
                    "fields2": "f51,f52,f53,f54,f55,f56,f57",
                },
            ).json()
            rows = []
            for value in (response.get("data") or {}).get("klines") or []:
                item = value.split(",")
                rows.append(
                    {
                        "date": item[0],
                        "open": numeric(item[1]),
                        "close": numeric(item[2]),
                        "high": numeric(item[3]),
                        "low": numeric(item[4]),
                        "volume": numeric(item[5]),
                        "amount": numeric(item[6]),
                        "data_source": "eastmoney-hk-history",
                    }
                )
        rows = sorted(
            (row for row in rows if (not start or row["date"] >= start) and (not end or row["date"] <= end)),
            key=lambda row: row["date"],
        )[-count:]
        for row in rows:
            date.fromisoformat(row["date"])
            if min(row[key] for key in ("open", "high", "low", "close")) <= 0 or row["volume"] < 0:
                raise ValueError("Invalid HK history observation")
            if row["low"] > min(row["open"], row["close"]) or row["high"] < max(row["open"], row["close"]):
                raise ValueError("HK historical OHLC ranges are inconsistent")
            row.update(currency="HKD", market="HK", volume_unit="shares", adjust=adjustment)
        if len({row["date"] for row in rows}) != len(rows):
            raise ValueError("Duplicate HK historical sessions")
        return rows

    def stock_detail(self, symbol, kline_count=60, kline_period="daily", price_adjustment="qfq"):
        canonical = hk_symbol(symbol)
        rows = self.history(canonical, count=kline_count, period=kline_period, adjustment=price_adjustment)
        closes = [row["close"] for row in rows]
        technical = {
            f"sma_{window}": sum(closes[-window:]) / window if len(closes) >= window else None
            for window in self.policy["technical_windows"]
        }
        technical["period_return"] = closes[-1] / closes[0] - 1 if len(closes) > 1 else None
        return {
            "symbol": canonical,
            "quote": self.stock_quote(canonical),
            "kline": rows,
            "technical": technical,
            "finance": {},
            "news": [],
            "reports": [],
            "score": {},
            "industry": "",
            "capabilities": self.policy["capabilities"],
            "currency": "HKD",
        }

    def strategy_snapshot(self, symbol, kline_count=60, kline_period="daily", price_adjustment="none"):
        return self.stock_detail(symbol, kline_count, kline_period, price_adjustment)

    def indices(self, refresh=False):
        def load():
            result = []
            for item in self.policy["indices"]:
                response = self._get(self.policy["endpoints"]["quote"] + "r_hk" + item["symbol"])
                response.encoding = "gbk"
                match = re.search(r'="([^"]+)"', response.text)
                fields = match.group(1).split("~") if match else []
                if len(fields) < 38 or fields[2] != item["symbol"]:
                    continue
                result.append(
                    {
                        "code": item["symbol"],
                        "name": item["name"],
                        "price": numeric(fields[3]),
                        "change_pct": numeric(fields[32]),
                        "amount": numeric(fields[37]),
                        "market": "HK",
                        "unit": "index points",
                        "data_source": "tencent-hk-index",
                        "updated_at": utc_now_iso(),
                    }
                )
            return result

        return self._cached(("indices",), load)

    def sectors(self, board="industry", limit=20):
        return []

    def heatmap(self, level="industry", board=None, threshold=0):
        return []

    def list_news(self, category=None, keyword=None):
        return []

    def keyword_cloud(self, category=None, top_n=50):
        return []

    def reports(self, keyword=None, symbol=None):
        return []

    def report_detail(self, report_id):
        return None

    def paper_search(self, keyword="", year_from=None, year_to=None):
        from .eastmoney import EastmoneyDataSource

        return EastmoneyDataSource(self.timeout).paper_search(keyword, year_from, year_to)

    def relation_graph(self, symbol, depth=1):
        quote = self.stock_quote(symbol)
        return {
            "nodes": [{"id": quote["symbol"], "name": quote["name"], "type": "stock"}],
            "edges": [],
            "availability": "HK relationship evidence unavailable",
        }
