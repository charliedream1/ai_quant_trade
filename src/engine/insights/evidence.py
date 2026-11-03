"""Collect dated, attributed platform observations for the two report skills."""

from collections.abc import Callable
from datetime import date, datetime
from math import isfinite
from typing import Any

import pandas as pd

from src.data import DataSourceManager
from src.data.security_master import SecurityMasterService
from src.engine.economics.config import economics_config
from src.engine.economics.service import EconomicAnalysis


def technical_readings(rows: list[dict[str, Any]], config: dict[str, Any]) -> dict[str, Any]:
    frame = pd.DataFrame(rows)
    if frame.empty or "close" not in frame:
        return {}
    close = pd.to_numeric(frame["close"], errors="coerce").dropna()
    close = close[close > 0]
    if close.empty:
        return {}
    result: dict[str, Any] = {"sample_points": int(close.notna().sum()), "latest_close": float(close.iloc[-1])}
    for window in config["technical_windows"]:
        if len(close) >= window:
            result[f"ma_{window}"] = round(float(close.rolling(window).mean().iloc[-1]), 4)
    window = config["volatility_window"]
    returns = close.pct_change().dropna()
    if len(returns) >= window:
        result["annualized_volatility"] = round(float(returns.tail(window).std() * config["annual_periods"] ** 0.5), 6)
        result["window_return"] = round(float(close.iloc[-1] / close.iloc[-window - 1] - 1), 6)
        deviation = float(close.tail(window).std()) * config["bollinger_deviation"]
        average = float(close.tail(window).mean())
        result.update(bollinger_upper=round(average + deviation, 4), bollinger_lower=round(average - deviation, 4))
    rsi_window = config["rsi_window"]
    if len(close) > rsi_window:
        delta = close.diff().tail(rsi_window)
        gains, losses = float(delta.clip(lower=0).mean()), float(-delta.clip(upper=0).mean())
        result["rsi"] = round(100 - 100 / (1 + gains / losses), 4) if losses else (100.0 if gains else 50.0)
    fast, slow, signal = config["macd_windows"]
    if len(close) >= slow + signal:
        difference = close.ewm(span=fast, adjust=False).mean() - close.ewm(span=slow, adjust=False).mean()
        result["macd_difference"] = round(float(difference.iloc[-1]), 5)
        result["macd_signal"] = round(float(difference.ewm(span=signal, adjust=False).mean().iloc[-1]), 5)
    return {key: value for key, value in result.items() if isfinite(value)}


class EvidenceCollector:
    def __init__(self, payload: dict[str, Any], config: dict[str, Any], emit: Callable[..., None], data: Any = None):
        self.payload, self.config, self.emit = payload, config, emit
        self.defaults = config["defaults"]
        self.data = data or DataSourceManager(market=payload["market"])
        self.sources: list[dict[str, Any]] = []
        self.gaps: list[str] = []

    def observe(self, name: str, function: Callable[[], Any]) -> Any:
        self.emit("tool", name, {"status": "started"})
        try:
            value = function()
        except Exception as exc:
            self.gaps.append(f"{name}: {exc}")
            self.emit("tool", name, {"status": "failed", "error": str(exc)})
            return None
        self.emit("tool", name, {"status": "completed", "result": value})
        return value

    def add(self, kind: str, value: Any, origin: str | None = None) -> None:
        if value is None or value == [] or value == {}:
            return
        self.sources.append(
            {
                "id": f"E{len(self.sources) + 1}",
                "kind": kind,
                "data": value,
                "data_source": origin or self.data.source_name,
                "is_mock": self.data.is_mock,
            }
        )

    def _dated_rows(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        cutoff = date.fromisoformat(self.payload["end_date"])
        accepted = []
        for row in rows:
            stamp = str(
                row.get("date")
                or row.get("updated_at")
                or row.get("published_at")
                or row.get("publish_time")
                or row.get("publish_date")
                or ""
            )
            try:
                observed = datetime.fromisoformat(stamp.replace("Z", "+00:00")).date()
            except ValueError:
                if self.data.is_mock:
                    accepted.append(row)
                continue
            if observed <= cutoff:
                accepted.append(row)
        return accepted

    def collect(self) -> dict[str, Any]:
        if self.payload["kind"] in {"macro_analysis", "fundamental_analysis"}:
            return self._economic()
        if self.payload["kind"] == "market_review":
            self._market()
        else:
            self._stock()
        if not self.sources:
            raise ValueError(self.config["messages"]["no_data"])
        if not any(row["kind"] in {"indices", "quote", "price_history"} for row in self.sources):
            raise ValueError(self.config["messages"]["no_data"])
        if self.data.is_mock:
            self.gaps.append(self.config["messages"]["demo_data"])
        return {
            "market": self.payload["market"],
            "data_source": self.data.source_name,
            "is_mock": self.data.is_mock or any(row["is_mock"] for row in self.sources),
            "sources": self.sources,
            "gaps": self.gaps,
        }

    def _market(self) -> None:
        indices = self.observe("market.indices", lambda: self.data.indices(refresh=True)) or []
        sectors = self.observe("market.sectors", lambda: self.data.sectors(limit=self.defaults["sector_limit"])) or []
        news = self.observe("market.news", lambda: self.data.list_news()) or []
        self.add("indices", self._dated_rows(indices))
        self.add("sectors", self._dated_rows(sectors))
        self.add("news", self._dated_rows(news)[: self.defaults["news_limit"]])
        self.gaps.extend(self.config["messages"]["market_gaps"])
        if self.payload["timeframe"] == "monthly":
            self.gaps.append(self.config["messages"]["monthly_gap"])

    def _stock(self) -> None:
        requested = self.payload["symbol"]
        security = self.observe(
            "security.resolve", lambda: SecurityMasterService().resolve(requested, self.payload["market"])
        )
        if not security:
            raise ValueError(self.config["messages"]["invalid_symbol"])
        self.add("security", security, "security-master")
        detail = self.observe(
            "stock.detail",
            lambda: self.data.stock_detail(
                security["symbol"],
                kline_count=self.defaults["kline_count"],
                kline_period="daily",
            ),
        )
        if not detail:
            raise ValueError(self.config["messages"]["no_data"])
        quote = detail.get("quote") or {}
        cutoff = self.payload["end_date"]
        if str(quote.get("updated_at") or "")[:10] <= cutoff:
            self.add("quote", quote)
            self.add("finance", detail.get("finance"))
        rows = self._dated_rows(detail.get("kline") or [])
        self.add("price_history", rows)
        readings = self.observe("stock.technical_readings", lambda: technical_readings(rows, self.defaults))
        self.add("technical", readings, "platform-calculated")
        self.add("news", self._dated_rows(detail.get("news") or []))
        self.add("reports", self._dated_rows(detail.get("reports") or []))
        self.gaps.extend(self.config["messages"]["stock_gaps"])
        if self.payload.get("include_fundamentals"):
            self._attach_fundamentals()

    def _economic(self) -> dict[str, Any]:
        service = EconomicAnalysis()
        identifier = self.payload.get("research_snapshot")
        kind = self.payload["kind"]
        if not identifier:
            value = (
                service.macro(market=self.payload["market"])
                if kind == "macro_analysis"
                else service.fundamentals(self.payload["symbol"], market=self.payload["market"])
            )
            identifier = value["snapshot_id"]
        snapshot = service.report_snapshot(identifier, kind, self.payload.get("symbol", ""), self.payload["end_date"])
        if kind == "macro_analysis":
            limit = economics_config()["defaults"]["report_history_rows"]
            content = {
                "overview": snapshot["overview"],
                "observations": [
                    row
                    for series in snapshot["overview"]
                    for row in [r for r in snapshot["observations"] if r["series"] == series["series"]][-limit:]
                ],
                "sources": snapshot["sources"],
            }
        else:
            content = {
                key: snapshot[key]
                for key in (
                    "symbol",
                    "name",
                    "industry",
                    "financial_industry",
                    "selected",
                    "peers",
                    "valuation",
                    "sources",
                )
            }
            content["periods"] = [
                {"report_period": row["report_period"], "metrics": row["metrics"], "statuses": row["statuses"]}
                for row in [
                    period
                    for period in snapshot["periods"]
                    if period["report_period"] <= snapshot["selected"]["report_period"]
                ][-economics_config()["defaults"]["report_periods"] :]
            ]
        content.update(snapshot_id=identifier, historical_pit_eligible=False, scope=snapshot["scope"])
        return {
            "market": "CN",
            "data_source": "economic-research-snapshot",
            "is_mock": snapshot["is_mock"],
            "sources": [
                {
                    "id": "E1",
                    "kind": kind,
                    "data": content,
                    "data_source": "public-dated-snapshot",
                    "is_mock": snapshot["is_mock"],
                }
            ],
            "gaps": [snapshot["scope"], *snapshot["gaps"]],
        }

    def _attach_fundamentals(self) -> None:
        def load():
            service = EconomicAnalysis()
            identifier = self.payload.get("research_snapshot")
            if not identifier:
                if self.payload["end_date"] < date.today().isoformat():
                    raise ValueError(economics_config()["messages"]["current_only"])
                identifier = service.fundamentals(self.payload["symbol"], market=self.payload["market"])["snapshot_id"]
            return service.report_snapshot(
                identifier, "fundamental_analysis", self.payload["symbol"], self.payload["end_date"]
            )

        snapshot = self.observe(
            "stock.fundamental_statements",
            load,
        )
        if snapshot:
            self.add(
                "fundamental_statements",
                {key: snapshot[key] for key in ("snapshot_id", "selected", "industry", "sources", "scope")},
                "economic-research-snapshot",
            )
            self.sources[-1]["is_mock"] = snapshot["is_mock"]
            self.gaps.extend(snapshot["gaps"])
