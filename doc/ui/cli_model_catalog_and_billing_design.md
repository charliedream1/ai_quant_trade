# CLI model selection and billing visibility

Date: 2026-11-15 (UTC+08:00). Approved by the user; implemented on 2026-11-16.

## Observed defects

The shared workbench/floating composer only queries Qoder's model catalogue.
Other CLI selections replace the list with a default-model placeholder. Even
Qoder performs discovery only after explicit refresh; switching without a warm
cache returns a placeholder. The reset callback and following metadata callback
do not provide a provider-scoped freshness contract for rapid selection changes.
Reasoning controls change interactivity without rebuilding supported choices.

The Qoder adapter discards model metadata beyond identifier and name, including
any available price factor. The composer has no billing view. WorkBuddy has a
separate verified graph-specific path, while ordinary chat explicitly reports
unavailable. Listing its installed models must not imply chat is connected.

Locations: frontend/common/composer.py:render_composer/select_backend;
agent/qoder_cli.py:model_choices; agent/workspace_backend.py:backend_events;
engine/market/model_graph/generation.py:GraphGeneration._workbuddy.

## User behavior

Selecting a CLI immediately clears models from the previous backend, shows
discovery status and loads the selected backend's available catalogue. A refresh
button bypasses that backend's cache. Preserve a selected model only if it still
belongs to the current catalogue. Late results from an earlier selection cannot
overwrite the active backend. Reasoning/permission choices follow the actual
provider and model capabilities. Both composer locations share one implementation.

Use bounded, read-only metadata commands or explicitly configured installed
catalogues supported by the detected CLI version. Do not submit a generation
prompt merely to discover models. Unsupported discovery, missing installation,
expired authentication and empty catalogues have distinct visible states. Allow
manual identifiers only where the existing execution protocol accepts them.
Do not read or publish authentication tokens or import local agent memories.

WorkBuddy remains explicitly unavailable for ordinary chat unless its existing
graph-only protocol can be safely reused and validated for this flow. Any such
reuse must retain current cancellation, real-model guards, permission boundaries,
RPM and observation policies; it must not silently substitute CodeBuddy accounts.

## Billing metadata

Each model label includes an evidence-backed billing category: explicitly free,
credits multiplier, subscription/quota, token billed, or unknown. A visible detail
area shows available rate/unit/currency, provider/account scope, source and last
refresh time. Selecting a model updates that area, including manually typed IDs.
Unknown pricing is displayed as unknown rather than zero. Promotional free access
is labelled with its reported conditions; subscription inclusion is not described
as universally free. No guessed fixed monetary price is derived from credits.

Prefer the selected CLI's current metadata. Optional reviewed price metadata lives
in YAML with source and verification time, never in source constants. API model
selection retains the existing configured profile and reports missing billing
metadata explicitly. Discovery does not scrape private account traffic or modify
vendor packages. Raw catalogue responses stay private and only allowlisted fields
reach logs/UI.

Official reference boundaries checked for this proposal:

- Qoder model selection and server-reported price factors:
  https://docs.qoder.com/cli/model
- Qoder credit usage: https://docs.qoder.com/cli/usage
- CodeBuddy native model listing:
  https://www.codebuddy.ai/docs/cli/slash-commands
- Codex subscription/credit pricing:
  https://chatgpt.com/codex/pricing/

These references describe billing mechanisms; they do not establish availability,
entitlements or a price for a particular local account.

## Acceptance

Verify real installed metadata discovery without paid generation. Controlled
catalogues cover multiple providers, free/credits/subscription/unknown rates,
unavailable/malformed metadata, timeout and refresh invalidation. Browser tests
switch providers quickly with delayed responses and assert final provider/model
agreement in both composers, supported effort choices, billing details and model
identity forwarded on send. No paid send is required to verify selection.

Run project and existing Conda browser acceptance, relevant unit/integration tests,
Ruff, mypy, privacy/security checks and strict public/help documentation builds.
Synchronize usage/design/changelog in English. Keep temporary evidence on E and
stop owned services. No package installation, file deletion or push is proposed.

## Implementation and verified boundaries

### Unified selectors and WorkBuddy chat

The 2026-11-22 revision shares provider labels and model metadata across page
reports, relationship graphs, the workbench, both floating chat tabs and
specialised research controls. Each action draws its eligible providers from
the registry and its execution policy. Cover the existing strategy simulation
entry with the same labels and identify the simulation action in its UI.

The floating CLI assistant uses the same workspace backend as the workbench.
The WorkBuddy adapter requires an explicit model, sends only bounded text and
reuses the isolated desktop runner already exercised in relationship research.
It validates the selected model and native capability events and emits observed
progress and model metadata. Existing demo-mode and permission checks apply.

The approved [daily reuse extension](cli_model_catalog_daily_cache_design.md)
replaces the initial five-minute process cache with private daily persistence,
cross-process discovery ownership, explicit refresh and labelled stale fallback.
The cache calendar defaults to Asia/Shanghai; account changes not represented by
observable configuration require manual refresh. This does not change discovery
commands, generation permissions or provider billing boundaries.

Codex discovery uses native app-server initialization followed only by model/list;
Qoder uses its explicit list-models command. TRAE and CodeBuddy versions without a
verified noninteractive command accept an explicitly configured catalogue and
otherwise show unsupported/missing state. WorkBuddy product metadata is optional
and informational; the graph-only restricted generator cannot safely become the
ordinary chat runner, so chat sending remains disabled for this backend.

Both composers use browser-session state revisions and allow overlapping metadata
events. This is necessary because the SDK's default event suppression drops fast
backend switches. Model IDs/rates and billing details are excluded from substring
translation. The selected model survives refresh only if still in the catalogue.
The existing safe-callback boundary supplies page cancellation to owned metadata
processes. Cancelled discovery is not cached as failure.

Actual Codex metadata returned nine models without generation; rates were absent
and remain unknown. Actual Qoder metadata timed out. Controlled browser catalogues
cover multiple billing categories, latest-selection identity, refresh and both
input locations under the two installed Gradio versions. This does not establish
real access or pricing for providers that were not authenticated/available.
