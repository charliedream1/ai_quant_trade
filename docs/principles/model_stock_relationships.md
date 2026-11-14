# Evidence-grounded company relationship construction

The model mode is a separate research workflow, not a replacement for the
[existing rule graph](relation_graph_principles.md). Rules expose mechanical
memberships, source-tagged co-occurrences and measured correlations. The model
mode interprets original text to propose explicit business relationships.

The application executes `quant-stock-relations`: resolve the selected listing,
recall authorized local passages with SAG2 BM25, read supplied originals, then
iterate bounded planning, source acquisition, extraction and review. Planning
uses traditional ReAct JSON actions (`search`, `read`, `finish`). All model text
is parsed with `json_repair`; schema and grounding checks follow parsing. No
function-calling or provider structured-output interface is required.

## Claim structure

Each edge carries subject/object IDs, relation type and direction, explanation,
source IDs, exact quotes, source/observation dates, optional validity interval,
contradictions and review rationale. The configuration defines supplier→customer,
investor→investee, parent→subsidiary and event→affected-company direction.
Partnership and competitor relations are symmetric. Multi-hop paths do not
establish a direct relationship between their endpoints.

The target listing identity comes from the security master. Newly discovered
company names remain unresolved until separately matched; generated ticker text
is discarded. Co-mention does not establish supply, competition or causation.
An MOU expresses an agreement/intention rather than completed deliveries.

The platform partitions frozen text into numbered spans without rewriting PDF
word breaks or punctuation. The model selects span IDs; the validator copies the
exact span text into the saved evidence. A direct quote remains supported only if
it matches the original after whitespace normalization. This avoids treating
model-corrected typography as an exact original quote.

Source-stated claims, inferences and candidates remain distinct. Unknown sources,
altered quotes, invalid dates/types/endpoints and future evidence are rejected.
One budgeted corrective extraction can repair formatting/quoting mistakes, but
must pass the same validation. A reviewer must accept, downgrade or reject every
proposed edge and cannot add new claims. Only a reviewed graph can be published;
later acquisition failures can retain the previous reviewed graph as partial.

The reviewer reads the same originals. Agreement is not independent corroboration,
and structural validation cannot prove semantic entailment. The UI exposes frozen
context so a human can check attribution, intent, control versus minority
ownership and any continuing-validity assumptions.

## Provenance, lifecycle and reuse

Original text is bounded and hashed before use. Search snippets remain discovery
metadata, never evidence. Redirects and public reads use the existing destination
policy; local libraries obey document/session access checks. Source publication
dates outside the selected window fail; undated historical sources become
candidates. Observation today does not grant point-in-time qualification.

Runs record market/qualified target, request, Skill/config hashes, actual CLI
model identity, calls and reported usage. Graph profiles do not weaken the
existing historical/strict provider contracts. CLI capability events are checked
as received, and owned processes stop on rejected capabilities/cancellation.
No quota or cost is inferred from missing CLI billing metadata.

The saved graph is immutable. History, filters and export operate on one run ID;
filtered views remove disconnected components and never invoke generation. Full
export preserves labelled inferences/expired claims for audit. New generation
creates a new run rather than reusing an unverified current-source cache.

Current limitations include incomplete issuer coverage, publisher access blocks,
source truncation, unverified PDF publication metadata, unresolved non-target
entities and same-corpus review. Rule graph weights are not supplied as business
facts, and neither model edge width nor node count measures research correctness.

The implementation is in `src/engine/market/model_graph`: `workflow.py` orchestrates
research, `evidence.py` acquires originals, `validation.py` grounds and filters
claims, `generation.py` and `transport.py` enforce CLI profiles, and
`service.py`/`store.py` manage task lifecycle and immutable artifacts.
