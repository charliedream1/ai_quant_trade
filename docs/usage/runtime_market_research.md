# Runtime diagnostics and market research

Normal startup and shutdown messages are English. The console shows readiness,
actionable warnings and failures. Explicit actions and worker readiness/progress are logged at INFO; polling, detailed source
locations and startup phases use DEBUG. A slow successful
request is not an execution error. To investigate a problem, set
`ALL_IN_ONE_LOG_LEVEL=DEBUG` locally and inspect the private application log.
Secret redaction remains enabled. Settings live in
`egs/config/ui/runtime_diagnostics.yaml`.
Changing pages also stops obsolete page-owned work; see
[navigation and cancellation](page_navigation.md).
Set `ALL_IN_ONE_LOG_FILE_LEVEL=DEBUG` to keep detailed file diagnostics while the
normal console remains at INFO. Leave it blank to use the console's configured
level for files as well.

Homepage initialization ignores unchanged market synchronization events.
Equivalent concurrent cache misses share one fetch. Market/account selection
revisions prevent an older result from replacing a newer selection. The market
and news panels share their news acquisition, while an explicit refresh still
requests current data.

## Calendar status and setup

On first startup, an unconfigured installation initializes its managed calendar
offline from the verified bundled 2026 SSE/SZSE schedule. Active files normally
live in the configured private data directory under
`calendars/trading_calendar.yaml`. Existing explicit and legacy calendars are
preserved. Calendar initialization does not download data during startup.

Open **System Settings → Scheduling and calendar**. **Initialize calendar** creates
a missing managed calendar without replacing an existing file. **Refresh official
calendar** reads bounded official originals and verifies the annual schedule
against the bundled version. It preserves the previous file if verification fails
or the schedule differs. Custom calendars continue to use their registered
calendar tasks; selecting a custom path does not authorize overwriting it.

The status displays market, source, coverage and update time. Missing, invalid
and out-of-range schedules are unavailable. Trading-day tasks skip unavailable
file-backed schedules rather than assuming every weekday trades. Explicit manual
inline calendar rules remain supported. HK execution retains its separate
verified calendar; a CN schedule does not supply HK coverage.

The bundle currently covers **2026 only**. An annual verified schedule needs a
new version when its coverage expires or an exchange changes the schedule.
Government makeup-work weekends do not imply exchange sessions. Sources:
[SSE notice](https://www.sse.com.cn/disclosure/announcement/general/c/c_20251222_10802507.shtml),
[SZSE notice](https://www.szse.cn/disclosure/notice/t20251222_618087.html).

## Gainers, decliners and sample scope

Open **Market Research → Quotes** and select **Gainers and decliners**, **Top
gainers** or **Top decliners**. The default combines positive and negative boards;
each row identifies its ranking side. This describes price changes, not realized
portfolio profit/loss. Industry and concept boards use the same selection.

The provider obtains both ranking directions, or reuses a complete cached board
universe. Reversing a truncated top-gainer list cannot establish the decliner
ranking. Missing/nonfinite returns do not become zero. An all-up market can have
an empty decliner list, and an all-down market can have an empty gainer list.
No opposite-sign observations are invented to fill the requested row count.

The homepage heatmap uses a balanced sample and remains labelled as a sample.
Displayed counts and sector-member breadth do not establish full-market breadth.
Check source and timestamp columns when comparing observations.

## Fundamentals and financial statements

The existing fundamental route now opens **Fundamentals & Financial Analysis**.
The default mainland code is `600519`, configured in
`egs/config/data/economic_analysis.yaml`. Navigation alone does not fetch sources
or generate a model report. Empty codes and invalid reporting periods are rejected
before source acquisition. Current financial/macro adapters support mainland
companies; HK financial statements remain explicitly unavailable.

After loading one snapshot, inspect **Income statement**, **Balance sheet**,
**Cash flow**, **Financial ratios** and **Financial history**. The overview and
charts remain available below. These are selected statement summaries, not a
claim of complete audited filing coverage. All sections reuse the same immutable
snapshot, and switching sections does not fetch the sources again.

Income/cash-flow amounts are cumulative year-to-date unless labelled single
quarter or TTM. Missing values, negative comparison bases, financial-industry
restrictions, quote timestamps and peer-period limitations remain visible. See
[economic analysis](economic_analysis.md) for accounting and source boundaries.

## Responsive relationship graphs

The default **Data and rules** mode starts at one hop. Deeper exploration remains
selectable. **Query relationships** creates a background run and immediately
returns its ID. Progress reports completed source stages. **Cancel rule graph**
stops the owned worker process, including unfinished provider threads.
Starting a new run clears the previous graph/export controls. Cancelled or failed
runs clear the current view; previously saved artifacts remain available by run ID.

The default whole-run deadline is 30 seconds, covering worker startup, provider
lock waits, initial quotes, branches and enrichment. The web process remains
responsive. A timeout/source failure can retain a clearly labelled partial graph;
no checkpoint means a failed run rather than invented relationships. Repeated
identical active requests reuse the active run. The provider gate coordinates
web and worker traffic across processes.

Export downloads the saved graph for the displayed run ID. Changing form inputs
does not change that artifact, and export does not perform another construction.
Private records live under `rule_graph_runs/<run-id>/` in the data directory.
The existing synchronous `/api/v1/relations/graph` endpoint remains available;
the responsive page uses the background lifecycle.

**CLI + Skill research** remains independent and optional, with explicit model
generation, original evidence, inference filters and saved-result history. See
[model relationship graphs](model_stock_relationships.md).

## Verification and limitations

Actual checks with the user's existing Conda/Python 3.11 interpreter verified
official calendar refresh, positive/negative board rankings, four financial
source groups for the 2026-09-30 reporting period and a shallow rule graph.
The measured standalone fetches took approximately 3.8 s (calendar), 6.7 s
(rankings), 4.5 s (financials) and 7.5 s (rule graph). These measurements are
environment/source observations rather than latency guarantees.

Controlled checks separately exercise missing inputs, cache concurrency, invalid
calendars, all-up ranking data, worker deadlines/cancellation and provider-lock
contention. Browser checks exercise the financial sections, immediate run
acknowledgement, continued health responses and byte-identical saved exports.
No model generation is needed for these checks. Public-source outages, incomplete
relationship coverage and historical point-in-time restrictions remain explicit.

The task-focused suite passed 75 cases and the existing Conda interpreter passed
70 related cases. Later focused lifecycle/calendar/cache checks passed separately.
These counts overlap and are not a full-repository pass claim. Broader legacy UI
checks still expose an older knowledge-label assertion and a factor-cache path
restriction with external isolated data. Dependency audit exceeded its 30-second
budget; OSV Scanner was unavailable. No package versions were changed.
