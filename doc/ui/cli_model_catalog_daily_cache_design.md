# Daily CLI model catalogue reuse

Date: 2026-11-19 (UTC+08:00). Status: approved, implemented and verified.

## Problem and scope

The shared workbench and floating composer call `agent/cli_catalog.py:discover`.
Its process-local cache expires after 300 seconds, so later selections and server
restarts can repeat slow native metadata discovery. The catalogue refresh control
already passes an explicit refresh flag. Preserve model identity, sourced billing,
reasoning capabilities, backend revisions and existing cancellation boundaries.

## Proposed behavior

- Reuse the first completed discovery for the current calendar day. Share results
  between both composers and browser windows, with a private disk cache allowing
  reuse after restart. Define the calendar timezone explicitly in YAML and show
  the actual discovery time and cache/stale status in the billing detail.
- Isolate entries by backend and a configuration/account-profile fingerprint.
  Configuration changes invalidate reuse; do not persist fingerprint inputs,
  credentials, environment variables, executable paths or private catalogue paths.
  Login/account changes outside observable configuration require manual refresh.
- Collapse overlapping discovery for the same scope into one owned operation.
  Waiting callbacks remain cancellable, and a different backend can load
  independently. A forced refresh bypasses the daily entry; overlapping refreshes
  share the in-flight refresh rather than creating duplicate native processes.
- On a new day, the first selection refreshes the catalogue. A failed refresh
  retains the last successful rows with an explicit stale/failure indicator.
  Record completed failures for the day to prevent repeated automatic attempts;
  manual refresh can retry immediately. Never cache page cancellation as failure.
- Invalid, oversized or unreadable cache entries are ignored safely. Cache writes
  are atomic and bounded, contain only allowlisted model metadata and discovery
  status, and live in the existing ignored application data area. No automatic
  file deletion, credential import, authentication query or generation is added.

## Implementation boundaries

Update `agent/cli_catalog.py:discover` and introduce a small cache helper only if
needed to keep discovery readable. Policy and limits belong in
`egs/config/ui/cli_catalog.yaml`. Update shared composer details only where needed
to communicate reuse and stale metadata. The unused legacy Qoder model-choice
helper must not remain a second active cache path; retain compatibility without
unrelated cleanup. Synchronize the existing catalogue design, usage guide and
weekly changelog in English. Preserve unrelated staged and working changes.

## Acceptance

Use controlled metadata counters to verify same-day reuse across callers and
restart, backend/profile isolation, timezone day boundaries, concurrent discovery,
forced refresh, failed refresh retaining old rows, first-load failure suppression,
malformed cache recovery and cancelled wait/process behavior. Verify that cache
files contain no credentials or private configuration values. Browser replay in
both composers must confirm that repeat selection uses cached rows, manual
refresh updates rows/billing, and delayed responses cannot overwrite a new CLI.

Run relevant unit/integration and browser tests, Ruff/format, mypy, privacy scans
and strict documentation builds. Keep temporary evidence on E, stop owned test
services, and make no package changes or file deletions. External model generation
is unnecessary for catalogue acceptance. Commit/push is outside this proposal.

## Verified results and limits

Acceptance passed 25 unit/transport cases, 4 project browser cases and 2 existing
Conda browser cases. The new tests exercise both threads and separate Python
processes, restart reuse, calendar boundaries, cancellation, malformed files and
credential/path exclusion. Native Codex returned 9 models with a single metadata
query; discovery took 2.3824 seconds and same-day reuse 0.1876 seconds in this run.
Other authenticated CLI providers were not queried; controlled catalogues cover
their common cache path. No generation request was submitted.

Full source mypy, targeted Ruff/format, secret scans, changed-helper Bandit and
both strict documentation builds passed. pip-audit timed out after 40 seconds;
OSV Scanner and physical Linux acceptance were unavailable. Existing dependency
findings remain unresolved and no packages were modified. Test-owned listeners
and processes exited; private evidence remains on E without cleanup.
