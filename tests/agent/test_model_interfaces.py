"""Actual SDK wire requests over a bounded local HTTP server, with no paid calls."""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from src.agent.llm_client import LLMClient
from src.core.exceptions import BusinessError
from src.core.repository import Repository


@pytest.fixture()
def model_server():
    requests = []
    statuses = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):  # noqa: N802
            request = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            requests.append({"body": request, "path": self.path, "authorization": self.headers.get("Authorization")})
            status = statuses.pop(0) if statuses else 200
            body = {
                "id": "fixture-response",
                "object": "chat.completion",
                "created": 1,
                "model": request["model"],
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": "有依据的回答[1]"},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            }
            if status != 200:
                body = {"error": {"message": "fixture failure", "type": "fixture"}}
            encoded = json.dumps(body, ensure_ascii=False).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
            self.send_header("Retry-After", "0")
            self.end_headers()
            self.wfile.write(encoded)

        def log_message(self, *args):
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/v1", requests, statuses
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        assert not thread.is_alive()


def create_model(client, server, backend, **extra):
    response = client.post(
        "/api/v1/llm-models",
        json={
            "name": "test-" + backend,
            "base_url": server,
            "model_name": "test-model",
            "api_backend": backend,
            "purpose": ["问答"],
            **extra,
        },
    ).json()
    assert response["code"] == 0, response
    return response["data"]


@pytest.mark.parametrize("backend", ["http", "openai", "litellm"])
def test_real_backends_preserve_wire_contract(client, model_server, backend, monkeypatch):
    url, records, _ = model_server
    monkeypatch.setenv("SDK_TEST_API_KEY", "synthetic-sdk-credential")
    model = create_model(client, url, backend, rpm=3, api_key_env="SDK_TEST_API_KEY", extra_body={"top_p": 0.8})
    result = LLMClient().complete("按资料回答", model_id=model["id"], enable_thinking=False, reasoning_effort="low")
    assert result["text"] == "有依据的回答[1]" and result["usage"]["total_tokens"] == 15
    assert result["api_backend"] == backend and result["retry_count"] == 0
    assert len(records) == 1 and records[0]["path"] == "/v1/chat/completions"
    body = records[0]["body"]
    assert body["model"] == "test-model" and body["enable_thinking"] is False and body["reasoning_effort"] == "low"
    assert body["top_p"] == 0.8 and "extra_body" not in body
    assert not {"tools", "functions", "response_format"} & body.keys()
    assert records[0]["authorization"] == "Bearer synthetic-sdk-credential"
    assert Repository().get("llm_models", model["id"])["success_count"] == 1


@pytest.mark.parametrize("backend", ["http", "openai", "litellm"])
def test_sdk_retry_disabled_platform_attempts_consume_rpm(client, model_server, backend):
    url, records, statuses = model_server
    statuses.extend([429, 200])
    model = create_model(client, url, backend, rpm=2, wait_on_limit=False, max_retries=1)
    result = LLMClient().complete("重试", model_id=model["id"])
    assert result["retry_count"] == 1 and len(records) == 2
    with pytest.raises(BusinessError, match="限流"):
        LLMClient().complete("不能绕过", model_id=model["id"])
    assert len(records) == 2


@pytest.mark.parametrize("backend", ["http", "openai", "litellm"])
def test_auth_failure_is_not_retried(client, model_server, backend):
    url, records, statuses = model_server
    statuses.append(401)
    model = create_model(client, url, backend, max_retries=3)
    with pytest.raises(BusinessError):
        LLMClient().complete("不可重试", model_id=model["id"])
    assert len(records) == 1


def test_configuration_group_and_body_validation(client, model_server):
    url, _, _ = model_server
    model = create_model(client, url, "http", rpm=10, quota_group="team")
    response = client.post(
        "/api/v1/llm-models",
        json={"name": "conflict", "base_url": url, "model_name": "another", "rpm": 11, "quota_group": "team"},
    ).json()
    assert response["code"] != 0
    for invalid in [
        {"api_backend": "unknown"},
        {"rpm": -1},
        {"rpm": None},
        {"extra_body": {"model": "overwrite"}},
        {"extra_body": {"api_key": "do-not-save"}},
        {"extra_body": {"nested": {"authorization": "no"}}},
    ]:
        response = client.put(f"/api/v1/llm-models/{model['id']}", json=invalid).json()
        assert response["code"] != 0, invalid
    shaped = client.get(f"/api/v1/llm-models/{model['id']}").json()["data"]
    assert shaped["api_backend"] == "http" and shaped["rpm"] == 10 and shaped["extra_body"] == {}
