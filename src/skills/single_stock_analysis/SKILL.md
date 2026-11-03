---
name: stock-analysis
description: Analyze stocks and cryptocurrencies using Yahoo Finance data. Supports portfolio management, watchlists with alerts, dividend analysis, 8-dimension stock scoring, viral trend detection (Hot Scanner), and rumor/early signal detection. Use for stock analysis, portfolio tracking, earnings reactions, crypto monitoring, trending stocks, or finding rumors before they hit mainstream.
description_zh: "股票与加密货币分析（8维评分、组合管理、趋势扫描、传闻探测）"
description_en: "Stock & crypto analysis with 8-dim scoring, portfolio, trend & rumor scanning"
version: 6.2.1
homepage: https://finance.yahoo.com
metadata:
  clawdbot:
    emoji: "\U0001F4C8"
    requires:
      bins:
        - uv
      env: []
    install:
      - id: uv-brew
        kind: brew
        formula: uv
        bins:
          - uv
        label: Install uv (brew)
commands:
  - /stock - Analyze a stock or crypto (e.g., /stock AAPL)
  - /stock_compare - Compare multiple tickers
  - /stock_dividend - Analyze dividend metrics
  - /stock_watch - Add/remove from watchlist
  - /stock_alerts - Check triggered alerts
  - /stock_hot - Find trending stocks & crypto (Hot Scanner)
  - /stock_rumors - Find early signals, M&A rumors, insider activity (Rumor Scanner)
  - /portfolio - Show portfolio summary
  - /portfolio_add - Add asset to portfolio
display_name: "Stock Analysis"
display_name_en: "Stock Analysis"
visibility: "public"
---

# Stock Analysis v6.1

Analyze US stocks and cryptocurrencies with 8-dimension analysis, portfolio management, watchlists, alerts, dividend analysis, and **viral trend detection**.

## What's New in v6.2

- 🔮 **Rumor Scanner** — Early signals before mainstream news
  - M&A rumors and takeover bids
  - Insider buying/selling activity
  - Analyst upgrades/downgrades
  - Twitter/X "hearing that...", "sources say..." detection
- 🎯 **Impact Scoring** — Rumors ranked by potential market impact

## What's in v6.1

- 🔥 **Hot Scanner** — Find viral stocks & crypto across multiple sources
- 🐦 **Twitter/X Integration** — Social sentiment via bird CLI
- 📰 **Multi-Source Aggregation** — CoinGecko, Google News, Yahoo Finance
- ⏰ **Cron Support** — Daily trend reports

## What's in v6.0

- 🆕 **Watchlist + Alerts** — Price targets, stop losses, signal changes
- 🆕 **Dividend Analysis** — Yield, payout ratio, growth, safety score
- 🆕 **Fast Mode** — `--fast` skips slow analyses (insider, news)
- 🆕 **Improved Performance** — `--no-insider` for faster runs

## Quick Commands

### Stock Analysis
```bash
# Basic analysis
uv run {baseDir}/scripts/analyze_stock.py AAPL

# Fast mode (skips insider trading & breaking news)
uv run {baseDir}/scripts/analyze_stock.py AAPL --fast

# Compare multiple
uv run {baseDir}/scripts/analyze_stock.py AAPL MSFT GOOGL

# Crypto
uv run {baseDir}/scripts/analyze_stock.py BTC-USD ETH-USD
```

### Dividend Analysis (NEW v6.0)
```bash
# Analyze dividends
uv run {baseDir}/scripts/dividends.py JNJ

# Compare dividend stocks
uv run {baseDir}/scripts/dividends.py JNJ PG KO MCD --output json
```

**Dividend Metrics:**
- Dividend Yield & Annual Payout
- Payout Ratio (safe/moderate/high/unsustainable)
- 5-Year Dividend Growth (CAGR)
- Consecutive Years of Increases
- Safety Score (0-100)
- Income Rating (excellent/good/moderate/poor)

### Watchlist + Alerts (NEW v6.0)
```bash
# Add to watchlist
uv run {baseDir}/scripts/watchlist.py add AAPL

# With price target alert
uv run {baseDir}/scripts/watchlist.py add AAPL --target 200

# With stop loss alert
uv run {baseDir}/scripts/watchlist.py add AAPL --stop 150

# Alert on signal change (BUY→SELL)
uv run {baseDir}/scripts/watchlist.py add AAPL --alert-on signal

# View watchlist
uv run {baseDir}/scripts/watchlist.py list

# Check for triggered alerts
uv run {baseDir}/scripts/watchlist.py check
uv run {baseDir}/scripts/watchlist.py check --notify  # Telegram format

# Remove from watchlist
uv run {baseDir}/scripts/watchlist.py remove AAPL
```

**Alert Types:**
- 🎯 **Target Hit** — Price >= target
- 🛑 **Stop Hit** — Price <= stop
- 📊 **Signal Change** — BUY/HOLD/SELL changed

### Portfolio Management
```bash
# Create portfolio
uv run {baseDir}/scripts/portfolio.py create "Tech Portfolio"

# Add assets
uv run {baseDir}/scripts/portfolio.py add AAPL --quantity 100 --cost 150
uv run {baseDir}/scripts/portfolio.py add BTC-USD --quantity 0.5 --cost 40000

# View portfolio
uv run {baseDir}/scripts/portfolio.py show

# Analyze with period returns
uv run {baseDir}/scripts/analyze_stock.py --portfolio "Tech Portfolio" --period weekly
```

### 🔥 Hot Scanner (NEW v6.1)
```bash
# Full scan - find what's trending NOW
python3 {baseDir}/scripts/hot_scanner.py

# Fast scan (skip social media)
python3 {baseDir}/scripts/hot_scanner.py --no-social

# JSON output for automation
python3 {baseDir}/scripts/hot_scanner.py --json
```

**Data Sources:**
- 📊 CoinGecko Trending — Top 15 trending coins
- 📈 CoinGecko Movers — Biggest gainers/losers
- 📰 Google News — Finance & crypto headlines
- 📉 Yahoo Finance — Gainers, losers, most active
- 🐦 Twitter/X — Social sentiment (requires auth)

**Output:**
- Top trending by mention count
- Crypto highlights with 24h changes
- Stock movers by category
- Breaking news with tickers

**Twitter Setup (Optional):**
1. Install bird: `npm install -g @steipete/bird`
2. Login to x.com in Safari/Chrome
3. Create `.env` with `AUTH_TOKEN` and `CT0`

### 🔮 Rumor Scanner (NEW v6.2)
```bash
# Find early signals, M&A rumors, insider activity
python3 {baseDir}/scripts/rumor_scanner.py
```

**What it finds:**
- 🏢 **M&A Rumors** — Merger, acquisition, takeover bids
- 👔 **Insider Activity** — CEO/Director buying/selling
- 📊 **Analyst Actions** — Upgrades, downgrades, price target changes
- 🐦 **Twitter Whispers** — "hearing that...", "sources say...", "rumor"
- ⚖️ **SEC Activity** — Investigations, filings

**Impact Scoring:**
- Each rumor is scored by potential market impact (1-10)
- M&A/Takeover: +5 points
- Insider buying: +4 points
- Upgrade/Downgrade: +3 points
- "Hearing"/"Sources say": +2 points
- High engagement: +2 bonus

**Best Practice:** Run at 07:00 before US market open to catch pre-market signals.

## Analysis Dimensions (8 for stocks, 3 for crypto)

### Stocks
| Dimension | Weight | Description |
|-----------|--------|-------------|
| Earnings Surprise | 30% | EPS beat/miss |
| Fundamentals | 20% | P/E, margins, growth |
| Analyst Sentiment | 20% | Ratings, price targets |
| Historical | 10% | Past earnings reactions |
| Market Context | 10% | VIX, SPY/QQQ trends |
| Sector | 15% | Relative strength |
| Momentum | 15% | RSI, 52-week range |
| Sentiment | 10% | Fear/Greed, shorts, insiders |

### Crypto
- Market Cap & Category
- BTC Correlation (30-day)
- Momentum (RSI, range)

## Sentiment Sub-Indicators

| Indicator | Source | Signal |
|-----------|--------|--------|
| Fear & Greed | CNN | Contrarian (fear=buy) |
| Short Interest | Yahoo | Squeeze potential |
| VIX Structure | Futures | Stress detection |
| Insider Trades | SEC EDGAR | Smart money |
| Put/Call Ratio | Options | Sentiment extreme |

## Risk Detection

- ⚠️ **Pre-Earnings** — Warns if < 14 days to earnings
- ⚠️ **Post-Spike** — Flags if up >15% in 5 days
- ⚠️ **Overbought** — RSI >70 + near 52w high
- ⚠️ **Risk-Off** — GLD/TLT/UUP rising together
- ⚠️ **Geopolitical** — Taiwan, China, Russia, Middle East keywords
- ⚠️ **Breaking News** — Crisis keywords in last 24h

## Performance Options

| Flag | Effect | Speed |
|------|--------|-------|
| (default) | Full analysis | 5-10s |
| `--no-insider` | Skip SEC EDGAR | 3-5s |
| `--fast` | Skip insider + news | 2-3s |

## Supported Cryptos (Top 20)

BTC, ETH, BNB, SOL, XRP, ADA, DOGE, AVAX, DOT, MATIC, LINK, ATOM, UNI, LTC, BCH, XLM, ALGO, VET, FIL, NEAR

(Use `-USD` suffix: `BTC-USD`, `ETH-USD`)

## Data Storage

| File | Location |
|------|----------|
| Portfolios | `~/.clawdbot/skills/stock-analysis/portfolios.json` |
| Watchlist | `~/.clawdbot/skills/stock-analysis/watchlist.json` |

## Limitations

- Yahoo Finance may lag 15-20 minutes
- Short interest lags ~2 weeks (FINRA)
- Insider trades lag 2-3 days (SEC filing)
- US markets only (non-US incomplete)
- Breaking news: 1h cache, keyword-based

## Disclaimer

⚠️ **NOT FINANCIAL ADVICE.** For informational purposes only. Consult a licensed financial advisor before making investment decisions.
