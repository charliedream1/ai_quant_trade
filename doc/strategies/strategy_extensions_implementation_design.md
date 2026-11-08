# Strategy Extensions and Evidence Design

Approved scope: repair synchronized industry rotation; add reusable dated research data; complete ETF/sector allocation and unlevered risk allocation; register financial factor recipes and benchmark-relative enhancement. Derivative, borrowing, primary-market ETF arbitrage and option strategies remain separate later projects.

## Data and accounting contract

A project-local research import produces the existing immutable pipeline snapshot format. It accepts long raw-price OHLCV histories, explicit instrument rules, dated sector classifications, dated original financial observations, benchmark constituent weights, corporate actions and cash rates. Identifiers and input sizes are bounded. Hashes, provenance, currencies, units and availability timestamps are preserved. Current economic-analysis snapshots marked ineligible for historical use cannot be relabeled as qualified historical financial data.

Each decision uses only records available by its configured decision cutoff. Changes in sector membership and benchmark weights have separate effective dates. A publication or availability timestamp after the cutoff cannot influence that decision. Missing input remains missing. Instrument policies come from dated supplied evidence, not inferred trading rules based only on a geographic market label.

Raw prices remain execution prices. Supported cash distributions and splits update the physical portfolio and the comparison benchmark separately from trading. Signal histories are adjusted only with events known by the observation date. Unsupported fractional-share or corporate-action cases are rejected rather than silently losing value. Cash interest uses documented unlevered rates and actual elapsed days, without changing portfolio units. ETF fees embedded in observed returns are not deducted twice.

A supplied cash-dividend payment date creates an entitlement receivable on the ex-date. Receivables contribute to NAV but cannot fund orders or earn cash interest. A date-only payment becomes cash after that observed session's execution; an intervening non-session payment is settled before the next observed open. Saved receivables survive sales, year boundaries and account restarts. An omitted payment date explicitly retains the original same-day cash assumption for compatibility. This is a source assumption, not proof of actual payment timing. The theoretical benchmark separately retains its documented ex-date fractional reinvestment policy.

Financial coverage counts complete, available observations before economic sustainability screening. An observed dividend-coverage rejection is an ordinary rejected candidate; it does not represent missing evidence or abort a valid cross-section. Ranking uses the complete observed cross-section. A fully rejected cross-section leaves cash. Missing financial evidence still enforces the declared coverage gate.

Dated benchmark reconstitution is keyed by effective/availability revision as well as numeric weights. A new revision with unchanged target weights still retargets at the following open; persistence must preserve its identity without creating extra rebalances after a restart.

## Strategy methods

ETF allocation uses relative momentum across declared horizons, an absolute trend/return eligibility gate, and target capital weights. An empty eligible set leaves cash. Sector-ETF momentum and stock-sector breadth are distinct recipes. Security records within one decision date are processed as one cross-section; the legacy example acts on the completed prior-date snapshot.

Risk allocation reuses the existing ERC, HRP and minimum-variance implementations. The new asset pool distinguishes equity, bond, gold and a cash alternative; configured identities do not certify historic availability. The volatility overlay is unlevered, respects maximum exposure and preserves risk reductions as cash.

Financial scoring uses explicitly dated profitability/cash-flow/leverage, value and dividend-sustainability fields. Directions, normalization, weights and minimum coverage are declared in YAML. The recipes are independent project methods informed by public factor research, not replicas of proprietary index methodologies. Missing financial history blocks the affected strategy; model narrative is not a substitute.

Index enhancement uses a complete dated benchmark vector and declared cross-sectional scores, with nonnegative weights, full-investment feasibility, active-weight, sector/beta/size, tracking-error and turnover constraints. Solver diagnostics and infeasibility are retained. A risk-clipped result reports its resulting benchmark deviation rather than claiming the pre-risk constraints still hold automatically.

## Integration and delivery

New components, portfolio settings and recipes use the existing graph catalog, run service, API, CLI, report and paper ledger. A small research-data panel imports evidence and returns a snapshot identifier accepted by all run paths. Viewing documentation or navigating the page does not fetch data, train a model or place orders.

Public principle documentation records each method's signal definition, timing, data requirements, accounting, source references and limitations. Sources include MSCI's factor catalog, Fidelity's sector-cycle research, Bridgewater's risk-balancing discussion, S&P's risk-control research and E Fund's benchmark-relative enhancement explanation. The implementation and frozen YAML define this project's exact behavior.

## Acceptance

Tests cover arrival-order invariance, next-session decisions, future/revised evidence exclusion, listing and sector changes, cash/split conservation, signal/price separation, no duplicate event application, benchmark/cash returns, ranking and missing-input gates, allocation feasibility and solver constraints. API/CLI/browser replay uses the same snapshot. Existing strategies, knowledge, model quotas and economic analysis receive regression coverage. Real public histories verify data paths where available; synthetic PIT records remain explicitly simulated and do not certify a commercial feed or long-run profitability.

English documentation/comments, Windows/Linux-compatible paths, Loguru, project-only files and existing security checks remain mandatory. Existing uncommitted work is preserved; no automatic commit, push or deletion is included.
