"""Optional standard embedding/rerank protocols operate only on scoped evidence."""

import math

from src.core.env_file import resolve_env_value

from .config import knowledge_config
from .sag_client import JsonConnection, RetrievalUnavailableError
from .tracing import traced


class SemanticRanking:
    def __init__(self, kind):
        self.kind = kind
        self.policy = knowledge_config()["sag"][kind]

    def configured(self):
        return all(resolve_env_value(self.policy[key]) for key in ("base_url_env", "model_env"))

    @traced("tool.knowledge_semantic_rank", "tool")
    def rank(self, question, rows, limit):
        if not rows or not self.configured():
            raise RetrievalUnavailableError(self.kind + "_not_configured")
        policy = self.policy
        rows = rows[: policy["max_candidates"]]
        texts = [str(row["chunk_content"])[: policy["text_chars"]] for row in rows]
        base = resolve_env_value(policy["base_url_env"]).rstrip("/")
        connection = JsonConnection(
            base, resolve_env_value(policy["token_env"]), policy["timeout_seconds"], policy["max_response_bytes"]
        )
        model = resolve_env_value(policy["model_env"])
        try:
            if self.kind == "rerank":
                data = connection.call(
                    "POST",
                    "/rerank",
                    {"model": model, "query": question, "documents": texts, "top_n": min(limit, len(rows))},
                )
                results = data["results"]
                selected = []
                seen = set()
                for item in results:
                    index, score = item["index"], float(item["relevance_score"])
                    if (
                        type(index) is not int
                        or index in seen
                        or not 0 <= index < len(rows)
                        or not math.isfinite(score)
                    ):
                        raise RetrievalUnavailableError("rerank_response_invalid")
                    seen.add(index)
                    selected.append({**rows[index], "score": score})
                return sorted(selected, key=lambda row: -row["score"])[:limit]
            data = connection.call("POST", "/embeddings", {"model": model, "input": [question, *texts]})
            entries = sorted(data["data"], key=lambda item: item["index"])
            if [item["index"] for item in entries] != list(range(len(rows) + 1)):
                raise RetrievalUnavailableError("embedding_response_invalid")
            vectors = [item["embedding"] for item in entries]
            size = len(vectors[0])
            if not size or size > policy["max_dimensions"] or any(len(vector) != size for vector in vectors):
                raise RetrievalUnavailableError("embedding_dimensions_invalid")
            if any(
                type(value) not in (int, float) or not math.isfinite(value) for vector in vectors for value in vector
            ):
                raise RetrievalUnavailableError("embedding_values_invalid")
            query = vectors[0]
            qnorm = math.sqrt(sum(value * value for value in query))
            scored = []
            for row, vector in zip(rows, vectors[1:], strict=True):
                norm = math.sqrt(sum(value * value for value in vector))
                score = (
                    sum(a * b for a, b in zip(query, vector, strict=True)) / (qnorm * norm) if qnorm and norm else 0.0
                )
                scored.append({**row, "score": score})
            return sorted(scored, key=lambda row: -row["score"])[:limit]
        except (KeyError, TypeError, ValueError, OverflowError):
            raise RetrievalUnavailableError(self.kind + "_response_invalid") from None
        finally:
            connection.close()
