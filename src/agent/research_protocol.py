"""Bounded text ReAct protocol for evidence-based research roles."""

from __future__ import annotations

import json
import re
from time import perf_counter
from typing import Any

from json_repair import loads as repair_json_loads

from src.agent.llm_client import LLMClient
from src.agent.providers import ProviderClient

TOOL_PATTERN = re.compile(r"<tool_use>(.*?)</tool_use>", re.DOTALL | re.IGNORECASE)
FINAL_PATTERN = re.compile(r"<final>(.*?)</final>", re.DOTALL | re.IGNORECASE)
VERDICTS = {"approve", "watch", "reject"}


def run_role(
    role: str,
    objective: str,
    evidence: dict[str, Any],
    peers: dict[str, Any],
    config: dict[str, Any],
    llm: LLMClient,
    model_id: int | None = None,
    selection: dict | None = None,
    emit=None,
    cancelled=None,
    expected_provider=None,
) -> dict[str, Any]:
    started = perf_counter()
    settings = config["roles"][role]
    replacements = {
        "role_name": settings["name"],
        "instruction": settings["instruction"],
        "objective": objective,
        "evidence_index": json.dumps(list(evidence), ensure_ascii=False),
        "peer_index": json.dumps(list(peers), ensure_ascii=False),
        "required_evidence": json.dumps(settings["required_evidence"], ensure_ascii=False),
    }
    prompt = str(config["prompt"])
    for key, value in replacements.items():
        prompt = prompt.replace("{" + key + "}", str(value))
    history: list[dict[str, str]] = []
    events: list[dict[str, Any]] = []
    model = ""
    reads: set[str] = set()
    peer_reads: set[str] = set()
    for turn in range(int(config["max_turns"])):
        if cancelled and cancelled():
            raise ValueError("多Agent研究已取消")
        selected = selection or {"model_id": model_id}
        if emit:
            emit("llm_request", {"role": role, "turn": turn + 1, "selection": selected})
        result = ProviderClient(llm).complete(
            prompt,
            purpose=f"多Agent投研-{role}",
            history=history,
            selection=selected,
            cancelled=cancelled,
            expected_provider=expected_provider,
            emit=(lambda kind, text, data: emit("provider_" + kind, {"role": role, "text": text, "details": data}))
            if emit
            else None,
        )
        if emit:
            emit(
                "llm_response",
                {
                    "role": role,
                    "turn": turn + 1,
                    "text": result.get("text"),
                    "usage": result.get("usage"),
                    "provider": result.get("provider"),
                },
            )
        model = str(result.get("model") or "")
        if model in {"mock-llm", "mock"}:
            raise ValueError("未配置真实模型，多 Agent 不接受 mock-llm 作为成功结果")
        text = str(result.get("text") or "")
        history.extend([{"role": "user", "content": prompt}, {"role": "assistant", "content": text}])
        calls = list(TOOL_PATTERN.finditer(text))
        if calls:
            observations = []
            for call in calls:
                if len(events) >= int(config["max_tool_calls"]):
                    raise ValueError("Agent 超过工具调用预算")
                payload = repair_json_loads(call.group(1))
                name, key = _tool_fields(payload)
                source = evidence if name == "read_evidence" else peers if name == "read_peer" else {}
                if key not in source:
                    raise ValueError(f"工具不可用或证据不存在：{name}/{key}")
                if name == "read_evidence":
                    reads.add(key)
                elif name == "read_peer":
                    peer_reads.add(key)
                content = json.dumps(source[key], ensure_ascii=False)
                if len(content) > int(config["max_evidence_chars"]):
                    raise ValueError("单项证据超过长度预算，请缩小回测报告")
                observations.append({"tool": name, "id": key, "content": source[key]})
                events.append({"turn": turn + 1, "tool": name, "id": key, "status": "success"})
            prompt = str(config["continue_prompt"]).replace(
                "{observations}", json.dumps(observations, ensure_ascii=False)
            )
            continue
        final = FINAL_PATTERN.search(text)
        parsed = repair_json_loads(final.group(1) if final else text)
        if peer_reads != set(peers):
            raise ValueError("Agent 尚未读取全部已有同事结果")
        if not set(settings["required_evidence"]).issubset(reads):
            raise ValueError("Agent 尚未读取本角色必要证据")
        decision = _validate_decision(parsed, evidence, reads, int(config["max_summary_chars"]))
        return {
            **decision,
            "role": role,
            "name": settings["name"],
            "model": model,
            "backend": selected.get("backend", "api"),
            "duration_ms": round((perf_counter() - started) * 1000),
            "tool_events": events,
        }
    raise ValueError("Agent 达到最大轮数，仍未返回有效结论")


def _tool_fields(payload: Any) -> tuple[str, str]:
    if not isinstance(payload, dict) or not isinstance(payload.get("arguments"), dict):
        raise ValueError("工具请求必须包含 name 和 arguments 对象")
    return str(payload.get("name") or ""), str(payload["arguments"].get("id") or "")


def _validate_decision(payload: Any, evidence: dict[str, Any], reads: set[str], limit: int) -> dict[str, Any]:
    if (
        not isinstance(payload, dict)
        or not isinstance(payload.get("verdict"), str)
        or payload["verdict"] not in VERDICTS
    ):
        raise ValueError("Agent 结论缺少合法 verdict")
    summary = payload.get("summary")
    references = payload.get("evidence_ids")
    concerns = payload.get("concerns")
    if not isinstance(summary, str) or not summary.strip() or len(summary) > limit:
        raise ValueError("Agent summary 为空或超过长度限制")
    if (
        not isinstance(references, list)
        or not references
        or any(not isinstance(key, str) or key not in evidence for key in references)
    ):
        raise ValueError("Agent 引用了不存在的证据")
    if not reads or any(key not in reads for key in references):
        raise ValueError("Agent 必须实际读取引用的证据")
    if not isinstance(concerns, list) or any(not isinstance(item, str) or len(item) > limit for item in concerns):
        raise ValueError("Agent concerns 格式无效")
    return {"verdict": payload["verdict"], "summary": summary, "evidence_ids": references, "concerns": concerns}
