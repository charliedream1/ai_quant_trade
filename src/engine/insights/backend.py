"""Streaming model adapters; only observed public output reaches process events."""

import json
import os
from collections.abc import Callable, Iterator
from time import perf_counter
from typing import Any
from urllib.parse import urlsplit

from src.agent.llm_client import LLMClient
from src.agent.providers import ProviderClient, provider_snapshot
from src.agent.providers.config import backend_names
from src.agent.providers.registry import check_identity
from src.core.config import get_settings


def validate_backend(payload: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    backend = payload["backend"]
    if backend == "api":
        client = LLMClient()
        try:
            profile = client._select_config(payload.get("model_id"))
            payload["model_id"] = profile["id"]
            state = provider_snapshot(payload, client=client)
            check_identity(payload.get("_provider_snapshot"), state)
            return state
        finally:
            client.session.close()
    elif backend in backend_names() - {"api"}:
        state = provider_snapshot(payload)
        if payload.get("_provider_snapshot"):
            state = provider_snapshot(payload, probe=True)
            check_identity(payload["_provider_snapshot"], state)
        if not state["installed"]:
            raise ValueError(config["messages"]["unavailable"])
        if get_settings().data_mode == "mock" and os.environ.get("ALL_IN_ONE_ENABLE_REAL_CLI", "").lower() not in {
            "1",
            "true",
            "yes",
        }:
            raise ValueError(config["messages"]["mock_cli_disabled"])
    else:
        raise ValueError(config["messages"]["invalid_backend"])
    return state


def _api_text(prompt: str, payload: dict[str, Any], config: dict[str, Any]) -> Iterator[str]:
    client = LLMClient()
    profile = client._select_config(payload.get("model_id"))
    check_identity(payload.get("_provider_snapshot"), provider_snapshot(payload, client=client))
    defaults = config["defaults"]
    base = str(profile.get("base_url") or "").rstrip("/")
    parsed = urlsplit(base)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or not profile.get("model_name"):
        raise ValueError(config["messages"]["unavailable"])
    key = client._resolve_api_key(profile)
    headers = {"Accept": "text/event-stream", "Content-Type": "application/json"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    url = base if base.endswith("/chat/completions") else base + "/chat/completions"
    request = {
        "model": profile["model_name"],
        "stream": True,
        "messages": [{"role": "system", "content": config["prompts"]["system"]}, {"role": "user", "content": prompt}],
        "max_tokens": defaults["output_tokens"],
        "temperature": defaults["temperature"],
    }
    if payload.get("reasoning_effort"):
        request["reasoning_effort"] = payload["reasoning_effort"]
    started = perf_counter()
    failure: Exception | None = None
    try:
        with client.session.post(
            url,
            headers=headers,
            json=request,
            stream=True,
            timeout=(defaults["connect_timeout"], defaults["read_timeout"]),
        ) as response:
            response.raise_for_status()
            response.encoding = "utf-8"
            if "text/event-stream" not in response.headers.get("content-type", ""):
                yield str(response.json()["choices"][0]["message"]["content"])
                return
            for line in response.iter_lines(chunk_size=1, decode_unicode=True):
                if perf_counter() - started > defaults["deadline_seconds"]:
                    raise TimeoutError(config["messages"]["timeout"])
                if not line or not line.startswith("data:"):
                    continue
                raw = line[5:].strip()
                if raw == "[DONE]":
                    return
                event = json.loads(raw)
                if event.get("error"):
                    raise ValueError(str(event["error"]))
                for choice in event.get("choices") or []:
                    if choice.get("finish_reason") == "length":
                        raise ValueError(config["messages"]["invalid_result"])
                    content = (choice.get("delta") or {}).get("content")
                    if isinstance(content, str) and content:
                        yield content
    except Exception as exc:
        failure = exc
        raise
    finally:
        client._record_usage(
            profile, success=failure is None, duration_ms=round((perf_counter() - started) * 1000), error=failure
        )
        client.session.close()


def generate_text(
    prompt: str,
    payload: dict[str, Any],
    config: dict[str, Any],
    emit: Callable[..., None],
) -> str:
    fragments = []
    size = 0
    if payload["backend"] == "api":
        events = ({"kind": "message", "text": text} for text in _api_text(prompt, payload, config))
    else:
        response = ProviderClient().complete(
            prompt,
            selection=payload,
            emit=emit,
            cancelled=payload.get("_cancelled"),
            expected_provider=payload.get("_provider_snapshot"),
            timeout_seconds=config["defaults"]["read_timeout"],
            max_output_chars=config["defaults"]["max_output_chars"],
        )
        return response["text"]
    for event in events:
        if payload.get("_cancelled") and payload["_cancelled"]():
            raise ValueError(config["messages"].get("cancelled", config["messages"]["timeout"]))
        text = event["text"]
        if event["kind"] == "error":
            raise ValueError(text)
        if text:
            emit(event["kind"], text, {key: value for key, value in event.items() if key != "text"})
        if event["kind"] == "message":
            fragments.append(text)
            size += len(text)
            if size > config["defaults"]["max_output_chars"]:
                raise ValueError(config["messages"]["invalid_result"])
    result = "".join(fragments).strip()
    if not result:
        raise ValueError(config["messages"]["no_output"])
    return result
