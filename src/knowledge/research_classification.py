"""Research taxonomy and bounded document classifiers."""

from __future__ import annotations

import json
import math
import re
import unicodedata
from collections import Counter
from functools import lru_cache
from typing import Any

import yaml

from src.core.config import PROJECT_ROOT


@lru_cache(maxsize=1)
def policy() -> dict[str, Any]:
    return yaml.safe_load((PROJECT_ROOT / "egs/config/knowledge/research_ingestion.yaml").read_text(encoding="utf-8"))


def topics() -> dict[str, tuple[list[str], list[str]]]:
    return {
        code: (group["label"], topic)
        for group in policy()["categories"].values()
        for code, topic in group["topics"].items()
    }


def topic_choices() -> list[tuple[str, str]]:
    return [
        ("待审核 / Needs review", ""),
        *[(f"{group[0]} / {topic[0]}", code) for code, (group, topic) in topics().items()],
    ]


def _features(text: str) -> Counter[str]:
    import jieba

    text = unicodedata.normalize("NFKC", text).casefold()
    chinese = re.findall(r"[\u3400-\u9fff]+", text)
    words = re.findall(r"[a-z][a-z0-9]+", text)
    for phrase in chinese:
        words.extend(word for word in jieba.lcut(phrase) if len(word) > 1)
        words.extend(phrase[index : index + 2] for index in range(len(phrase) - 1))
    return Counter(words)


@lru_cache(maxsize=1)
def _training():
    examples = {code: _features(topic[2]) for code, (_, topic) in topics().items()}
    frequency = Counter(word for counts in examples.values() for word in counts)
    idf = {word: 1 + math.log((1 + len(examples)) / (1 + count)) for word, count in frequency.items()}
    return examples, idf


def _traditional(text: str) -> dict[str, float]:
    examples, idf = _training()

    def vector(counts):
        raw = {word: (1 + math.log(count)) * idf[word] for word, count in counts.items() if word in idf}
        norm = math.sqrt(sum(value * value for value in raw.values())) or 1
        return {word: value / norm for word, value in raw.items()}

    query = vector(_features(text))
    return {
        code: sum(query.get(word, 0) * value for word, value in vector(example).items())
        for code, example in examples.items()
    }


def classify(text: str, mode: str, model_id: int | None = None) -> tuple[str, float, str]:
    cfg = policy()
    text = text[: cfg["limits"]["text_chars"]]
    if mode == "llm":
        from json_repair import loads

        from src.agent.llm_client import LLMClient
        from src.agent.real_models import require_real_model

        if not model_id:
            raise ValueError("Select an enabled classification model")
        payload = {"categories": {code: topic[1] for code, (_, topic) in topics().items()}, "document": text}
        with require_real_model():
            response = LLMClient().complete(
                cfg["model"]["prompt"].format(payload=json.dumps(payload, ensure_ascii=False)),
                purpose="research_classification",
                model_id=model_id,
                timeout_seconds=cfg["limits"]["model_timeout"],
                max_output_tokens=cfg["limits"]["model_output_tokens"],
                max_output_chars=cfg["limits"]["model_output_chars"],
            )
        result = loads(response["text"])
        if not isinstance(result, dict) or result.get("category") not in {"", *topics()}:
            raise ValueError("Invalid classification response")
        score = result.get("confidence")
        if isinstance(score, bool) or not isinstance(score, (int, float)) or not 0 <= score <= 1:
            raise ValueError("Invalid classification confidence")
        topic = result["category"] if score >= cfg["thresholds"][mode]["minimum"] else ""
        return topic, float(score), str(response.get("model") or model_id)
    if mode == "zero_shot":
        from .research_onnx import score_topics

        scores, version = score_topics(text, {code: topic[1] for code, (_, topic) in topics().items()})
    elif mode == "traditional":
        scores, version = _traditional(text), f"tfidf:{cfg['version']}"
    else:
        raise ValueError("Unknown classification mode")
    first, second = sorted(scores, key=scores.__getitem__, reverse=True)[:2]
    score = scores[first]
    thresholds = cfg["thresholds"][mode]
    accepted = score >= thresholds["minimum"] and score - scores[second] >= thresholds["margin"]
    return first if accepted else "", score, version
