"""SAG evidence is scoped before recall and checked against current local originals."""

import math
import re

from .sag_client import RetrievalUnavailableError
from .sag_sync import content_digest
from .semantic_ranking import SemanticRanking
from .tracing import traced


class SAGEvidence:
    def __init__(self, repo, client):
        self.repo, self.client = repo, client

    @traced("tool.sag_evidence", "tool")
    def search(self, question, documents, strategy, limit):
        eligible = {
            row["sag_source_id"]: row
            for row in documents
            if row.get("sag_source_id")
            and row.get("sag_sync_status", "").lower() == "ready"
            and row.get("sag_endpoint_hash") == self.client.identity
            and row.get("sag_content_hash") == content_digest(row)
        }
        if len(eligible) != len(documents):
            raise RetrievalUnavailableError("sag_index_not_ready_or_stale")
        cfg = self.client.policy
        if strategy not in {"auto", "multi_jev", "multi", "vector", "rerank"}:
            raise ValueError("Unknown retrieval strategy")
        methods = (
            [
                cfg["preferred_strategy"] if strategy == "auto" else "multi_jev",
                cfg["fallback_strategy"],
                cfg["final_fallback_strategy"],
            ]
            if strategy in {"auto", "multi_jev"}
            else ["vector"]
            if strategy == "rerank"
            else [strategy]
        )
        if strategy == "multi":
            methods.append(cfg["final_fallback_strategy"])
        methods = list(dict.fromkeys(methods))
        reasons: list[str] = []
        trace: list[dict] = []
        for method in methods:
            if method == "multi_jev" and not cfg["jev_enabled"]:
                reasons.append("jev_not_enabled")
                continue
            try:
                result = self.client.search(question, list(eligible), method, limit)
                rows = self._evidence(result, eligible)
                if (
                    strategy == "rerank"
                    or strategy == "auto"
                    and method != "multi_jev"
                    and SemanticRanking("rerank").configured()
                ):
                    try:
                        rows = SemanticRanking("rerank").rank(question, rows, limit)
                        method = "rerank"
                    except RetrievalUnavailableError as exc:
                        reasons.append(str(exc))
                trace.append(
                    {"round": len(trace) + 1, "keywords": [], "hits": len(rows), "backend": "sag", "strategy": method}
                )
                return (
                    rows[:limit],
                    trace,
                    "retrieved" if rows else "no_hits",
                    {
                        "retrieval_backend": "sag",
                        "retrieval_strategy": method,
                        "fallback_reasons": reasons,
                        "fallback_used": bool(reasons),
                    },
                )
            except RetrievalUnavailableError as exc:
                reasons.append(method + ":" + str(exc))
        raise RetrievalUnavailableError(";".join(reasons))

    def _evidence(self, result, allowed):
        if not isinstance(result, dict) or not isinstance(result.get("sections"), list):
            raise RetrievalUnavailableError("sag_evidence_invalid")
        rows, seen = [], set()
        for section in result["sections"]:
            if not isinstance(section, dict):
                raise RetrievalUnavailableError("sag_section_invalid")
            score = float(section.get("score") or 0)
            if not math.isfinite(score):
                raise ValueError("SAG evidence score is invalid")
            source = section.get("source_id")
            if source not in allowed:
                raise ValueError("SAG returned evidence outside the permitted document scope")
            row, content = allowed[source], str(section.get("content") or "")
            original = str(row.get("content") or "")
            normalized = re.sub(r"\s+", " ", content).strip()
            if not normalized or normalized not in re.sub(r"\s+", " ", original):
                raise ValueError("SAG evidence does not match the current original")
            key = row["id"], normalized
            if key in seen:
                continue
            seen.add(key)
            chunks = self.repo.db.query(
                "SELECT id,chunk_index,heading,content FROM kb_document_chunks WHERE doc_id=? ORDER BY chunk_index",
                (row["id"],),
            )
            chunk = next((item for item in chunks if normalized in re.sub(r"\s+", " ", item["content"])), None)
            rows.append(
                {
                    **row,
                    "chunk_id": chunk["id"] if chunk else None,
                    "chunk_index": chunk["chunk_index"] if chunk else 0,
                    "chunk_heading": chunk["heading"] if chunk else section.get("heading", ""),
                    "chunk_content": content,
                    "snippet": content,
                    "line_number": original[: max(0, original.find(content))].count("\n") + 1,
                    "score": score,
                    "sag_chunk_id": section.get("chunk_id"),
                }
            )
        return rows
