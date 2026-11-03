"""SDKs retain DNS pinning, credential isolation and redirect boundaries."""

import socket
from unittest.mock import patch

import httpx
import pytest

from src.agent.llm_client import LLMClient
from src.agent.model_budget import CallBudget
from src.agent.model_options import model_options
from src.agent.model_transport import ModelTransport
from src.core.exceptions import BusinessError
from src.core.network_policy import network_session
from tests.agent.test_model_interfaces import model_server as model_server


@pytest.mark.parametrize("backend", ["http", "openai", "litellm"])
def test_sdk_requests_reject_metadata_after_dns(client, backend):
    config = {
        "base_url": "http://public-name.invalid/v1",
        "model_name": "test-model",
        "api_backend": backend,
        "max_retries": 2,
    }
    answer = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("169.254.169.254", 80))]
    with patch("src.core.network_policy.socket.getaddrinfo", return_value=answer) as dns:
        with pytest.raises((ValueError, BusinessError)):
            LLMClient()._request(config, [{"role": "user", "content": "test"}])
        assert dns.call_count == 1


def test_sdk_transport_refuses_origin_changes_without_connecting():
    with network_session() as session:
        transport = ModelTransport(session, CallBudget(3), "https://safe.example/v1")
        with pytest.raises(ValueError, match="其他来源"):
            transport.handle_request(httpx.Request("POST", "https://other.example/chat/completions"))


@pytest.mark.parametrize("backend", ["http", "openai", "litellm"])
def test_redirects_are_not_followed(client, model_server, backend):
    url, records, statuses = model_server
    statuses.append(302)
    with pytest.raises(BusinessError):
        LLMClient()._request(
            {"base_url": url, "model_name": "test-model", "api_backend": backend, "max_retries": 2},
            [{"role": "user", "content": "test"}],
        )
    assert len(records) == 1


@pytest.mark.parametrize("field", ["api_key", "apiKey", "x-api-key", "authorization", "password", "cookie"])
def test_secret_fields_cannot_be_smuggled_in_extra_body(field):
    with pytest.raises(ValueError, match="凭据"):
        model_options({"extra_body": {"nested": {field: "sensitive"}}})


def test_proxy_environment_does_not_change_sdk_connection(client, model_server, monkeypatch):
    url, records, _ = model_server
    monkeypatch.setenv("HTTPS_PROXY", "http://127.0.0.1:1")
    monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:1")
    result = LLMClient()._request(
        {"base_url": url, "model_name": "test-model", "api_backend": "openai"}, [{"role": "user", "content": "test"}]
    )
    assert result["text"] and len(records) == 1


@pytest.mark.parametrize("backend", ["openai", "litellm"])
def test_unconfigured_global_credentials_and_endpoints_are_not_inherited(client, model_server, monkeypatch, backend):
    url, records, _ = model_server
    monkeypatch.setenv("OPENAI_API_KEY", "unrelated-private-provider-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "http://169.254.169.254/v1")
    result = LLMClient()._request(
        {"base_url": url, "model_name": "test-model", "api_backend": backend}, [{"role": "user", "content": "test"}]
    )
    assert result["text"] and len(records) == 1
    assert records[0]["authorization"] != "Bearer unrelated-private-provider-key"
