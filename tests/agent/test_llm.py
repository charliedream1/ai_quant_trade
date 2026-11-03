import os

from src.agent import model_catalog as llm_models
from src.agent.llm_client import LLMClient
from src.core.env_file import (
    delete_env_value,
    env_status,
    import_env_file,
    masked_env_rows,
    read_env_values,
    save_env_value,
)
from src.frontend.services import FrontendService


class FakeResponse:
    status_code = 200
    text = ""

    def raise_for_status(self):
        return None

    def json(self):
        return {
            "model": "test-model",
            "choices": [{"message": {"content": "真实兼容接口回答"}}],
            "usage": {"total_tokens": 12},
        }


class FakeSession:
    def __init__(self):
        self.request = None

    def post(self, url, **kwargs):
        self.request = {"url": url, **kwargs}
        return FakeResponse()


def test_optional_thinking_flag_is_only_sent_when_explicit(client):
    session = FakeSession()
    model = {"base_url": "https://llm.example.test/v1", "model_name": "test-model"}
    llm = LLMClient(session=session)
    llm._request(model, [{"role": "user", "content": "test"}])
    assert "enable_thinking" not in session.request["json"]
    llm._request(model, [{"role": "user", "content": "test"}], enable_thinking=False)
    assert session.request["json"]["enable_thinking"] is False
    assert "tools" not in session.request["json"] and "response_format" not in session.request["json"]


def test_model_config_and_openai_compatible_request(client, monkeypatch):
    monkeypatch.setenv("TEST_LLM_API_KEY", "secret-value")
    created = client.post(
        "/api/v1/llm-models",
        json={
            "name": "test-provider",
            "base_url": "https://llm.example.test/v1/",
            "api_key_env": "TEST_LLM_API_KEY",
            "model_name": "test-model",
            "temperature": 0.35,
            "max_tokens": 2048,
            "timeout_seconds": 45,
            "system_prompt": "测试系统提示词",
            "level": "fast",
            "purpose": ["问答"],
        },
    ).json()["data"]

    assert created["is_default"] is True
    assert created["api_key"] == ""
    assert created["temperature"] == 0.35
    assert created["max_tokens"] == 2048

    session = FakeSession()
    result = LLMClient(session=session).complete(
        "测试问题",
        history=[{"role": "user", "content": "上一问"}, {"role": "assistant", "content": "上一答"}],
    )

    assert result["text"] == "真实兼容接口回答"
    assert session.request["url"] == "https://llm.example.test/v1/chat/completions"
    assert session.request["headers"]["Authorization"] == "Bearer secret-value"
    assert session.request["json"]["temperature"] == 0.35
    assert session.request["json"]["max_tokens"] == 2048
    assert session.request["json"]["messages"][-1]["content"] == "测试问题"
    stats = client.get(f"/api/v1/llm-models/{created['model_id']}").json()["data"]
    assert stats["call_count"] == 1
    assert stats["success_count"] == 1
    assert stats["failure_count"] == 0
    assert stats["last_status"] == "success"
    assert stats["avg_duration_ms"] >= 0

    disabled = client.put(f"/api/v1/llm-models/{created['model_id']}", json={"enabled": False}).json()["data"]
    assert disabled["enabled"] is False
    assert disabled["is_default"] is False
    client.post(f"/api/v1/llm-models/{created['model_id']}/set-default", json={"level": "fast"})
    restored = client.get(f"/api/v1/llm-models/{created['model_id']}").json()["data"]
    assert restored["enabled"] is True
    assert restored["is_default"] is True


def test_environment_file_import_masks_values(tmp_path, monkeypatch):
    key = "TEST_IMPORTED_LLM_KEY"
    monkeypatch.delenv(key, raising=False)
    source = tmp_path / "provider.env"
    source.write_text(f"{key}=first-secret\nMODEL_NAME=test-model\n", encoding="utf-8")
    target = tmp_path / ".llm_env"

    result = import_env_file(source, target=target)
    assert result["imported"] == [key, "MODEL_NAME"]
    assert read_env_values(target)[key] == "first-secret"
    assert os.environ[key] == "first-secret"
    rows = {row["name"]: row for row in masked_env_rows(target)}
    assert rows[key]["value"] == "****cret"
    assert "first-secret" not in str(rows)

    replacement = tmp_path / "replacement.env"
    replacement.write_text(f"{key}=second-secret\n", encoding="utf-8")
    assert import_env_file(replacement, overwrite=False, target=target)["skipped"] == [key]
    assert import_env_file(replacement, overwrite=True, target=target)["imported"] == [key]
    assert read_env_values(target)[key] == "second-secret"

    checked = env_status(key, target=target)
    assert checked["configured"] is True
    assert checked["masked_value"] == "****cret"
    deleted = delete_env_value(key, target=target)
    assert deleted["deleted"] is True
    assert key not in read_env_values(target)
    assert env_status(key, target=target)["configured"] is False


def test_save_env_value_validates_name(tmp_path):
    target = tmp_path / ".llm_env"
    save_env_value("VALID_ENV_NAME", "ok", target=target)
    assert read_env_values(target)["VALID_ENV_NAME"] == "ok"


def test_plain_api_key_is_moved_to_environment(monkeypatch):
    saved = {}
    monkeypatch.setattr(llm_models, "save_env_value", lambda name, value: saved.update({name: value}))

    values = llm_models._validated_values(
        {
            "name": "My Provider",
            "base_url": "https://example.test/v1",
            "api_key": "top-secret",
            "model_name": "provider-model",
        },
        creating=True,
    )

    assert saved == {"LLM_MY_PROVIDER_API_KEY": "top-secret"}
    assert values["api_key_env"] == "LLM_MY_PROVIDER_API_KEY"
    assert values["api_key"] == ""


def test_floating_chat_uses_message_history(monkeypatch):
    captured = {}

    def complete(_client, prompt, purpose, *, history):
        captured.update(prompt=prompt, purpose=purpose, history=history)
        return {"model": "test-model", "text": "当前回答", "duration_ms": 12}

    monkeypatch.setattr(LLMClient, "complete", complete)
    messages, cleared, status = FrontendService().floating_chat(
        "当前问题",
        [
            {"role": "user", "content": "上一问"},
            {"role": "assistant", "content": "上一答"},
        ],
    )

    assert captured["history"][-1] == {"role": "assistant", "content": "上一答"}
    assert messages[-2:] == [
        {"role": "user", "content": "当前问题"},
        {"role": "assistant", "content": "当前回答"},
    ]
    assert cleared == ""
    assert "test-model" in status
