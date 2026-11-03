"""New report tasks use the actual SDK and shared quota admission path."""

import pytest

from src.core.repository import Repository
from src.engine.insights.backend import generate_text
from src.engine.insights.config import insight_config
from tests.agent.test_model_interfaces import model_server as model_server


@pytest.mark.parametrize("backend", ["http", "openai", "litellm"])
def test_economic_reports_reach_shared_sdk_and_quota(client, model_server, backend):
    url, records, _ = model_server
    model = client.post(
        "/api/v1/llm-models",
        json={
            "name": "economic-sdk-" + backend,
            "model_name": "test-model",
            "base_url": url,
            "api_backend": backend,
            "rpm": 10,
        },
    ).json()["data"]
    result = generate_text(
        "Read only supplied observations",
        {"kind": "macro_analysis", "backend": "api", "model_id": model["id"]},
        insight_config(),
        lambda *args: None,
    )
    assert result and len(records) == 1
    assert records[0]["body"].get("stream", False) is False
    assert "tools" not in records[0]["body"] and "response_format" not in records[0]["body"]
    repo = Repository()
    assert repo.get("llm_models", model["id"])["call_count"] == 1
    assert repo.db.query_one("SELECT COUNT(*) AS n FROM llm_request_slots")["n"] == 1
