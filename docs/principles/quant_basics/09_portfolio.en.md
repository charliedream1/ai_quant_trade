# 09 Portfolio allocation and risk

**Goal:** Separate signal strength, target weights and actual positions. Prerequisites: [signals](07_signals.en.md), [execution](08_execution.en.md).

## Concepts and formulas

Allocation distributes capital; risk controls define acceptable exposure. Equal weights, inverse volatility and risk budgets require comparison of input stability, constraints and costs. Expected portfolio return is the weighted asset-return sum. Variance also depends on covariance, rather than the average of individual volatilities.

Constraints can limit assets, sectors, aggregate exposure, cash, stop losses and drawdown. Substrategies propose targets before netting and portfolio-level checks. Opposing substrategies do not each possess a separate copy of account cash.

## Synthetic examples

Raw scores 2 and 1 normalize to 2/3 and 1/3. With a 40% asset cap, clipping to 40% and 33.3% does not permit arbitrary redistribution back to the first asset. Follow the allocation policy or retain cash and record exposure.

Capital of 10,000, a 30% target and price 20 imply 150 units before lot-size, fees and cash constraints. Actual weights may be below 30%.

## Pitfalls

Gaps can prevent stop execution at the threshold. Risk parity is not equal returns, and multiple strategies can overlap heavily. Preserve risk evidence at target and execution stages.

## Exercise and answer

**Exercise:** Three substrategies each target 80% in one asset. May the account buy 240%?

**Answer:** Not by default. Define strategy budgets, net targets, then apply total exposure, single-asset and cash constraints. Do not assume leverage exists.
