# Ask about the active page

The floating assistant has a default-enabled **Use current page context** control.
It applies to model/API conversation, CLI conversation and knowledge Q&A. Click
**Preview current page context** to inspect the scope and bounded evidence before
sending. Previewing does not call a model or reload market sources.

Load the page's normal rule data first, then ask a concrete question such as
"What does this ratio mean?" or "Which assumptions explain this result?" The
assistant receives the active module/view, market, available selected inputs and
server-completed observations. These may include indicator tables, compact chart
series, reporting periods and saved task IDs. It does not scrape the whole screen.

The scope line identifies the page and source-group count. Page observations use
`P1`, `P2`, etc.; knowledge-document citations keep their independent numeric IDs
and original previews. A page number is not a quoted document passage. Knowledge
retrieval retains its existing library/document/session access restrictions.

If nothing has been loaded, the assistant gets page identity and a missing-data
state. If current inputs no longer match the loaded result, old observations are
excluded; refresh the rule view before asking about the new selection. Data can
also be unavailable after navigation because page snapshots are isolated by
window/revision. Unsupported configuration/login views provide safe page identity
only, without credentials or form values.

Large sources are compacted or omitted within configured row/text/total budgets,
and the context reports this limitation. The original rule view remains the
complete source. Preview values are not silently treated as full-market coverage,
real-time prices or independently verified calculations. Source timestamps and
mock markings remain inspectable.

Turning the control off sends the ordinary question/history/attachments without
page evidence. The visible user message remains unchanged when context is on;
redacted scope identity and a digest are stored with model-chat turns. Changing
the page/data scope starts a fresh floating conversation to prevent prior page
facts being reused as current evidence. Older stored sessions remain in history.
Knowledge Q&A uses a scope-specific floating session for the same reason.

The context is assembled when previewing or sending, with no hidden polling.
Navigation invalidates old source/answer updates through existing page lifetimes.
Generation retains the existing model guards, backend permissions, RPM and stop
behavior; this feature does not grant trading, filesystem or publishing rights.

Policy, prompts and English copy live in `egs/config/ui/assistant_context.yaml`.
The page input/method mapping reuses `egs/config/ui/page_analysis.yaml`. Context
sources are server-owned completed results, not browser-provided arbitrary facts.
Only currently supported mappings receive data; unavailable fields are not guessed.

Acceptance inspects API and CLI prompts using declared controlled responses,
tests context off, stale inputs, window/revision isolation, budget/privacy guards,
knowledge citation separation and both installed Gradio versions. This establishes
context delivery and UI behavior, not external model answer quality or live data
completeness. See [page Skill analysis](page_skill_analysis.md) for the separate
one-click report workflow.
