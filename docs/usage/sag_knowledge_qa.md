# SAG2 knowledge and single-document questions

Actual Hy3 generation, local BGE inference, isolation and browser acceptance are
recorded in [SAG2 live validation](sag2_live_validation.md), including measured
query times and the limits of the available JEV/rerank coverage.

## Retrieval choices

The knowledge Q&A page offers **SAG2 (BM25 with evidence expansion)** and the
original **Model-guided recursive search (zvec-grep)** as independent choices.
Original SAG is retired. SAG2 runs locally over the existing normalized source
chunks: it needs no SAG service, LanceDB, event/entity extraction or vector store.
The zvec-grep option remains the default and retains model-generated keywords.

## How SAG2 works

1. Scope original chunks to the selected library, session, category, source type
   and optional single document before retrieval.
2. Prepare or reuse a derived SQLite FTS5 index, with no indexing-time model calls.
3. Retrieve candidates with BM25 and score their usefulness for the question.
4. Extract new terms from selected evidence, retrieve fresh passages, merge
   retained evidence and score the next round against the original question.
5. Return deduplicated original passages for cited answer generation.

The round limit includes the initial BM25 round. Three rounds mean initial
recall plus up to two expansions. Search stops early when no fresh evidence or
expansion terms remain. Limits, stopwords, time budgets and selector instructions
are in `egs/config/knowledge/knowledge.yaml`, under `sag2`.

This is a portable adaptation of the official SAG2 method, using Python and
SQLite FTS5 rather than upstream's compiled scoring extension. Latin words and
Chinese character bigrams support English and Chinese lexical recall. This
implementation does not claim exact upstream benchmark reproduction.

## Select an evidence scorer

| Selector | Behavior and configuration |
| --- | --- |
| `auto` | Try JEV, rerank, embedding, then BM25, reporting skipped/failed providers. |
| `jev` | Prefer contextual JEV `noul` decisions; use `KB_JEV_BASE_URL`, `KB_JEV_MODEL`, optional `KB_JEV_API_KEY`. |
| `rerank` | Prefer a standard reranker with `KB_RERANK_BASE_URL`, `KB_RERANK_MODEL`, optional `KB_RERANK_API_KEY`. |
| `embedding` | Prefer query-time cosine scoring with `KB_EMBEDDING_BASE_URL`, `KB_EMBEDDING_MODEL`, optional `KB_EMBEDDING_API_KEY`. |
| `bm25` | Pure lexical ranking with evidence-term expansion, making no scoring requests. |

Set credentials only in local `.env`. The JEV URL must be the complete
`/decisions` or `/systemone` endpoint. Embedding and rerank URLs are API roots;
the client appends `/embeddings` or `/rerank`. No paid provider/model is selected
by default. Only authorized candidate passages are sent to configured providers,
at query time. Embeddings are not persisted and do not replace BM25 recall.

Embedding and rerank replace the evidence scorer while retaining lexical recall
and term expansion. They are different scoring approximations and are not
claimed to reproduce JEV decisions. All unavailable/invalid providers produce
visible fallback reasons. A deadline failure can fall back to the original
keyword loop, with the effective backend reported explicitly.

## Use the page

Import files into a named knowledge library. In Knowledge Q&A, select the library,
choose SAG2 and a selector, then choose the whole library or one document.
**Prepare SAG2 Local Index** builds the local lexical cache; a query also prepares
its current scope automatically. Attachments are available only to their session.
Other libraries and other sessions never enter the candidate corpus.

Answers retain clickable local citations and the existing source preview. The
selected answer model retains its RPM and optional Langfuse monitoring. The
retrieval trace records each round, terms, candidate/selected chunk IDs, actual
selector and fallback reasons. Source content is always read from the local
catalogue, never from scoring-provider responses.

Index caches live inside the configured knowledge storage under `sag2_indexes`.
Their content fingerprints include scope-specific chunk identity, titles and
text. Changes create another cache; old cache files and user data are not deleted
automatically. They contain private document text and must not be committed.

## API and migration

- `GET /api/v1/kb/retrieval/status`: local SQLite/scorer readiness; no network probe.
- `POST /api/v1/kb/sag2/index`: prepare the selected library/document/session index.
- `POST /api/v1/kb/qa`: choose `retrieval_backend=sag2` and
  `retrieval_strategy=auto|jev|embedding|rerank|bm25`.
- `retrieval_backend=local` keeps the original zvec-grep workflow.

Old `retrieval_backend=sag`, `multi_jev`, `multi` and `vector` selections must be
updated. `/kb/sag/sync` returns an explicit retirement error. Old
`ALL_IN_ONE_SAG_*` settings and SAG source-status columns are not used. Original
files, documents, chunks and conversation records remain intact; no remote
service is contacted for ingestion or cleanup.

## Sources and evidence boundary

The [official SAG2 guide](https://github.com/Zleap-AI/SAG-Benchmark/tree/main/sag2)
and [reference algorithm](https://github.com/Zleap-AI/SAG-Benchmark/blob/main/sag2/scripts/sag2.py)
describe BM25 recall, JEV evidence decisions, term expansion and diversification.
The [paper](https://arxiv.org/abs/2610.22588) describes the original method;
[SAG-Wiki](https://github.com/Zleap-AI/SAG-Wiki) is its application.

Repository tests use explicitly synthetic source documents and local HTTP
protocol fixtures. These verify multi-hop bridging, scoring substitution,
citations and isolation, not live JEV/reranker quality or upstream benchmark
scores. Earlier original-SAG acceptance results do not validate SAG2.
