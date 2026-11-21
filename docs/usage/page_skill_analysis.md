# Page-specific CLI and Skill analysis

Select **Page analysis** in the left sidebar of a supported research view to
open its report drawer. Opening the drawer loads the model catalog for the
selected CLI. Generation starts when you click **Generate HTML report**.

1. Select the CLI and model. The catalog is shared across the workspace and
   reused daily. Click **Refresh models** to query it again. The drawer displays
   when a CLI is missing or its catalog is unavailable.
   If Qoder reports that its account is signed out, run `qodercli login` and
   refresh the model list after authentication.
2. Click **Generate HTML report**. The drawer selects the current view's task
   and generates the report in the current interface language. Sector and news
   reports can load current observations from the active filters. For other
   views, first load the relevant data or open a saved result.
3. Preview the report in the drawer or download the same HTML. Expand **Run
   details** to see the evidence scope and process events. **Analysis options**
   shows the active task and other tasks available for that view.
4. Expand **Report history** to reopen a saved report.

Click **Cancel analysis** to stop an active report. The drawer shows the
stopping state until the CLI process and its children exit. Leaving the page
also cancels the report. Use **Generate HTML report** to start a new run.

If inputs changed after data was loaded, refresh the corresponding rule data.
Snapshots are isolated by database, browser owner, navigation revision and market.
Another window's observations are not available to this panel. Returning after a
navigation revision may require a fresh rule read, even if an old chart is cached.
The analysis does not train a model, optimize parameters, execute a strategy,
publish a report externally or place orders.

## Supported analysis tasks

| Surface | Required completed rule observations |
| --- | --- |
| Industry/concept sectors | Current board/ranking result, loaded on demand |
| News | Results with the selected geography, subject and query, loaded on demand |
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
