# SAG2 live retrieval and answer validation

## Result and scope

The 2026-11-12 acceptance passed using actual SQLite FTS5/BM25 retrieval,
WorkBuddy CLI's free Hy3 generation and cached local
BAAI/bge-small-zh-v1.5 ONNX embedding inference (512 dimensions).
Neither generated answers nor embedding vectors were replaced with fixed
responses. All source documents were explicitly synthetic acceptance material,
not real trading policies or a production corpus.

The final run made six Hy3 completions. Its model usage identified only hy3,
reported zero cost for each call and recorded zero native tool calls. The
existing platform LLMClient and an actual loopback HTTP service carried the
generation requests. No original SAG service was started.

## Observed results

| Case | Observed behavior | Query time |
| --- | --- | --- |
| BM25 expansion and Hy3, whole library | All 8 preregistered facts present, supported by 3 original citations | 21.724 s |
| Actual BGE scoring and Hy3, whole library | All 8 facts present, supported by 3 original citations | 21.931 s |
| JEV unavailable, actual embedding fallback | All 8 facts present; effective selector embedding; JEV/rerank unconfigured reasons visible | 24.627 s |
| Single-document question | Both expected facts present; only the selected document cited | 12.024 s |
| Session-owned attachment | Both expected facts present; only the attachment cited | 9.172 s |
| Other-library secret query | No hits, no citations, no secret disclosure | 0.208 s |
| Unrelated query | No hits and no invented sources | 0.175 s |
| Unsupported guaranteed-return claim | Model stated that the documents make no future-return commitment | 26.539 s |

The eight synthesis facts were the drawdown threshold and duration, position
limit, recovery threshold and duration, two reviewers, and review identifier.
Manual inspection confirmed that each cited document contained its attributed
facts, including after embedding changed the citation ordering. Citation checks
allow Markdown whitespace normalization, but reject changes to source words or
numbers and out-of-range citation indices.

A separate question containing only the project name first retrieved the index
document. Its terms retrieved the policy in round two and the review receipt in
round three. The original question did not contain the downstream thresholds or
reviewer names. This validates evidence-driven lexical expansion on this corpus.

Three repeated cached BM25 retrievals, excluding answer generation, took
7.919, 8.522 and 7.799 ms (median 7.919 ms). These small-corpus measurements are
not a throughput benchmark or proof of performance on large libraries. The
small difference in whole-answer times does not establish superiority of either
selector.

## Isolation and browser verification

A different session was rejected when explicitly requesting the private
attachment. The authorized owner could answer from that attachment. Cross-library
and empty retrievals supplied no evidence to answer generation. Original source
snippets matched the permitted uploaded text after whitespace normalization.

The browser restored the actual generated answer and references from its
session, clicked the review receipt citation and opened its original Markdown in
the left-side reader. The reader displayed the expected reviewers and review
identifier. Browser, platform HTTP, generation bridge and embedding service
owned by the test were stopped after verification.

## Reproduction and limitations

The opt-in runner is `tests/knowledge/test_sag2_live.py`; source material,
questions, expectations and budgets are in
`tests/knowledge/sag2_live_acceptance.yaml`. Set `SAG2_LIVE=1` and select a new
E-drive evidence directory with `SAG2_LIVE_OUTPUT`. The existing WorkBuddy helper
uses the runtime path environment variable names documented in
`tests/knowledge/hy3_acceptance.yaml`. `SAG2_EMBEDDING_RUNTIME` selects an existing
private acceptance runtime containing its environment, cached model and
`embed_server.py`. That runtime is deliberately excluded from Git; the test does
not install packages, download models or change the desktop application's files.
The reproduction environment is Windows; Linux live execution was not tested.

The first attempt exposed changed WorkBuddy internal codec exports. The helper
now handles the inspected old and current layouts and keeps decoded login data
only in memory. The next attempt completed model calls but exposed two acceptance
script issues: exact whitespace comparison did not account for Markdown blank
line normalization, and the browser needed to expand session settings before
restoring history. Those checks were corrected and the final complete run passed.
Failed-attempt evidence was retained separately rather than overwritten.

JEV and a real cross-encoder rerank endpoint were not configured. Their live
ranking quality remains unmeasured; the JEV-named case above is explicitly a
fallback test. A query-time embedding selector is an approximation to contextual
JEV scoring, and this acceptance does not reproduce upstream SAG2 benchmarks.

Raw answers, traces, calls, inference logs and screenshots remain in private
E-drive evidence storage. Published documentation contains no credentials or
machine-specific account paths. See the [SAG2 guide](sag_knowledge_qa.md) for
deployment settings and [retrieval principles](../principles/knowledge_retrieval.md).
