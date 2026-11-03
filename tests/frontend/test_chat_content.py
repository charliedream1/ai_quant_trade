"""Multi-turn Gradio histories remain plain text and CLI updates arrive progressively."""

from src.frontend.common.callbacks import safe
from src.frontend.service.foundation import _chat_history_messages
from src.frontend.services import FrontendService
from src.strategy.codex_cli import CodexStreamEvent


def test_gradio_text_blocks_and_legacy_pairs_are_flattened():
    blocks = [{"type": "text", "text": "第一轮"}, {"type": "text", "text": "补充内容"}]
    history = _chat_history_messages([{"role": "user", "content": blocks}, {"role": "assistant", "content": "回答"}])
    assert history == [{"role": "user", "content": "第一轮\n补充内容"}, {"role": "assistant", "content": "回答"}]
    assert _chat_history_messages([[blocks, "回答"]]) == history


def test_floating_cli_yields_native_progress_before_final_message(client, monkeypatch):
    monkeypatch.setenv("ALL_IN_ONE_ENABLE_REAL_CLI", "true")
    prompts = []

    def stream(self, prompt, **kwargs):
        assert kwargs.get("stdin_prompt") is True
        prompts.append(prompt)
        yield CodexStreamEvent("process", "running", "已启动")
        yield CodexStreamEvent("message", "running", "你好")
        yield CodexStreamEvent("process", "completed", "已完成")

    monkeypatch.setattr("src.frontend.service.assistant.CodexCliRunner.stream", stream)
    history = [{"role": "user", "content": [{"type": "text", "text": "第一轮"}]}]
    events = list(safe(FrontendService().floating_cli_chat_stream)("第二轮", history, "codex"))
    assert len(events) >= 4
    assert events[0][2] == "已接收 CLI 消息" and "running" in events[1][2]
    assert events[-1][0][0]["content"] == "第一轮"
    assert events[-1][0][-1]["content"] == "你好" and "completed" in events[-1][2]
    assert "第一轮" in prompts[0] and "第二轮" in prompts[0]
