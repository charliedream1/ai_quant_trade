# Model-assisted stock relationship graphs through CLI and Skill workflows

Date: 2026-11-14. Status: approved and implemented; acceptance notes below.

## Existing behavior and observed gaps

RelationGraphService.graph delegates to the selected market data provider,
augments local task relationships and normalizes layout and summaries. The
mainland provider builds sector/concept/index membership, shareholder links,
news entity matches/co-occurrences and date-aligned return correlations. The
construction path contains no model call. Rule weights are visualization
heuristics rather than calibrated probabilities. The current HK provider returns
the selected security alone and explicitly reports missing relationship evidence.

This architecture offers useful mechanical links but does not extract explicit
business semantics from issuer disclosures or documents. Increasing depth expands
more predefined branches; it does not establish a business reasoning chain.

The existing ProviderClient research contract prevents recursive native Skill
execution, and several installed CLI profiles lack strict research eligibility.
A new graph mode must not silently bypass those contracts or present installed
programs as verified model execution.

## User-facing modes

Keep the existing rule/data graph as the default and add a CLI + Skill research
mode. Selection is explicit; changing the mode, a filter or depth does not start a
paid or remote model call. A Generate action starts one inspectable background
run. A previously generated result can be reopened without another model call.
If a model backend fails, report its failed/partial state; show a rule fallback
only with its actual mode and reason visibly identified.

Expose registered CLI backend, model, reasoning effort where supported, as-of
date/lookback, maximum expansion depth and bounded research budget. Optional
selected knowledge libraries/documents and public original-source URLs provide
additional evidence. Respect existing library/session permissions. The user
can inspect progress, stop a task and revisit prior graph versions.

CN and HK securities share the workflow with explicit qualified identities and
market/currency metadata. Existing US availability remains explicit. Avoid
promising complete market coverage or issuer knowledge from ticker spelling.

## Skill and CLI responsibilities

Register a dedicated repository Skill workflow for stock relationship research,
with a canonical English Skill specification under src/skills and existing
platform/native entry points. Record the actual workflow run, Skill version/hash,
provider/model identity and calls. Do not merely concatenate a Skill name into a
prompt and claim the Skill ran.

The platform executes the workflow and loads its approved Skill instructions.
The CLI supplies ordinary-text generation for planning, extraction and review;
bounded tool actions use the platform's traditional ReAct executor. Do not use
provider function calling or structured-output APIs. Parse model JSON with
json_repair, then apply schema and evidence validation.

Reuse existing CLI discovery and authentication where valid. Introduce a
graph-specific current-research capability profile if needed, rather than
weakening existing historical/strict-role checks. Preflight must verify the
actual backend/version/model and its declared isolation/operation controls.
Providers without suitable controls remain unavailable with a concrete reason;
there is no silent provider switch or permission escalation. Current exploratory
research does not acquire point-in-time qualification merely by selecting an
older date.

Use an isolated run workspace with approved evidence and Skill instructions.
Do not read or export personal CLI memories, local credentials or unrelated
project data. Any platform-managed Skill export is separate from personal memory
files. No model subprocess recursively launches this or other research Skills.

## Evidence acquisition and graph construction

1. Resolve the target company, listing and aliases. Load explicit data-source
   relationships and relevant local research documents as seed evidence.
2. Plan bounded public-source searches for missing relation categories. Prefer
   issuer reports, exchange announcements, dated corporate disclosures and
   original reporting. Public web reads use existing network/download policies;
   a link or search snippet alone does not prove the full article was read.
3. Freeze retrievable source text, publication/availability dates, URL, excerpt
   coverage and content hash. Local documents retain their authorized IDs and
   revision hashes. Existing SAG2 retrieval can select local passages, but is not
   a replacement for verifying the original.
4. Extract proposed directed relationships from the frozen passages, referring
   only to supplied evidence IDs. Permit new candidate companies when supported
   by an original, not only existing rule-graph neighbors. Unresolved company
   names remain unresolved entities rather than invented tradable tickers.
5. Review entity identities, relation direction, dates, conflicting sources and
   whether each cited passage supports the actual relationship claim. A second
   model review aids interpretation but does not turn model agreement into fact.
6. Expand the strongest grounded frontier within the configured depth and node,
   edge, call, token, source-count and time limits. A multi-hop path does not
   establish a direct commercial relationship between its endpoints.

Prompts, relation taxonomy, budget settings and example fixtures belong in YAML
or versioned Skill resources. No invented company links or mock facts belong in
production source code.

## Relationship semantics and validation

Add business categories such as supplier/customer, ownership/investment,
subsidiary, competitor, partnership and event exposure alongside existing
sector/membership/statistical categories. Define their meanings and direction
in configuration. Record subject, predicate, object, business explanation,
evidence IDs, exact excerpts, source/availability dates, valid interval and
known contradictions. Ownership percentages and amounts are optional and must
not be invented.

Separate source-stated facts, model inferences and unverified candidates. The
default view emphasizes supported facts; inference visibility is an explicit
filter and uses distinct line style. Unverifiable source IDs or altered quotes
are rejected. Structural checks cannot themselves prove that an excerpt entails
the model claim; use review and make the original accessible for human judgment.

Returns correlation stays a computed statistical relation with dates and sample
size. It is not promoted into supplier/competitor/causal exposure by model prose.
News co-mention alone is not a commercial relationship. Model confidence and
edge width must not be labelled as calibrated correctness probabilities.

Preserve contradictions and expired relationships as inspectable dated evidence
instead of silently overwriting them. Bound all paths to the selected center
and prevent placeholder or disconnected entities from becoming verified nodes.
Sparse graphs and missing evidence remain legitimate outcomes.

## UI and API integration

Retain the existing GET rule-graph contract. Add explicit model-graph run,
status/events/result and cancellation routes. Persist immutable graph results
with the same graph/run ID used by view and export. Exporting or switching
filters must not regenerate the graph or produce different paid results.

Reuse current graph visualization and evidence preview. Labels should explain
the relationship and direction rather than only its broad category. Group the
view around business context, ownership, peers and events, with graph mode,
as-of date, evidence coverage and unresolved/expired counts visible. Evidence
selection shows the original excerpt and link alongside interpretation and
provenance. Local task links remain distinct from issuer business relations.

## Caching, observations and lifecycle

Key result reuse by market/qualified issuer, date, authorized document revisions,
source snapshot, Skill/config/provider version and research parameters. Keep
rule and model result caches independent. Existing RPM and optional Langfuse
should cover API-backed generation; CLI usage/quota limitations must be reported
honestly rather than recorded as zero. Preserve bounded progress and failure
evidence without recording secrets. Cancel owned subprocesses and release slots
on timeout/cancellation. Stop test-owned services after acceptance.

## Acceptance and delivery

Unit checks cover entity ambiguity, HK/mainland identity, edge direction,
unsupported relation labels, fabricated citations, quote changes, future/stale
evidence, same-article co-mention, conflicts, bounded expansion and JSON repair.
Integration checks cover real CLI processes with deterministic protocol fixtures,
no-native-recursive-Skill behavior, permissions, task lifecycle, cache reuse,
cancellation and export/view consistency. Preserve the rule backend regression.

Actual acceptance should use at least one mainland and one HK stock with a
manually checked set of dated original sources. Score supported-edge precision,
expected important relations recovered, citation entailment, unresolved entities,
direction errors, total latency and observed model calls/usage. Do not present
more nodes as better quality. Where configured and available, use the user's
preferred free Hy3 CLI; otherwise record the unavailable backend and test the
actual selected registered CLI explicitly.

Browser acceptance covers mode switching, provider availability, progress,
cancellation, edge evidence, original preview, date/filter controls, graph
reopening and exporting the same result on desktop/mobile. Run applicable pytest,
Ruff/format, mypy, secret/dependency checks and both strict documentation builds.
Update English design, usage/principles, README capability summary and weekly
changelog. Preserve existing uncommitted work and local memories. No file
deletion or Git publication is implied by this proposal.

## Implementation decisions

The first capability profiles are Qoder and explicitly configured WorkBuddy;
other registered platform CLIs are not claimed as graph-capable. WorkBuddy's
observed schema explicitly reports tools/MCP, while optional Skill/plugin counts
are absent and recorded as unknown. Existing strict/historical profiles remain
unchanged. Process-local native permission denial and streamed event rejection
bound this current exploratory workflow.

Frozen text is partitioned into quote spans. The model selects source/span IDs;
the platform copies exact original text and rejects fabricated IDs or altered
quotes. This preserves PDF punctuation and word breaks without semantic fuzzy
matching. Review remains a same-corpus check, not independent corroboration.

Rule graph heuristics are not promoted to business facts. The model mode reads
authorized local SAG2 passages/public originals separately. History reuse is
explicit by immutable run ID; a new Generate action obtains a new snapshot and
does not silently reuse a current-source cache. The full export includes labelled
inferences even when the default connected view hides them. Usage and measured
acceptance are maintained in the public relationship graph guides.

## Repository references

- src/engine/market/relation_graph.py
- src/data/relation_graph.py and src/data/relation_evidence.py
- src/data/hong_kong.py
- src/agent/providers/service.py and src/agent/providers/registry.py
- src/agent/skill_runner and egs/config/agents/skill_workflows.yaml
- docs/principles/relation_graph_principles.md
- docs/usage/agent_cli_skills.md
