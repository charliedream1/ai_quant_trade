# Page-owned work cancellation on navigation

Date: 2026-11-14. Status: approved and implemented; acceptance evidence is recorded in the weekly changelog.

## Problem and evidence

The shell caches module iframes and sends a deactivate message when switching
modules. The child route handler currently cancels only routing observers and
timeouts. Same-module view changes also cancel only those routing waits. Existing
source requests, Gradio callbacks/streams and timers can continue in hidden views.

The shared safe-callback boundary records market context but has no page-owner
cancellation context. SSE already has a stop event for some streaming work, while
ordinary callbacks have no equivalent common lifecycle. The initial Gradio build
path also uses one shared UI-build limiter. Cancelling its awaiter does not stop
the synchronous thread: AnyIO defaults to waiting for thread completion.

These gaps explain why old work can retain provider locks/capacity after a
navigation change. Ignoring stale results alone does not reclaim those resources.

## User behavior

Switching modules, switching views inside a module, browser back/forward and
leaving/reloading the document invalidate the previous page's transient work.
Navigation updates the visible destination immediately and never waits for the
old page's cleanup. Returning to the page preserves available form inputs and
shows a cancelled state rather than silently restarting abandoned work.

Page-owned work includes initial data loading, quotes/news/financial reads,
temporary searches, chart computations, preview reads and rule/model graph work
created for that page. A viewer leaving an existing run stops its polling or
subscription; viewing alone does not acquire permission to cancel its producer.

Explicit independent jobs retain their existing lifecycle: submitted backtests,
durable research campaigns, schedules and trading services. In particular,
submitting a backtest and navigating to its result must not cancel the backtest.
Each callback and spawned run must be classified explicitly; do not infer task
ownership from the most recent run, a function-name pattern or a process-wide flag.

## Page ownership and cancellation protocol

Introduce a bounded page-work registry, with an owner unique to the top-level
browser document, the module/view and a monotonically advancing navigation
revision. Embedded frames inherit that ownership; independent windows receive
different owners. Ownership must be associated with authenticated workspace and
Gradio session context where applicable, with same-origin validation and bounded
metadata. Missing legacy metadata must not authorize cancellation of other work.

Activation invalidates earlier revisions atomically. Cancellation signals apply
only to work owned by that document/revision. An out-of-order old activation,
deactivation or pagehide message cannot cancel the newer page. Expiry/recovery
handles closed tabs or a missing browser signal without retaining unlimited
registry entries.

Browser transport cancels obsolete fetch/queued-event/SSE work and suspends
hidden-page polling. Backend callbacks receive a cancellation context and check
it before source acquisition, provider-lock waits, retries, expensive transforms
and publication. Expected navigation cancellation is not an application ERROR
or a repeated error toast. Completed saved results and entered user content are
preserved; this operation does not delete files or undo committed writes.

## Releasing resources

Reuse existing run cancellation for owned rule/model graph processes and native
CLI calls. Cancellation must stop owned subprocesses, release task leases and
quota/provider slots and stop subsequent source calls. Preserve observed usage
and partial evidence; cancellation cannot undo already consumed model tokens.

For blocking read-only network/SDK/CPU work that cannot stop cooperatively, use
a bounded owned-worker boundary rather than claiming that cancelling a Python
Future or abandoning a thread terminates it. Verify termination and resource
release independently of the browser's loading indicator. Do not edit installed
packages or close a shared client/session in a way that disrupts other users.

Separate expensive reads from synchronous Gradio construction so they cannot
hold the shared build queue indefinitely. Skip obsolete queued builds. Keep
SDK context-critical construction bounded and validate its isolation on both
installed Gradio versions before permitting independent module construction.
The new destination must remain navigable while an obsolete source/build wait
is being cancelled.

## Shared work and saved state

Coalesced cache misses and deduplicated runs need consumer ownership. Leaving
one page detaches that consumer; shared acquisition is cancelled only when no
active consumer remains. An independent subscriber/run retains its explicit
lifetime. Incomplete/cancelled results must not be presented as a new successful
snapshot or overwrite a newer page's state.

Retain form/draft preservation and existing unsaved-edit handling. Avoid removing
a cached iframe simply to conceal ongoing work. Pause its activity and reject
late updates; dispose resources when the frame is evicted. Keep shell-wide
notifications, navigation and unrelated sessions operational.

## Integration scope

The minimal integration spans shell/child navigation, a shared request/stream
bridge, callback cancellation context/registry and page-owned source/run adapters.
Reuse current task leases, stream-stop context, worker process control and cache
infrastructure. Store tunable limits/operation policies in YAML and keep new
source comments and documentation English.

Apply the policy to homepage loads, market/news/financial reads, knowledge
queries/previews and rule/model graph views. Audit other module loads through
the common callback boundary so navigation cannot leave untracked transient
work. Preserve existing REST/CLI behavior and independent execution contracts.

## Verification

Reproduce a stalled source and a provider-lock wait, then navigate to a new page.
Measure destination interaction, cancellation acknowledgement, source/worker
termination, slot release and zero late updates. Cover cached and cold modules,
same-module views, rapid A/B/C changes, back/forward, reload and closing a tab.

Verify that two independent windows sharing a query do not cancel each other,
and that backtest-to-result navigation leaves the independent backtest running.
Check form/draft retention and return-to-page behavior. A cancelled load must
neither auto-restart in a hidden frame nor publish its old result into the new
view. Normal navigation cancellation must not generate console ERROR spam.

Use controlled slow/failing endpoints and actual public-source browser runs with
the existing Conda interpreter and project environment. Keep hard-stop tests in
owned test processes. Use fresh E-drive scratch directories, no implicit cleanup,
and stop only test-owned services. Run applicable pytest, Ruff, mypy, security
checks and both strict documentation builds. Update usage/principles and the
weekly changelog. Do not delete files, alter installed packages, commit or push
as part of this proposal.

## Implementation decisions

Transient read policy and tunable limits live in a dedicated UI YAML. The early
browser bridge is injected ahead of Gradio scripts and supports both installed
Gradio generations. The server registry uses document capabilities, ordered
revisions, same-origin control and expiry. Callback publication checks remain a
second guard even after the browser cancels its transport.

A reusable spawn-based pool isolates synchronous read callbacks and graph source
acquisition. Trusted named dispatch avoids additional serialization packages;
table styling crosses as Gradio metadata. JSON observations preserve snapshot reuse across independently scheduled homepage workers. Coalesced reads and graph runs track their active creators, while
independent callers retain an explicit consumer. A terminated read worker frees
only its own model concurrency slots and retains RPM admission history.
Nested document readers use separate preview capabilities. The parent view
suspends their requests and conversion consumers while preserving editor state.
Conversion processes stop after the last reader leaves; an explicit reload can
retry without deleting the original or incomplete private evidence.

The browser uses the native Gradio cancellation endpoint for queued events,
allowing the SSE close message to drain. Directly aborting that stream produced
an upstream async-generator error during acceptance. Other stale requests are
aborted, hidden timers pause, and cached drafts remain available. Independent
backtests/research and trading services keep their separate lifecycle.

Tests cover actual worker/HTTP termination, file-lock release, shared consumers,
out-of-order revisions, input retention, cold module construction and graph
ownership. Runtime acceptance uses the current Conda interpreter and the project
environment. Linux process-tree behavior is reviewed and unit checked; this
Windows workstation does not establish a physical Linux browser acceptance run.

Standalone acceptance also exercises first-use financial snapshots near the
legacy Windows path limit. Atomic temporary filenames use a short unique name
in the destination directory instead of repeating the snapshot hash. Financial
browser fixtures are explicitly loaded inside each worker, avoiding accidental
dependence on live sources or a pre-existing cache. Unexpected worker errors
retain redacted diagnostic details while public error messages remain bounded.
