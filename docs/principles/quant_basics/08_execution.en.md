# 08 Backtest execution and bias

**Goal:** Reconcile signals → orders → fills → cash. Prerequisites: [signals](07_signals.en.md), [returns](04_returns.en.md).

## Concepts and formulas

A backtest applies information available at the time and explicit execution assumptions to history. An order expresses intent; a fill realizes it. Untouched limits, liquidity, lot size or insufficient cash can prevent fills. Daily OHLC cannot reproduce the full intraday path; conditions within one bar may have an uncertain order.

Buy cash debit = quantity × fill price + costs. Sell cash credit = quantity × fill price - costs. Net assets = cash + marked positions. State slippage, commissions, tax, distributions and suspension treatment; unmodeled items are not implicitly included.

## Synthetic example

With cash of 10,000, buying 100 shares at 10 with a 0.1% fee debits 1,001 and leaves 8,999. Selling all shares at 11 with the same fee credits 1,098.9, producing 10,097.9. Gross price profit is 100; net profit is 97.9.

## Pitfalls

Avoid future-close decisions at today's open, current membership in past universes, row-number alignment across dates and claims of old coverage from recent bars. Simple strategies use the simple engine, frozen compositions use composition, and Qlib workflows require separate data/configuration.

## Exercise and answer

**Exercise:** A January 5–16 request produces an October curve but says completed. Is that acceptable?

**Answer:** No. Actual dates must fall in the request interval and coverage must match a trading calendar. Retain failures and reasons rather than inventing bars.
