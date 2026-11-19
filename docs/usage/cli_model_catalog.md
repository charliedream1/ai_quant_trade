# CLI models and billing in the composer

The workbench and floating model assistant share the same backend/model controls.
Selecting a CLI clears the previous provider's models and automatically discovers
the selected catalogue. The refresh icon bypasses its cache. Discovery runs only
after selection or refresh, never while constructing a page, and does not submit
a generation request. A delayed response cannot replace a newer backend choice.
Leaving the page cancels its owned metadata process. Discovery failures are
bounded; use the visible refresh control after repairing login/connectivity.

Each CLI/configuration automatically discovers models once per calendar day
(Asia/Shanghai by default). Later selections, both composers, other windows and
server restarts reuse the private daily cache. Overlapping requests share one
discovery; waiting callbacks remain cancellable. Click **Refresh models** to
update immediately, including after an account/login change. Configuration/profile
changes use a separate cache scope. A new day triggers discovery on first use,
not a background request at midnight.

The billing detail marks daily reuse. If discovery fails, the last successful
list stays available and is explicitly marked stale, with its original refresh
time. Completed failures are also remembered for the day to prevent repeated
slow retries; manual refresh retries immediately. Cancellation is not a cached
failure. Cached billing can change at the provider before the next refresh.

Model labels show provider-reported billing metadata. The detail below the input
shows its source, refresh time and discovery status. Explicit free access, credit
multipliers, subscription/quota and token billing are different categories.
`Price unknown` means a verified rate was not supplied; it does not mean free.
Default routing and manually typed IDs have unknown pricing unless the catalogue
identifies them. Account entitlements, promotions and the final invoice still
depend on the provider. API profiles currently expose unknown prices here.

| Backend | Discovery | Billing boundary |
| --- | --- | --- |
| Codex | Native app-server initialization and `model/list` | Model listing does not establish ChatGPT-plan/API billing; missing rates stay unknown |
| Qoder | Native `--list-models` using the configured CLI profile | A reported `price_factor` is a credit multiplier, not a fixed task price |
| TRAE / CodeBuddy | Explicit configured catalogue; unverified native discovery is reported as unsupported | Only explicitly supplied metadata is displayed |
| WorkBuddy | Explicit installed product catalogue, when configured | Informational only: ordinary chat remains unavailable; the graph-specific adapter is separate |

Model selection and sending keep the underlying model ID unchanged. Supported
reasoning choices intersect the provider and model metadata. Refresh preserves a
model only while it remains in that provider's list. WorkBuddy sending is disabled;
other unavailable/unsupported states show their limitation rather than invented
models. Existing native runners validate actual installation and invocation.

## Configuration

Policy, timeout, limits, daily-cache timezone and UI copy live in
`egs/config/ui/cli_catalog.yaml`. The metadata timeout defaults to 12 seconds and
the cache is private under the application's ignored `data/cli_profiles/model_catalogs`
area (relative to the configured data directory). It stores allowlisted,
redacted model metadata and opaque configuration fingerprints, never raw
credentials, environment variables or installation paths. Keep the runtime data
directory private when relocating it. Read-only storage permits discovery but
cannot guarantee persistent reuse. The normal CLI executable/profile settings remain as
documented in [CLI installation](cli_installation.md).

For a CLI without verified noninteractive discovery, set a local `.env` variable
to a bounded UTF-8 JSON catalogue file. Supported variables are
`ALL_IN_ONE_CODEX_MODEL_CATALOG`, `ALL_IN_ONE_QODER_MODEL_CATALOG`,
`ALL_IN_ONE_TRAE_MODEL_CATALOG`, `ALL_IN_ONE_CODEBUDDY_MODEL_CATALOG`, and the
existing WorkBuddy product setting `ALL_IN_ONE_WORKBUDDY_PRODUCT`.
These paths and account-specific files stay private and must not be committed.
No authentication or memory files are imported by catalogue discovery.

The JSON root is an object with a `models` array. Each record requires `id` or
`model`, with optional `name`, `enabled`, `hidden`, `reasoning_efforts` and billing
metadata. Billing accepts explicit boolean `free`/`is_free`, a nonnegative numeric
`price_factor`, or `billing_type` of `subscription`/`tokens`. Token-rate detail
requires `pricing.input`, `pricing.output`, `pricing.currency` (USD/CNY/EUR) and
`pricing.unit` (`per_million_tokens`/`per_thousand_tokens`). Unknown vendor formats
are not guessed. Only allowlisted fields reach the UI; raw responses and private
installation paths are not displayed.

## Validation and sources

Local acceptance queried the installed Codex metadata interface and received nine
models without generation. The configured Qoder query timed out and was reported
as failed. Controlled catalogues verify billing, refresh, late-response rejection,
model effort controls and both composer locations; this does not prove account
access or current pricing for an unavailable provider.

Official references: [Codex app-server](https://developers.openai.com/codex/app-server/),
[Codex pricing](https://chatgpt.com/codex/pricing/),
[Qoder model and credit factors](https://docs.qoder.com/cli/model), and
[CodeBuddy native commands](https://www.codebuddy.ai/docs/cli/slash-commands).
Consult the provider for current account-specific terms.
