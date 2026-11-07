"""One scoped answer boundary with explicit SAG, semantic and lexical fallback metadata."""

from .files import KnowledgeFiles
from .retrieval import RetrievalLoop
from .sag_client import RetrievalUnavailableError, SAGClient
from .sag_retrieval import SAGEvidence
from .semantic_ranking import SemanticRanking


class AnswerRetrieval:
    def __init__(self, repo, llm):
        self.repo, self.llm = repo, llm

    def run(self, question, history, *, backend="local", strategy="auto", **options):
        if backend not in {"local", "sag"}:
            raise ValueError("Unknown knowledge backend")
        documents = KnowledgeFiles(self.repo).documents(
            options["library"],
            session_id=options["session_id"],
            category_id=options.get("category_id"),
            scope=options.get("scope", "all"),
            document_id=options.get("document_id"),
        )
        if options.get("document_id") is not None and not documents:
            raise ValueError("Document is not available in this library/session scope")
        reasons = []
        if backend == "sag" and documents:
            client = SAGClient()
            try:
                return SAGEvidence(self.repo, client).search(question, documents, strategy, options["limit"])
            except RetrievalUnavailableError as exc:
                reasons.append(str(exc))
            finally:
                client.close()
            candidates = self._candidates(documents)
            for kind in ("rerank", "embedding"):
                ranking = SemanticRanking(kind)
                if not ranking.configured():
                    continue
                try:
                    rows = ranking.rank(question, candidates, options["limit"])
                    return (
                        rows,
                        [{"round": 1, "keywords": [], "hits": len(rows), "backend": kind}],
                        "retrieved" if rows else "no_hits",
                        {
                            "retrieval_backend": kind,
                            "retrieval_strategy": kind,
                            "fallback_reasons": reasons,
                            "fallback_used": True,
                        },
                    )
                except RetrievalUnavailableError as exc:
                    reasons.append(str(exc))
        rows, trace, status = RetrievalLoop(self.repo, self.llm).run(question, history, **options)
        return (
            rows,
            trace,
            status,
            {
                "retrieval_backend": "local",
                "retrieval_strategy": "keywords",
                "fallback_reasons": reasons,
                "fallback_used": backend == "sag",
            },
        )

    def _candidates(self, documents):
        result: list[dict] = []
        maximum = max(
            SemanticRanking("embedding").policy["max_candidates"], SemanticRanking("rerank").policy["max_candidates"]
        )
        for row in documents:
            chunks = self.repo.db.query(
                "SELECT * FROM kb_document_chunks WHERE doc_id=? ORDER BY chunk_index LIMIT ?",
                (row["id"], maximum - len(result)),
            )
            for chunk in chunks:
                result.append(
                    {
                        **row,
                        "chunk_id": chunk["id"],
                        "chunk_index": chunk["chunk_index"],
                        "chunk_heading": chunk["heading"],
                        "chunk_content": chunk["content"],
                        "snippet": chunk["content"],
                        "line_number": 1,
                    }
                )
            if len(result) >= maximum:
                break
        return result
