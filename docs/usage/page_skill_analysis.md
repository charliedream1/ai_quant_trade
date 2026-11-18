# Page-specific CLI and Skill analysis

Supported research modules provide a **CLI + Skill analysis** panel below their
normal rule view. Rule tables, charts and actions remain available. Opening a
page or the panel does not submit a model request.

1. Select the market and page inputs, then load the relevant rule data or open a
   saved result. The server retains a bounded snapshot of that completed result.
2. Open the analysis panel and choose the task for the current view. Stock pages
   offer technical and financial interpretation; simulation offers backtest and
   paper-account interpretation. Required observations must already be available.
3. Choose a supported CLI, model and reasoning effort. The shared catalogue shows
   provider-reported billing or explicitly unknown pricing. Model discovery and
   ordinary chat access do not prove eligibility for strict research.
4. Click **Run Skill analysis**. The page shows the frozen request, actual stages,
   returned process events and the resulting HTML. Cancel stops the page-owned
   work; leaving the page also cancels it and clears old-view polling.
5. Use report history to reopen the saved result or download its identical HTML.
   Opening/downloading a report does not rerun generation.

If inputs changed after data was loaded, refresh the corresponding rule data.
Snapshots are isolated by database, browser owner, navigation revision and market.
Another window's observations are not available to this panel. Returning after a
navigation revision may require a fresh rule read, even if an old chart is cached.
The analysis does not train a model, optimize parameters, execute a strategy,
publish a report externally or place orders.

## Supported analysis tasks

| Surface | Required completed rule observations |
| --- | --- |
| Overview | Account, market, news or local-task results |
| Industry/concept sectors | Current board/ranking result |
| News | Results with the selected geography, subject and query |
| Stock technical | Stock identity, period and deterministic result |
| Company financials / macro | Loaded economic snapshot with its original period/scope |
| Candidates / resource pool | Generated candidate comparison or loaded pool members |
| ETF | Loaded selected ETF universe |
| Factor / Qlib | Completed monitor result or saved diagnostics |
| Composition | Saved/opened run or explicit definition preview; a preview is not a backtest |
| Backtest | Existing result/analysis/comparison |
| Paper / live attribution | Existing account, risk/status or workflow snapshot |
| Papers and broker reports | Selected original detail |
| Knowledge | Retrieved references or selected document text in the current page scope |

Relationship graphs retain their existing rule and CLI/Skill workflow; see the
[graph guide](model_stock_relationships.md). Administrative configuration, login,
bindings and learning/navigation controls do not acquire automatic model actions.

## Evidence and execution boundaries

Analysis reuses server-completed results; the browser does not supply arbitrary
facts as trusted evidence. Records are bounded by row/text/combined-size limits,
so large scopes may require narrowing. A displayed sample is not full-market
coverage. Sources retain their original request/capture scope and mock markings;
the report must distinguish observations, calculations, interpretation and gaps.
Absent data, unsupported HK financials and unavailable sources remain limitations.
The current US real-mode fallback is not accepted as real page evidence.

The actual prompt loads the project Skill and mapped method resources, recording
their content digests. New page methods are project-authored adaptations, not
claims that an external Skill package was installed or validated. Existing market,
stock and economic resources are reused as guidance. Native scripts, implicit
publishing instructions and private agent memories are not imported or executed.

Current-observation Codex commentary uses the existing read-only CLI runner and is
explicitly labelled as interpretation, not independent historical/PIT validation.
Experiment/backtest/factor/composition review preserves the existing strict native
research admission. An installed CLI may therefore be unavailable for one task
while ordinary commentary is available. WorkBuddy remains limited to the existing
verified graph flow; it is not substituted for CodeBuddy or enabled as general chat.

Unknown fees remain unknown. The platform cannot infer a zero bill from missing
CLI usage metadata. Report interpretation is not investment advice or an execution
instruction. HTML uses project templates and escaped findings in a sandboxed
preview; model text is not run as privileged same-origin JavaScript.
The existing mock-data guard remains: demo mode does not start a real CLI unless
`ALL_IN_ONE_ENABLE_REAL_CLI` is explicitly enabled. Declared fixtures are used for
protocol acceptance and are never presented as live vendor-model evidence.

## Configuration and verification

`egs/config/ui/page_analysis.yaml` owns task/view mappings, field bindings, method
instructions, limits and copy. `src/skills/page_analysis` contains the project
method guides. Reports use the existing insight store under the configured private
data root, retaining request, evidence, resources, events and report artifacts.

Acceptance separates declared fixture rendering/consistency checks from real CLI
availability and source quality. Missing authentication or a free verified test
route is a live-acceptance limitation; a controlled response does not prove vendor
model quality. Windows project and Conda SDKs are checked separately; Linux behavior
uses portable process/path contracts and needs its own physical acceptance run.
