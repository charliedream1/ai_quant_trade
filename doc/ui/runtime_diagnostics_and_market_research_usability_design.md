# Runtime diagnostics and market research usability

Date: 2026-11-14. Status: implemented and verified; acceptance and limitations are documented in docs/usage/runtime_market_research.md.

## Findings

Startup output in `start.py`, `core/runtime_environment.py`, `core/logger.py`
and `api/app.py` contains Chinese messages and repeated readiness information.
Frontend callbacks log both start and finish at INFO with operation identifiers,
source locations and timing fields. Every successful callback exceeding 1,500 ms
becomes a WARNING. The supplied 2,311 ms financial callback therefore indicates
slowness, while the later empty-symbol ValueError is an actual failed request.
Homepage load and market-change bindings can overlap, and the shared UI cache
releases its lock before loading, allowing duplicate concurrent misses.

The active calendar path is unset. Status falls back to
`egs/config/data/trading_calendar.yaml`, which does not exist; only an empty
example template is present. Creating an empty template cannot establish valid
market holidays or coverage. Scheduler path resolution and health reporting must
agree on the same active file and market.

`EastmoneyDataSource._load_sectors()` requests descending change percentages,
then returns a limited prefix. `QuoteService.sectors()` sorts that prefix in
descending order again and does not implement its sort argument. Both the
market page and homepage reuse this biased sample. The view describes price
changes, not realized portfolio profit/loss.

The fundamental page has no initial stock code and forwards blank input to
`EconomicAnalysis._symbol()`, producing the reported ValueError. The existing
financial engine already fetches income, balance-sheet, cash-flow and financial
indicator datasets and computes period/growth/cash-flow metrics. Its UI exposes
mostly one mixed metric table and two trend panels, making financial analysis
hard to find. This data adapter currently supports mainland companies.

The rule graph callback runs synchronously and performs extra stock/sector reads
after graph construction. Initial quote/board acquisition is outside the layer
deadline. `_http_get()` holds a shared Eastmoney lock during request execution;
layer workers can wait behind unrelated requests. Cancelling a Future does not
stop an already running network operation. The model graph already has separate
explicit generation and saved-run controls and must remain optional.

## English and concise diagnostics

Use English for application-controlled startup, preflight, readiness and shutdown
messages, including dependency diagnostics. Preserve strict/non-strict behavior,
credential redaction and existing package validation. Show a compact readiness
summary and actionable warnings in the normal console; put startup phase/router
details, successful callback start/finish, operation IDs and source locations at
DEBUG. Diagnostic verbosity and timing thresholds belong in YAML configuration.

Distinguish expected input rejection, slow successful work, source unavailability
and unexpected execution failure. Keep real failures visible. Normal network
latency alone should not produce repeated warning pairs. Optional detailed file
logging remains available without flooding the normal console.

Deduplicate equivalent homepage initialization and concurrent cache misses.
Scope reuse by market, data source and request parameters. Explicit refresh must
still fetch current data, and older requests must not overwrite a newer market
selection. Do not suppress useful failures merely to reduce log volume.

## Reliable calendar setup

Provide a versioned 2026 mainland exchange schedule in YAML, with official source
links and explicit coverage. Use an approved bundled schedule for first-run setup
when no user calendar is configured. Keep the active managed calendar under the
configured private data directory. Reuse existing explicitly selected/legacy
calendars without deleting or silently overwriting them.

Expose calendar status and an explicit initialization/refresh operation in system
settings. A source failure preserves the prior valid calendar and reports the
failure. Missing, invalid and out-of-coverage calendars remain distinct states.
Startup must not block on a network download. Validate actual exchange sessions;
government makeup-work weekends are not automatically trading sessions. Preserve
the separate verified HK calendar and display unsupported market coverage
explicitly. Do not invent dates beyond a published schedule.

Official references:

- [SZSE 2026 holiday notice](https://www.szse.cn/disclosure/notice/t20251222_618087.html)
- [SSE 2026 holiday notice](https://www.sse.com.cn/disclosure/announcement/general/c/c_20251222_10802507.shtml)

## Balanced market presentation

Show top gainers, top decliners and an overview/scope indicator for industry and
concept boards. Obtain both ranking directions from the provider or a complete
validated board universe; reversing a truncated top-gainer list is insufficient.
Respect sorting in the service/provider/API/cache keys and preserve existing
default API behavior for callers that omit the new selection.

Label the homepage heatmap as a sample and construct a balanced sample from both
directions. Handle all-up, all-down, flat, unavailable and missing-number cases
honestly. Do not manufacture a negative board or substitute zero for missing
returns. Positive/negative counts must identify whether they cover the full
market or only the displayed sample. Preserve source and timestamp metadata.

## Discoverable company financial analysis

Keep one fundamental/financial workspace rather than adding a duplicate page.
Expose statement summaries, financial ratios, multi-period trends, cash-flow
quality, peers, valuation timestamps and sources as clear sections/tabs. Reuse
the existing immutable financial snapshot and calculation engine. Distinguish
year-to-date, single-quarter and TTM values; preserve missing/negative-base and
financial-industry limitations. Do not present selected metrics as a complete
audited financial statement.

Set a valid mainland default code in YAML. Validate empty/whitespace input and
invalid periods before starting source work; show actionable field errors and
retain the entered value. Default values must not launch a model or network
analysis merely on navigation. HK financial coverage remains explicitly
unavailable until a suitable adapter exists; HK quote/graph support is preserved.

## Responsive relationship research

Make rule graph generation a bounded background action with immediate progress,
per-stage source status, cancellation and an overall deadline. Start from a
configured shallow default while retaining deeper exploration controls. The
deadline must cover initial acquisition, shared-provider-lock waits, retries,
branch work and presentation enrichment. Do not mistake Future cancellation for
termination of a network request. Stop subsequent acquisition after cancellation
and release task/provider resources.

Avoid redundant quote/sector reads and fetch only branches needed for the
selected relation types. Retain completed branches on source failure as a clearly
labelled partial result. Keep graph view/export tied to the same completed run;
export and navigation must not trigger a second network/model construction.
Keep caches market/date/filter/depth scoped and prevent duplicate requests from
starting duplicate work. Preserve the independent CLI + Skill mode and all
existing citation/inference safeguards.

## Scope and verification

Production changes are limited to startup/logging, calendar setup/status, market
ranking/cache presentation, existing financial views/input validation and rule
graph execution. Prompts/settings/examples remain in YAML; new comments and
documentation are English. Preserve unrelated working-tree changes, installed
packages, private memories and user data. No deletion, commit or push is included.

Test with the user's current Conda/Python 3.11 interpreter and the declared project
environment. Check console log volume/content and DEBUG diagnostics, one-time
initialization, real official calendar dates and coverage, mixed/all-up/all-down
rankings, default/blank stock input, financial arithmetic/source periods and
unsupported markets. Exercise stalled sources, provider-lock contention,
cancellation, partial graphs, repeated clicks, saved export and browser navigation
responsiveness. Verify actual public market/financial sources separately from
controlled failure fixtures and report source outages honestly.

Run applicable unit/integration/browser checks, Ruff, mypy, secret/dependency
checks and both strict documentation builds. Record before/after timings and
limitations, update usage/principles/design and the weekly changelog, and stop
only test-owned services. Private evidence and temporary files stay on the E
drive; file cleanup requires separate explicit authorization.

## Implementation decisions

Rule construction runs in an owned disposable Python process. The parent enforces
the whole-run deadline and cancellation and can stop unfinished network threads
with that process. Source checkpoints are atomic, labelled partial results. An
interprocess provider gate coordinates web/worker traffic without editing SDKs.
The legacy synchronous graph API remains available; the page uses background
runs and exports its saved artifact.

Gradio module reuse is scoped by private data/database/runtime identity to avoid
callbacks retaining another application's store. Homepage session revisions
reject stale responses and ignore unchanged market synchronization events.
Successful callback diagnostics require DEBUG; normal console output preserves
readiness, actionable warnings and errors.
