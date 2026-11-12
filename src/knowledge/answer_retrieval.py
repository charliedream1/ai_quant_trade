"""One scoped answer boundary with explicit SAG2 and lexical fallback metadata."""

from .files import KnowledgeFiles
from .retrieval import RetrievalLoop
from .retrieval_http import RetrievalUnavailableError
from .sag2_retrieval import SAG2Retrieval


class AnswerRetrieval:
    def __init__(self, repo, llm):
        self.repo, self.llm = repo, llm

    def run(self, question, history, *, backend="local", strategy="auto", **options):
        if backend not in {"local", "sag2"}:
            raise ValueError("Select local or sag2; original SAG has been retired")
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
        if backend == "sag2":
            try:
                return SAG2Retrieval(self.repo).search(
                    question, documents, strategy, options["limit"], options.get("rounds")
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
                "fallback_used": backend == "sag2",
            },
        )
