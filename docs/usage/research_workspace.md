# Research workspace controls

The floating assistant lists enabled real HTTP model profiles. Missing model
configuration produces a setup error; explicit market-data test mode does not
authorize a simulated assistant answer. Native CLI choices retain their existing
installation and authorization checks. Model keys stay in the local environment.

Drag the assistant header to move it, or its bottom corner to resize it. The
corner also accepts arrow keys. Size persists in browser storage and is bounded
again when the viewport changes, including while the panel is closed.

Knowledge Q&A separates the answer from **Sources and full citation**. Retrieval
settings collapse independently. Select a source title to open its full chunk
and original-file preview; large answers and references scroll separately.

## Company and sector research

**Stock Analysis** shares one code between **Technical analysis** and **Financial
analysis**. Enter the company once, then explicitly load the desired data.
Switching sections cancels unfinished transient reads. Existing fundamentals
URLs open the financial section. Macroeconomic research remains independent.
Financial coverage restrictions, such as unavailable HK statements, still apply.

**Industry and Concept Sectors** shows sector rankings with indices for context.
The homepage **Sector performance overview** shows the count, source and time of
the returned observations. Partial coverage is not fake data, but it also does
not establish full-market breadth. Configured development data remains labelled.

## News and notifications

News geography and topic are independent filters. A cross-border item can affect
several markets. Only items matching an explicit transmission channel enter the
default list: monetary/fiscal policy, regulation/trade, supply/energy or material
market/company events. Ordinary unrelated politics and entertainment are excluded.
Unknown locations and source times stay unknown. Each item includes inclusion
reasons and affected asset tags; these rules are not price predictions or a claim
that every relevant original has been found. Original news records are retained.
Policy and word lists live in `egs/config/data/market_news.yaml`.

The inbox defaults to **today in Asia/Shanghai**. Choose a date or **View history**
to inspect earlier records. The badge and mark-as-read action use the displayed
scope. Dates use original occurrence time, not the time an old task was imported.
Repeated successes collapse into an expandable group. History is not replayed as
toasts; unresolved critical events retain a compact carryover summary. Reading
or dismissing a card never changes the business source or deletes its history.

## Operation logs

INFO logs identify page selection, explicit actions, queued/started reads,
meaningful source stages, cancellation and completion. They include operation
identifiers and elapsed times without prompts or uploaded contents. Heartbeats,
polling and repeated automatic callbacks stay at DEBUG. Progress reports stages,
not invented percentages. Model requests can consume time before returning a
response; changing pages cancels eligible page-owned work as described in
[navigation cancellation](page_navigation.md).

Interaction limits and copy are configured in `egs/config/ui/research_workspace.yaml`;
daily inbox configuration remains in `egs/config/ui/notifications.yaml`.

## Loading performance

Homepage operations use a small service facade. Domain exports and feature renderers
load on demand, one lightweight worker warms initially, and independent account,
market and news callbacks no longer queue behind each other. Raw observations
share a runtime-scoped JSON cache; stored source times remain unchanged. Worker
logs distinguish assignment, readiness and business stages. Cached navigation and
first data completion are separate timings; real source gates and network delays
still apply. A hard cancellation may require a replacement worker on the next action.

## Sections appear as they become ready

The active page and its controls appear first. Independent sections can update
in parallel, while sections that share data follow their dependencies. For
example, index data can be visible while sectors are still loading; search
results appear before their chart; retrieved citations appear while the model
answer is pending. The homepage uses independent account, market, local-task and
news groups. Each group retains the established complete-result transport on
both supported Gradio installations; its eight account metrics and six plots
must remain available after initialization, refresh and return navigation.

Loading markers belong to individual sections. A failed section is marked for
retry and does not erase completed sections. Use the view's refresh/query control
to retry. Switching pages cancels unfinished work and marks pending sections
cancelled. Financial tables and charts continue to reference one saved snapshot;
display timing does not authorize mixing reporting periods or unfinished ratios.

The application uses cumulative streamed updates for eligible read callbacks.
Ordinary service/API return values and independent accepted-job lifecycles remain
compatible. Writes retain their atomic behavior, and single-result forms/readers
keep their existing independent request boundaries.
