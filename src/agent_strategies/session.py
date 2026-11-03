"""One bounded real request per attempt; plain text ReAct and repaired JSON only."""

import json
import re
from time import monotonic

from json_repair import loads as repair_json

from src.agent.llm_client import LLMClient
from src.agent.providers import ProviderClient
from src.agent.providers.contracts import merge_selection

from .evidence import market_view
from .store import LOCK

TOOLS = re.compile(r"<tool_use>(.*?)</tool_use>", re.S | re.I)
FINAL = re.compile(r"<final>(.*?)</final>", re.S | re.I)


class Session:
    def __init__(self, store, run: dict, emit=None, cancelled=None, llm=None, budget=None):
        self.store, self.run = store, run
        self.emit = emit or (lambda *args: None)
        self.cancelled = cancelled or (lambda: False)
        self.llm = llm or LLMClient(repo=store.repo)
        self.started = monotonic()
        self.budget = budget

    def event(self, kind: str, payload: dict):
        self.store.event(self.run["id"], kind, payload)
        self.emit(kind, payload.get("role", kind), {**payload, "agent_strategy_run": self.run["id"]})

    def role(self, role: str, evidence: dict, contract: str) -> dict:
        cfg, request = self.run["config"], self.run["request"]
        request = merge_selection(request, cfg["policy"]["role_models"].get(role, {}))
        if "market" in evidence:
            evidence = {**evidence, "market": market_view(evidence["market"], cfg)}
        prompts, limits = cfg["prompts"], cfg["limits"]
        prompt = prompts["protocol"]
        variables = {
            "system": prompts["system"],
            "role": role,
            "instruction": prompts["roles"][role],
            "objective": cfg["definition"]["focus"],
            "index": list(evidence),
            "contract": prompts["contracts"][contract],
        }
        for key, value in variables.items():
            prompt = prompt.replace("{" + key + "}", str(value))
        history: list[dict[str, str]] = []
        reads: set[str] = set()
        tools = 0
        self.event("role_started", {"role": role})
        for turn in range(limits["max_turns"]):
            if self.cancelled() or monotonic() - self.started > limits["deadline_seconds"]:
                raise ValueError("研究已取消或超时")
            if len(prompt) + sum(len(row["content"]) for row in history) > limits["max_prompt_chars"]:
                raise ValueError("角色上下文超出预算")
            with LOCK:
                calls = self.store.repo.db.scalar(
                    "SELECT COUNT(*) FROM agent_strategy_events WHERE run_id=? AND kind='llm_request'",
                    (self.run["id"],),
                )
                if calls >= cfg["policy"]["calls"]:
                    raise ValueError("达到研究实际调用预算")
                if self.budget:
                    self.budget.take()
                self.event(
                    "llm_request",
                    {
                        "role": role,
                        "turn": turn + 1,
                        "backend": request.get("backend", "api"),
                        "model_id": request.get("model_id"),
                        "model_name": request.get("model_name"),
                        "reasoning_effort": request.get("reasoning_effort"),
                    },
                )
            requested_at = monotonic()
            response = ProviderClient(self.llm).complete(
                prompt,
                selection=request,
                history=history,
                purpose="Agent策略-" + role,
                expected_provider=cfg.get("role_model_snapshots", {}).get(role) or cfg.get("provider_snapshot"),
                timeout_seconds=max(0.1, limits["deadline_seconds"] - (monotonic() - self.started)),
                max_output_chars=limits["max_response_chars"],
                cancelled=self.cancelled,
                emit=lambda kind, text, data: self.event(
                    "provider_" + kind, {"role": role, "text": text, "details": data}
                ),
                enable_thinking=cfg["policy"]["enable_thinking"],
                max_output_tokens=cfg["policy"]["output_tokens"],
            )
            text = str(response.get("text") or "")
            if str(response.get("model", "")).lower() in {"mock", "mock-llm", ""}:
                raise ValueError("研究拒绝mock模型作为真实成功结果")
            usage, model = response.get("usage"), str(response.get("model") or "")
            if len(text) > limits["max_response_chars"] or not text.strip():
                raise ValueError("后端没有有效正文或输出超过预算")
            self.event(
                "llm_response",
                {
                    "role": role,
                    "text": text,
                    "usage": usage,
                    "model": model,
                    "provider": response.get("provider"),
                    "duration_ms": round((monotonic() - requested_at) * 1000),
                },
            )
            history.extend([{"role": "user", "content": prompt}, {"role": "assistant", "content": text}])
            calls = TOOLS.findall(text)
            if calls:
                observations = []
                for raw in calls:
                    tools += 1
                    call = repair_json(raw)
                    if tools > limits["max_tools"] or not isinstance(call, dict) or call.get("name") != "read_evidence":
                        raise ValueError("研究只允许有界读取证据")
                    arguments = call.get("arguments") or {}
                    if not isinstance(arguments, dict):
                        raise ValueError("工具参数必须为对象")
                    evidence_id = arguments.get("id")
                    if not isinstance(evidence_id, str) or evidence_id not in evidence:
                        raise ValueError("请求了未知研究证据")
                    reads.add(evidence_id)
                    if evidence_id == "documents":
                        reads.update(evidence[evidence_id])
                    elif evidence_id == "peers":
                        reads.update(evidence[evidence_id])
                    elif evidence_id == "factors":
                        reads.update(
                            row["id"]
                            for row in evidence[evidence_id]
                            if isinstance(row, dict) and isinstance(row.get("id"), str)
                        )
                    observations.append({"id": evidence_id, "content": evidence[evidence_id]})
                    self.event("tool", {"role": role, "id": evidence_id, "content": evidence[evidence_id]})
                prompt = prompts["observation"].replace("{observations}", json.dumps(observations, ensure_ascii=False))
                continue
            final = FINAL.search(text)
            value = repair_json(final.group(1) if final else text)
            if not isinstance(value, dict) or not set(evidence).issubset(reads):
                raise ValueError("角色未返回对象或未读取全部必要证据")
            value["read_ids"] = sorted(reads)
            self.event("role_finished", {"role": role, "result": value})
            return value
        raise ValueError("角色用完轮数而没有有效结论")
