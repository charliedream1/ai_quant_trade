"""Optional local ONNX or OpenAI-compatible BGE embeddings for public news phrases."""

from functools import lru_cache
from importlib import import_module
from math import isfinite
from pathlib import Path

import numpy as np
import yaml

from src.core.config import PROJECT_ROOT, get_settings
from src.core.env_file import resolve_env_value
from src.core.logger import get_logger
from src.core.network_policy import validate_url
from src.knowledge.retrieval_http import JsonConnection


@lru_cache(maxsize=1)
def config():
    return yaml.safe_load((PROJECT_ROOT / "egs/config/data/news_bge.yaml").read_text(encoding="utf-8"))


def model_directory():
    directory = resolve_env_value("ALL_IN_ONE_NEWS_BGE_DIRECTORY")
    return PROJECT_ROOT / Path(directory).expanduser() if directory else get_settings().data_dir / config()["directory"]


def _file_signature(path):
    info = path.stat()
    return str(path.resolve()), info.st_size, info.st_mtime_ns


@lru_cache(maxsize=2)
def _onnx_session(tokenizer_signature, model_signature):
    ort = import_module("onnxruntime")
    tokenizers = import_module("tokenizers")
    cfg = config()["runtime"]
    tokenizer = tokenizers.Tokenizer.from_file(tokenizer_signature[0])
    tokenizer.enable_truncation(max_length=cfg["sequence_length"])
    tokenizer.enable_padding()
    options = ort.SessionOptions()
    options.intra_op_num_threads = cfg["cpu_threads"]
    options.inter_op_num_threads = cfg["cpu_threads"]
    session = ort.InferenceSession(model_signature[0], sess_options=options, providers=["CPUExecutionProvider"])
    return tokenizer, session


def local_vectors(directory, texts):
    candidates = (directory / "onnx/model_quantized.onnx", directory / "model.onnx")
    model = next((path for path in candidates if path.is_file()), candidates[0])
    tokenizer, session = _onnx_session(_file_signature(directory / "tokenizer.json"), _file_signature(model))
    encodings = tokenizer.encode_batch(texts)
    # ONNX field names map to tokenizer attributes.
    columns = {"input_ids": "ids", "attention_mask": "attention_mask", "token_type_ids": "type_ids"}  # nosec B105
    inputs = {
        entry.name: np.asarray([getattr(item, columns[entry.name]) for item in encodings], dtype=np.int64)
        for entry in session.get_inputs()
    }
    vectors = np.asarray(session.run(None, inputs)[0])
    return vectors[:, 0, :] if vectors.ndim == 3 else vectors


def remote_vectors(url, token, model, texts):
    parsed, _ = validate_url(url)
    if token and parsed.scheme != "https" and parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError("A credential-bearing BGE endpoint requires HTTPS or loopback")
    cfg = config()["runtime"]
    connection = JsonConnection(url, token, cfg["timeout_seconds"], cfg["max_response_bytes"])
    try:
        response = connection.call("POST", "/embeddings", {"model": model, "input": texts})
    finally:
        connection.close()
    data = sorted(response["data"], key=lambda row: row["index"])
    if [row["index"] for row in data] != list(range(len(texts))):
        raise ValueError("Embedding response indices do not match the request")
    return np.asarray([row["embedding"] for row in data], dtype=np.float64)


def _provider():
    mode = resolve_env_value("ALL_IN_ONE_NEWS_BGE_MODE").lower() or "auto"
    if mode == "remote":
        url = resolve_env_value("ALL_IN_ONE_NEWS_BGE_URL")
        token = resolve_env_value("ALL_IN_ONE_NEWS_BGE_API_KEY")
        name = resolve_env_value("ALL_IN_ONE_NEWS_BGE_MODEL") or "bge-small-zh-v1.5"
        return mode, lambda texts: remote_vectors(url, token, name, texts)
    directory = model_directory()
    if mode == "local" or mode == "auto" and (directory / "tokenizer.json").is_file():
        return "local", lambda texts: local_vectors(directory, texts)
    return "lexical", None


def rerank(rows):
    cfg = config()
    mode, provider = _provider()
    if not rows or provider is None:
        return rows, cfg["labels"]["lexical"]
    candidates = rows[: cfg["runtime"]["keyword_limit"]]
    phrases = [row["keyword"] for row in candidates]
    evidence = [row["headline"] for row in candidates]
    try:
        vectors = np.asarray(provider(phrases + evidence), dtype=np.float64)
        if vectors.ndim != 2 or vectors.shape[0] != len(phrases) * 2 or not np.isfinite(vectors).all():
            raise ValueError("Invalid embedding matrix")
        lengths = np.linalg.norm(vectors, axis=1)
        if not np.isfinite(lengths).all() or np.any(lengths == 0):
            raise ValueError("Invalid embedding norms")
        normalized = vectors / lengths[:, None]
        semantic = (normalized[: len(phrases)] * normalized[len(phrases) :]).sum(axis=1)
        peak = max(row["weight"] for row in candidates)
        blend = cfg["runtime"]["semantic_weight"]
        mixed = [
            ((1 - blend) * row["weight"] / peak + blend * (float(score) + 1) / 2, index, row)
            for index, (row, score) in enumerate(zip(candidates, semantic, strict=True))
        ]
        if not all(isfinite(value) for value, _, _ in mixed):
            raise ValueError("Invalid embedding score")
        ordered = [row for _, _, row in sorted(mixed, key=lambda item: (-item[0], item[1]))]
        return ordered + rows[len(candidates) :], cfg["labels"][mode]
    except Exception as exc:
        get_logger("market.news").warning(
            "News embedding fallback | provider={} error_type={}", mode, type(exc).__name__
        )
        return rows, cfg["labels"]["fallback"]


def extract_phrases(rows, *, lexical_label):
    """Select source phrases nearest to the normalized headline centroid."""
    cfg = config()
    mode, provider = _provider()
    if not rows:
        return rows, lexical_label
    if provider is None:
        return rows, cfg["labels"]["fallback"]
    phrases = [row["keyword"] for row in rows]
    headlines = list(dict.fromkeys(row["headline"] for row in rows))
    try:
        vectors = np.asarray(provider(phrases + headlines), dtype=np.float64)
        if vectors.ndim != 2 or len(vectors) != len(phrases) + len(headlines) or not np.isfinite(vectors).all():
            raise ValueError("Invalid embedding matrix")
        lengths = np.linalg.norm(vectors, axis=1)
        if not np.isfinite(lengths).all() or np.any(lengths == 0):
            raise ValueError("Invalid embedding norms")
        vectors = vectors / lengths[:, None]
        centroid = vectors[len(phrases) :].mean(axis=0)
        scores = vectors[: len(phrases)] @ centroid
        penalty = cfg["runtime"]["duplicate_penalty"]
        available = set(range(len(rows)))
        result: list[dict] = []
        while available and len(result) < cfg["runtime"]["keyword_limit"]:
            index = max(available, key=lambda i: (scores[i], -i))
            available.remove(index)
            result.append(rows[index])
            scores -= penalty * np.maximum(vectors[: len(phrases)] @ vectors[index], 0)
        return result, cfg["labels"][f"semantic_{mode}"]
    except Exception as exc:
        get_logger("market.news").warning(
            "News phrase extraction fallback | provider={} error_type={}", mode, type(exc).__name__
        )
        return rows, cfg["labels"]["fallback"]
