# Fast page loading and bounded worker initialization

Date: 2026-11-15 (UTC+08:00). Status: approved and implemented; acceptance results are recorded in the weekly changelog.

## Measured problem

The configured Conda/Gradio 6.3 application log records a dashboard module build
of about 2.4 seconds. A homepage read was assigned at 13:38:19.507, but its first
business-stage event arrived at 13:38:42.840: a 23.333-second gap before source
processing became visible. News completed at 13:38:45.054; the market presentation
completed at 13:38:52.889. End-to-end callback records show approximately 25.6
seconds for news, 26.4 for account data and 33.4 for market data.

A fresh standalone import of the frontend foundation using the existing Conda
interpreter took 12.576 seconds with an isolated mock-data directory. This read
only import benchmark makes no market or model request. Its evidence is kept
privately on E. These measurements establish substantial initialization and
queue delay; they do not establish a universal timing for every environment.

## Confirmed amplification paths

Every first Gradio request initiates a four-process pool warmup. Each Windows
spawn process imports the frontend foundation before reading its first request.
Importing the service package also imports all its domain Mixins. The foundation
re-exports agent, research, backtest, trading, document and market dependencies.
Consequently, a simple homepage news read initializes unrelated domains, and four
workers repeat this cost together. Resource contention is a likely amplifier;
the independent import benchmark is not a direct measurement of that contention.

The four homepage callbacks have affinity to the same worker to reuse in-process
snapshots. This serializes account, market, news and operational reads. Slow news
can therefore delay unrelated account/market results. Market composition also
fetches indices, sectors, watchlist and news serially. Cache reuse must be
preserved, but a single serial worker is too broad a synchronization boundary.

Module construction imports all feature renderers and creates controls for all
views in a module. That adds cold-build work before the requested view becomes
interactive. Existing worker logs announce started when a process is assigned,
without distinguishing process initialization from business execution.

## Proposed implementation

1. Make worker bootstrap small and domain imports lazy. Keep compatibility
   exports while removing the eager service-package imports and unrelated
   foundation dependencies from the homepage execution path. Do not import model
   or native CLI capabilities merely to show a page.
2. Replace simultaneous full-pool warmup with bounded, staggered readiness.
   Expose initializing, ready, queued, executing and completed states. Start
   additional workers only when needed; do not create four heavy interpreters
   during shell rendering. Reuse ready workers and initialize replacements off
   the navigation critical path.
3. Separate independent homepage reads. Provide consumer-aware shared acquisition
   for identical source/snapshot work rather than serializing the entire homepage.
   Prevent duplicate news and quote fetches across callbacks and processes. Keep
   provider throttling, account consistency and explicit refresh semantics.
4. Show local account/task state and cached observations first. Independent
   panels update as ready; unavailable sources have bounded waits and visible
   status. Cached data retain their original timestamp and stale marker. Never
   substitute simulated observations or present partial coverage as complete.
5. Reduce unnecessary synchronous module construction and browser rerendering
   where the timing trace shows material cost. Preserve drafts and legacy routes.
   A missing optional CLI must not stall unrelated market or financial controls.

Keep hard cancellation in owned processes for blocking transient work. Preserve
multiwindow consumer isolation, independent accepted jobs, real-model guards,
RPM limits, Langfuse integration, and Windows/Linux behavior. Do not replace
hard-stop guarantees with an abandoned thread or disable provider limits for
apparent speed.

## Verification and limits

Record shell response, requested-view interactivity, process readiness, queue
wait, actual source acquisition, result serialization and browser rendering as
separate intervals. Compare a fresh process, first and repeated homepage entry,
first market/financial entry and return to cached views. Exercise offline fixtures
first to isolate initialization, then actual public sources under the current
Conda and project environments. Do not hide regression behind a warmed cache.

Acceptance requires a material reduction in cold initialization and homepage
queue time against the measured baseline, independent panel progress, and no
duplicate acquisition, stale result overwrite or weakened cancellation. Report
actual timings and separate external-source latency from application overhead;
do not promise that every external endpoint completes within a fixed duration.

Run relevant unit/integration/browser regressions, Ruff, mypy, security checks
and both strict documentation builds. New source comments, design and usage text
are English. Update the weekly changelog. All temporary evidence stays on E;
stop owned services. No package changes, file deletions, commit or push are part
of this proposal.

## Homepage rendering acceptance correction

The 2026-11-15 progressive-output change exposed a homepage regression after
initial market synchronization. Source completion alone is insufficient evidence
of page readiness. Acceptance now requires all eight account metrics and all six
plots, plus summaries and news, after initialization, refresh and return.
The homepage retains its original independent complete-result group transport;
lazy initialization and shared raw observations remain enabled. Detailed section
streaming on other pages is covered by its own compatibility checks.
