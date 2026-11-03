"""Validate native events before accepting their text as a research response."""


def check_research_event(row: dict) -> None:
    raw = row.get("raw") or {}
    if not raw:
        return  # Locally generated process-start/exit observations.
    kind = raw.get("type")
    allowed = {
        "system",
        "assistant",
        "result",
        "stream_event",
        "user",
        "thread.started",
        "turn.started",
        "turn.completed",
        "turn.failed",
        "item.started",
        "item.updated",
        "item.completed",
        "error",
    }
    if kind not in allowed:
        raise ValueError("研究角色返回未核验的原生事件：" + str(kind))
    if kind == "system":
        for key in ("tools", "mcp_servers", "plugins", "skills"):
            if raw.get(key):
                raise ValueError("研究初始化仍载入原生能力：" + key)
    item = raw.get("item") or {}
    if item and item.get("type") not in {"agent_message", "reasoning", "error"}:
        raise ValueError("研究角色触发了原生工具：" + str(item.get("type")))
    message = raw.get("message") or {}
    for part in message.get("content") or []:
        if isinstance(part, dict) and part.get("type") in {"tool_use", "tool_result"}:
            raise ValueError("研究角色触发了原生工具内容块")
    event = raw.get("event") or {}
    block = event.get("content_block") or {}
    delta = event.get("delta") or {}
    if block.get("type") in {"tool_use", "tool_result"} or delta.get("type") == "input_json_delta":
        raise ValueError("研究角色正在流式调用原生工具")


def collect_response(iterator, backend, config, emit, cancelled, output_limit, events) -> dict:
    fragments, usage, model = [], None, ""
    size = 0
    required_init = config["providers"][backend].get("required_init_fields", [])
    initialized = not required_init
    for event in iterator:
        if cancelled and cancelled():
            raise ValueError(config["messages"]["cancelled"])
        row = {"kind": event.kind, "status": event.status, "text": event.text, "raw": event.raw}
        events.append(row)
        check_research_event(row)
        raw = event.raw
        if raw.get("type") == "system" and raw.get("subtype") == "init" and required_init:
            if any(key not in raw or raw[key] != [] for key in required_init):
                raise ValueError("研究初始化未证明工具、MCP、插件和Skill全部关闭")
            initialized = True
        if emit:
            emit(event.kind, event.text, {"provider": backend, "raw": event.raw})
        if event.kind == "error":
            raise ValueError(event.text)
        if event.kind == "action":
            raise ValueError(config["messages"]["native_tool"])
        if event.kind == "message":
            fragments.append(event.text)
            size += len(event.text)
        if event.raw.get("usage"):
            usage = event.raw["usage"]
        model = str(event.raw.get("model") or (event.raw.get("message") or {}).get("model") or model)
        if size > output_limit:
            raise ValueError("CLI正文超过输出预算")
    text = "".join(fragments).strip()
    if not initialized:
        raise ValueError("缺少可核验的研究初始化事件，不能接受原生CLI正文")
    if not text:
        raise ValueError(config["messages"]["empty"])
    return {"text": text, "model": model, "usage": usage}
