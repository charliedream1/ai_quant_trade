from pathlib import Path
from typing import Any

from src.agent.generic_agent_runtime import GenericAgentRuntime, GenericToolCall


class FakeLLM:
    def __init__(self, responses: list[str]) -> None:
        self.responses = responses
        self.prompts: list[str] = []

    def complete(
        self,
        prompt: str,
        purpose: str = "问答",
        *,
        history: list[dict[str, str]] | None = None,
        model_id: int | None = None,
    ) -> dict[str, Any]:
        self.prompts.append(prompt)
        text = self.responses.pop(0)
        return {"model": "fake-model", "text": text, "duration_ms": 1, "usage": {}, "purpose": purpose}


def test_generic_agent_runtime_repairs_tool_json_and_reads_project_file(tmp_path: Path):
    readme = tmp_path / "README.md"
    readme.write_text("AIQuant\n第二行\n", encoding="utf-8")
    llm = FakeLLM(
        [
            "先读取文件。\n<tool_use>{'name':'file_read','arguments':{'path':'README.md','count':1,}}</tool_use>",
            "已读取 README，可以继续分析。",
        ]
    )

    result = GenericAgentRuntime(llm=llm, project_root=tmp_path).run_once("读取 README")

    assert "已读取 README" in result.text
    assert result.model == "fake-model"
    assert result.tool_events[0]["tool"] == "file_read"
    assert result.tool_events[0]["status"] == "success"
    assert "AIQuant" in result.tool_events[0]["content"]
    assert "<tool_result" in llm.prompts[1]


def test_generic_agent_runtime_rejects_paths_outside_project(tmp_path: Path):
    runtime = GenericAgentRuntime(llm=FakeLLM(["无工具"]), project_root=tmp_path)

    result = runtime.dispatch_tool(GenericToolCall(name="file_read", arguments={"path": "../secret.txt"}))

    assert result.status == "error"
    assert "只能访问项目目录内" in result.content
