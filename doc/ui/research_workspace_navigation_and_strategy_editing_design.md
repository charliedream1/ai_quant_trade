# Research Workspace Navigation and Strategy Editing

Date 2026-11-23 (UTC+08:00). Approved and implemented.

## Findings from the current checkout

- The workspace shell opens a Gradio frame and synchronizes its route after the frame loads. The overview also binds initial load, market revision and account changes to the same five callback groups. Account valuation and market data still have grouped output paths. The release calendar is built during page construction and loaded again on initialization. These are measurable candidates for the two-stage display. A browser trace is needed to establish which events cause the visible transition.
- The news list reads the latest records under the selected filters. Keyword strength makes a second query limited to the current day. A valid list can therefore coexist with an empty chart, particularly before the first release of the day or on a non-trading day. The Hong Kong news path explicitly reports that its provider is unavailable.
- The callback log uses backend callable names for the visible action. Navigation, page-owned tasks and worker stages already have separate event paths that can supply user-facing descriptions.
- The rule graph already runs in a separate process with checkpoints and a deadline. The market frame constructs the model graph and other market tabs together. Terminal polling also builds the graph figure in its response path. Entry, submission, server-side figure building and browser drawing need separate traces to locate the freeze.
- The shared CLI catalog currently composes option labels from a model name and a billing string. Persisted catalogs do not expose structured comparable rates to the selector. Report entry points exist in both the workspace navigation and page bodies.
- Individual-stock research currently combines technical analysis with unstructured news and reports, and has one financial tab. The recommendation page combines candidate comparison and backtesting in one open section. The factor monitor uses a growing Markdown area for recent events.
- The strategy canvas already supports dragging some connections, a property panel, server-side validation and frozen strategy versions. Saving a mutable draft and publishing a runnable version are separate operations. The working tree contains earlier canvas changes that must be included in regression checks.

### Controlled browser measurements

The Conda Python 3.11 Chromium full-overview test used the same seeded account case and checked all eight metrics and six charts. Each row is a single run with a separate server and test database. These timings exclude live market network delays.

| Revision | Cold complete | Cached return |
| --- | ---: | ---: |
| November 9 commit `794c0d2` | 7.05 s | — |
| November 15 complete-overview commit `6dc1de9` | 13.64 s | 0.70 s |
| Current checkout on November 23 | 19.34 s | 0.88 s |

The November 9 run used the same completeness assertions. It measured the
cold load only because a notification overlay intercepted the refresh action.

The controlled financial-subview cancellation test reached interactive relationship controls in 1.02 seconds, including cleanup. This covers entry from a stalled financial read. The reported freeze still needs reproduction on cold navigation, job submission and graph drawing with real data.

## 1. Overview and relationship graph responsiveness

Compare the November 9 workspace revision, the November 15 complete-overview revision and the current checkout on the same interpreter and fixture. When a historical revision cannot run in the shared environment, record the blocker and compare the nearest runnable revision. Run a controlled browser trace, then repeat with available live sources. Measure frame reveal, first usable content, first account and market content, all sections, task queue wait, worker startup, source calls and plot rendering. Count component mounts and callback dispatches during frame and market synchronization.

Keep one overview layout from entry through refresh. Render stable card positions and localized section states. Publish stored account/task data and timestamped market observations independently, with the cheapest reads reaching the page ahead of network retrieval and chart construction. Revalidate quotes and valuations separately. Apply stale markers with original timestamps and update only the affected cards. Share identical source work and guard delivery by page and input revision. Preserve the eight account metrics, six plots and their detailed tables. News and both keyword extraction modes stay in independent sections. Add one regression fixture where headline or quote work stalls while other cards finish.

Measure the relationship page from the navigation click through interactive controls, task acceptance, progress and first result. Mount the active graph experience on demand. Move preparation or layout work off the interactive request path where the trace shows blocking. Keep status polling lightweight and publish each result once. Bound the visible graph preview for large results with an explicit coverage note and preserve the full saved export. Reuse the existing server-side cancellation and deadline, preserve the distinction between rules and model-assisted graphs, and show named progress stages, elapsed time and partial-result coverage. Verify navigation and cancellation using a deliberately stalled data source, then exercise CN and HK graph inputs with available live evidence.

## 2. Operational logging and factor run history

Use localized descriptions of the page, operation and stage in the console. Startup diagnostics retain the established English wording. Console output can identify transitions such as entering Stock Analysis, loading saved financial statements, fetching prices, building a relationship graph, completing a section, timing out or cancelling. Show relevant elapsed time and a short operation reference for failures or slow tasks. Keep detailed component names and correlation fields available at diagnostic verbosity. Summarize repeated polling and successful refresh activity, preserve Loguru redaction and omit raw input, prompts, credentials and private paths from operational events. Keep log catalog copy and display policy in configuration.

Give both factor research and monitoring a bounded, scrollable execution log. Keep the latest messages available and respect the user's scroll position while inspecting earlier entries. Verify a long run at desktop and narrow widths.

## 3. Rule data, model analysis and model choices

Give each eligible page a consistent top action area. Label the rule-data action **Refresh data** and the model action **Analyze with AI**, with Chinese labels **刷新规则数据** and **AI 分析**. The analysis panel identifies the selected CLI and model and shows a separate **Run AI analysis** action. A completed run exposes **Preview report** and **Download HTML**. Progress, cancellation and saved report history use the existing page analysis flow. Adapt the action area to small widths and reuse it in standalone views and deep links. Regular data loading stays automatic where the existing page expects it, and generation requires an explicit action.

Use one ordering policy across all shared CLI model selectors, including the floating assistant and workbench. Group by verified model family or maintained identifier mappings, with an **Other models** group for unmapped entries. Inside each family, put explicitly free models first and sort known rates from low to high within comparable billing units and currency. Normalize token units and compare input rate first, with output rate as the tie-breaker. Show credit multipliers, subscription allowance, metered tariffs and unknown pricing with their own units and labels. Give unknown rates a stable position at the end. Retain the original model identifiers, underlying billing sources, supported reasoning settings and daily refresh behavior. Handle historical cache rows whose structured fields are missing using their existing labels until refreshed. Test the real WorkBuddy catalog, billing ties, different units and currencies, and provider switching while discovery is pending.

## 4. News keyword strength and stock research

Make the news table and keyword chart share a date window, geography, subject, source and keyword filters. Use a configured recent window by default so the useful corpus survives midnight and weekends. Build the chart from a bounded matched corpus before pagination. Show the window, sample size and how the strength was calculated. Publish headlines while keyword extraction runs. Distinguish an empty filtered corpus, no usable phrases, a tokenizer error and an unconfigured regional source. Preserve the lexical and explicitly selected semantic modes where supported and retain the existing model download confirmation. Verify known terms with timestamped news across day boundaries and exercise real public news under the same filters.

Organize stock research around one market and security selection. Add accessible tabs for **Fundamentals**, **Technical**, **Financials**, **News & Disclosures**, and **Relationships**. Fundamentals covers company profile, business, sector and sourced valuation. Technical covers price, volume, indicators and relative performance. Financials covers statements, profitability, cash flow and reporting periods. News & Disclosures covers issuer announcements, reported events and related research. Relationships shows saved graph evidence and opens the shared relationship workspace for construction. Add **Events & Risk** for sourced upcoming or recent disclosures and available volatility, drawdown and liquidity measures. Verify coverage and units by market, label unavailable data, and keep source timestamps. Load tab-specific data independently with current security checks and page-owned cancellation. Preserve current links to financials and stock-specific report evidence.

## 5. Recommendation workspace

Group existing operations as **Recommendations**, **Candidate comparison**, and **Backtesting**, with templates beside recommendation setup. Show the run action and latest results first. Put watchlist, resource pool and relationship actions near the selected candidates. Candidate comparison keeps single-factor and multi-plan evaluation. Backtesting presents its selected universe, configuration, run state, performance, attribution and trades. Switching between these sections retains current inputs and accepted results. Validate transfers between recommendation, comparison and backtest, including empty candidates, stale candidate selection and history download.

## 6. Strategy workshop

Open the canvas in view mode. **Edit** creates a local working copy and enables node insertion, drag-to-connect, positioning and right-side properties. Four plus controls on an eligible node open a compatible-node chooser and place the new node on the selected side. Direction follows the graph's input/output rules. Keep connector handles distinct from plus buttons and retain keyboard-accessible alternatives. Validate properties, port compatibility, duplicate connections and cycles through the existing graph contract. **Cancel editing** discards the local changes and returns to the saved view.

**Save version** validates the complete definition and layout before persisting it as a new immutable revision of the same strategy. Reuse the version store and make repeated or concurrent saves consistent. Surface a version selector with revision and save time. **Run backtest** uses the selected saved version and records its identity with the result. When editing is active, require an explicit save before the altered definition can run. Keep historical versions directly viewable and retain existing registry publication workflows. Check both the Gradio-hosted editor and the standalone browser component, including unsaved edits, a duplicate save, two versions of one strategy, a backtest that uses the selected version, and compatible keyboard and pointer operations.

## Verification and delivery

Exercise all ten reported behaviors with existing regression tests and focused tests for missing coverage. Run browser checks in the project and compatible Conda environments, including cold and warm overview entry, repeated and cross-page navigation, stalled-source cancellation, Chinese/English text, responsive layouts, accessible controls and saved HTML preview/download. Exercise one real WorkBuddy free-model report through the normal page action and confirm the selected model and saved artifact. Use representative graphs and enough events to trigger scroll behavior. Compare before/after timing and dispatch counts on the same fixture, and report live-source waits separately. Run applicable Ruff, mypy, dependency and secret checks, and both strict documentation builds. Update the relevant usage and design references and the weekly English changelog. Keep test artifacts on E and stop the test services.

The final Conda Chromium run completed the overview in 14.67 seconds, with
cached return in 0.58 seconds. The project runtime completed it in 9.08 seconds,
with cached return in 0.67 seconds. Both rendered the full set of metrics
and charts. Leaving a blocked financial read and reaching the relationship
controls took 1.30 seconds and 0.77 seconds, respectively.
Live rule-graph probes completed for the mainland sample with eight nodes and
one relation. The Hong Kong source produced a partial result with just the
selected security.
The news regression verified the same prior-day story in the filtered table and
keyword chart. The live provider returned an empty sample during the test.

The WorkBuddy browser check used eight archived real macro series after a
live-source DNS failure. The configured `hy4flash-free` model generated a
four-section HTML report at zero reported cost. The downloaded bytes matched
the saved artifact.

The Gitleaks scan found no secrets in the task files. Dependency audits
reported advisories in existing pinned packages.
