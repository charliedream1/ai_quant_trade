# Progressive section loading across workspace pages

Date: 2026-11-15 (UTC+08:00). Status: implemented and verified in browser simulations on both installed Gradio versions. Scope: the approved page-loading performance work.

## Behavior

Render the workspace and active-page controls first. Independent sections load
concurrently; dependent sections load in order. Publish a section as soon as its
own data and presentation are ready. A slow chart, source or model must not hide
an already completed table or citation. Pending sections carry their own loading
marker. Failed sections show failure/retry state; completed sections remain.
Leaving the page cancels its unfinished work and marks pending sections cancelled.

Financial statements and ratios retain one immutable snapshot. Tables, raw
evidence, snapshot identity and charts can appear at different times, but they
must not combine different snapshots. Submitted backtests, research jobs and
trading services retain their independent producer lifecycle.

## Read paths and dependencies

| Page area | Early publication | Subsequent publication |
| --- | --- | --- |
| Homepage | Local state, account metrics and each completed source | Dependent risk plots, market summary and remaining charts |
| Sector monitoring | Index table | Sector table, then sector plot |
| Company research | Available quote summary | Scores, indicators, K-line, news and reports |
| Financial/macro research | Validated snapshot table, raw evidence and identity | Derived section views and history chart |
| News | Filtered list and count | Keyword visualization |
| Reports and papers | Search results and status | Rating/distribution chart |
| Backtest result viewer | Metrics and explanations | Equity, attribution, trade and diagnostic views |
| Paper-account viewer | Overview, positions and orders | NAV chart |
| Model administration | Model table | Usage statistics chart |
| ETF and candidate comparison | Status and tables | Styled coverage and comparison charts |
| Factor read adapters | Shared snapshot status, metrics and tables | Dependent diagnostics and factor plots |
| Knowledge Q&A | Scoped retrieved citations | Model-generated answer and persisted conversation |
| AI/Skill/graph jobs | Existing acknowledgement and progress | Existing streamed events, saved result and export |
| Single-result forms/readers | Existing independent local read or preview stage | Existing explicit actions; no whole-page barrier |

Unused tabs remain on-demand. Writes are not divided into partial commits for
display purposes. Composite callbacks with ambiguous output mapping retain
their transaction/snapshot boundary rather than publishing to incorrect fields.

## Transport and compatibility

An optional section observer supplements existing service methods without
changing their normal return values. Owned read workers send bounded indexed
updates over the existing private pipe. Each browser consumer receives its own
sequence while equivalent reads keep shared ownership. The parent adapter only
waits for cancellable owned work; abandoning its UI generator releases its read
subscription instead of abandoning a network/SDK thread.

The shared safe-callback boundary registers eligible reads as queued generators
in both installed Gradio versions. A dedicated context advances each generator
because executor threads can differ between iterations. Every yielded result
retains previously delivered values: the SDK computes differences from cumulative
state. Using isolated skip patches loses earlier output under streaming diffs.
Existing component classes, including original-evidence translation protection,
are preserved when loading/failure markers change.
The SDK's whole-callback progress overlay is disabled for these events so it
cannot dim completed content while another section is still pending.

## Verification

Use a controlled source that returns indices immediately but blocks sectors.
Assert the index is visible while the worker and sector request remain pending.
Then release the sector and verify its table/chart appear without losing the
index. Repeat with source failure, retry and navigation cancellation. Validate
early knowledge citations before the final model answer, stable financial
snapshot identity, read return compatibility, shared consumers and both Gradio
versions. Evidence stays on E; stop owned services and retain failed attempts.

The blocked-sector browser case passed for success, failure and retry. A gated
OpenAI-compatible local endpoint confirmed that retrieved citations are visible
before the answer is released; this verifies rendering order rather than external
model quality. Existing navigation, shared-consumer, snapshot and accepted-job
regressions passed. Ordinary backend/service calls still return complete tuples.
