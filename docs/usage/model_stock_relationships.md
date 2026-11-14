# Stock relationships with CLI and Skill research

The market relationship page offers **Data and rules** (the default) and
**CLI + Skill research**. The rule mode keeps existing sector, concept,
shareholder, news and return-correlation behavior. The Skill mode reads original
documents and proposes business links with direction, explanation and citations.
It can discover entities beyond the existing rule graph.

## Generate and inspect a graph

1. Open **Market → Relationships**, select the market, then select
   **CLI + Skill research**. CN and HK target identities are supported.
2. Enter the stock code and select an available graph CLI backend and model.
   **Check CLI availability** checks local configuration, not model quality or
   account credit. Actual generation verifies the native event stream.
3. Set the as-of date, source lookback and maximum research rounds. Add public
   issuer/exchange original URLs, or choose an authorized knowledge library and
   optional document IDs/attachment session. Blank document selection uses SAG2
   BM25 to recall relevant local passages.
4. Click **Generate Skill graph**. The run ID, progress and terminal state are
   persisted. **Cancel graph research** stops owned CLI processes; an HTTP source
   read may first need to reach its bounded network timeout.
5. Click **Open saved graph** after completion. Expand a relationship to read the
   exact quote, review explanation, original link and frozen source context.
   Directed business links have arrows. Inferences use dashed lines.
6. **Refresh graph history** reopens previous run IDs. **Export this saved graph**
   exports that run's full immutable JSON, including labelled candidates. Viewing,
   filtering and export never regenerate a graph or call a model.

The default view shows source-stated, non-expired links connected to the target.
The inference/expired-candidate checkbox reveals the complete retained result.
If hiding a bridge disconnects a component, that component is hidden too. Export
retains all labelled evidence, so it can contain more edges than the default view.
The research panel retains English labels and original evidence text in both
site languages. Automatic substring translation is disabled there to preserve
exact quotations and avoid confusing actions with trading-price labels.

## CLI configuration

The graph capability profile currently permits Qoder and an explicitly
configured existing WorkBuddy installation. Other registered platform CLIs remain
available to their existing workflows; graph generation rejects an unsupported
profile rather than switching providers.

Qoder uses the existing verified text-only native profile. WorkBuddy uses its
existing desktop login and installed model catalogue. In the ignored root `.env`,
set these absolute local paths without copying credentials into the repository:

| Variable | Local resource |
| --- | --- |
| `ALL_IN_ONE_WORKBUDDY_INSTALLATION` | Existing WorkBuddy installation directory containing its executable |
| `ALL_IN_ONE_WORKBUDDY_AUTHENTICATION` | Existing encrypted desktop authentication file |
| `ALL_IN_ONE_WORKBUDDY_PRODUCT` | Existing CLI product JSON containing the installed model catalogue |

The WorkBuddy adapter was exercised on Windows with the free `hy3` model.
WorkBuddy desktop layout/codec changes fail explicitly and may require an adapter
update. Linux uses the existing Qoder path; WorkBuddy Linux desktop execution has
not been verified. Authentication is decoded by the installed native codec only
into parent/child memory. Do not commit real paths, login files or CLI profiles.

The platform loads the versioned `quant-stock-relations` Skill and executes its
acquisition/extraction/review workflow. The CLI performs ordinary text generation;
it does not recursively execute native Skills. WorkBuddy receives an isolated
working/config directory and process-local settings denying native tools, with
empty native tool/MCP manifests required before output is accepted. Optional
Skill/plugin fields are rejected if nonempty; this CLI version does not report
those fields, so their counts are recorded as unknown, not measured zero.
Personal Codex/TRAE/WorkBuddy memories are neither exported nor incorporated.

Reasoning effort is accepted only for the verified Qoder profile. Leave it blank
for WorkBuddy. The platform's API RPM limiter does not govern CLI account quotas;
CLI calls record reported usage/cost when available, and missing costs remain
unknown. Optional platform Langfuse monitoring observes workflow/generation spans
under the existing content-capture policy.

## Evidence and budgets

Defaults live in `egs/config/data/model_relation_graph.yaml`: at most two active
runs, three research rounds, six total model calls, 600 seconds per run and 120
seconds per CLI call. Twenty originals, 140,000 total source characters, 60 nodes
and 100 edges bound each graph. A failed extraction may use one corrective call
inside the same total budget; exact citation validation is never relaxed.

Public discovery uses bounded DuckDuckGo HTML search. A result link/snippet is
only a candidate until the platform reads an original through its public-network
policy. Publisher blocks, search challenges and missing sources can produce a
failed or sparse result. Supplying accessible original URLs is more reproducible.
Previously reviewed edges may survive a later failure as a clearly marked partial
result. Failed review never publishes the unreviewed extraction.

Source publication metadata, when parseable, must fit the as-of/lookback window.
Undated sources are labelled with first observation time; historical requests
downgrade their links to candidates. A date selected in this page does not make
the run a historical point-in-time dataset. PDF dates appearing in prose may
remain unverified metadata. Old source claims do not prove a relationship is
still current, and a planned plant does not prove production has begun.

Only the selected target listing is resolved through the security master. Other
company names remain explicitly unresolved; model-supplied ticker guesses are
discarded. The model selects numbered frozen quote spans and the platform copies
their exact text; unknown spans and altered direct quotes are rejected. A model
review tests interpretation against the same corpus and is not independent
confirmation. Edge widths are display weights, not correctness probabilities.

## CLI, API and storage

The editable example is
`egs/examples/skills_examples/quant-stock-relations.yaml`:

```shell
python egs/entrypoints/skills.py preview --config egs/examples/skills_examples/quant-stock-relations.yaml
python egs/entrypoints/skills.py run --config egs/examples/skills_examples/quant-stock-relations.yaml
```

Preview does not call a model. The registered workflow also appears in the
existing Skill catalog and can use the existing project-only export mechanism;
this feature does not automatically overwrite personal native Skills.

The API prefix is `/api/v1/relations/research`: `GET /providers`,
`POST /runs`, `GET /runs`, `GET /runs/{id}`, `GET /runs/{id}/events`,
`GET /runs/{id}/graph`, `POST /runs/{id}/cancel` and
`GET /runs/{id}/export`. Viewing uses `include_inferences=true` for the full graph.
The existing `/api/v1/relations/graph` rule endpoint is preserved.

Private records live under the configured data directory's
`relation_graph_runs/<run-id>/`, including request/status, events, parsed model
responses, source snapshots and `graph.json`. Reuse is explicit by immutable run
ID; a fresh Generate action starts a fresh source/model run. Do not publish these
artifacts: authorized document content and issuer originals can be included.

See [construction principles](../principles/model_stock_relationships.md) and
[actual-model validation](model_stock_relationship_validation.md).
