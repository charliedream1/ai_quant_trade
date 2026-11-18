# Page-specific CLI and Skill analysis with HTML reports

Date: 2026-11-17 (UTC+08:00). Status: approved and implemented; acceptance completed on 2026-11-18 with the live-provider limitations recorded below.

## Goal and current implementation

Keep deterministic page data and calculations available while adding an explicit
CLI plus Skill analysis action to suitable research pages. The action should use
the page's current context without requiring the user to compose a prompt, show
actual execution stages and present an attributable HTML report on the same page.

The repository already contains eleven registered research workflows, additional
economic Skill material, original market/stock method resources and a directed
relationship-graph workflow. InsightReportService already reads actual Skill
resources, saves their digests and evidence, records events and renders HTML.
LocalSkillService dispatches to existing insight/team/alpha/composition/agent/graph
services. The report library already aggregates several of their stores. These
are reusable foundations, not proof that every page already has a complete Skill.

Relevant implementation locations:

- frontend/features/insights.py and service/insights.py: report controls and preview.
- engine/insights/config.py, execution.py, research.py and rendering.py: actual
  resource loading, evidence collection, bounded ReAct and HTML rendering.
- agent/skill_runner/catalog.py, service.py and workflows.py: registered research
  contracts, progress, cancellation and domain dispatch.
- egs/config/agents/skill_workflows.yaml and src/skills: registered method resources.
- frontend/features/model_relation_graph.py: existing rule/model graph controls.
- frontend/service/report_library.py: shared history and report viewing.
- core/page_work.py and frontend/page_reads.py: page lifetimes and hard cancellation.

## Page and Skill mapping

The first implementation includes the following analysis surfaces. A missing
required input disables the action with a specific explanation rather than
creating fabricated data or silently starting a different workflow.

| Page | Bound inputs | Skill or adaptation | Main report |
| --- | --- | --- | --- |
| Overview | Market, account view, dated market observations | Existing market review with read-only account-risk context | Market/risk summary, data gaps and follow-up checklist |
| Industry and concept sectors | Market, board type, ranking selection, period and returned rows | Adapted sector-rotation interpretation method | Breadth, strength/weakness, evidence and limitations |
| News | Geography, subject, search/filter scope and selected originals | New market-policy news analysis method | Event timeline, market/policy transmission hypotheses and citations |
| Stock technical analysis | Canonical security, market, period and computed indicators | Existing stock-analysis Skill and technical references | Technical interpretation, scenarios, invalidation conditions and risks |
| Company financial analysis | Immutable economic snapshot, reporting period and matched peers | Existing economic-evidence-analysis material | Growth, accounting scope, cash flow, valuation limits and risks |
| Macroeconomics | Immutable macro snapshot, release periods, units and stale flags | Existing economic-evidence-analysis material | Growth/inflation/credit/policy interpretation with evidence |
| Relationship graph | Target, as-of date and authorized source scope | Existing quant-stock-relations workflow | Existing directed evidence graph plus report/history |
| Stock candidates/resource pool | Selected candidates, selection criteria and evidence | Adapted comparative stock/portfolio review | Candidate differences, concentration and additional verification needs |
| ETF research | Selected ETF exposure; completed backtest when performance is reviewed | Existing quant-etf-review contract and explanatory method | Exposure, tracking, liquidity and execution/cost limitations |
| Factor research | Saved experiment, universe version and diagnostics | Adapted factor-evaluation method | Coverage, IC/stability, leakage checks and result limitations |
| Strategy composition | Saved definition/version and an existing run | Existing composition workflow in read-only review mode | Sleeve/vote/cascade explanation, risk and cost interpretation |
| Backtest and attribution | Completed task, resolved parameters, ledger and cost profile | Existing quant-backtest-review | Performance, drawdown, cost, attribution and implementation correctness review |
| Paper/live attribution | Selected saved account/run observations and actual ledger | Read-only portfolio/risk review adaptation | Exposure and execution diagnostics; no order placement or configuration changes |
| Reports/papers | Selected documents and their dated originals | New document-review method using authorized knowledge evidence | Research question, method, assumptions, findings and relevance |
| Knowledge document/Q&A | Selected library/document/session and retrieved evidence | Existing retrieval with a document-review report adaptation | Cited document summary or synthesized answer; existing Q&A remains |

Administrative settings, binding/login, uploads and learning/navigation controls
retain their ordinary workflows. They do not need automatic model execution.
Existing independent Alpha/agent research actions remain available with their
current required datasets and research gates; a page report does not implicitly
start a discovery campaign, run a backtest, publish a strategy or place a trade.

## Interaction

Expose Rule data and CLI + Skill analysis as distinct views or adjacent panels,
using one shared analysis component. Keep Rule data as the default. Opening or
switching a page must not start a model request or preload all analysis resources.
Existing tables, charts and refresh behavior remain accessible throughout.

The analysis panel shows the mapped task, required inputs and current data scope.
Reuse the existing CLI/model catalogue, billing provenance and reasoning controls;
show execution capability separately from model discovery or authentication.
The primary Run Skill analysis button validates inputs and creates a task ID.
Provide Cancel, History, Open saved report and Download HTML without rerunning
generation. Use existing graph/economic controls where possible rather than
duplicating two competing analysis buttons on one page.

Capture market, symbol, date, filters and dataset/snapshot/task IDs at submission.
Freeze the actual acquired evidence and resource hashes used by that run. Report
headers show these values, source timestamps, provider/model and verified scope.
If the page context changes, label the previous report with its original scope;
do not present an old company's report as the newly selected company. Reject stale
process/result updates using the page and run revision.

Display observable stages: validation, Skill/resource loading, source acquisition,
calculation, CLI request, returned output, citation checks, rendering and completion.
Show elapsed time and actual warnings/errors; do not invent completion percentages
or expose private credentials or hidden model reasoning. Partial results retain
their missing-evidence labels. A failed task must not show a success placeholder.

## Skill resources and provider execution

Create a YAML page-to-workflow registry with input adapters, required fields,
supported markets, prompts, allowed tools, limits and report sections. Keep method
text and reviewed references in src/skills. Domain source collection and arithmetic
remain in the existing services; models interpret actual values instead of
recalculating balances, ratios, returns or transaction fees.

Read the registered Skill and required references into the actual generation
context, record version/digests and distinguish facts, calculations, inferences and
gaps. This is explicit prompt composition using ordinary text generation and
traditional bounded ReAct. It does not require enabling the CLI's unrestricted
native Skill tool or recursively launching the platform through a provider.
Structured model responses continue to use json_repair, not function calling or
mandatory provider-native structured output.

Retain existing native capability checks and strict research requirements. A CLI
that can chat or list models is not automatically eligible for a historical/PIT
research role. Unsupported combinations show the reason before generation and do
not silently fall back to another CLI or API model. WorkBuddy remains limited to
its verified graph-specific flow unless a separate capability is established;
this proposal does not equate it with CodeBuddy or copy desktop authentication.

Reuse internal resources first. For any external Skill adoption, record the
upstream URL, version/commit, license/redistribution terms, content digests and
adaptations before vendoring it. Review instructions and referenced scripts;
exclude personal memory/configuration, credentials, implicit publishing/installers
and machine-specific paths. Do not execute arbitrary upstream shell scripts merely
because a Skill references them. Existing provenance records need review where
licensing or supported scope is incomplete; do not claim an external package has
already been evaluated or installed.

## Data and market correctness

Use the current platform market capabilities. CN and HK securities must retain
canonical identity, currency, source dates, board lot/calendar context and actual
available data. The current general insight service excludes HK, so connecting
the HK page requires a verified HK evidence adapter; do not reuse CN collectors
or manufacture mainland financial ratios. Unsupported fields remain explicit
gaps. Existing US real-mode mock fallback cannot be labelled real Skill evidence.

Keep accounting periods and economic snapshot IDs immutable. Historical research
continues to require original point-in-time gates; latest web evidence does not
prove past availability. News transmission paths are hypotheses rather than causal
facts or trading instructions. Reported sources and quoted spans must match the
selected authorized document/library/session and source revision.

## Shared execution, reports and lifetimes

Reuse existing domain runners behind a shared page-analysis coordinator, with a
uniform task/status/event/report contract. Extend existing report task types and
thin adapters where required rather than building a second model or report stack.
Register explicit page ownership and bounded concurrency/time/request budgets.
Propagate RPM and Langfuse observation context across background boundaries.

Page-started analysis is transient by default: cancelling or leaving the page
stops its eligible owned CLI/source work and hidden polling. Preserve existing
independently submitted backtests/research/trading lifecycles and multiwindow
consumer isolation. Never cancel another window's active consumer merely because
one page leaves. Interrupted or failed runs retain their observed events and
metadata; do not automatically retry paid generation on refresh or reconnect.

Render validated structured findings through project templates, escape untrusted
text/URLs and isolate HTML previews with existing sandbox/CSP controls. Model output
must not become unrestricted scripts or privileged same-origin HTML. Charts use
actual datasets; report text cannot create unsupported measurements. Persist the
request/evidence/resource/model identities and expose private authorized artifacts
through existing containment and report-library rules. Saved report previews and
downloads must refer to the same immutable result and must not call the model.

## Implementation order and review scope

1. Build the shared registry/coordinator/panel and integrate existing market,
   stock, macro/financial, graph and completed-backtest analysis first.
2. Add the listed sector/news, ETF/factor/composition, candidate/portfolio and
   document-review adapters, reusing saved inputs and existing gates.
3. Consolidate report history, add the remaining page hooks and complete the
   page-by-page parity/cancellation/latency acceptance matrix before delivery.

This order partitions implementation, not approval or final delivery. Do not stop
after the first few panels and describe all pages as supported. If a required
source/backend is unavailable, finish its explicit unavailable/partial path and
record the precise unverified boundary. New code/comments/design/usage are English;
localized UI copy remains configurable. Do not modify docs/task-prefixed Markdown.

## Acceptance

For each mapped page test valid/missing inputs, ordinary-rule parity, no model call
on page entry, exact context binding, supported CLI/model selection and fees,
actual stage events, cancellation, history, HTML preview and identical download.
Simulate delayed CLI/source responses and rapid context changes; assert no stale
report overwrite, shared-window disruption or abandoned owned process. Recheck
the complete eight-metric/six-plot homepage and cold/cached navigation timings.

Use deterministic declared fixtures and a controlled OpenAI-compatible/CLI response
for each report schema and citation/HTML boundary. Separately execute real public
data and at least one available real CLI Skill report without presenting fixture
results as live quality evidence. Paid calls require explicit authorization;
prefer a locally available explicitly free route when verified. An unavailable
model is an acceptance limitation, not permission to fabricate a report.

Run relevant unit/integration/browser tests under project and existing Conda
Gradio versions, Ruff, mypy, privacy/security tools and both strict documentation
builds. Synchronize English design/usage/principles, the existing README capability
summary and the dated weekly changelog. Keep evidence/installations on E; stop
owned services, preserve unrelated work/staging and obtain deletion approval.
No package changes, automatic deployment, commit or push are included in this
new implementation proposal.

## Implemented adaptation and acceptance boundaries

The shared panel uses server-captured completed rule results rather than repeating
page source acquisition. Captures are bounded and isolated by database, browser
owner, navigation revision and market. Matched input changes reject stale sources.
Market/stock/economic methods load existing project resources; new news, portfolio,
experiment and document guides are project-authored adaptations. No external Skill
package or native shell script was installed. Reading a review guide into a prompt
does not execute its separate multi-agent or historical-validation workflow.

Current-observation Codex commentary uses the existing read-only native runner and
is labelled accordingly. Experiment/backtest/factor/composition roles retain the
strict native provider contract; this is not a general strict-mode relaxation.
The mock-data real-CLI opt-in remains enforced. The graph-specific WorkBuddy path
is preserved separately, with no new account binding or ordinary-chat capability.

Task synchronization is deferred until the user expands the analysis panel.
Sending callbacks to its collapsed controls at initial route activation disturbed
queued rule-chart rendering under Gradio 6.3. The route field itself has no loading
callback; navigation closes an open analysis panel and its page-owned work is
cancelled through the existing lifetime registry. Saved HTML downloads use the
existing insight-artifact API, avoiding SDK-version-dependent file-link prefixes.

Controlled process/browser acceptance exercises actual CLI stdio event parsing,
Skill prompt loading, report schema/citations, escaped HTML, identical HTTP
download, history reopen, route transitions, market/window isolation and cancellation.
The process fixture is explicitly declared, not a vendor-model quality or billing
claim. The available native Codex metadata protocol was previously verified;
an independently verified free vendor generation route was not configured for
this run. No paid generation or silent substitution was performed. Physical Linux
execution and unavailable provider profiles remain unverified.

## Explicit interruption completion

The stop button acknowledges cancellation immediately and retains a stopping
status until the owned work has exited. Local page runs receive a direct event
as well as the persisted cross-process cancellation request. Native CLI cleanup
terminates the owned process tree, including silent children holding stdout or
stderr pipes; Unix runners create their own session. Timeout and generator-close
cleanup use the same termination boundary. An already cancelled request does not
start a new CLI. Final cancelled runs keep observed events, expose no success
report and release their task lease/page slot. Repeated cancellation is safe.

Acceptance must use a real silent parent/child process and verify lock release,
terminal cancellation, lease release and immediate restart, in addition to
browser clicks while a declared generation request is blocked. This verifies
local resource cleanup, not reversal of usage already incurred at a provider.
