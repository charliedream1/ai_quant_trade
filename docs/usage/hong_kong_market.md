# Hong Kong stocks: quotes, technical research and HKD accounts

## Supported workflow

Select **Hong Kong** in the top market switcher. REST and CLI requests use market
`HK`; the API accepts `X-AIQuant-Market: HK`, and the CLI accepts `--market HK`.
The browser persists its market independently of interface language. Gradio
callbacks carry their own market header and restore their previous request
context when the callback completes or fails.

Accepted equity identifiers include `00700.HK`, `HK00700`, `00700` and `700.HK`.
They normalize to `00700.HK`, preserving leading zeros and remaining distinct
from mainland six-digit identifiers. Initial name lookup includes Tencent and
HSBC from the public example security catalogue; other valid codes can be queried
directly. Existing catalogues receive missing HK seed entries without replacing
user rows. This is not a complete exchange security-master feed.

The real provider supports public quotes, Hang Seng/China Enterprises index
quotes, daily/weekly/monthly bars and available unadjusted/forward/backward
adjustments. Each response identifies its actual source, currency, timestamp,
adjustment and volume unit. Quotes are public-feed observations, not guaranteed
exchange-grade real-time data. No CN data or synthetic bars replace a failed HK
real-data request. Explicit mock mode uses separate, labelled HK development
fixtures under `egs/examples/data/hong_kong_mock.yaml`.

Individual-stock analysis shows K-lines, moving averages and observed-period
returns. Missing fundamental statements, news, sector data, composite scores and
automatic recommendations are not fabricated or replaced by mainland records.
Existing macro/fundamental research recipes remain A-share-specific. Paper search
is a global capability, independent of the selected equity market.

## Research backtests

Use the ordinary `simple` engine with explicit HK symbols and dates. The engine
uses actual dated HK observations and freezes market, execution settings and
relevant rule-file hashes into its experiment snapshot. Changing the current UI
market after creating a task does not change its data routing.

The HK execution profile is selected automatically for an HK ordinary backtest,
or explicitly by choosing **Hong Kong HKD cash equities** in the shared execution
panel. Under **Advanced execution overrides**, provide `instruments` with dated
board-lot metadata. The following YAML shows the corresponding request shape;
adapt identifiers, dates and source evidence to your experiment:

```yaml
market: HK
execution_costs:
  profile: hk_cash
  instruments:
    00700.HK:
      from: '2026-10-01'
      to: '2026-12-31'
      lot_size: 100
      currency: HKD
      asset_type: stock
      source: Explicit research assumption; replace with dated source evidence
      assumption: true
```

The UI's advanced editor accepts the same `execution_costs` fields as a JSON
object, without the outer `market` and `execution_costs` wrappers. Its market comes
from the page selection. `egs/examples/data/hong_kong_acceptance.yaml` is an
executable acceptance configuration using explicit research assumptions, not an
authoritative historical board-lot dataset.

Board lots are resolved per security and date. Missing metadata blocks execution;
the engine does not assume all HK securities trade in 100-share lots. Broker
commission/minimum commission and slippage remain editable. Statutory charges,
ticks and sale eligibility come from dated HK rules; contradictory generic
tax/tick/lot/settlement overrides are rejected rather than silently ignored.

Rules currently cover ordinary HKD cash equities from 2023-11-17. Stamp duty is
rounded upward to an HK dollar while regulatory components are individually
rounded to cents. The model distinguishes SFC, AFRC, exchange trading and
settlement charges. Its settlement-fee schedule changes on 2025-06-30; stock
spread tables change on 2025-08-04 and 2026-08-03. Rule definitions and sources
are in `egs/config/strategies/hong_kong_execution.yaml` and are frozen in resolved
execution settings. Broker commission that already includes regulatory charges
can exclude the additional SFC/AFRC/trading components.

Fees accumulate per external order/day in this research ledger. That aggregation
does not reconstruct a broker's actual contract-note grouping or clearing trade
allocation. Bid/ask queues, auctions, volatility-control interruptions, odd-lot
execution and corporate-action cash flows are not reconstructed from daily bars.

Hong Kong sale eligibility is distinct from clearing settlement. The model
allows same-session sale eligibility; it does not impose an A-share one-day
restriction or misinterpret T+2 clearing as a two-day resale prohibition.
Broker cash availability and T+2 clearing cash movements are not simulated.

The configured HKEX calendar covers 2026 public holidays and identifies half-day
sessions, using Asia/Hong_Kong time. Date-bounded history is checked against those
sessions; missing observations stop the run. Older years are explicitly marked
as unverified calendar coverage in research results. No mainland holiday helper
or fabricated weekday bars fill real-data gaps.

Strict execution rejects assumed metadata and missing historical trading status
or corporate-action evidence. Changing a flag does not establish those facts.
The verified workflow is research mode with disclosed assumptions.

## HKD paper accounts

Create a paper account under HK with the same `execution_costs` metadata in its
API request. Market, HKD currency and resolved rules are saved with the account.
Orders use canonical symbols, dated tick/lot checks, HK fees and same-session
sale availability. Changing the UI market later does not change the account.
Existing legacy accounts default to CN/CNY through an additive migration.

The current paper-account form does not collect per-security historical trading
units. Supply them through the account-create API; an unconfigured account refuses
HK fills instead of using a guessed lot. Paper accounts are research simulations
and do not send broker orders.

## Availability limits

This release does not enable HK broker execution, margin/short trading, derivatives,
RMB/USD dual counters, mixed-currency portfolios or Stock Connect eligibility and
tax processing. HK-listed ETF market observations may be available by code, but
ETF execution is rejected until its product-specific tick table and exemptions
are supported; do not relabel an ETF as an ordinary share.

Current public catalogue metadata cannot establish historical trading units.
Use dated evidence for historical claims. A price adjustment series is not a
complete dividend/corporate-action account ledger.

## Actual acceptance on 2026-11-12

Real Tencent and HSBC quotes, actual dated Tencent/Eastmoney history and Hang
Seng/China Enterprises index observations were obtained. A two-security strategy
using 20 sessions in October 2026 produced four fills. An independent Decimal
calculation matched each price, quantity, fee, cash balance, daily holding and
daily NAV within HKD 0.01.

| Item | Result |
| --- | --- |
| Initial cash | HKD 500,000.00 |
| Final cash/NAV | HKD 478,815.84 |
| Execution fees | HKD 624.16 |
| Net P&L | HKD -21,184.16 |
| Net return | -4.236832% |

The strategy intentionally exercised buying and final liquidation; this loss is
an accounting/behavior check, not a profitable-strategy claim. Lot metadata was
explicitly supplied as acceptance research assumptions. A corrected-source run
completed in approximately 1.8 seconds after input retrieval/cache preparation;
that is not an end-to-end network-latency guarantee.

Browser tests used explicit HK fixtures for market round trips, stock analysis
and persistence. Separate actual-data acceptance is in
`tests/engine/test_hong_kong_live.py`; enable it with `HK_LIVE=1` and set a private
E-drive `HK_LIVE_OUTPUT` directory. Default tests never require public sources.
Private snapshots and full ledgers are retained outside Git on the E drive.

## Browser verification on 2026-11-13

An actual browser session queried Tencent through the real public provider,
rendered its K-line, kept HK selected after language changes and reload, and
opened the HKD execution preview. Final layout checks also ran against an isolated
commit snapshot with explicitly labelled HK fixtures. Screenshots exposed and
helped fix a narrow-screen sidebar overlay and technical-indicator translation
and precision artifacts. At 390 pixels the navigation now collapses automatically
and the HK market button remains accessible. Monetary control labels follow the
selected HKD cost profile.

The public-source flow passed once end to end; a subsequent attempt failed to
return the stock summary within its test deadline. That attempt is retained as
failed, and does not establish continuous upstream availability. Final UI layout
checks with deterministic fixtures passed separately. The application must keep
provider failures explicit rather than replacing real data with fixtures.

Screenshots and browser-check records remain in the private E-drive verification
directory and are excluded from the commit.

## Official references

- [HKEX trading and board lots](https://www.hkex.com.hk/Global/Exchange/FAQ/Securities-Market/Trading?sc_lang=en)
- [Trading charges and rounding](https://www.hkex.com.hk/services/rules-and-forms-and-fees/fees/securities-%28hong-kong%29/trading/transaction?sc_lang=en)
- [Settlement-fee restructuring](https://www.hkex.com.hk/News/Market-Communications/2025/250221news?sc_lang=en)
- [Dated minimum-spread reductions](https://www.hkex.com.hk/Services/Trading/Securities/Overview/Trading-Mechanism/Reduction-of-Minimum-Spreads?sc_lang=en)
- [2026 HK securities calendar](https://www.hkex.com.hk/-/media/HKEX-Market/Services/Circulars-and-Notices/Participant-and-Members-Circulars/SEHK/2025/ce_SEHK_CT_075_2025.pdf)

Current rules and published fee changes must not be generalized to unsupported
historical dates or investor-specific broker arrangements.
