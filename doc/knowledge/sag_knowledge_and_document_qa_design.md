# SAG Retrieval and Scoped Document Questions

Date: 2026-11-07. Author: Codex. Status: implemented; isolated REST-contract and browser acceptance completed.

## Scope

Integrate the self-hosted Zleap-AI/SAG REST API as an optional knowledge retrieval backend. Preserve the existing file-based zvec-grep backend and the platform's Python 3.10.1–3.14 contract. Add explicit whole-library and single-document questions, standard embedding/rerank alternatives, original-source citations, safe readiness reporting and visible fallback reasons. This design contains no implementation code.

## Integration boundary

The platform continues parsing supported text files, storing originals, selecting libraries and protecting session attachments. SAG receives normalized text only after explicit synchronization or a locally enabled auto-sync policy. Auto-sync is off by default and excludes session attachments. No SAG package, desktop application, managed cloud account or model weight is installed into the platform runtime.

Use SAG's source creation, source document ingestion/status and global search routes. Each local document revision maps to its own SAG source. A library search supplies only the current permitted source identifiers; a single-document search supplies one. This avoids relying on an undocumented document-filter parameter or fetching global evidence before filtering it locally.

Persist source/document identifiers, indexing state, endpoint identity hash and local content hash. An edited document or changed endpoint invalidates its previous mapping. Source creation and ingestion are not blindly repeated after an uncertain network result. The existing local document remains usable when optional indexing fails. Concurrent identical synchronization is claimed under a database transaction before network work begins.

## Questions and evidence

Validate document identity against the selected library, category, source scope and attachment session before retrieval. Empty, zero, negative, foreign-library and another session's document identifiers do not broaden into a library query. Scope conversation history by library and document so a previous whole-library answer cannot contaminate a single-document turn.

SAG returns original sections rather than authority to execute tools. Resolve each source identifier to the permitted local document, verify that its content revision is current, and check returned text against that original before generation. An out-of-scope source or fabricated evidence fails closed. Preserve local document/chunk identities for the existing clickable preview and provide actual retrieval backend/strategy metadata.

Actual engine acceptance additionally verified SAG's ARTICLE title wrapper: an exact submitted-title heading may precede the original section. Remove only that known wrapper when necessary, then apply the full original-content check. Honor upstream effective-strategy and fallback metadata so a successful HTTP response after internal multi-to-vector recovery does not masquerade as successful multi-hop retrieval.

Answer generation remains in the platform's ordinary model client. Existing OpenAI/HTTP/LiteLLM configuration, shared RPM controls, JSON repair for keyword planning and optional observations remain applicable. SAG's own event extraction and multi-hop ranking are separate external-service model work; configure that service independently. The platform ignores the search API's generated summary and builds its own cited answer from validated sections.

## JEV and replacement ranking

JEV is optional precision ranking, while embeddings support SAG indexing and semantic retrieval. They are different capabilities. With JEV requested, attempt the documented JEV strategy, then ordinary multi-hop retrieval, then vector retrieval. Without JEV enabled, skip its network attempt. A standard rerank endpoint can score SAG candidates instead; a standard embedding endpoint can rank bounded authorized local chunks when SAG is unavailable or not indexed. The existing keyword planner/search remains the final fallback.

Report the requested and effective backend, effective strategy, attempted steps and categorized fallback reasons. A fallback answer is not presented as a successful JEV call. Standard rerank and embedding protocols are explicit alternatives; this integration does not claim to reproduce JEV's ranking quality or upstream benchmark scores. All candidate expansion stays within the original document boundary.

## Configuration, lifecycle and privacy

Policy, bounded synchronization batches, limits, timeouts, strategy names and UI text belong in YAML. Endpoints, model names and keys can be selected through named local environment values; credentials remain in `.env` or `.llm_env`. Status inspection reports configuration only and performs no network request. Provider payloads, tokens, endpoint addresses and private paths are not exported as diagnostic errors.

Use the existing validated network session, disable redirects and inherited proxies, limit response bytes, and give one SAG operation a finite deadline. Requests close owned sessions, and tests close every local HTTP service. Optional ranking errors produce safe categories rather than raw provider errors. No local file or remote source is deleted by this feature.

## Application changes

Add independent modules for REST transport, synchronization, evidence checks, ranking alternatives and backend routing under `src/knowledge`. Extend the existing RAG request and history scope; add protected indexing/readiness API routes and frontend callbacks. Keep page construction, business services and configuration separate. Add document/backend/strategy selectors, explicit synchronization, clear indexing state and actual fallback metadata to the Q&A page.

Remote-access instructions are a separate completed change, committed before SAG work. Preserve unrelated pending channel, strategy and observation work when staging this feature. Public documentation must not link private audit artifacts or developer-specific absolute paths.

## Acceptance

Use actual local HTTP exchanges following the inspected public SAG contracts, ordinary OpenAI-compatible generation, embeddings and rerank. Verify whole-library and single-document answers, source/session/history isolation, JEV unavailability and vector fallback, external ranking alternatives, idempotent indexing, stale revisions, uncertain writes, malicious evidence and no-network status checks. Browser verification must exercise selection, synchronization, question submission and source preview.

Run relevant legacy knowledge/API checks, Ruff, mypy, security and UTF-8 checks and both documentation builds. Distinguish local protocol simulation from a live self-hosted SAG engine, paid ranking service or real model quality evaluation. Retain failed attempts and temporary files unless cleanup is explicitly approved. Commit only feature changes; do not push.

## Primary references

- [SAG project](https://github.com/Zleap-AI/SAG): self-hosted REST, original chunks and retrieval modes.
- [Search contracts](https://github.com/Zleap-AI/SAG/blob/main/apps/api/sag_api/schemas/search.py): explicit source identifiers and section fields.
- [Search routes](https://github.com/Zleap-AI/SAG/blob/main/apps/api/sag_api/api/v1/search.py): source/global search and optional generated summary.
- [Document ingestion](https://github.com/Zleap-AI/SAG/blob/main/apps/api/sag_api/api/v1/documents.py): normalized text ingestion and asynchronous document status.
- [SAG configuration](https://github.com/Zleap-AI/SAG/blob/main/.env.example): independent JEV and embedding settings.
