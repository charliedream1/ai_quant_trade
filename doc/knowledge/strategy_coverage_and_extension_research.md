# Strategy Coverage and Industry Extension Research

Reviewed on 2026-11-04. Scope: the integrated platform under `src`, its `egs` entry points and documented public methods used by index providers, asset managers and exchanges. This is a coverage assessment and proposed roadmap, not implementation approval or a statement of expected investment returns. No strategy source was modified.

This is the baseline survey recorded before implementation approval. The subsequently approved delivery is described in [Strategy Extensions and Evidence Design](../strategies/strategy_extensions_implementation_design.md) and [published strategy methods](../../docs/principles/strategy_methods.md); those documents distinguish implemented paths from later derivative projects.

The review preserves the existing uncommitted README-placement correction. New research documentation uses English. Public sources establish that the method families are used or studied in the industry; they do not establish a market-share ranking, a currently profitable trade or production readiness of this repository.

## Current coverage

| Strategy family | Actual integrated capability | Remaining boundary |
| --- | --- | --- |
| ETF relative-strength rotation | Delayed historical-return ranking, configurable lookback/top selection/rebalance interval, parameter profiles and backtest evidence | Standalone examples emit fixed-quantity intents. A complete allocation recipe needs explicit target weights, cash alternatives, turnover control and universe enforcement |
| ETF trend allocation | Delayed moving-average filter and ETF strategy metadata | A single trend rule does not establish cross-asset tactical allocation or a managed-futures strategy |
| Sector rotation | A legacy relative-strength proxy example and a composition filter that ranks sector groups from supplied stocks | The composition strategy needs dated industry classifications. The legacy example has a reproduced within-day order dependence; neither path establishes earnings-driven or macro-cycle sector rotation |
| Portfolio allocation | Equal/score weights, inverse volatility, ERC, HRP and shrinkage minimum variance; fixed or inverse-volatility sleeve budgets | These are existing reusable estimators. The shipped ETF pools do not supply a complete stock/bond/gold/cash allocation. HRP/ERC is not a reproduction of Bridgewater's All Weather portfolio |
| Volatility and drawdown controls | Correlation/sector/asset-class caps, drawdown reductions and covariance-based volatility scaling | Current volatility scaling only reduces exposure above a limit. It is not a complete target-volatility mandate with cash yield, financing and optional leverage |
| Trend and mean reversion | Moving averages, MACD, momentum/volume, Donchian and related rules; RSI/Bollinger reversion recipes | These are directional daily rules, not two-leg statistical arbitrage, market neutrality or exchange market making |
| Equity factors and machine learning | Price/volume factor panels, lagged-label research, equal/ICIR aggregation, LightGBM/XGBoost/MLP paths | Financial value, dividend sustainability, profitability quality and earnings revisions are not registered factor operators. Model availability does not add those missing inputs |
| Macro regimes and fundamental analysis | PIT-imported regime research plus current-version macro/company evidence and reports | Current public financial and macro snapshots remain `historical_pit_eligible: false`. Analysis/report pages are not automatically connected to a tradable, historically valid factor or timing strategy |
| Strategy combinations | Nested sleeves, target netting, one market-cost charge and shared risk checks | Requires independently validated sleeves and benchmarks; combining correlated rules does not establish new alpha |

Primary implementation references:

- [ETF rotation example](../../egs/examples/strategy_examples/etf_momentum_rotation_strategy.py) and [ETF trend example](../../egs/examples/strategy_examples/etf_trend_allocation_strategy.py).
- [Legacy industry example](../../egs/examples/strategy_examples/industry_rotation_strategy.py), [industry composition recipe](../../egs/examples/strategy_pipelines/industry_rotation.yaml), [batch industry rules](../../src/strategy/components/rules.py) and [classification preflight](../../src/engine/composition/preflight.py).
- [ETF pools](../../egs/config/strategies/etf_universes.yaml), [ETF allocation recipe](../../egs/examples/strategy_pipelines/etf_allocation.yaml), [portfolio estimators](../../src/portfolio/allocation.py) and [risk policy](../../src/risk/policies.py).
- [Price/volume factor catalog](../../egs/config/strategies/factor_research.yaml), [execution capability checks](../../src/engine/execution/policy.py) and [current economic evidence](../../src/engine/economics/service.py).

The configured `cn_core` pool contains four A-share broad-market ETFs; `cn_sector` contains four sector/theme ETFs. Thus, the recipe named multi-asset allocation currently defaults to equity ETFs. Its name does not prove exposure to independent bond, gold or cash assets. Fund expense fields in the example configuration also need source/date verification before operational comparisons.

Legacy material such as [standalone equity momentum rotation](../../egs_trade/vanilla/momentum_rotation/README.md) and portfolio-optimization notebooks exists elsewhere in the repository. It is separate from an integrated platform recipe and must not be counted as an available UI/API/live capability without explicit integration and acceptance.

## Reproduced legacy-sector issue

`IndustryRotationStrategy.on_bar()` appends the current security's bar before comparing it with securities whose current-day bar may not yet have arrived. A deterministic probe warmed two securities at equal prices, then supplied gains of 10% and 20% on the same date. Reversing the arrival order changed the weaker security's intent from buy to sell. The original order emitted two buy intents despite a top-one ranking.

This finding concerns the legacy example, not an assertion that the separate composition batch implementation has the same defect. The discovery is preserved locally in `docs/audit/strategy_coverage_2026-11-04/legacy-industry-order-probe.json`. Repair and regression requirements are a synchronized cross-sectional decision snapshot, delayed execution, arrival-order invariance and explicit target-holding/rebalance semantics. No repair was silently applied during this research task.

## Documented industry families and proposed extensions

| Family | Public institutional evidence | Proposed project work | Priority and prerequisites |
| --- | --- | --- | --- |
| Cross-asset ETF tactical allocation | ETF instruments are used across asset classes; the project's existing momentum/trend methods can supply a practical research baseline | Add a dated stock/bond/gold/cash universe, relative plus absolute momentum, explicit cash handling, target weights and rebalance buffers | P1 after trustworthy long histories, instrument metadata and same-date execution |
| Sector rotation with complementary signals | Fidelity describes business-cycle sector analysis and its combination with inflation, industry and fundamental evidence [S2] | Keep price-strength baseline; add breadth and, when data permits, earnings-quality and macro overlays with separate attribution | P1 for a synchronized sector-ETF baseline; financial/macro variants wait for PIT evidence |
| Dividend, quality, value and low-risk Smart Beta | MSCI maintains these factor index families [S1] | Add point-in-time valuation/profitability/leverage/cash-flow inputs, dividend history and sustainability checks, sector/size controls and composite ranking | P1/P2; a price/volume factor or current ROE snapshot is insufficient |
| Multi-asset risk allocation | Bridgewater documents All Weather as a risk-balancing approach [S3] | Reuse existing ERC/HRP/variance estimators; add real asset sleeves, risk/exposure attribution, rebalancing and a strategic allocation comparison | P1; do not rebuild working solvers or label generic risk parity as an institutional proprietary implementation |
| Target-volatility overlay | S&P publishes dynamic-risk-exposure methodologies and risk-control research [S4] | Complete the existing reduction-only control with a declared exposure policy, cash treatment, forecast/realized risk reporting and turnover buffers | P1 for an unlevered version; leverage needs a separately validated financing ledger |
| Benchmark-relative index enhancement | E Fund describes excess-return objectives subject to deviation/tracking-error limits [S5]; MSCI documents capacity and turnover constraints [S10] | Add historical benchmark constituents/weights, active risk, sector/beta/size exposure constraints, turnover-aware optimization and actual benchmark-relative performance | P2; current minimum variance and an equal-weight pool benchmark are not index enhancement |
| Diversified CTA/time-series trend | AQR describes trend strategies across equity, fixed-income, commodity futures and currency forwards [S6] | Add contract metadata, continuous signal series, actual-contract fills, rolls, margin, variation settlement and risk scaling | P2/P3; an unlevered long/cash ETF trend proxy can precede futures infrastructure but must keep its own name |
| Pairs/statistical arbitrage and market-neutral equity | The NBER Gatev/Goetzmann/Rouwenhorst paper documents pairs-trading research [S11] | Separate formation and trading samples, test spread stability, control both legs, beta and borrow availability; include borrow/financing costs | P3; ordinary sell intents currently do not establish an opening short or a financing account |
| ETF discount/premium and creation/redemption arbitrage | iShares explains AP creation/redemption and valuation-time mismatches [S7] | Start with timestamped premium/discount monitoring; execution needs basket/PCF data, synchronized fair value, eligibility and multi-leg cost/execution logic | P3; a closing NAV discrepancy alone is not an executable riskless spread |
| Equity-index cash/futures basis | CME describes index basis and its financing/dividend carry [S8] | Add matching spot exposure, futures contracts, financing/dividends, maturity and margin-aware multi-leg execution | P3; positive or negative basis alone is not a net-return signal |
| Covered-call, put-writing and collars | Cboe publishes option-strategy benchmark families [S9] | Add option chains, contract multipliers, spreads, collateral, exercise/assignment and expiry settlement; compare premium receipts with full strategy P&L | P3; an ETF price series alone cannot validate option-income mechanics |

Priority indicates fit with the current software and data, not a ranking of future returns. The sector-cycle framework is probabilistic, and translating a US institutional framework to Chinese sectors requires independent local evidence. Existing rules should remain valid baselines rather than being relabeled as more advanced families.

## Shared foundations to address first

1. **Long, dated and survivorship-aware data.** The composition defaults request 240 unadjusted daily bars. User imports may supply more, but the default collection is too short to claim multi-cycle validation. Preserve listings, delistings, historical constituents and sector classifications. Current classifications cannot be backdated into history.
2. **Total return and execution-price separation.** Add distributions, splits and other corporate actions to both strategy and benchmark accounting. Adjusted prices used for signals must not become impossible execution prices; fund NAV-based total-return series must not have expenses or dividends counted twice.
3. **Instrument-specific rules.** Populate lot/tick sizes, settlement availability, exchange calendars, trading status, actual fee schedules, cash yields and, where relevant, FX. A regional A-share default is not proof of each ETF's actual trading/settlement rules.
4. **ETF economic metadata.** Verify inception/termination dates, duplicate exposure, fund/benchmark mapping, AUM, liquidity, spreads, fees and timestamped NAV/IOPV evidence. Keep unknown or stale metadata visible.
5. **Financial and macro availability.** Build forward archived observations or acquire verified vintages/announcements. Do not transform today's revised snapshots into historical PIT features by shifting dates. Forward-only research can begin with correctly dated new observations.
6. **Investable portfolio construction.** Reuse target weights and the existing ledger; add ranking buffers, minimum trade/no-trade bands, turnover budgets and capacity-sensitive costs where a recipe requires them. Fixed share quantities are not a general portfolio allocation method.
7. **Relevant benchmarks and attribution.** Keep equal-weight price baselines, but also add the actual total-return benchmark or declared strategic asset allocation. Attribute asset beta, selection, timing, weights, fees and cash separately. Existing pool-relative tracking error is not official fund tracking error or a complete active-risk model.

## Suggested implementation sequence

**Foundation and correction:** fix the legacy sector synchronization issue; establish dated ETF pools, longer history, corporate-action accounting and instrument rules; record replayable snapshots and unchanged baselines.

**First usable strategy package:** complete cross-asset ETF momentum/trend allocation, synchronized sector-ETF relative strength, multi-asset ERC/HRP allocation and an unlevered volatility overlay. Reuse the existing graph, portfolio estimators, risk engine and reporting. Require one signal definition and ledger to agree across UI, API, CLI, backtest and forward simulation.

**Fundamental and benchmark package:** add verified PIT quality/value/dividend features, then a benchmark-relative enhancement recipe with active-risk and cost constraints. Connect macro/industry evidence through explicit frozen inputs and retain independent quant-only baselines. Language-model narrative must not substitute for missing observations.

**Separate derivatives/shorting package:** evaluate CTA, pairs/market neutrality, basis and options only after the required instruments, collateral, borrow and settlement ledgers have their own acceptance evidence.

For each family, preregister signal timing, universe, refresh/rebalance policy, costs and comparisons; use walk-forward or frozen out-of-sample checks, stress periods, parameter neighborhoods and a forward shadow period. Acceptance must include missing-data/corporate-action cases, realistic rejection/partial fills, deterministic replay, turnover/capacity and cash conservation. A passing workflow test or attractive in-sample backtest is not a production performance conclusion.

## Validation performed for this survey

The focused ETF, strategy-example and composition/API workflow suite passed **36 tests** in **66.33 seconds** on Windows. It exercised controlled/mock data and is evidence of implementation paths, not a live profitability test. The additional legacy-order probe reproduced the issue described above. No new real-model calls, trading instructions, package changes or service deployment were performed. Test-owned services stopped, and temporary evidence was retained under the user's established preference.

## Primary public sources

All links were checked or retrieved from official-source search results on 2026-11-04. Publication dates vary; historical research is not presented as newly discovered evidence or a current performance forecast.

- **S1:** [MSCI Factor Indexes](https://www.msci.com/indexes/factor-indexes). Official factor-family catalog; used to identify established families, not to copy unpublished portfolio models.
- **S2:** [Fidelity: The Business Cycle Approach to Equity Sector Investing](https://institutional.fidelity.com/advisors/insights/topics/portfolio-construction/the-business-cycle-approach-to-equity-sector-investing). Institutional sector-cycle framework, updated in February 2025.
- **S3:** [Bridgewater: The All Weather Story](https://www.bridgewater.com/research-and-insights/the-all-weather-story). January 2012 description of risk-balancing origins, not a license or a recipe for proprietary current holdings.
- **S4:** [S&P: Limiting Risk Exposure with S&P Risk Control Indices](https://www.spglobal.com/spdji/en/documents/research/research-limiting-risk-exposure-with-sp-risk-control-indices.pdf). Public description of volatility-based exposure control.
- **S5:** [E Fund: Enhanced ETFs](https://edu.efunds.com.cn/c/27/27047.shtml). Benchmark-relative enhancement objectives and deviation/tracking-error constraints.
- **S6:** [AQR: A Century of Evidence on Trend-Following Investing](https://www.aqr.com/insights/research/journal-article/a-century-of-evidence-on-trend-following-investing). Published in 2017; identifies diversified time-series trend methods, with no return promise adopted here.
- **S7:** [iShares: ETP Premiums and Discounts](https://www.ishares.com/us/investor-education/etf-education/etf-premiums-and-discounts). September 2026 explanation of AP mechanisms and apparent valuation gaps.
- **S8:** [CME: What Is Equity Index Basis?](https://www.cmegroup.com/education/courses/introduction-to-equity-index-products/what-is-equity-index-basis). Financing and dividends in futures-versus-spot basis.
- **S9:** [Cboe Strategy Benchmark Indices](https://www.cboe.com/us/indices/benchmark_indices/). Public buy-write, put-write and other option-strategy benchmarks.
- **S10:** [MSCI: What Drives the Capacity of Factor Index Strategies?](https://www.msci.com/research-and-insights/blog-post/what-drives-the-capacity-of-factor-index-strategies). Portfolio investability and turnover considerations.
- **S11:** [NBER: Pairs Trading: Performance of a Relative Value Arbitrage Rule](https://www.nber.org/papers/w7032). Official publication record surfaced in search; direct page access returned 403 in this session. No new empirical estimates were inferred from the inaccessible full paper.
