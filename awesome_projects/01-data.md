# Data

## Recommended Sources

- **[baostock](http://www.baostock.com)** — Free, no-registration A-share data (used by qlib).
  - Metadata: Stars: N/A (not GitHub) · License: See website · Maintenance: Check website
  - Docs/Homepage: http://www.baostock.com
  - Value: Practical free source for A-share historical data prototypes; validate coverage and latency before production use.
- **Wind** — Industry-authoritative paid data vendor.
  - Metadata: Stars: N/A (commercial vendor) · License: Commercial · Maintenance: Vendor-maintained
  - Docs/Homepage: https://www.wind.com.cn
  - Value: Institutional-grade paid data source; useful when compliance, coverage and support matter more than openness.

## Open-Source Data Libraries

- **[qlib](https://github.com/microsoft/qlib)** — Microsoft AI quant framework with Yahoo Finance data (China & US markets).
  - Metadata: Language: Python · Stars: 49,218 · License: MIT · Maintenance: Active (last push 2026-10-08)
  - Docs/Homepage: https://qlib.readthedocs.io/en/latest/
  - Value: Useful for evaluating data coverage, freshness and integration cost in the data layer.
- **[akshare](https://github.com/akfamily/akshare)** — Comprehensive crawler-based data library.
  - Metadata: Language: Python · Stars: 22,851 · License: MIT · Maintenance: Active (last push 2026-10-07)
  - Docs/Homepage: https://akshare.akfamily.xyz
  - Value: Useful for evaluating data coverage, freshness and integration cost in the data layer.
- **[efinance](https://github.com/Micro-sheep/efinance)** — Crawler-based data library (no market-index API).
  - Metadata: Language: Python · Stars: 4,078 · License: MIT · Maintenance: Active (last push 2026-07-17)
  - Docs/Homepage: -
  - Value: Useful for evaluating data coverage, freshness and integration cost in the data layer.
- **[adata](https://github.com/1nchaos/adata)** — A-share data library.
  - Metadata: Language: Python · Stars: 5,209 · License: APACHE-2.0 · Maintenance: Recent (last push 2025-12-26)
  - Docs/Homepage: https://adata.30006124.xyz
  - Value: Useful for evaluating data coverage, freshness and integration cost in the data layer.
- **[mootdx](https://github.com/mootdx/mootdx)** — TDX market data.
  - Metadata: Language: Python · Stars: 2,293 · License: MIT · Maintenance: Recent (last push 2024-07-16)
  - Docs/Homepage: -
  - Value: Useful for evaluating data coverage, freshness and integration cost in the data layer.
- **[easyquotation](https://github.com/shidenggui/easyquotation)** — Real-time Sina/Tencent quotes.
  - Metadata: Language: Python · Stars: 5,326 · License: MIT · Maintenance: Active (last push 2026-02-28)
  - Docs/Homepage: -
  - Value: Useful for evaluating data coverage, freshness and integration cost in the data layer.
- **[stock-api](https://github.com/zhangxiangliang/stock-api)** — Stock data API.
  - Metadata: Language: TypeScript · Stars: 1,963 · License: MIT · Maintenance: Active (last push 2026-10-11)
  - Docs/Homepage: https://zhangxiangliang.github.io/stock-api/
  - Value: Useful for evaluating data coverage, freshness and integration cost in the data layer.
- **[OpenBB](https://github.com/openbq-org/OpenBB)** — Open data platform for analysts, quants and AI agents; useful when data access, dashboards and agent workflows need a shared finance API surface.
  - Metadata: Language: Python · Stars: 74,092 · License: Other/Custom · Maintenance: Active (last push 2026-10-02)
  - Docs/Homepage: https://openbb.co
  - Value: Strong candidate for a unified financial data and analytics layer; review licensing before commercial use.

## Multimodal / Open Datasets

- **[stocknet-dataset](https://github.com/yumoxu/stocknet-dataset)** — 2-year price movements of 88 stocks with tweets & prices (Twitter + Yahoo Finance); paper "Stock Movement Prediction from Tweets and Historical Prices" (2018, Univ. of Edinburgh).
  - Metadata: Language: Unknown · Stars: 681 · License: MIT · Maintenance: Inactive (last push 2019-03-06)
  - Docs/Homepage: -
  - Value: Useful for evaluating data coverage, freshness and integration cost in the data layer.

## News Data

- **[Horizon](https://github.com/Thysrael/Horizon)** — Open-source AI-driven news radar: multi-source crawling (Hacker News, RSS, Reddit, Telegram, Twitter/X, GitHub, OpenBB), AI scoring, dedup, bilingual Markdown daily briefings.
  - Metadata: Language: Python · Stars: 9,550 · License: MIT · Maintenance: Active (last push 2026-10-04)
  - Docs/Homepage: https://www.horizon1123.top
  - Value: Useful for evaluating data coverage, freshness and integration cost in the data layer.
- **[Listed-company-news-crawl-and-text-analysis](https://github.com/DemonDamon/FinnewsHunter)** — Crawls listed-company news for text analysis and classification (SVM, random forest).
  - Metadata: Language: Python · Stars: 1,495 · License: APACHE-2.0 · Maintenance: Active (last push 2026-10-01)
  - Docs/Homepage: -
  - Value: Useful for evaluating data coverage, freshness and integration cost in the data layer.
- **[FinnewsHunter](https://github.com/DemonDamon/FinnewsHunter)** — Crawls financial news from Sina, Meijin, JRJ, CNStock, STCN for text analysis and classification.
  - Metadata: Language: Python · Stars: 1,495 · License: APACHE-2.0 · Maintenance: Active (last push 2026-10-01)
  - Docs/Homepage: -
  - Value: Useful for evaluating data coverage, freshness and integration cost in the data layer.

## Financial Data Sources

- **[FinRL-Meta](https://github.com/AI4Finance-Foundation/FinRL-Meta)** — A metaverse for financial deep reinforcement learning; dynamic market environments for stock, cryptocurrency, forex, paper/live trading, etc.
  - Metadata: Language: Python · Stars: 1,946 · License: MIT · Maintenance: Active (last push 2026-10-06)
  - Docs/Homepage: https://ai4finance.org
  - Value: Useful as a shortlist source for the Data Source layer; verify fit before production adoption.

- **[Tushare Python SDK](https://github.com/waditu/tushare)** — Crawling historical data of CN stocks.
  - Metadata: Language: Python · Stars: 15,421 · License: BSD-3-CLAUSE · Maintenance: Recent (last push 2024-03-13)
  - Docs/Homepage: https://tushare.pro/
  - Value: Useful as a Python access layer for Tushare data; verify token quota and licensing before production use.

- **[Tushare Pro](https://tushare.pro/)** — High-quality A-share data service with paid tiers.
  - Metadata: Stars: N/A (commercial data service) · License: Platform terms · Maintenance: Vendor-maintained
  - Docs/Homepage: https://tushare.pro/
  - Value: Useful as a paid A-share data option; verify quota, licensing and operational fit.

- **[yfinance](https://github.com/ranaroussi/yfinance)** — Provide market historical data, easy to connect and use.
  - Metadata: Language: Python · Stars: 25,485 · License: APACHE-2.0 · Maintenance: Active (last push 2026-10-06)
  - Docs/Homepage: https://ranaroussi.github.io/yfinance
  - Value: Useful as a shortlist source for the Data Source layer; verify fit before production adoption.

- **[WRDS](https://github.com/wharton/wrds)** — A Python data access library for academic usage.
  - Metadata: Language: Python · Stars: 160 · License: BSD-3-CLAUSE · Maintenance: Active (last push 2026-02-11)
  - Docs/Homepage: http://wrds.wharton.upenn.edu/
  - Value: Useful as a shortlist source for the Data Source layer; verify fit before production adoption.

- **[FinanceDatabase](https://github.com/JerBouma/FinanceDatabase)** — Database of symbols: Equities, ETFs, Funds, Indices, Currencies, Cryptocurrencies and Money Markets.
  - Metadata: Language: Python · Stars: 9,455 · License: MIT · Maintenance: Active (last push 2026-10-11)
  - Docs/Homepage: https://www.jeroenbouma.com/projects/financedatabase
  - Value: Useful for maintaining cross-asset symbol universes; validate coverage and update cadence before adoption.

- **[jqdatasdk](https://github.com/JoinQuant/jqdatasdk)** — JoinQuant data API (3-month free trial; good quality for live use).
  - Metadata: Language: Python · Stars: 1,208 · License: MIT · Maintenance: Active (last push 2026-01-29)
  - Docs/Homepage: https://www.joinquant.com/
  - Value: Useful as a shortlist source for the Data layer; verify fit before production adoption.

## Time-Series Databases

- **[qlib-server](https://github.com/microsoft/qlib-server)** — Qlib data server system (online mode, shared data service).
  - Metadata: Language: Python · Stars: 394 · License: MIT · Maintenance: Recent (last push 2025-12-18)
  - Docs/Homepage: -
  - Value: Useful as a shortlist source for the Data layer; verify fit before production adoption.

- **[arctic](https://github.com/man-group/arctic)** — High-performance datastore for time series and tick data (MongoDB + Python).
  - Metadata: Language: Python · Stars: 3,087 · License: LGPL-2.1 · Maintenance: Recent (last push 2024-04-09)
  - Docs/Homepage: https://arctic.readthedocs.io/en/latest/
  - Value: Useful as a shortlist source for the Data layer; verify fit before production adoption.

- **[kairosdb](https://github.com/kairosdb/kairosdb)** — Cassandra-based time series database.
  - Metadata: Language: Java · Stars: 1,761 · License: APACHE-2.0 · Maintenance: Active (last push 2026-03-06)
  - Docs/Homepage: -
  - Value: Useful as a shortlist source for the Data layer; verify fit before production adoption.

- **[opentsdb](https://github.com/OpenTSDB/opentsdb)** — HBase-based time series database.
  - Metadata: Language: Java · Stars: 5,064 · License: LGPL-2.1 · Maintenance: Recent (last push 2024-12-13)
  - Docs/Homepage: http://opentsdb.net
  - Value: Useful as a shortlist source for the Data layer; verify fit before production adoption.
