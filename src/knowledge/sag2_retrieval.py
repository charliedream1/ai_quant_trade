"""BM25 recall, evidence decisions and evidence-driven lexical expansion."""

from itertools import zip_longest
from time import monotonic
from typing import Any

from .config import knowledge_config
from .retrieval_http import RetrievalUnavailableError
from .sag2_index import SAG2Index, tokens
from .sag2_ranking import EvidenceSelector
from .tracing import traced


class SAG2Retrieval:
    def __init__(self, repo):
        self.repo = repo
        self.policy = knowledge_config()["sag2"]

    @traced("agent.sag2_retrieval", "agent")
    def search(self, question, documents, strategy, limit, rounds=None):
        if strategy not in {"auto", "jev", "embedding", "rerank", "bm25"}:
            raise ValueError("SAG2 selector must be auto, jev, embedding, rerank or bm25")
        budget = self.policy["default_rounds"] if rounds is None else int(rounds)
        if not 1 <= budget <= self.policy["max_rounds"]:
            raise ValueError("SAG2 retrieval rounds exceed the configured range")
        deadline = monotonic() + self.policy["deadline_seconds"]
        selector = EvidenceSelector(strategy, deadline)
        index = SAG2Index(self.repo, documents)
        seen: set[int] = set()
        used: set[str] = set()
        trace: list[dict[str, Any]] = []
        evidence: list[dict[str, Any]] = []
        method = "bm25"
        try:
            terms = list(dict.fromkeys(tokens(question)))[: self.policy["query_terms"]]
            used.update(terms)
            candidates = index.recall(terms, self.policy["candidate_count"])
            for hop in range(budget):
                if not candidates:
                    break
                if monotonic() >= deadline:
                    raise RetrievalUnavailableError("sag2_deadline")
                seen.update(row["chunk_id"] for row in candidates)
                pool = list({row["chunk_id"]: row for row in [*evidence, *candidates]}.values())[
                    : self.policy["candidate_count"]
                ]
                evidence, method = selector.rank(question, pool, evidence)
                trace.append(
                    {
                        "round": hop + 1,
                        "keywords": terms,
                        "hits": len(candidates),
                        "backend": "sag2",
                        "strategy": method,
                        "candidate_chunk_ids": [row["chunk_id"] for row in pool],
                        "selected_chunk_ids": [row["chunk_id"] for row in evidence[:limit]],
                    }
                )
                if hop + 1 == budget:
                    break
                terms = index.expansion_terms(evidence, used)
                used.update(terms)
                if not terms:
                    break
                lists = [index.recall([term], self.policy["candidate_count"], seen) for term in terms]
                fresh: dict[int, dict[str, Any]] = {}
                for group in zip_longest(*lists):
                    for row in group:
                        if row is not None:
                            fresh.setdefault(row["chunk_id"], row)
                    if len(fresh) >= self.policy["candidate_count"]:
                        break
                # Keep the current result intact when expansion yields no fresh hits.
                if not fresh:
                    break
                evidence = evidence[: self.policy["seed_count"]]
                candidates = list(fresh.values())[: self.policy["candidate_count"] - len(evidence)]
            rows = self._diversify(evidence, limit, len(documents))
            return (
                rows,
                trace,
                "retrieved" if rows else "no_hits",
                {
                    "retrieval_backend": "sag2",
                    "retrieval_strategy": method,
                    "requested_strategy": strategy,
                    "fallback_reasons": selector.reasons,
                    "fallback_used": bool(selector.reasons),
                    "index_reused": index.reused,
                },
            )
        finally:
            index.close()

    def _diversify(self, rows, limit, document_count):
        selected = []
        counts: dict[int, int] = {}
        cap = limit if document_count == 1 else self.policy["per_document_limit"]
        for row in rows:
            identifier = row["id"]
            if counts.get(identifier, 0) < cap:
                selected.append(row)
                counts[identifier] = counts.get(identifier, 0) + 1
            if len(selected) == limit:
                break
        return selected
