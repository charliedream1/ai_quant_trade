"""Shared research snapshots for REST, CLI, Gradio and optional model reports."""

from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime
from typing import Any

from src.core.timeutil import utc_now_iso
from src.data import DataSourceManager, SecurityMasterService, current_market
from src.data.economics import EconomicDataSource
from src.data.symbols import parse_symbol

from .calculations import financial_periods, numeric
from .config import economics_config
from .store import EconomicStore


class EconomicAnalysis:
    def __init__(self, provider: Any = None, store: EconomicStore | None = None):
        self.store = store or EconomicStore()
        self.source = provider or EconomicDataSource(self.store)
        self.config = economics_config()

    def _market(self, market: str | None):
        if str(market or current_market()).upper() != "CN":
            raise ValueError(self.config["messages"]["unsupported"])

    def _fetch(self, names: list[str], symbol: str = "", refresh: bool = False):
        def one(name):
            try:
                return name, self.source.fetch(name, symbol=symbol, refresh=refresh), None
            except Exception as exc:
                return name, None, f"{name}: {type(exc).__name__}"

        with ThreadPoolExecutor(max_workers=self.config["defaults"]["workers"]) as pool:
            results = list(pool.map(one, names))
        return {name: value for name, value, _ in results if value}, [error for _, _, error in results if error]

    def macro(self, series: list[str] | None = None, *, refresh=False, market=None) -> dict:
        self._market(market)
        selected = list(dict.fromkeys(self.config["macro"] if series is None else series))
        if not selected or set(selected) - set(self.config["macro"]):
            raise ValueError("Unknown macroeconomic series")
        sources, gaps = self._fetch(selected, refresh=refresh)
        observations, overview = [], []
        for name, source in sources.items():
            definition = self.config["macro"][name]
            rows = []
            for raw in source["rows"]:
                value = numeric(raw.get(definition["field"]))
                stamp = str(raw.get(definition["date"]) or "")
                if name == "social_finance" and len(stamp) == 6:
                    stamp = stamp[:4] + "-" + stamp[4:] + "-01"
                try:
                    period = date.fromisoformat(stamp[:10])
                except ValueError:
                    continue
                if value is None or period > date.today():
                    continue
                rows.append(
                    {
                        "series": name,
                        "label": definition["label"],
                        "observation_date": period.isoformat(),
                        "period_label": str(raw.get("TIME") or raw.get(definition["date"]) or period.isoformat()),
                        "value": value,
                        "unit": definition["unit"],
                        "basis": definition["basis"],
                        "frequency": definition["frequency"],
                        "published_at": None,
                        "first_seen_at": source["first_seen_at"],
                        "version": source["version"],
                    }
                )
            rows.sort(key=lambda row: row["observation_date"])
            if not rows:
                gaps.append(name + ": no valid observations")
                continue
            stale_days = self.config["defaults"][
                "quarterly_stale_days" if definition["frequency"] == "quarterly" else "macro_stale_days"
            ]
            latest = dict(rows[-1], age_days=(date.today() - date.fromisoformat(rows[-1]["observation_date"])).days)
            latest["stale"] = latest["age_days"] > stale_days
            if latest["stale"]:
                gaps.append(name + ": stale observation")
            overview.append(latest)
            observations.extend(rows[-self.config["defaults"]["source_rows"] :])
        if not observations:
            raise ValueError(self.config["messages"]["empty"] + " " + "; ".join(gaps))
        return self._save("macro", sources, {"observations": observations, "overview": overview, "gaps": gaps})

    def fundamentals(
        self, symbol: str, *, period="", peers: list[str] | None = None, refresh=False, market=None
    ) -> dict:
        self._market(market)
        if period:
            date.fromisoformat(period)
        peers = list(dict.fromkeys(peers or []))
        if len(peers) > self.config["defaults"]["max_peers"]:
            raise ValueError("Peer sample exceeds the configured budget")
        primary = self._company(symbol, refresh)
        periods = primary["periods"]
        selected = next((row for row in reversed(periods) if not period or row["report_period"] == period), None)
        if not selected:
            raise ValueError("The requested reporting period is unavailable")
        peer_rows, gaps = [], list(primary["gaps"])
        if selected["missing_statements"]:
            gaps.append("Missing statements at the selected period: " + ", ".join(selected["missing_statements"]))
        if any(selected["metrics"][key] is None for key in ("short_loan", "long_loan", "bonds")):
            gaps.append(self.config["messages"]["debt_gap"])
        seen = {primary["symbol"]}
        for peer in peers:
            try:
                canonical = self._symbol(peer).code
                if canonical in seen:
                    continue
                seen.add(canonical)
                company = self._company(canonical, refresh)
                matching = next(
                    (row for row in company["periods"] if row["report_period"] == selected["report_period"]), None
                )
                if not matching or not primary["industry"] or company["industry"] != primary["industry"]:
                    gaps.append(peer + ": report period or industry mismatch")
                    continue
                peer_rows.append(
                    {
                        "symbol": company["symbol"],
                        "name": company["name"],
                        "industry": company["industry"],
                        **matching,
                        "sources": company["sources"],
                        "snapshot_id": company["snapshot_id"],
                        "is_mock": company["is_mock"],
                    }
                )
            except (ValueError, OSError) as exc:
                gaps.append(peer + ": " + type(exc).__name__)
        simulated = primary["is_mock"] or any(row["is_mock"] for row in peer_rows)
        if simulated and not primary["is_mock"]:
            gaps.append(self.config["messages"]["simulated"])
        return self.store.save(
            {
                **primary,
                "kind": "fundamentals",
                "selected": selected,
                "periods": [row for row in periods if row["report_period"] <= selected["report_period"]],
                "peers": peer_rows,
                "is_mock": simulated,
                "gaps": gaps,
                "comparison_scope": self.config["messages"]["peer_scope"],
                "snapshot_id": None,
            }
        )

    def _symbol(self, requested: str):
        resolved = SecurityMasterService().resolve_symbol(requested, "CN")
        parsed = parse_symbol(resolved, stock_only=True)
        if parsed.market not in {"SH", "SZ", "BJ"}:
            raise ValueError(self.config["messages"]["invalid_symbol"])
        return parsed

    def _company(self, requested: str, refresh: bool) -> dict:
        parsed = self._symbol(requested)
        sources, gaps = self._fetch(list(self.config["statements"]), f"{parsed.code}.{parsed.market}", refresh)
        if not sources:
            raise ValueError(self.config["messages"]["empty"])
        raw = next(iter(sources.values()))["rows"][0]
        industry = str(raw.get("INDUSTRY_NAME") or "")
        financial = any(term in industry for term in self.config["financial_industries"])
        if financial:
            gaps.append(self.config["messages"]["financial_scope"])
        periods = financial_periods(sources, parsed.code, financial)
        if not periods:
            raise ValueError(self.config["messages"]["empty"])
        if (date.today() - date.fromisoformat(periods[-1]["report_period"])).days > self.config["defaults"][
            "quarterly_stale_days"
        ]:
            gaps.append("Financial statements are stale")
        return self._save(
            "company",
            sources,
            {
                "symbol": parsed.code,
                "name": str(raw.get("SECURITY_NAME_ABBR") or parsed.code),
                "industry": industry,
                "financial_industry": financial,
                "periods": periods,
                "gaps": gaps,
                "currency": "CNY",
                "valuation": self._valuation(parsed.qualified),
            },
        )

    def _valuation(self, symbol):
        data = DataSourceManager(market="CN")
        if data.is_mock:
            return {"status": "unavailable_in_mock_mode"}
        try:
            quote = data.stock_quote(symbol)
            return {
                "status": "current_quote_only",
                **{key: quote.get(key) for key in ("pe", "pb", "market_cap", "updated_at", "data_source")},
            }
        except Exception:
            return {"status": "unavailable"}

    def _save(self, kind: str, sources: dict, payload: dict) -> dict:
        metadata = {
            name: {key: value for key, value in source.items() if key != "rows"} for name, source in sources.items()
        }
        simulated = any(bool(source.get("is_mock")) for source in sources.values())
        if simulated:
            payload = {**payload, "gaps": [*payload.get("gaps", []), self.config["messages"]["simulated"]]}
        return self.store.save(
            {
                "kind": kind,
                "market": "CN",
                "sources": metadata,
                "created_at": utc_now_iso(),
                "historical_pit_eligible": False,
                "is_mock": simulated,
                "scope": self.config["messages"]["revision_scope"],
                **payload,
            }
        )

    def report_snapshot(self, identifier: str, kind: str, symbol: str = "", end_date: str = "") -> dict:
        snapshot = self.store.read(identifier)
        expected = "macro" if kind == "macro_analysis" else "fundamentals"
        if snapshot.get("kind") != expected or snapshot.get("market") != "CN":
            raise ValueError("The report snapshot does not match the requested task")
        if (
            symbol
            and snapshot.get("symbol")
            != parse_symbol(SecurityMasterService().resolve_symbol(symbol, "CN"), stock_only=True).code
        ):
            raise ValueError("The report snapshot belongs to a different company")
        if end_date and end_date < datetime.fromisoformat(snapshot["created_at"]).astimezone().date().isoformat():
            raise ValueError(self.config["messages"]["current_only"])
        return snapshot
