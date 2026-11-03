import builtins
import sys
import types
from pathlib import Path
from typing import Any

from src.agent.generic_agent_runtime import GenericAgentRuntime
from src.agent.langfuse_observer import LangfuseObserver


class FakeLLM:
    def __init__(self, responses: list[str]) -> None:
        self.responses = responses

    def complete(
        self,
        prompt: str,
        purpose: str = "问答",
        *,
        history: list[dict[str, str]] | None = None,
        model_id: int | None = None,
    ) -> dict[str, Any]:
        text = self.responses.pop(0)
        return {
            "model": "fake-model",
            "text": text,
            "duration_ms": 7,
            "usage": {"prompt_tokens": 11, "completion_tokens": 13, "total_tokens": 24},
            "purpose": purpose,
        }


class FakeContext:
    def __init__(self, value: Any = None) -> None:
        self.value = value

    def __enter__(self) -> Any:
        return self.value

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> bool:
        return False


class FakeObservation:
    def __init__(self, calls: list[tuple[str, dict[str, Any]]], name: str) -> None:
        self.calls = calls
        self.name = name

    def update(self, **kwargs: Any) -> None:
        self.calls.append((f"update:{self.name}", kwargs))


class FakeLangfuseClient:
    def __init__(self, calls: list[tuple[str, dict[str, Any]]]) -> None:
        self.calls = calls

    def start_as_current_observation(self, **kwargs: Any) -> FakeContext:
        self.calls.append(("start", kwargs))
        return FakeContext(FakeObservation(self.calls, str(kwargs.get("name") or "-")))

    def flush(self) -> None:
        self.calls.append(("flush", {}))


def test_langfuse_observer_is_disabled_by_default(monkeypatch):
    monkeypatch.delenv("ALL_IN_ONE_GENERIC_AGENT_LANGFUSE_ENABLED", raising=False)
    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)

    observer = LangfuseObserver.from_config({})

    assert not observer.enabled
    assert observer.reason == "disabled"


def test_langfuse_observer_missing_sdk_degrades_to_noop(monkeypatch):
    monkeypatch.setenv("ALL_IN_ONE_GENERIC_AGENT_LANGFUSE_ENABLED", "true")
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-test")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-test")
    real_import = builtins.__import__

    def fake_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "langfuse":
            raise ImportError("langfuse is not installed")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    observer = LangfuseObserver.from_config({"enabled": True})
    with observer.generation(turn=1, prompt="hello", history_count=0) as observation:
        observation.finish(output="world", metadata={"ok": True})

    assert not observer.enabled
    assert observer.reason == "sdk_missing"


def test_generic_agent_records_langfuse_without_content_by_default(
    tmp_path: Path,
    monkeypatch,
):
    calls: list[tuple[str, dict[str, Any]]] = []
    fake_module = types.ModuleType("langfuse")

    def fake_get_client() -> FakeLangfuseClient:
        return FakeLangfuseClient(calls)

    def fake_propagate_attributes(**kwargs: Any) -> FakeContext:
        calls.append(("propagate", kwargs))
        return FakeContext()

    fake_module.get_client = fake_get_client
    fake_module.propagate_attributes = fake_propagate_attributes
    monkeypatch.setitem(sys.modules, "langfuse", fake_module)
    monkeypatch.setenv("ALL_IN_ONE_GENERIC_AGENT_LANGFUSE_ENABLED", "true")
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-test")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-test")

    (tmp_path / "README.md").write_text("AIQuant\n", encoding="utf-8")
    config_path = tmp_path / "generic_agent.yaml"
    config_path.write_text(
        """
generic_agent:
  max_turns: 2
  observability:
    langfuse:
      enabled: true
      capture_content: false
      trace_name: Test GenericAgent
      environment: test
      tags:
        - unit-test
""".strip()
        + "\n",
        encoding="utf-8",
    )
    llm = FakeLLM(
        [
            '<tool_use>{"name":"file_read","arguments":{"path":"README.md","count":1}}</tool_use>',
            "已完成。",
        ]
    )

    result = GenericAgentRuntime(llm=llm, project_root=tmp_path, config_path=config_path).run_once(
        "读取 README",
        session_id=123,
    )

    start_types = [item[1]["as_type"] for item in calls if item[0] == "start"]
    assert start_types == ["agent", "generation", "tool", "generation"]
    assert ("flush", {}) in calls
    propagate = next(item[1] for item in calls if item[0] == "propagate")
    assert propagate["session_id"] == "123"
    assert propagate["trace_name"] == "Test GenericAgent"
    assert all(item[1].get("input") is None for item in calls if item[0] == "start")
    assert all("output" not in item[1] for item in calls if item[0].startswith("update:"))
    assert result.model == "fake-model"
    assert result.tool_events[0]["tool"] == "file_read"
