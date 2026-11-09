# 05 Statistics, volatility and drawdown

**Goal:** Read returns alongside uncertainty. Prerequisite: [returns](04_returns.en.md).

## Concepts and formulas

The mean describes location and standard deviation describes dispersion. Both depend on sample size and outliers. Annualized daily volatility commonly multiplies daily standard deviation by the square root of annual trading days, subject to stability assumptions. Sharpe usually divides mean excess return by standard deviation and adjusts frequency; state risk-free returns and annualization factors.

Drawdown = current NAV / previous running peak NAV - 1. Maximum drawdown is the deepest loss over the complete period and describes path risk. Correlation measures linear association, not causation or crisis stability. Align dated returns rather than correlating two rising price levels.

## Synthetic example

NAV of 100 → 120 → 90 → 108 has a peak of 120 and trough of 90: maximum drawdown is -25%, while final cumulative return is +8%. Profit and a deep interim drawdown can coexist.

Three identical returns of 1%, 1%, 1% have zero standard deviation. Display Sharpe as unavailable or explain the insufficient sample rather than awarding an infinitely good score.

## Pitfalls

Small samples, outliers, repeated trials and different frequencies can destabilize metrics. Radar charts compress information: inspect definitions, scaling and missing dimensions before treating area as a score.

## Exercise and answer

**Exercise:** Does high price-level correlation prove that diversification is ineffective?

**Answer:** No. Recompute with aligned returns and inspect sample periods and regimes. Shared price trends can create spurious correlation, and correlation alone does not capture tail risk.
