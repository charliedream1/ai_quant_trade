"""Shared data constants and sample records."""

from typing import Any

INDEX_QUOTES: list[dict[str, Any]] = [
    {
        "code": "000001",
        "name": "上证指数",
        "price": 3158.42,
        "change": 12.38,
        "change_pct": 0.39,
        "volume": 342100000,
        "amount": 412350000000.0,
    },
    {
        "code": "399001",
        "name": "深证成指",
        "price": 9821.77,
        "change": -18.64,
        "change_pct": -0.19,
        "volume": 401220000,
        "amount": 497510000000.0,
    },
    {
        "code": "399006",
        "name": "创业板指",
        "price": 1962.10,
        "change": 8.71,
        "change_pct": 0.45,
        "volume": 184500000,
        "amount": 210050000000.0,
    },
    {
        "code": "000688",
        "name": "科创50",
        "price": 804.32,
        "change": 5.03,
        "change_pct": 0.63,
        "volume": 56910000,
        "amount": 75100000000.0,
    },
]

SECTOR_QUOTES: list[dict[str, Any]] = [
    {
        "code": "BK0428",
        "name": "半导体",
        "change_pct": 2.18,
        "leader": "中芯国际",
        "amount": 93200000000.0,
        "up_count": 84,
        "down_count": 19,
    },
    {
        "code": "BK0475",
        "name": "证券",
        "change_pct": 1.36,
        "leader": "东方财富",
        "amount": 71000000000.0,
        "up_count": 42,
        "down_count": 8,
    },
    {
        "code": "BK1033",
        "name": "机器人概念",
        "change_pct": 1.05,
        "leader": "汇川技术",
        "amount": 68400000000.0,
        "up_count": 66,
        "down_count": 22,
    },
    {
        "code": "BK0437",
        "name": "白酒",
        "change_pct": -0.74,
        "leader": "贵州茅台",
        "amount": 51100000000.0,
        "up_count": 12,
        "down_count": 31,
    },
]

STOCKS: dict[str, dict[str, Any]] = {
    "600519": {"symbol": "600519", "name": "贵州茅台", "market": "SH", "price": 1518.20, "change_pct": -0.52},
    "000001": {"symbol": "000001", "name": "平安银行", "market": "SZ", "price": 11.42, "change_pct": 0.88},
    "300750": {"symbol": "300750", "name": "宁德时代", "market": "SZ", "price": 198.35, "change_pct": 1.46},
    "688981": {"symbol": "688981", "name": "中芯国际", "market": "SH", "price": 61.18, "change_pct": 2.64},
    "300124": {"symbol": "300124", "name": "汇川技术", "market": "SZ", "price": 58.93, "change_pct": 1.31},
}

NEWS_ITEMS: list[dict[str, Any]] = [
    {
        "category": "finance",
        "title": "两市成交额维持高位，科技成长方向活跃",
        "summary": "半导体、机器人、券商板块成交活跃，市场风险偏好温和修复。",
        "keywords": ["半导体", "成交额", "成长"],
    },
    {
        "category": "domestic",
        "title": "多部门部署扩大有效需求，关注设备更新与消费支持",
        "summary": "政策组合强调稳增长与结构升级，市场关注受益行业景气改善。",
        "keywords": ["政策", "设备更新", "消费"],
    },
    {
        "category": "international",
        "title": "海外主要股指震荡，市场等待通胀数据指引",
        "summary": "美元指数小幅回落，科技龙头表现分化。",
        "keywords": ["海外", "通胀", "美元"],
    },
    {
        "category": "company",
        "title": "宁德时代发布新一代储能解决方案",
        "summary": "公司强调循环寿命与系统效率提升，储能产业链关注度升温。",
        "keywords": ["宁德时代", "储能"],
    },
]

PAPERS: list[dict[str, Any]] = [
    {
        "title": "Deep Reinforcement Learning for Portfolio Allocation",
        "authors": ["J. Li", "M. Chen"],
        "source": "arXiv",
        "year": 2025,
        "abstract": "A practical review of DRL portfolio allocation with transaction costs.",
    },
    {
        "title": "Limit Order Book Forecasting with Temporal Transformers",
        "authors": ["S. Wang"],
        "source": "SSRN",
        "year": 2024,
        "abstract": "Transformer features for short horizon market microstructure prediction.",
    },
    {
        "title": "Factor Timing under Regime Switching",
        "authors": ["Y. Zhang", "Y. Liu"],
        "source": "Journal",
        "year": 2023,
        "abstract": "A regime switching framework for factor exposure timing.",
    },
]

# ---------------------------------------------------------------------------
# US market sample data (field layout mirrors the CN records above)
# ---------------------------------------------------------------------------

US_INDEX_QUOTES: list[dict[str, Any]] = [
    {
        "code": "^GSPC",
        "name": "S&P 500",
        "price": 6321.44,
        "change": 28.61,
        "change_pct": 0.45,
        "volume": 2310000000,
        "amount": 382450000000.0,
    },
    {
        "code": "^IXIC",
        "name": "Nasdaq Composite",
        "price": 20648.32,
        "change": -52.18,
        "change_pct": -0.25,
        "volume": 3140000000,
        "amount": 421800000000.0,
    },
    {
        "code": "^DJI",
        "name": "Dow Jones Industrial",
        "price": 44692.61,
        "change": 102.35,
        "change_pct": 0.23,
        "volume": 412000000,
        "amount": 96420000000.0,
    },
    {
        "code": "^RUT",
        "name": "Russell 2000",
        "price": 2418.75,
        "change": -11.42,
        "change_pct": -0.47,
        "volume": 655000000,
        "amount": 42830000000.0,
    },
]

US_SECTOR_QUOTES: list[dict[str, Any]] = [
    {
        "code": "XLK",
        "name": "Technology",
        "change_pct": 1.86,
        "leader": "NVIDIA",
        "amount": 48230000000.0,
        "up_count": 72,
        "down_count": 14,
    },
    {
        "code": "XLF",
        "name": "Financials",
        "change_pct": 0.92,
        "leader": "JPMorgan Chase",
        "amount": 18460000000.0,
        "up_count": 48,
        "down_count": 12,
    },
    {
        "code": "XLE",
        "name": "Energy",
        "change_pct": -1.24,
        "leader": "Exxon Mobil",
        "amount": 12680000000.0,
        "up_count": 9,
        "down_count": 34,
    },
    {
        "code": "XLV",
        "name": "Health Care",
        "change_pct": 0.41,
        "leader": "Eli Lilly",
        "amount": 9840000000.0,
        "up_count": 31,
        "down_count": 22,
    },
    {
        "code": "XLY",
        "name": "Consumer Discretionary",
        "change_pct": 0.68,
        "leader": "Amazon",
        "amount": 11220000000.0,
        "up_count": 38,
        "down_count": 18,
    },
    {
        "code": "XLI",
        "name": "Industrials",
        "change_pct": -0.35,
        "leader": "Caterpillar",
        "amount": 7640000000.0,
        "up_count": 21,
        "down_count": 26,
    },
]

US_STOCKS: dict[str, dict[str, Any]] = {
    "AAPL": {"symbol": "AAPL", "name": "Apple Inc.", "market": "US", "price": 242.36, "change_pct": 0.58},
    "MSFT": {"symbol": "MSFT", "name": "Microsoft Corp.", "market": "US", "price": 451.87, "change_pct": 1.12},
    "NVDA": {"symbol": "NVDA", "name": "NVIDIA Corp.", "market": "US", "price": 138.64, "change_pct": 2.94},
    "GOOGL": {"symbol": "GOOGL", "name": "Alphabet Inc. Class A", "market": "US", "price": 196.42, "change_pct": -0.34},
    "AMZN": {"symbol": "AMZN", "name": "Amazon.com Inc.", "market": "US", "price": 224.18, "change_pct": 0.86},
    "TSLA": {"symbol": "TSLA", "name": "Tesla Inc.", "market": "US", "price": 428.53, "change_pct": -1.42},
    "META": {"symbol": "META", "name": "Meta Platforms Inc.", "market": "US", "price": 618.92, "change_pct": 1.24},
    "JPM": {"symbol": "JPM", "name": "JPMorgan Chase & Co.", "market": "US", "price": 246.75, "change_pct": 0.47},
}

US_NEWS_ITEMS: list[dict[str, Any]] = [
    {
        "category": "finance",
        "title": "US equities close mixed as tech leads gains",
        "summary": "Mega-cap tech names rallied on AI capex optimism while energy lagged crude weakness.",
        "keywords": ["S&P 500", "Technology", "AI capex"],
    },
    {
        "category": "domestic",
        "title": "Fed officials signal patience on rate path",
        "summary": "FOMC minutes highlight data-dependent stance; market pricing shifts toward fewer cuts.",
        "keywords": ["Fed", "Rates", "FOMC"],
    },
    {
        "category": "international",
        "title": "Global PMIs improve as Europe recovery firms",
        "summary": "Euro-area manufacturing beats expectations; dollar index eases from multi-week highs.",
        "keywords": ["Global PMI", "Europe", "Dollar"],
    },
    {
        "category": "company",
        "title": "NVIDIA unveils next-gen datacenter platform",
        "summary": "Management guides hyperscaler demand stronger than consensus; supply chain checks positive.",
        "keywords": ["NVIDIA", "Datacenter", "Earnings"],
    },
]

US_REPORTS: list[dict[str, Any]] = [
    {
        "id": 1,
        "title": "US Semiconductor Capex Cycle Update",
        "org": "Mock Research",
        "analyst": "Analyst A",
        "rating": "Overweight",
        "symbols": ["NVDA"],
        "pages": 30,
    },
    {
        "id": 2,
        "title": "Cloud Software Spend: Early Inflection",
        "org": "Mock Research",
        "analyst": "Analyst B",
        "rating": "Buy",
        "symbols": ["MSFT"],
        "pages": 24,
    },
    {
        "id": 3,
        "title": "Consumer Health amid Rate Uncertainty",
        "org": "Mock Research",
        "analyst": "Analyst C",
        "rating": "Neutral",
        "symbols": ["AMZN"],
        "pages": 16,
    },
]
