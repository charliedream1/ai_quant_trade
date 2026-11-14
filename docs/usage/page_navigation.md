# Cancelling work when changing pages

Change the sidebar destination or an in-page module tab to leave a slow page.
The destination appears immediately. Loading, searches, temporary previews and
page-created relationship graph runs on the previous page are cancelled. Hidden
pages stop issuing timer requests. Returning to a cached page retains its form
inputs and completed display; refresh or repeat the action to start new work.
A cancellation notice can appear when an outstanding load was abandoned.
The lightweight Gradio session heartbeat remains available to retain cached
session state; it does not continue the abandoned source reads.

This applies to initial dashboard loads, quotes/news, company and financial
analysis, knowledge Q&A, document previews and both rule/CLI relationship modes.
Knowledge attachments already imported before cancellation and completed saved
reports remain stored. Cancellation does not undo completed writes or consumed
model requests.

Windows and browser tabs have separate lifetimes. If another window still needs
the same shared query or graph, leaving one window only detaches that window.
The backend terminates the producer after its last consumer leaves. Closing or
reloading the browser also cancels its transient work. If a close signal is lost,
the inactive lifetime expires after the configured heartbeat grace period.
Side-panel document readers keep a separate preview lifetime. Leaving their
parent view stops pending Office conversion and preview polling; unsaved Markdown
stays in the cached reader. Return to that view to recover the draft. Use the
reader's **Reload** control to restart an abandoned conversion.

Submitted independent backtests/research campaigns, schedules, paper trading and
live services keep their own lifecycle. Leaving a result viewer stops viewing
updates; use that job's explicit stop control to cancel the producer. Closing the
browser does not shut down the application server.

## Configuration and diagnosis

`egs/config/ui/page_work.yaml` defines the worker count, read deadline, heartbeat,
document capacity and explicit transient callback/source policies. The default
pool has four processes. The homepage callbacks share one process to retain
snapshot/news cache reuse; other page reads use the remaining capacity. Idle
workers are reused, and a worker stopped during a read is replaced when needed.
No new Python dependency or special Conda environment is required.

Normal cancellation is silent at INFO and is recorded at DEBUG. Detailed
diagnostics remain private; see [runtime diagnostics](runtime_market_research.md).
Unexpected worker failures retain their original error type and redacted details
in the private backend log; the browser receives the public error message.
Completed reads preserve table styling and charts across the worker boundary.
Model RPM admission records remain counted after cancellation, while concurrency
slots owned by a terminated worker are released.

For remote access, keep the existing authentication, host and TLS settings.
Lifetime control requires the same origin and an unpredictable per-document
capability. Never publish runtime files or private test evidence. See
[runtime principles](../principles/runtime_navigation.md#page-owned-work).
