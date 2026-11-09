# 12 Paper trading, monitoring and review

**Goal:** Understand how research becomes an observable operating process. Prerequisites: [execution](08_execution.en.md), [portfolio risk](09_portfolio.en.md).

## Concepts

Paper trading checks calendars, data arrival, signals, risk, orders and cash bookkeeping. It cannot reproduce all liquidity and market impact. Live trading adds broker interfaces, permissions, market rules, failures and operating responsibility. A successful backend startup does not mean a strategy filled an order.

Monitor data freshness, failure rates, strategy versions, target/actual deviations, risk triggers, rejected orders and cash discrepancies. Missing data, unavailable models and absent signals are distinct states. Factor monitoring retains universes, coverage, dates and matured labels.

## Synthetic example and review

Starting cash is 10,000. A buy is rejected because the quantity fails the lot-size rule. Correct records show the rejected order and reason, no fill and unchanged cash. A signal alone must not create a position. If the browser times out, inspect the same run ID before submitting again.

Compare frozen parameters/data, node inputs/outputs, target/actual weights, orders, fills, costs, NAV and risk events. After fixes, retain failed evidence alongside verification rather than keeping successful screenshots only.

## Pitfalls

Paper success does not promise live returns. Weekdays are not a trading calendar. Simulated logs are not actual CLI execution. A cancellation request and actual process completion are different states and should be reported separately.

## Exercise and answer

**Exercise:** If a backtest response never reaches the page, should you click submit again?

**Answer:** Check the task ID and persistent status first. Wait or request cancellation if it is still running. Retry only after confirming completion and the failure reason, to avoid duplicates and inconsistent records.
