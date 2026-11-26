"""Optional local multilingual NLI classifier for research ingestion."""

import json
from functools import lru_cache
from hashlib import sha256
from importlib import import_module
from pathlib import Path
from uuid import uuid4

from filelock import FileLock

from src.core.env_file import resolve_env_value
from src.core.network_policy import network_session
from src.core.page_work import check

from .research_classification import policy


def model_directory() -> Path:
    from src.core.config import get_settings

    path = resolve_env_value(policy()["model"]["directory_env"])
    return Path(path).expanduser() if path else get_settings().data_dir / "models" / "research-minilm"


@lru_cache(maxsize=2)
def _session(directory, signature):
    from tokenizers import Tokenizer

    config = json.loads((directory / "config.json").read_text(encoding="utf-8"))
    labels = {str(label).casefold(): int(index) for index, label in config["id2label"].items()}
    weights = directory / "model_quantized.onnx"
    if not weights.is_file():
        weights = directory / "model.onnx"
    session = import_module("onnxruntime").InferenceSession(str(weights), providers=["CPUExecutionProvider"])
    tokenizer = Tokenizer.from_file(str(directory / "tokenizer.json"))
    tokenizer.enable_truncation(max_length=policy()["model"]["max_tokens"])
    tokenizer.enable_padding(pad_id=tokenizer.token_to_id("<pad>") or 0)
    return session, tokenizer, labels["entailment"]


def score_topics(text, labels):
    import numpy as np

    directory = model_directory()
    paths = [directory / "config.json", directory / "tokenizer.json"]
    weights = next(
        (path for name in ("model_quantized.onnx", "model.onnx") if (path := directory / name).is_file()), None
    )
    if weights is None or any(not path.is_file() for path in paths):
        raise ValueError("Configure a local NLI ONNX model directory")
    signature = tuple((path.name, path.stat().st_mtime_ns, path.stat().st_size) for path in [*paths, weights])
    session, tokenizer, entailment = _session(directory.resolve(), signature)
    inputs = tokenizer.encode_batch(
        [(text, policy()["model"]["hypothesis"].format(label=label)) for label in labels.values()]
    )
    features = {
        "input_ids": [item.ids for item in inputs],
        "attention_mask": [item.attention_mask for item in inputs],
        "token_type_ids": [item.type_ids for item in inputs],
    }
    logits = session.run(
        None, {item.name: np.asarray(features[item.name], dtype=np.int64) for item in session.get_inputs()}
    )[0]
    if not np.isfinite(logits).all():
        raise ValueError("Invalid NLI scores")
    scores = np.exp(logits - logits.max(axis=1, keepdims=True))
    version = "local-nli:" + sha256(repr(signature).encode()).hexdigest()[:12]
    return dict(zip(labels, (scores[:, entailment] / scores.sum(axis=1)).tolist(), strict=True)), version


def install(confirmed):
    if not confirmed:
        raise ValueError("Confirm the model download first")
    from src.core.config import get_settings

    cfg = policy()["model"]
    data = get_settings().data_dir.resolve()
    directory = model_directory().resolve()
    if not directory.is_relative_to(data):
        raise ValueError("For an externally configured directory, supply the existing ONNX model files")
    directory.mkdir(parents=True, exist_ok=True)
    with FileLock(str(directory / ".install.lock"), timeout=5), network_session(public_only=True) as session:
        for name, (size, expected) in cfg["files"].items():
            target = directory / Path(name).name
            if target.exists():
                if target.stat().st_size == size:
                    with target.open("rb") as artifact:
                        digest = sha256()
                        for block in iter(lambda: artifact.read(65536), b""):
                            check()
                            digest.update(block)
                        if digest.hexdigest() == expected:
                            continue
                raise ValueError("A different model artifact already exists in the selected directory")
            temporary = target.with_name(f"{target.name}.{uuid4().hex}.part")
            address = f"{cfg['repository']}/resolve/{cfg['revision']}/{name}"
            digest, received = sha256(), 0
            with session.get(address, stream=True, timeout=policy()["limits"]["model_timeout"]) as response:
                response.raise_for_status()
                with temporary.open("wb") as output:
                    for block in response.iter_content(65536):
                        check()
                        received += len(block)
                        if received > size:
                            raise ValueError("Model file exceeded its declared size")
                        digest.update(block)
                        output.write(block)
            if received != size or digest.hexdigest() != expected:
                raise ValueError("Model checksum or file size did not match")
            temporary.replace(target)
    return "本地零样本模型已就绪"
