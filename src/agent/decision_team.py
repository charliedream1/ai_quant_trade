"""Constrained candidate decisions over ordinary generation and textual ReAct."""

import json
import re
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

from json_repair import loads as repair_loads

from src.core.timeutil import utc_now_iso
from src.engine.insights.backend import generate_text, validate_backend
from src.strategy.composition.config import config, fail
from src.strategy.composition.validation import digest

TOOL = re.compile(r"<tool_use>(.*?)</tool_use>", re.DOTALL | re.IGNORECASE)


def validate_decision(
    text: str, candidates: list[str], holdings: list[str], evidence: dict[str, Any]
) -> dict[str, Any]:
    result = repair_loads(text)
    if (
        not isinstance(result, dict)
        or not isinstance(result.get("summary"), str)
        or not isinstance(result.get("decisions"), list)
    ):
        raise fail("invalid_agent")
    seen = set()
    for decision in result["decisions"]:
        if not isinstance(decision, dict):
            raise fail("invalid_agent")
        symbol = decision.get("symbol")
        action = decision.get("action")
        ids = decision.get("evidence_ids")
        if not isinstance(symbol, str) or symbol in seen or symbol not in set(candidates) | set(holdings):
            raise fail("invalid_agent", symbol)
        if (
            action not in {"select", "watch", "reject", "exit"}
            or not isinstance(decision.get("reason"), str)
            or not decision["reason"].strip()
        ):
            raise fail("invalid_agent", symbol)
        if action == "select" and symbol not in candidates or action == "exit" and symbol not in holdings:
            raise fail("invalid_agent", symbol)
        if not isinstance(ids, list) or not ids or any(not isinstance(key, str) or key not in evidence for key in ids):
            raise fail("invalid_agent", symbol)
        seen.add(symbol)
    if not set(candidates) <= seen:
        raise fail("invalid_agent", "missing decisions")
    return {
        "summary": result["summary"],
        "decisions": [
            {key: row[key] for key in ("symbol", "action", "reason", "evidence_ids")} for row in result["decisions"]
        ],
    }


class DecisionTeam:
    def __init__(self, payload: dict[str, Any], emit: Callable, generator: Callable = generate_text):
        self.payload = payload
        self.emit = emit
        self.generate = generator
        self.cfg = config()

    def decide(
        self, as_of: str, candidates: list[str], holdings: list[str], evidence: dict[str, Any], workflow: str
    ) -> dict[str, Any]:
        defaults = self.cfg["defaults"]["agent"]
        adapter = {
            "defaults": defaults,
            "messages": self.cfg["messages"],
            "prompts": {"system": self.cfg["prompts"]["system"]},
        }
        payload = {**self.payload, "backend": self.payload.get("backend") or defaults["backend"]}
        model = validate_backend(payload, adapter)
        if len(candidates) > defaults["max_candidates"] or workflow not in self.cfg["prompts"]["roles"]:
            raise fail("invalid_agent", "budget/workflow")
        peers: dict[str, Any] = {}
        final = {}
        for role in self.cfg["prompts"]["roles"][workflow]:
            prompt = self.cfg["prompts"]["request"].format(
                system=self.cfg["prompts"]["system"],
                role=role,
                as_of=as_of,
                symbols=json.dumps({"candidates": candidates, "holdings": holdings}, ensure_ascii=False),
                evidence=json.dumps(evidence, ensure_ascii=False),
                peers=json.dumps(peers, ensure_ascii=False),
            )
            for turn in range(defaults["max_turns"]):
                if len(prompt) > defaults["max_prompt_chars"]:
                    raise fail("invalid_agent", "prompt budget")
                self.emit("agent_role", role, {"turn": turn + 1, "status": "started", "model": model})
                text = self.generate(prompt, payload, adapter, self.emit)
                tools = TOOL.findall(text)
                if not tools:
                    try:
                        final = validate_decision(text, candidates, holdings, evidence)
                        break
                    except ValueError as exc:
                        self.emit("agent_validation", str(exc), {"turn": turn + 1})
                        prompt += "\n" + self.cfg["prompts"].get("retry", "") + "\n" + text
                        continue
                observations = []
                for raw in tools:
                    call = repair_loads(raw)
                    args = call.get("arguments", {}) if isinstance(call, dict) else {}
                    key = args.get("id") if isinstance(args, dict) else None
                    if (
                        not isinstance(call, dict)
                        or call.get("name") != "read_evidence"
                        or not isinstance(key, str)
                        or key not in evidence
                    ):
                        raise fail("unsupported_tool")
                    result = {"id": key, "result": evidence[key]}
                    observations.append(result)
                    self.emit("agent_tool", "read_evidence", result)
                prompt += "\n" + self.cfg["prompts"]["observation"].format(
                    observation=json.dumps(observations, ensure_ascii=False)
                )
            else:
                raise fail("invalid_agent", "turn budget")
            peers[role] = final
            self.emit("agent_role", role, {"status": "completed", "result": final})
        now = datetime.now(UTC)
        return {
            **final,
            "as_of": as_of,
            "generated_at": utc_now_iso(),
            "valid_until": (now + timedelta(days=defaults["validity_days"])).isoformat(),
            "model": model,
            "roles": peers,
            "evidence": evidence,
            "input_digest": digest(
                {"as_of": as_of, "candidates": candidates, "holdings": holdings, "evidence": evidence}
            ),
        }
