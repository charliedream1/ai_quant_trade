"""Data-source router and deterministic provider used by tests."""

import hashlib
import os
from contextvars import ContextVar
from threading import RLock
from typing import Any

from src.core.config import get_settings
from src.core.timeutil import utc_now_iso

from .eastmoney import EastmoneyDataSource
from .models import (
    INDEX_QUOTES,
    NEWS_ITEMS,
    PAPERS,
    SECTOR_QUOTES,
    STOCKS,
    US_INDEX_QUOTES,
    US_NEWS_ITEMS,
    US_REPORTS,
    US_SECTOR_QUOTES,
    US_STOCKS,
)

MARKET_CN = "CN"
MARKET_US = "US"
_MARKET_ALIASES = {
    "cn": MARKET_CN,
    "cn_a": MARKET_CN,
    "a": MARKET_CN,
    "a股": MARKET_CN,
    "us": MARKET_US,
    "usa": MARKET_US,
    "美股": MARKET_US,
    "us_market": MARKET_US,
}
_market_lock = RLock()
_current_market = MARKET_CN
REQUEST_MARKET: ContextVar[str | None] = ContextVar("all_in_one_request_market", default=None)


def normalize_market(value: Any) -> str:
    """Map user-facing market labels to the canonical CN/US codes."""
    key = str(value or "").strip().lower()
    return _MARKET_ALIASES.get(key, key.upper() if key in {"cn", "us"} else MARKET_CN)


def set_current_market(market: Any) -> str:
    """Update the process-wide market selection used by data providers."""
    global _current_market
    selected = normalize_market(market)
    with _market_lock:
        _current_market = selected
    return selected


def current_market() -> str:
    """Return the process-wide market selection (CN by default)."""
    scoped = REQUEST_MARKET.get()
    if scoped is not None:
        return scoped
    with _market_lock:
        return _current_market


class MockDataSource:
    """Deterministic provider covering both the CN and US sample datasets."""

    _UNKNOWN_NAMES = {"CN": "未知标的", "US": "Unknown symbol"}

    def __init__(self, market: str | None = None) -> None:
        self.market = normalize_market(market) if market else current_market()
        self.source_name = "mock-local" if self.market == MARKET_CN else "mock-local-us"

    @property
    def _indices(self) -> list[dict[str, Any]]:
        return US_INDEX_QUOTES if self.market == MARKET_US else INDEX_QUOTES

    @property
    def _sectors(self) -> list[dict[str, Any]]:
        return US_SECTOR_QUOTES if self.market == MARKET_US else SECTOR_QUOTES

    @property
    def _stocks(self) -> dict[str, dict[str, Any]]:
        return US_STOCKS if self.market == MARKET_US else STOCKS

    @property
    def _news_items(self) -> list[dict[str, Any]]:
        return US_NEWS_ITEMS if self.market == MARKET_US else NEWS_ITEMS

    def health(self) -> dict[str, Any]:
        return {
            "quotes": {"status": "ok", "active_source": self.source_name, "market": self.market},
            "news": {"status": "ok", "active_source": self.source_name, "market": self.market},
            "reports": {"status": "ok", "active_source": self.source_name, "market": self.market},
            "papers": {"status": "ok", "active_source": self.source_name, "market": self.market},
        }

    def list_news(self, category: str | None = None, keyword: str | None = None) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        source_label = "Mock Wire" if self.market == MARKET_US else "本地模拟源"
        for index, item in enumerate(self._news_items, start=1):
            if category and category not in (item["category"], self._category_alias(item["category"])):
                continue
            text = item["title"] + item["summary"]
            if keyword and keyword not in text:
                continue
            items.append(
                {
                    "id": index,
                    "source": source_label,
                    "category": item["category"],
                    "title": item["title"],
                    "summary": item["summary"],
                    "url": f"https://example.local/news/{index}",
                    "published_at": utc_now_iso(),
                    "fetched_at": utc_now_iso(),
                    "keywords": item["keywords"],
                    "sentiment": "positive" if index % 2 else "neutral",
                    "symbols": ["NVDA"]
                    if self.market == MARKET_US and "NVIDIA" in text
                    else (["300750"] if "宁德" in text else []),
                }
            )
        return items

    def keyword_cloud(self, category: str | None = None, top_n: int = 50) -> list[dict[str, Any]]:
        counts: dict[str, int] = {}
        for item in self._news_items:
            if category and category not in (item["category"], self._category_alias(item["category"])):
                continue
            for keyword in item["keywords"]:
                counts[keyword] = counts.get(keyword, 0) + 1
        return [
            {
                "keyword": key,
                "count": value,
                "weight": round(value / max(sum(counts.values()), 1), 4),
                "sentiment": "neutral",
            }
            for key, value in sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[:top_n]
        ]

    def indices(self, refresh: bool = False) -> list[dict[str, Any]]:
        return [dict(item, data_source=self.source_name, updated_at=utc_now_iso()) for item in self._indices]

    def sectors(self, board: str = "industry", limit: int = 20) -> list[dict[str, Any]]:
        return [dict(item, board=board, updated_at=utc_now_iso()) for item in self._sectors[:limit]]

    def stock_quote(self, symbol: str) -> dict[str, Any]:
        stock = dict(
            self._stocks.get(
                symbol,
                {
                    "symbol": symbol,
                    "name": self._UNKNOWN_NAMES.get(self.market, "未知标的"),
                    "market": self.market,
                    "price": self._price_for(symbol),
                    "change_pct": 0.0,
                },
            )
        )
        stock.update(
            {
                "latest_price": stock["price"],
                "volume": 1000000 + int(self._price_for(symbol) * 1000),
                "turnover_rate": round(abs(stock["change_pct"]) + 1.2, 2),
                "updated_at": utc_now_iso(),
                "data_source": self.source_name,
            }
        )
        return stock

    def stock_quotes(self, symbols: list[str]) -> list[dict[str, Any]]:
        return [self.stock_quote(symbol) for symbol in symbols]

    def heatmap(
        self, level: str = "industry", board: str | None = None, threshold: float = 0.0
    ) -> list[dict[str, Any]]:
        return [
            {
                "name": item["name"],
                "code": item["code"],
                "value": item["amount"],
                "change_pct": item["change_pct"],
                "children": [] if level == "industry" else self.stock_quotes(list(self._stocks.keys())[:2]),
            }
            for item in self._sectors
            if item["amount"] >= threshold
        ]

    def stock_detail(
        self,
        symbol: str,
        kline_count: int = 60,
        kline_period: str = "daily",
        price_adjustment: str = "qfq",
    ) -> dict[str, Any]:
        quote = self.stock_quote(symbol)
        base = float(quote["latest_price"])
        adjustment = _normalize_price_adjustment(price_adjustment)
        kline = []
        for i in range(max(1, min(kline_count, 120))):
            close = round(base * (1 + (i - kline_count / 2) * 0.0008), 2)
            kline.append(
                {
                    "date": f"D-{kline_count - i:03d}",
                    "open": close * 0.99,
                    "high": close * 1.01,
                    "low": close * 0.98,
                    "close": close,
                    "volume": 1000000 + i * 2000,
                    "adjust": adjustment,
                }
            )
        score = 72 + int(abs(quote["change_pct"]) * 3)
        return {
            "symbol": symbol,
            "quote": quote,
            "kline": kline,
            "finance": {"pe": 18.5, "pb": 2.3, "roe": 12.7, "revenue_growth": 8.4},
            "news": self.list_news(category="company")[:3],
            "score": {"total": min(score, 95), "trend": 74, "volume": 70, "fundamental": 76, "sentiment": 68},
            "reports": self.reports(symbol=symbol)[:3],
        }

    def relation_graph(self, symbol: str, depth: int = 1) -> dict[str, Any]:
        """按 1-5 层生成确定性的模拟关系网络，覆盖全部可筛选关系类型。"""
        depth = max(1, min(int(depth or 1), 5))
        center = self.stock_quote(symbol)
        nodes: dict[str, dict[str, Any]] = {}
        edges: list[dict[str, Any]] = []

        def add_node(node_id: str, name: str, node_type: str, change_pct: float = 0.0) -> None:
            nodes.setdefault(
                node_id,
                {"id": node_id, "name": name, "type": node_type, "change_pct": change_pct},
            )

        def add_edge(source: str, target: str, relation_type: str, description: str, weight: float) -> None:
            edges.append(
                {
                    "source": source,
                    "target": target,
                    "relation_type": relation_type,
                    "description": description,
                    "weight": round(weight, 2),
                }
            )

        add_node(symbol, center["name"], "stock", center["change_pct"])

        is_us = self.market == MARKET_US
        industry = self._sectors[0]
        add_node(industry["code"], industry["name"], "sector", industry["change_pct"])
        add_edge(
            industry["code"], symbol, "industry", "Simulated industry membership" if is_us else "模拟行业分类归属", 1.0
        )
        for sector in self._sectors[2:4]:
            add_node(sector["code"], sector["name"], "sector", sector["change_pct"])
            add_edge(
                sector["code"], symbol, "concept", "Simulated concept exposure" if is_us else "模拟概念题材暴露", 0.82
            )
        for index, weight in zip(self._indices[:2], (0.78, 0.72), strict=True):
            index_id = f"IDX:{index['code']}"
            add_node(index_id, index["name"], "index")
            add_edge(index_id, symbol, "index", "Simulated index membership" if is_us else "模拟指数成分归属", weight)

        peers = [code for code in self._stocks if code != symbol][:4]

        if depth >= 2:
            # 第二层：同行业关联标的 + 收益相关 + 新闻共现
            concept_anchor = self._sectors[2]["code"]
            corr_weights = (0.88, 0.76, 0.62, -0.31)
            for peer_index, peer_symbol in enumerate(peers):
                quote = self.stock_quote(peer_symbol)
                add_node(peer_symbol, quote["name"], "stock", quote["change_pct"])
                add_edge(
                    industry["code"],
                    peer_symbol,
                    "industry",
                    "Peer in same industry" if is_us else "同行业候选标的",
                    0.7,
                )
                if peer_index % 2 == 0:
                    add_edge(
                        concept_anchor,
                        peer_symbol,
                        "concept",
                        "Shared concept theme" if is_us else "共享概念题材",
                        0.66,
                    )
                corr = corr_weights[min(peer_index, len(corr_weights) - 1)]
                corr_label = (
                    f"Simulated 60d return correlation {corr:+.2f}" if is_us else f"模拟60日收益相关系数 {corr:+.2f}"
                )
                add_edge(
                    peer_symbol,
                    symbol,
                    "correlation",
                    corr_label,
                    round(0.5 + abs(corr) * 0.5, 2),
                )
            for news_index, news in enumerate(self._news_items[:2], start=1):
                event_id = f"EVENT:{news_index}"
                add_node(event_id, news["keywords"][0], "event")
                add_edge(event_id, symbol, "news_cooccurrence", news["title"], 0.58)

        if depth >= 3:
            # 第三层：产业链上下游 + 股东机构 + 新闻向关联标的扩散
            if is_us:
                supply_nodes = [
                    ("SUPPLY:UP-MATERIAL", "Upstream raw materials", 0.58),
                    ("SUPPLY:UP-EQUIPMENT", "Core equipment", 0.52),
                    ("SUPPLY:DOWN-DEMAND", "Downstream demand", 0.5),
                ]
                supply_desc = "Simulated supply chain linkage"
                holder_nodes = [
                    ("HOLDER:CONTROLLING", "Simulated controlling shareholder", 0.92),
                    ("HOLDER:PUBLIC-FUND", "Simulated institutional fund", 0.61),
                ]
                holder_desc = "Simulated top holders / institutional ownership"
                news_spread_desc = "News mentions peer symbol too"
            else:
                supply_nodes = [
                    ("SUPPLY:UP-MATERIAL", "上游原材料", 0.58),
                    ("SUPPLY:UP-EQUIPMENT", "核心装备", 0.52),
                    ("SUPPLY:DOWN-DEMAND", "下游需求", 0.5),
                ]
                supply_desc = "模拟产业链上下游关联"
                holder_nodes = [
                    ("HOLDER:CONTROLLING", "模拟控股股东集团", 0.92),
                    ("HOLDER:PUBLIC-FUND", "模拟公募基金组合", 0.61),
                ]
                holder_desc = "模拟十大股东/机构持仓"
                news_spread_desc = "新闻同时提及关联标的"
            for node_id, name, weight in supply_nodes:
                add_node(node_id, name, "factor")
                add_edge(node_id, symbol, "supply_chain", supply_desc, weight)
            for node_id, name, weight in holder_nodes:
                add_node(node_id, name, "institution")
                add_edge(node_id, symbol, "shareholder", holder_desc, weight)
            if peers:
                add_edge("EVENT:1", peers[0], "news_cooccurrence", news_spread_desc, 0.42)

        if depth >= 4:
            # 第四层：关联标的的二跳概念/指数与机构持仓
            extra_concept = self._sectors[3]
            add_node(extra_concept["code"], extra_concept["name"], "sector", extra_concept["change_pct"])
            if len(peers) >= 2:
                add_edge(
                    extra_concept["code"],
                    peers[1],
                    "concept",
                    "Second-hop concept theme" if is_us else "二跳概念题材",
                    0.56,
                )
                add_edge(
                    "HOLDER:PUBLIC-FUND",
                    peers[0],
                    "shareholder",
                    "Cross institutional ownership" if is_us else "同一机构交叉持仓",
                    0.48,
                )
            if len(peers) >= 3:
                add_edge(
                    "IDX:000001", peers[2], "index", "Shared index membership" if is_us else "共同指数成分股", 0.54
                )

        if depth >= 5:
            # 第五层：二级供应链、宏观风格因子与第三跳新闻
            if is_us:
                add_node("SUPPLY:UP-TIER2", "Tier-2 material supplier", "factor")
                add_edge("SUPPLY:UP-TIER2", "SUPPLY:UP-MATERIAL", "supply_chain", "Simulated tier-2 supply chain", 0.44)
                add_node("FACTOR:LIQUIDITY", "Market liquidity factor", "factor")
                add_edge("FACTOR:LIQUIDITY", symbol, "correlation", "Simulated style factor sensitivity", 0.4)
                if peers:
                    add_edge("FACTOR:LIQUIDITY", peers[-1], "correlation", "Shared style factor exposure", 0.38)
            else:
                add_node("SUPPLY:UP-TIER2", "二级材料供应商", "factor")
                add_edge("SUPPLY:UP-TIER2", "SUPPLY:UP-MATERIAL", "supply_chain", "模拟二级供应链传导", 0.44)
                add_node("FACTOR:LIQUIDITY", "市场流动性因子", "factor")
                add_edge("FACTOR:LIQUIDITY", symbol, "correlation", "模拟风格因子敏感度", 0.4)
                if peers:
                    add_edge("FACTOR:LIQUIDITY", peers[-1], "correlation", "共同风格因子暴露", 0.38)
            news = self._news_items[3]
            add_node("EVENT:4", news["keywords"][-1], "event")
            add_edge("EVENT:4", peers[-1], "news_cooccurrence", news["title"], 0.36)

        return {"nodes": list(nodes.values()), "edges": edges}

    def reports(self, keyword: str | None = None, symbol: str | None = None) -> list[dict[str, Any]]:
        if self.market == MARKET_US:
            records: list[dict[str, Any]] = [dict(item) for item in US_REPORTS]
        else:
            records = [
                {
                    "id": 1,
                    "title": "半导体设备国产替代跟踪",
                    "org": "模拟证券",
                    "analyst": "研究员A",
                    "rating": "增持",
                    "symbols": ["688981"],
                    "pages": 32,
                },
                {
                    "id": 2,
                    "title": "储能产业链景气度观察",
                    "org": "模拟证券",
                    "analyst": "研究员B",
                    "rating": "买入",
                    "symbols": ["300750"],
                    "pages": 26,
                },
                {
                    "id": 3,
                    "title": "高股息资产配置价值",
                    "org": "模拟证券",
                    "analyst": "研究员C",
                    "rating": "中性",
                    "symbols": ["600519"],
                    "pages": 18,
                },
            ]
        results: list[dict[str, Any]] = []
        for item in records:
            text = item["title"] + "".join(item["symbols"])
            if keyword and keyword not in text:
                continue
            if symbol and symbol not in item["symbols"]:
                continue
            results.append(dict(item, publish_date="2026-08-15", source=self.source_name))
        return results

    def report_detail(self, report_id: int) -> dict[str, Any] | None:
        if self.market == MARKET_US:
            body_text = "This report is local mock content for validating report viewing and knowledge import flows."
        else:
            body_text = "本报告为本地模拟研报内容，用于验证研报查看接口与后续知识库导入流程。"
        for item in self.reports():
            if item["id"] == report_id:
                return dict(item, body=body_text, charts=[])
        return None

    def paper_search(
        self,
        keyword: str = "",
        year_from: int | None = None,
        year_to: int | None = None,
    ) -> list[dict[str, Any]]:
        results = []
        for idx, item in enumerate(PAPERS, start=1):
            text = (item["title"] + item["abstract"]).lower()
            if keyword and keyword.lower() not in text:
                continue
            if year_from and item["year"] < year_from:
                continue
            if year_to and item["year"] > year_to:
                continue
            results.append(
                {
                    "id": idx,
                    "title": item["title"],
                    "authors": item["authors"],
                    "abstract": item["abstract"],
                    "source": item["source"],
                    "published_at": f"{item['year']}-01-01",
                    "url": f"https://example.local/papers/{idx}",
                    "is_favorite": False,
                }
            )
        return results

    def _category_alias(self, category: str) -> str:
        aliases = {"domestic": "国内", "international": "国外", "finance": "财经", "company": "公司"}
        return aliases.get(category, category)

    def _price_for(self, symbol: str) -> float:
        digest = hashlib.sha1(symbol.encode("utf-8"), usedforsecurity=False).hexdigest()
        return round(8 + int(digest[:4], 16) % 24000 / 100, 2)


def _normalize_price_adjustment(value: str) -> str:
    selected = str(value or "qfq").strip().lower()
    aliases = {
        "forward": "qfq",
        "pre": "qfq",
        "前复权": "qfq",
        "backward": "hfq",
        "post": "hfq",
        "后复权": "hfq",
        "raw": "none",
        "none": "none",
        "不复权": "none",
        "bfq": "none",
    }
    return aliases.get(selected, selected if selected in {"qfq", "hfq", "none"} else "qfq")


class DataSourceManager:
    """Select a real provider by default; mock data must be explicitly enabled.

    The process-wide market selection (``set_current_market``) is applied on
    every instantiation, so switching markets requires no changes downstream.
    Under ``real`` mode the US market falls back to the US mock dataset because
    the Eastmoney provider only covers A-shares.
    """

    def __init__(self, mode: str | None = None, market: str | None = None) -> None:
        settings = get_settings()
        selected = str(mode or os.environ.get("ALL_IN_ONE_DATA_MODE") or settings.data_mode).strip().lower()
        selected_market = normalize_market(market) if market else current_market()
        self.market = selected_market
        if selected == "mock":
            self.provider: Any = MockDataSource(market=selected_market)
        elif selected == "real":
            if selected_market == MARKET_US:
                self.provider = MockDataSource(market=MARKET_US)
                self.provider.source_name = "mock-local-us (real US source pending)"
            else:
                self.provider = EastmoneyDataSource(settings.data_timeout_seconds)
        else:
            raise ValueError("ALL_IN_ONE_DATA_MODE 只支持 real 或 mock")
        self.mode = selected

    @property
    def source_name(self) -> str:
        return str(self.provider.source_name)

    @property
    def is_mock(self) -> bool:
        provider = getattr(self.provider, "source_name", "")
        return self.mode == "mock" or str(provider).startswith("mock-local")

    def __getattr__(self, name: str) -> Any:
        return getattr(self.provider, name)
