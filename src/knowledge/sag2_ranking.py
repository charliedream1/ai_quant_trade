"""Replaceable query-time evidence decisions over BM25 candidates."""

import json
import math
from time import monotonic
from urllib.parse import urlsplit

from src.core.env_file import resolve_env_value

from .config import knowledge_config
from .retrieval_http import JsonConnection, RetrievalUnavailableError
from .semantic_ranking import SemanticRanking
from .tracing import traced


class EvidenceSelector:
    def __init__(self, strategy, deadline):
        self.policy = knowledge_config()["sag2"]
        self.strategy, self.deadline = strategy, deadline
        self.reasons = []

    @traced("tool.sag2_selector", "tool")
    def rank(self, question, rows, evidence):
        methods = (
            [self.strategy]
            if self.strategy == "bm25"
            else list(
                dict.fromkeys(([] if self.strategy == "auto" else [self.strategy]) + self.policy["selector_order"])
            )
        )
        for method in methods:
            remaining = self.deadline - monotonic()
            if remaining <= 0:
                raise RetrievalUnavailableError("sag2_deadline")
            try:
                if method == "bm25":
                    return sorted(rows, key=lambda row: (-row["bm25_score"], row["chunk_id"])), method
                if method == "jev":
                    return self._jev(question, rows, evidence, remaining), method
                ranking = SemanticRanking(method)
                if not ranking.configured():
                    raise RetrievalUnavailableError(method + "_not_configured")
                context = self.policy["context_template"].format(
                    question=question,
                    evidence="\n".join(row["chunk_content"] for row in evidence)[: self.policy["context_chars"]],
                )
                scored = ranking.rank(context, rows, len(rows), timeout=remaining)
                if len(scored) != len(rows):
                    raise RetrievalUnavailableError(method + "_incomplete_scores")
                return scored, method
            except RetrievalUnavailableError as exc:
                reason = method + ":" + str(exc)
                if reason not in self.reasons:
                    self.reasons.append(reason)
        raise RetrievalUnavailableError("sag2_no_selector")

    def _jev(self, question, rows, evidence, remaining):
        cfg = self.policy["jev"]
        endpoint, model = (resolve_env_value(cfg[key]) for key in ("base_url_env", "model_env"))
        if not endpoint or not model:
            raise RetrievalUnavailableError("jev_not_configured")
        parsed = urlsplit(endpoint.rstrip("/"))
        if not parsed.path.endswith(("/decisions", "/systemone")):
            raise ValueError("JEV URL must end in /decisions or /systemone")
        connection = JsonConnection(
            endpoint,
            resolve_env_value(cfg["token_env"]),
            min(remaining, cfg["timeout_seconds"]),
            cfg["max_response_bytes"],
        )
        questions = {
            f"candidate_{row['chunk_id']}": {
                "type": "noul",
                "instructions": {
                    "question": cfg["criterion"],
                    "candidate_title": row["title"],
                    "candidate_passage": row["chunk_content"][: cfg["text_chars"]],
                },
                "criteria": cfg["criteria"],
            }
            for row in rows
        }
        state = {
            "original_question": question,
            "previously_retrieved_evidence": [
                {"title": row["title"], "passage": row["chunk_content"][: cfg["text_chars"]]}
                for row in evidence[: self.policy["seed_count"]]
            ],
        }
        try:
            answers, models = {}, {}
            for batch in self._batches(model, state, questions, cfg["max_request_chars"]):
                remaining = self.deadline - monotonic()
                if remaining <= 0:
                    raise RetrievalUnavailableError("sag2_deadline")
                connection.timeout = min(remaining, cfg["timeout_seconds"])
                result = connection.call("POST", "", batch)
                if set(result["answers"]) != set(batch["questions"]):
                    raise ValueError("Candidate scores do not match")
                answers.update(result["answers"])
                models.update({key: result.get("model", model) for key in batch["questions"]})
            scored = []
            for row in rows:
                answer = answers[f"candidate_{row['chunk_id']}"]
                score = answer["noul"]
                if (
                    answer["type"] != "noul"
                    or type(score) not in (float, int)
                    or not math.isfinite(score)
                    or not 0 <= score <= 1
                ):
                    raise ValueError("Invalid evidence score")
                scored.append({**row, "score": float(score), "selector_model": models[f"candidate_{row['chunk_id']}"]})
            return sorted(scored, key=lambda row: (-row["score"], -row["bm25_score"], row["chunk_id"]))
        except (KeyError, TypeError, ValueError):
            raise RetrievalUnavailableError("jev_response_invalid") from None
        finally:
            connection.close()

    @staticmethod
    def _batches(model, state, questions, maximum):
        batch = {"model": model, "state": json.dumps(state, ensure_ascii=False), "questions": {}}
        for key, question in questions.items():
            proposed = {**batch, "questions": {**batch["questions"], key: question}}
            if len(json.dumps(proposed, ensure_ascii=False)) > maximum:
                if not batch["questions"]:
                    raise RetrievalUnavailableError("jev_candidate_exceeds_request_budget")
                yield batch
                batch = {**batch, "questions": {key: question}}
                if len(json.dumps(batch, ensure_ascii=False)) > maximum:
                    raise RetrievalUnavailableError("jev_candidate_exceeds_request_budget")
            else:
                batch = proposed
        if batch["questions"]:
            yield batch
