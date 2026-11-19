# Floating assistant context from the active research page

Date: 2026-11-18 (UTC+08:00). Status: approved and implemented; controlled acceptance and external-model limitations are recorded in the weekly changelog.

## Observed behavior

The floating assistant is rendered inside each module, but its model-chat send
callback supplies only the message, chat history, attachments, backend/model,
reasoning effort and access mode. The service delegates to workspace chat and
does not append active-page observations. Knowledge Q&A sends its question and
retrieval settings independently. Being mounted on a page does not mean the
model receives the page's data.

Relevant locations: frontend/features/assistant.py:render_floating_assistant;
frontend/service/assistant.py:floating_send/floating_qa;
agent/workspace_backend.py:backend_events. The existing page_work capability and
page_analysis_snapshot capture already supply useful server-side foundations.

## Intended behavior

The assistant can answer questions such as why a selected stock has a particular
indicator, which cost assumptions apply to a backtest, or what a displayed
financial ratio means using the active page's actual observations. It should
include enough relevant context within a configured budget rather than dumping
the entire page or silently refetching all sources.

Add an explicit Use current page context toggle, enabled by default for supported
research views, with a compact scope summary and an expandable context preview.
The preview shows page/subview, market, canonical security or saved task identity,
period/filters, observation timestamp, available data sections, gaps and truncation.
Turning it off retains normal chat. Do not call a model merely to build a preview.

Collect context at each send rather than only when the panel opens. Reuse the
server's completed rule observations and active browser capability/revision;
bind current controls using the same page registry. Preserve source identity,
snapshot/task IDs, accounting period, units/currency and mock/stale markers.
Include deterministic table values and compact chart series where available,
not screenshots or invisible DOM text. Do not let browser-submitted HTML or
arbitrary fact bundles become trusted source data.

If inputs changed but the displayed result was not refreshed, show the mismatch
and exclude the old result from current-data claims. If no data has been loaded,
provide the known page/selection context with an explicit missing-data state and
invite a rule refresh. Unsupported administrative or login pages provide only
safe page identity/help context, never configuration values or credentials.

## Model, CLI and knowledge integration

Model-API and CLI conversation paths receive the same bounded evidence envelope.
Keep the visible user message separate from the appended contextual evidence so
chat history is readable. Persist a redacted context identity/summary alongside
the turn where appropriate, allowing answers to be traced to their original
scope. Do not silently replace the stored user question with a large evidence dump.

For knowledge Q&A, use page context to clarify the question and retrieval plan,
but retain existing library/document/session restrictions. Page observations and
retrieved document citations are distinct evidence types. A displayed number
must not be presented as a quoted document passage; document citations retain
their original IDs and previews. All original text remains untrusted data rather
than instructions.

No automatic CLI/backend fallback, change to real-model guards, expansion of
filesystem permissions, native tools, order placement or externally published
messages is introduced. RPM, Langfuse redaction and explicit stop/navigation
cancellation continue through the existing call boundaries.

## Isolation and history

Context is scoped by database, browser window, page capability/revision, market
and selected subview. It must not contain another tab's page data. Navigation
updates the scope badge and invalidates pending context/answer updates. Old
conversation turns keep their original page label; they cannot establish the
current stock or a newly selected reporting period. Either partition conversations
by page context or attach explicit turn scope with a clear reset policy; do not
carry stale page facts forward as current facts.

Collapse state and preview contents must not start hidden polling or reproduce
the previous SDK 6.3 collapsed-control rendering issue. Context should be acquired
through explicit panel/send actions or safe local scope notifications, retaining
ordinary rule/chart loading behavior.

## Implementation and validation

Add a small context serializer/service that reuses page-analysis registry and
snapshot matching rather than a second source collector. Context budget, safe
fields, summaries, prompts and labels belong in YAML. All new design/usage text
and source comments are English; user-facing language remains configurable.

Exercise overview, sectors/news, stock technical/financial, macro, ETF/factors,
saved backtest/portfolio and knowledge/document views. Tests must inspect the
actual API/CLI prompt and verify page/market/security/task/period identity and
numeric values. Cover unloaded data, changed inputs, toggling context off,
bounded/truncated data, two windows, page/subview changes, chat history and
knowledge citation separation. Browser acceptance runs on both installed Gradio
versions and retains the complete eight-metric/six-plot homepage.

Use controlled model/CLI responses for prompt and answer provenance checks; do
not claim that those fixtures prove external model quality. Run relevant unit,
integration/browser, Ruff, mypy, privacy/security and strict documentation checks.
Synchronize usage/principles and weekly changelog. Retain temporary evidence on E,
stop owned services and preserve unrelated work. No dependency installation,
file deletion, commit or push is part of this proposal.

## Implemented contracts

The panel collects source/input scope only on preview/send, using the existing
page-analysis mapping and window/revision/market checks. Safe page identity is
available on unmapped views. Large sources receive explicit compact/omitted
labels; bounded JSON is never truncated into malformed prompt instructions.

A per-turn context variable appends the same evidence to API and CLI generation,
while stored user messages remain original and metadata retains only redacted
scope identity, digest and source count. Scope changes reset floating chat/CLI
history and model-chat session identity. Knowledge retrieval uses a scope-specific
floating session, contextual planning/answer evidence and unchanged document refs.

Streamed safe callbacks now retain one context across SDK executor iterations,
using the same dedicated-context iterator already used by progressive reads.
Browser testing exposed lost context and token-reset errors without this boundary.
Only actual view changes reset the local scope badge; repeated routing messages
must not overwrite a completed preview. Both corrections require regression
coverage alongside model/CLI prompt inspection.
