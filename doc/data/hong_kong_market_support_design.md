# Hong Kong market research and backtesting support

Date: 2026-11-12. Status: confirmed and implemented for HKD ordinary-equity research; availability limits are documented in the usage guide.

## Findings

The current data router supports CN and US only. Unknown market values, including
HK, normalize to CN. The ticker parser accepts six-digit mainland codes; the
security master, mock provider and market switcher contain two-market branches.
The real mainland provider cannot safely serve Hong Kong requests. Execution
defaults contain a single lot size, fixed tick and mainland assumptions. These
are functional gaps rather than a missing market label.

Installed AKShare 1.18.83 exposes stock_hk_hist and stock_hk_spot_em. Reuse the
tested dependency baseline rather than upgrading packages before verifying it.
Existing uncommitted changes in ETF/backtest/composition code must be preserved.

## Initial supported workflow

Add a separate HK market with stock lookup, names, watchlists/resource pools,
quotes, daily/weekly/monthly history, applicable price adjustments, charts,
technical stock analysis, and research backtests/paper workflows. Historical
observations retain actual coverage, source, retrieval time, adjustment and unit
metadata. Public quotes are not promised to be exchange-grade real-time feeds.

Start with HKD-denominated ordinary cash equities. Hong Kong-listed ETFs may
use the same workflow only when instrument type, trading units and applicable
fee exemptions are explicitly available; ambiguous products are not treated as
ordinary shares. Derivatives, margin/short trading, mixed-currency portfolios,
RMB dual counters and live broker execution are separate capabilities. Stock
Connect eligibility, quota and mainland investor taxes are not inferred from
Hong Kong listing status.

## Identity, routing and isolation

Use a canonical qualified identifier such as 00700.HK. Accept common HK-prefixed
and HK-suffixed forms and five-digit codes in an explicit HK context, preserving
leading zeros. Keep existing mainland identities stable and reject conflicting
market/code combinations. Do not infer Hong Kong membership from a mainland
six-digit code. Include market in cache, catalogue, resource and task identity;
audit symbol-only uniqueness constraints before migrations.

Add HK aliases and reject invalid markets instead of silently routing them to
CN. Propagate market explicitly through REST/CLI, task snapshots and background
execution. Switching one browser's market must not silently mutate another
request's market. Existing CN/US behavior needs regression coverage.

## Data adapter

Implement a small Hong Kong-specific adapter rather than adding more unrelated
branches to the large mainland provider. Prefer current tested AKShare/Eastmoney
HK quote and history interfaces; use independently verified alternatives where
available. Centralize endpoints, timeouts, request limits and source mappings in
YAML. Do not alter installed dependencies or hide failures behind synthetic data.

Normalize timezone, currency, traded quantity units, turnover and price adjustment
before data enters shared analytics. Display unavailable fundamentals, news or
industry data explicitly; never substitute A-share records or generated values.
Research and financial-statement components must advertise actual HK capability
and reject unsupported A-share-only queries. Real-data checks must verify source
and units, not merely an HTTP success code.

## Execution and accounting

Use HKD-labelled single-market cash accounting and Asia/Hong_Kong timestamps.
Use the Hong Kong exchange calendar and sessions, including partial days where
supported; do not reuse mainland public-holiday helpers. Historical market data
dates constrain execution and no missing sessions are fabricated.

Resolve board lots by security and applicable date; unknown lots require an
explicit research assumption or block strict execution. Resolve price ticks
from date-effective price bands, with correct boundary rounding. Same-day sale
eligibility and clearing/cash settlement are separate concepts; do not map T+2
clearing onto a two-day prohibition on selling purchased shares. This daily-bar
workflow does not claim to simulate intraday trading, auctions, VCM or queueing.

Store dated fee components separately, including stamp duty, exchange trading
fee, SFC/AFRC levies, applicable settlement charges and editable broker commission.
Respect component-specific rounding, minimums, effective dates and product
exemptions. Current rates must not be applied indiscriminately to earlier periods.
Do not reuse the mainland single tax-rounding rule for Hong Kong stamp duty.
Expose the effective execution assumptions and currency in preview/results.

Use strict checks for unavailable historical trading status, corporate actions,
lots or ticks. Research mode may use clearly disclosed assumptions; price
adjustment does not establish complete corporate-action cash accounting. Show
unsupported engine/strategy combinations explicitly rather than claiming all
existing mainland workflows are Hong Kong-ready.

## UI, API and documentation

Add Hong Kong to both shell and embedded market switchers, persist selection and
propagate it to stock search, resource pools, watchlists, technical analysis and
backtest forms. Prevent misleading RMB amounts in HKD workflows. Market/model
identifiers remain stable when UI language changes. User-facing availability
states explain missing HK capabilities without implementation details.

Document setup, accepted symbols, price/volume units, fees, supported research
flows and data limitations in English. Update README, market/data/execution
guides and monthly weekly changelog. Keep secrets in local dotenv and runtime
downloads/evidence on the E drive.

## Validation and acceptance

- Unit checks: aliases, identifier ambiguity, leading zeros, cache separation,
  source field mapping, share/lot volume units, dated lot/tick selection, tick
  boundaries, per-component fee rounding, market sessions and missing data.
- Integration: explicit HK REST/CLI/task requests, watchlist/resource persistence,
  technical analysis, ordinary cash-equity backtest and unsupported capability
  errors. Include existing CN/US regression and source-failure tests.
- Actual acceptance: obtain several liquid HK securities with actual HKD quotes
  and dated histories, then run a deterministic strategy over a documented
  historical interval. Compare the frozen input snapshot, signals, fills, fees,
  holdings and net asset value with an independent reference calculation.
- Browser checks: CN/HK/US round trips, symbol search, charts, execution previews,
  backtest result/currency and persistence. Check cold/warm request latency using
  identical snapshots and label public-source outages honestly.
- Run applicable pytest, Ruff/format, mypy, secret/dependency checks and both
  strict documentation builds. Record unavailable tools without claiming success.
  Stop owned services; preserve unrelated edits and local memories.

## Primary sources inspected

- Installed AKShare 1.18.83 public stock_hk_hist and stock_hk_spot_em interfaces.
- https://github.com/akfamily/akshare
- https://www.hkex.com.hk/Global/Exchange/FAQ/Securities-Market/Trading?sc_lang=en
- https://www.hkex.com.hk/Services/Trading/Securities/Overview/Trading-Mechanism?sc_lang=en
- https://www.hkex.com.hk/services/rules-and-forms-and-fees/fees/securities-%28hong-kong%29/trading/transaction?sc_lang=en
- https://www.hkex.com.hk/Services/Settlement-and-Depository/T1-Settlement-for-the-Hong-Kong-Cash-Market?sc_lang=en

Recheck dated rules, trading units and source availability during implementation.
Current operational rules are not historical execution evidence.
