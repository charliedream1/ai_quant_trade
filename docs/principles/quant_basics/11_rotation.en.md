# 11 ETF and sector rotation

**Goal:** Build an inspectable rotation study. Prerequisites: [ETFs](02_instruments.en.md), [allocation](09_portfolio.en.md), [model tests](10_models.en.md).

## Concepts

ETF rotation reallocates among tradable funds. Sector rotation additionally requires dated classifications, historical members and a tradable implementation. Index research, ETF trading and current sector membership are different. Examine overlapping exposures, volume, spreads and listing dates.

Common research rules include momentum ranks, trend filters, volatility adjustments and defensive switches. Rules, models and Agent review can form cascades or parallel scores, but must retain a common universe, score definitions, frozen versions and stage evidence.

## Synthetic example

Three ETFs have window returns of 6%, 4%, -1% and annualized volatility estimates of 20%, 10%, 8%. Momentum chooses the first. Crude return/volatility scores of 0.30, 0.40, -0.125 put the second first. These answer different questions; do not select whichever won after observing outcomes.

## Pitfalls

Do not backfill fashionable ETFs into periods before listing, treat same-sector funds as independent diversification, equate flow proxies with real institutional holdings, or let today's news explain a past decision. Explicit limits are more reliable than invented history.

## Exercise and answer

**Exercise:** An ETF lists in July. May it remain in a January–June universe using index prices as fills?

**Answer:** Not without a separately stated proxy study. Index research must disclose its nontradable assumptions; actual ETF backtests start from tradable dates and use historical universes.
