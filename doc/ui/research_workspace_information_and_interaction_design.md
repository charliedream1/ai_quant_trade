# Research workspace information and interaction improvements

Date: 2026-11-15 (UTC+08:00). Status: implemented and verified; measurements and limits are in the weekly changelog.

## Scope and existing evidence

This proposal covers the eight reported problems with the floating assistant,
dashboard naming, sector monitoring, news relevance, notification volume,
company research navigation, page responsiveness and backend visibility.
New comments and documentation are English. UI text follows the selected
language. Existing unrelated staged and working changes remain outside scope.

Source inspection confirms the following behavior:

- The assistant panel has a fixed CSS width and maximum height. Its button can
  move, but the panel has no resize controls. Knowledge Q&A places a fixed-height
  citation table below the answer, and the whole panel scrolls. Model choices
  currently include every enabled database row without checking simulation
  profiles. The shared model client can produce a simulated response when the
  process is explicitly in mock mode.
- The dashboard heatmap uses returned sectors with finite changes, normally a
  limited balanced selection. The word sample describes incomplete coverage,
  not synthetic observations. Renaming must preserve coverage disclosure and
  distinguish real mode from deliberately configured test data.
- The quotes page shows indices and industry/concept rankings. Its broad
  Market Monitor label does not accurately describe its sector emphasis.
- News uses one category field for company, international, domestic and finance.
  Geography and subject are mixed. The aggregator does not consistently enforce
  market relevance or isolate source geography across stored rows.
- Notifications select the complete retention interval, including unresolved
  critical history. There is no selected-date query. Repeated source states can
  produce new notifications when their signatures change.
- Financials and technical stock analysis are separate module views with
  separate symbol controls. An existing link connects them without sharing the
  full company-research context.
- Navigation already cancels page workers, but previous acceptance focused on
  a controlled stalled read. It does not establish responsiveness during large
  financial table updates, Plotly rendering, translation or simultaneous queue
  cancellation. The mount path also acquires a process-pool condition from the
  event-loop thread; worker startup holds that condition. This is a candidate
  blocking path, not yet a measured explanation of the reported freeze.
- Successful callbacks and their duration records are DEBUG. The default
  console explicitly suppresses frontend callbacks below WARNING. Navigation
  lacks a concise business event and live worker progress is mostly absent.

## Intended behavior

### Floating assistant

The visible assistant offers only configured real model/CLI choices. It must
also reject simulated profiles or responses at execution time; filtering labels
alone is insufficient. Missing real configuration produces an actionable setup
message. Offline fixtures remain confined to explicit test entry points.

The panel can be resized with mouse handles and moved by its header. Bounds
follow the viewport, size persists locally, and small screens use a usable
constrained layout. Closing, reopening, language switching and page navigation
preserve existing conversation behavior.

Knowledge Q&A uses a compact question/composer area, a growing readable answer
area, collapsible retrieval settings and a separately accessible citations area.
Long citations can be opened in full with source preview. Scrolling the answer
must not make the references permanently inaccessible. Existing retrieval and
library/document isolation remain unchanged.

### Dashboard and sector page naming

Rename the dashboard display to Sector performance overview. Show the displayed
sector count, selection basis, source and timestamp. Partial coverage remains
explicit; the selected subset must not become a full-market breadth claim.

Rename the current quotes page to Sector performance, with industry/concept
selection and an indices reference area. Keep its existing route compatible.
Do not imply that stock quotes, order books or full-market breadth exist on this
page merely by changing its title.

### Market-relevant news

Separate geography (domestic, overseas, cross-border, unknown) from subject
(finance/economy, politics/policy, with company/industry tags where useful).
Users can filter geography and subject independently. An overseas event's
location is separate from its potential effect on domestic markets.

Only include items with an identifiable market or policy transmission channel:
monetary/fiscal policy, regulation, trade restrictions, geopolitics affecting
energy/supply chains, industry policy or material company/financial events.
Display the relevance reason, affected market/industry tags, original source
and publication time. This is an explainable inclusion assessment, not proof of
future price movement. Ordinary social, entertainment and unrelated political
items are excluded. Ambiguous items are labelled or withheld, not invented.

Preserve original records. Add backward-compatible classification metadata and
versioned rules/configuration. Source timestamps must not silently become the
current time when parsing fails. Verify available source endpoints before adding
new adapters; missing coverage is reported instead of filled with fixtures.
The listing, homepage news and keyword statistics must use consistent filters.

### Daily notification inbox

Default to today's date in Asia/Shanghai, with date selection and an explicit
history view. Compute UTC boundaries from the selected local day. Group entries
by date and paginate within that day. The default badge and mark-as-read action
use the same visible date scope, including correct behavior at local midnight.

Keep original occurrence time separate from synchronization/import time so old
events are not relabelled as today's news. Deduplicate repeated source episodes,
coalesce high-frequency task summaries and avoid replaying history as toasts.
Unresolved serious issues from earlier dates appear in a compact carryover
summary linked to history. No notification records are deleted by this change.

### Unified company analysis

Move financial/fundamental research under Stock Analysis using one company and
market context, with technical/price, financial statements, fundamental metrics
and research subviews. Sources load only on explicit action or first entry to
their subview. Reuse an immutable snapshot across financial sections.

Remove the duplicate top-level financial menu entry. Existing fundamentals URLs,
report links and saved contexts resolve to the financial subview. Keep the
macroeconomic view independent. Unsupported market financial data remains
explicitly unavailable.
Nested subview transitions must also advance the transient-work lifetime;
moving financials under a tab must not bypass cancellation on exit.

### Responsive navigation and useful English logs

Measure financial-to-graph navigation with a stalled source, a completing source
and a large result being rendered. Capture browser long tasks, navigation timing,
callback queue state, worker lifecycle and provider lock ownership together.

Move blocking pool startup/cleanup away from the event loop. Remove synchronous
cross-frame heavy cancellation from the visible navigation critical path where
measurements justify it. Bound/deduplicate route messages, obsolete callbacks
and translation/table/plot processing. Preserve the existing hard cancellation,
shared-consumer isolation, draft retention and independent-job contracts.

At INFO, log page changes and explicit user actions with module/view, operation
identifier, start, queue/load stage, meaningful source progress, terminal status
and elapsed time. Progress is throttled and stage-based; unknown work does not
receive an invented percentage. Automatic timers, heartbeats and identical
polls stay DEBUG. Expected cancellation gets one clear lifecycle event.
Never log prompts, message bodies, secrets, uploaded content or private paths
as routine operation metadata. Genuine failures retain redacted diagnostics.

## Implementation sequence and verification

1. Establish a browser timing/log baseline for the reported financial-to-graph
   flow and crowded assistant before changing behavior.
2. Fix nonblocking navigation and structured lifecycle/progress events, then
   exercise cold/cached modules, same-module subviews and two windows.
3. Implement the resizable assistant, real-provider guards and usable references.
4. Consolidate company research and naming with compatible old links.
5. Add news geography/topic/relevance metadata and the dated notification inbox.
6. Review the combined diff and update English design/usage/principles, README
   feature summaries, site navigation and the weekly changelog.

Verify desktop/mobile sizes, pointer resize and persisted bounds; long answers
and citations; empty real-model configuration; domestic/overseas finance/policy
fixtures and actual available sources; date boundaries, pagination and repeated
notification synchronization; company-code consistency and legacy links.

Measure click-to-visible-view separately from destination data completion.
Use a target below 500 ms for cached-view navigation on the acceptance machine;
record observed measurements instead of declaring a universal guarantee. Check
that obsolete workers/connections stop, shared readers survive, no late results
overwrite a new view, and independent accepted backtests continue.

Run appropriate pytest unit/integration/browser tests under both the existing
Conda interpreter and the project environment, Ruff, mypy, secret/security checks
and both strict MkDocs builds. Preserve failed evidence. All temporary files and
test outputs stay on E; stop owned services. No package changes, file deletions,
commit or push are included without the corresponding existing authorization.
