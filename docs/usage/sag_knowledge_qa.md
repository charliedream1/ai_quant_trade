# SAG knowledge and single-document questions

The knowledge page offers **模型递归搜索（zvec-grep）** and **SAG with fallback** as independent choices. The default remains the original model-guided workflow: ordinary model generation plans keywords, bounded recursive rounds call zvec-grep, and the model answers from retrieved original passages with citations. Selecting this backend does not contact SAG or an embedding/rerank service. The maximum retrieval rounds control continues to govern the original workflow. SAG is optional and disabled by default; this application connects to an independently running self-hosted SAG service through REST. It does not install SAG's desktop app or Python package.

## Connect and index

Start SAG following its [official deployment guide](https://github.com/Zleap-AI/SAG). Choose an API port distinct from this platform. Configure the external service's generation and embedding models before expecting indexed documents to become ready.

Set `ALL_IN_ONE_SAG_ENABLED=true`, `ALL_IN_ONE_SAG_BASE_URL` and `ALL_IN_ONE_SAG_TOKEN` in local `.env` or `.llm_env`. The base may include `/api/v1`; the client adds it when absent. Use an endpoint without embedded credentials, query strings or fragments. A local trusted SAG address is allowed; metadata/link-local targets are blocked by the shared network policy. Do not commit local endpoints or keys.

Upload files normally. On the Q&A page, select the library and choose a whole-library or single-document scope. Refresh document choices and select the document where needed, then press **同步所选范围到SAG / 刷新索引状态**. This explicitly sends normalized text to the configured service and reports the real document status. If processing is pending, press again later to refresh; the gateway does not pretend pending documents are ready.

Each revision uses its own SAG source, keeping single-document retrieval isolated before recall. Already synchronized content refreshes status without another ingestion. Edited content or a different endpoint needs synchronization again. An uncertain write stops automatic resubmission and requires local review of the remote source rather than creating duplicates. No remote document or source is deleted automatically.

`sag.auto_sync` in `egs/knowledge.yaml` optionally synchronizes ordinary new imports. It defaults to false and excludes private session attachments. Manual synchronization can include a current session's attachment. Large libraries must be synchronized document by document when they exceed the configured batch size. Limits are reported rather than silently truncating documents.

## Ask a question

Select backend **SAG（可降级）**, choose a strategy and ask a question. **整个知识库** searches the permitted current library; **仅所选文档** searches exactly one selected document. For a new attachment, single-document mode can use exactly one newly attached file when no existing document is selected. Other libraries and other attachment sessions never become implicit search scope.

Single-document conversation history is separate from whole-library history. Answers retain local document IDs and clickable original-source previews. Returned SAG sections must match the permitted current original; unrelated source IDs or fabricated text are rejected before generation. Answer generation uses the platform's selected model and its existing RPM and optional Langfuse monitoring.

The response shows the effective backend and strategy, citation count and fallback reasons. A successful answer after fallback is not labeled as a successful JEV request. Configuration readiness does not prove a live service connection.

## JEV, embedding and rerank

| Choice | Behavior |
| --- | --- |
| `auto` | JEV when explicitly enabled, then SAG multi-hop, then vector retrieval. A configured standard reranker can replace precision ranking on candidates. |
| `multi_jev` | Attempts JEV only when `ALL_IN_ONE_SAG_JEV_ENABLED=true`; otherwise skips it with a visible reason and uses the declared fallback. |
| `multi` | Ordinary SAG multi-hop retrieval, then vector fallback if unavailable. |
| `vector` | SAG embedding/vector retrieval without requiring JEV. |
| `rerank` | SAG vector candidates followed by the configured standard rerank endpoint. |

JEV is a separate ranking service. SAG still needs embeddings for normal semantic indexing; choosing JEV does not eliminate that requirement. Configure JEV credentials on the external SAG service. This platform's JEV flag controls which search strategy it requests; it is not a live provider-health claim.

For a standard reranker, configure `KB_RERANK_BASE_URL`, `KB_RERANK_MODEL` and optional `KB_RERANK_API_KEY`. It uses the common `/rerank` JSON request with query, documents, model and top-n, and indexed relevance-score results. For a standard OpenAI-compatible embedding service, configure `KB_EMBEDDING_BASE_URL`, `KB_EMBEDDING_MODEL` and optional `KB_EMBEDDING_API_KEY`; it uses `/embeddings` with indexed vectors. Supply a service base such as its versioned API root, not the full method endpoint.

When SAG is unavailable, stale or not indexed, a configured standard reranker or embedding endpoint can rank a bounded set of authorized local chunks. If those paths are unavailable, the existing zvec-grep keyword loop remains the last fallback. Local semantic fallback is bounded by candidate limits, so it does not promise full-library semantic recall for arbitrarily large libraries. It creates no local vector database.

Provider response size, dimensions, candidate count, text lengths, timeouts and synchronization batch sizes are configured in YAML. No default paid provider or model is selected. Local deterministic protocol tests verify integration and boundaries, not SAG/JEV production quality or the upstream benchmark claims.

## API and troubleshooting

`GET /api/v1/kb/retrieval/status` reports safe configuration booleans without network calls. `POST /api/v1/kb/sag/sync` accepts a library, optional document ID and current session ID. `POST /api/v1/kb/qa` additionally accepts `retrieval_backend`, `retrieval_strategy` and optional `document_id`. Existing requests default to local library search.

Use the indexing-status refresh when a document is not ready. Check local credentials and external SAG permissions for authentication errors; inspect model/index settings on SAG for persistent strategy failures. The platform ignores SAG's generated summary and builds its answer from checked original sections, although a SAG deployment may still perform its own server-side query/summary model calls according to its settings.

See [remote access](remote_access.md) for connecting a chat client or browser. A new retrieval backend does not grant another remote account permission to use a library.
