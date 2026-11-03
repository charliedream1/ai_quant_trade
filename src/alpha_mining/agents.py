"""Real bounded text-ReAct calls with complete visible-output and tool evidence logs."""

import json
import re
from time import perf_counter
from typing import Any
from uuid import uuid4

from json_repair import loads as repair_json

from src.agent.llm_client import LLMClient
from src.agent.providers import ProviderClient

from .config import digest, invalid
from .store import LOCK, AlphaStore

TOOLS = re.compile(r"<tool_use>(.*?)</tool_use>", re.DOTALL | re.IGNORECASE)
FINAL = re.compile(r"<final>(.*?)</final>", re.DOTALL | re.IGNORECASE)


class AgentSession:
    def __init__(self, store: AlphaStore, study: dict, llm=None, cancelled=None):
        self.store, self.study = store, study
        self.llm = llm or LLMClient(repo=store.repo)
        self.cancelled = cancelled or (lambda: False)

    def run(self, role: str, evidence: dict, objective: str, model: dict | None = None) -> dict[str, Any]:
        cfg = self.study["config"]
        selected = model or cfg["models"].get(role) or cfg["models"].get("default", {})
        if selected.get("backend", "api") == "api" and not selected.get("model_id"):
            raise invalid("该研究角色没有选择真实模型：" + role)
        prompt_cfg = cfg["prompts"]
        settings = prompt_cfg["roles"][role]
        prompt = prompt_cfg["protocol"]
        for key, value in {
            "role": role,
            "required": settings["required"],
            "index": list(evidence),
            "objective": objective,
            "instruction": settings["instruction"],
        }.items():
            prompt = prompt.replace("{" + key + "}", str(value))
        history: list[dict[str, str]] = []
        reads: set[str] = set()
        tool_calls = 0
        call_id = uuid4().hex
        provider = cfg.get("provider_snapshots", {}).get(role) or cfg.get("provider_snapshots", {}).get("default")
        if model is not None:
            provider = next(
                (
                    value
                    for choice, value in zip(
                        cfg.get("configurations", []), cfg.get("configuration_providers", []), strict=False
                    )
                    if choice == selected
                ),
                None,
            )
        for turn in range(cfg["limits"]["max_turns"]):
            if self.cancelled():
                raise invalid("研究已取消")
            if len(prompt) > cfg["limits"]["max_prompt_chars"]:
                raise invalid("研究证据超过单轮长度预算，请缩小范围")
            with LOCK:
                used = self.store.repo.db.scalar(
                    "SELECT COUNT(*) FROM alpha_events WHERE study_id=? AND kind='llm_request'", (self.study["id"],)
                )
                if used >= cfg["limits"]["max_model_calls"]:
                    raise invalid("研究达到实际模型调用预算")
                self.store.event(
                    self.study["id"],
                    "llm_request",
                    {
                        "role": role,
                        "backend": selected.get("backend", "api"),
                        "model_id": selected.get("model_id"),
                        "model_name": selected.get("model_name"),
                        "reasoning_effort": selected.get("reasoning_effort", ""),
                        "call_id": call_id,
                        "turn": turn + 1,
                    },
                )
            self.store.write(
                self.study["id"], f"{call_id}-{turn + 1}-request.json", {"prompt": prompt, "history": history}
            )
            started = perf_counter()
            request_options = (
                {"enable_thinking": selected["enable_thinking"]} if selected.get("enable_thinking") is not None else {}
            )
            response = ProviderClient(self.llm).complete(
                prompt,
                selection=selected,
                expected_provider=provider,
                timeout_seconds=cfg["limits"]["timeout_seconds"],
                max_output_chars=cfg["limits"]["max_response_chars"],
                cancelled=self.cancelled,
                emit=lambda kind, text, data: self.store.event(
                    self.study["id"], "provider_" + kind, {"role": role, "text": text, "details": data}
                ),
                history=history,
                model_id=selected.get("model_id"),
                reasoning_effort=selected.get("reasoning_effort") or None,
                purpose="Alpha研究-" + role,
                **request_options,
            )
            text, name = str(response.get("text") or ""), str(response.get("model") or "")
            if name.lower() in {"mock", "mock-llm", ""}:
                raise invalid("真实研究拒绝mock模型作为成功结果")
            if len(text) > cfg["limits"]["max_response_chars"]:
                raise invalid("模型输出超过研究预算")
            artifact = f"{call_id}-{turn + 1}-response.md"
            self.store.write(self.study["id"], artifact, text)
            self.store.event(
                self.study["id"],
                "llm_response",
                {
                    "role": role,
                    "model": name,
                    "duration_ms": round((perf_counter() - started) * 1000),
                    "call_id": call_id,
                    "artifact": artifact,
                    "text": text,
                    "usage": response.get("usage"),
                    "provider": response.get("provider"),
                },
            )
            history.extend([{"role": "user", "content": prompt}, {"role": "assistant", "content": text}])
            tools = list(TOOLS.finditer(text))
            if tools:
                observations = []
                for match in tools:
                    tool_calls += 1
                    if tool_calls > cfg["limits"]["max_tool_calls"]:
                        raise invalid("研究角色达到实际工具调用预算")
                    request = repair_json(match.group(1))
                    if not isinstance(request, dict) or request.get("name") != "read_evidence":
                        raise invalid("研究只允许读取登记证据，不执行任意工具")
                    evidence_key = (request.get("arguments") or {}).get("id")
                    if not isinstance(evidence_key, str) or evidence_key not in evidence:
                        raise invalid("模型请求不存在的证据")
                    reads.add(evidence_key)
                    observations.append({"id": evidence_key, "content": evidence[evidence_key]})
                    self.store.event(
                        self.study["id"],
                        "tool",
                        {
                            "role": role,
                            "tool": "read_evidence",
                            "id": evidence_key,
                            "digest": digest(evidence[evidence_key]),
                        },
                    )
                prompt = prompt_cfg["continue"].replace("{observations}", json.dumps(observations, ensure_ascii=False))
                continue
            final = FINAL.search(text)
            result = repair_json(final.group(1) if final else text)
            if not isinstance(result, dict) or not set(settings["required"]).issubset(reads):
                raise invalid("模型未返回对象或未实际读取必要证据")
            return result
        raise invalid("研究角色达到轮数预算，未取得有效结果")
