"""Explicit free-hy3 smoke through both actual SDKs and the ordinary HTTP contract."""

import json
import os
from pathlib import Path

import pytest
import yaml

from src.agent.llm_client import LLMClient
from tests.knowledge.workbuddy_hy3_runtime import Hy3Runtime, openai_bridge

pytestmark = pytest.mark.skipif(
    os.environ.get("MODEL_API_HY3_LIVE") != "1", reason="Explicit real-model acceptance only"
)


@pytest.mark.parametrize("backend", ["openai", "litellm"])
def test_free_hy3_through_sdk(client, tmp_path, backend):
    policy = yaml.safe_load(Path("tests/knowledge/hy3_acceptance.yaml").read_text(encoding="utf-8"))
    output = Path(os.environ["MODEL_API_HY3_OUTPUT"]) / backend
    output.mkdir(parents=True, exist_ok=True)
    runtime = Hy3Runtime(policy, output)
    with openai_bridge(runtime) as endpoint:
        config = client.post(
            "/api/v1/llm-models",
            json={
                "name": "real-hy3-" + backend,
                "base_url": endpoint,
                "model_name": "hy3",
                "api_backend": backend,
                "rpm": 3,
                "timeout_seconds": 180,
            },
        ).json()["data"]
        response = LLMClient().complete(
            "资料：恢复申请需净值回撤低于4.2%且持续5个交易日。请仅根据资料说明恢复条件。", model_id=config["id"]
        )
        assert "4.2" in response["text"] and "5" in response["text"]
        assert response["api_backend"] == backend and response["retry_count"] == 0
        assert len(runtime.records) == 1 and set(runtime.records[0]["model_usage"]) == {"hy3"}
        (output / "response.json").write_text(json.dumps(response, ensure_ascii=False, indent=2), encoding="utf-8")
