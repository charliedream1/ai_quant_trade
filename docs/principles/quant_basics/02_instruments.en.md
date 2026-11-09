# 02 Stocks, indexes and ETFs

**Goal:** Distinguish tradable assets from comparison series. Prerequisite: [research process](01_research.en.md).

## Concepts

A stock represents company equity. An index aggregates assets under construction rules and usually serves as an indicator or benchmark. An ETF is a tradable fund with share prices, NAV and a tracking objective. Index points are not executable ETF prices.

ETF prices can trade above or below NAV. Funds tracking the same index can differ in fees, liquidity, spreads and tracking error. Trading units, hours, limits, settlement and creation/redemption depend on market and product rules. Check exchange and fund notices for the study date rather than treating one market's rules as universal.

## Formula and synthetic example

Premium/discount = market price / contemporaneous reference NAV - 1. A price of 1.02 and NAV of 1.00 imply a 2% premium. If NAV is stale, the comparison also contains a timing difference.

Allocating 50% to each of two ETFs tracking the same index does not provide two independent risk sources. Examine underlying overlap and return correlation.

## Pitfalls

Integer symbols lose leading zeros; identical codes can identify different securities across markets. Index lists and tradable universes are different. An ETF cannot appear in a backtest before it was listed.

## Exercise and answer

**Exercise:** An index rises 1% while its ETF rises 0.8%. Must the data be wrong?

**Answer:** No. Align timestamps, return definitions, distributions and adjustments, then examine tracking error, premiums and fees. A single day cannot establish data or product quality.
