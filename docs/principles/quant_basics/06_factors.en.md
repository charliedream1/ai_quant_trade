# 06 Factors and cross-sectional evaluation

**Goal:** Distinguish predictive factor evidence from executable returns. Prerequisites: [data](03_data.en.md), [statistics](05_statistics.en.md).

## Concepts and formulas

A factor describes an asset at a given time, such as past returns, valuation or volatility. Cross-sectional analysis compares assets on the same date; time-series analysis follows one asset through time. Preprocessing may include outlier treatment, missing values and normalization. Neutralization controls industry or size exposure and requires corresponding historical data.

IC correlates contemporaneous factor values with subsequent returns; RankIC compares ranks. ICIR commonly means mean IC / IC standard deviation; state any annualization. Return labels cannot enter monitoring before they mature. Coverage uses the selected parent universe as its denominator, not only successful responses.

## Synthetic example

Assets A/B/C have factor values 1/2/3 and subsequent returns 3%/2%/1%, giving RankIC = -1. Negating the factor reverses ranks, but direction must be chosen in research/training rather than after observing profits.

## Pitfalls

A strong IC on three stocks does not establish market-wide usefulness, and turnover costs can erase predictive gains. Bucket returns are diagnostics rather than automatically executable long/short portfolios. Qlib signal evaluation and model workflows are separate capabilities.

## Exercise and answer

**Exercise:** Of 100 parent-universe assets, only 60 are retrieved. What is coverage?

**Answer:** 60%, with reasons for the 40 failures. Do not use 60 as the denominator or assign zero returns to labels that have not matured.
