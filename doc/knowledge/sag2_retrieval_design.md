# SAG2 lexical retrieval with replaceable evidence selectors

## Scope and migration

Replace original SAG event/entity and vector-service integration with a local
SAG2-inspired pipeline. Keep model-guided recursive zvec-grep as an independent
backend. Original SAG backend and strategy values are rejected with migration
guidance. Existing source files, chunks, citations, sessions and database columns
remain intact; no remote source or local user data is deleted.

## Retrieval pipeline

Build a derived SQLite FTS5/BM25 index from the currently authorized original
chunks. Scope the corpus before indexing by library, attachment session, category,
source scope and optional document. Hash content, identity and index configuration
to reuse an immutable cache; edits and scope changes produce another index.
Indexing requires no model calls, embedding computation or vector database.

Recall question terms with BM25. Score the bounded candidate pool, retain earlier
evidence, extract new terms from the best evidence using frequency and corpus
rarity, and interleave fresh results from each term. Repeat within the configured
round, candidate and time budgets. Scores are recomputed against the original
question and previous evidence. Return local original chunks with citations and
per-round trace. Deduplicate chunks and use a configurable document diversity cap.

## Selectors and availability

Selectors are JEV noul decisions, a standard rerank endpoint, or OpenAI-compatible
embeddings with cosine similarity. Auto tries them in configured order and falls
back to BM25 with explicit reasons. Explicit selectors also report any fallback.
Selector responses can supply scores only: they cannot introduce source text or
document identifiers. Invalid/missing/duplicate/nonfinite scores are rejected.
Only bounded authorized candidates are sent externally, at query time.

This adaptation retains SAG2's lexical recall and evidence-driven expansion. It
uses portable Python/SQLite tokenization, rather than upstream's compiled scoring
extension. Chinese character bigrams support Chinese recall without an additional
tokenizer package. It does not claim benchmark or selector-quality equivalence.

## Interfaces and validation

Expose backend sag2 and selectors auto, jev, embedding, rerank and bm25. The UI
offers local index preparation; querying also prepares the current scope. No SAG
server address is required. Preserve old sync routes only as explicit retired
errors, never as silent aliases. Readiness is local and makes no network requests.

Test Chinese/English BM25, multi-hop bridging, scope and session isolation,
revisions, index reuse, provider contracts, score validation, fallback reporting,
round limits, actual REST question answering and clickable citation metadata.
Keep RPM/observability on existing generation and instrument retrieval/selector
spans. Use mocked provider protocols explicitly; live JEV quality requires a
configured account and separate evidence.

## Sources

- https://github.com/Zleap-AI/SAG-Benchmark/tree/main/sag2
- https://github.com/Zleap-AI/SAG-Benchmark/blob/main/sag2/scripts/sag2.py
- https://github.com/Zleap-AI/SAG-Wiki
- https://arxiv.org/abs/2610.22588
