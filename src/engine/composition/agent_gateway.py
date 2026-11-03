"""Persist actual decisions and require exact dated evidence on replay."""

import json
from dataclasses import asdict
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from src.agent.decision_team import DecisionTeam, validate_decision
from src.agent_strategies.graph import stage as strategy_stage
from src.agent_strategies.ports import COMPONENTS as AGENT_STRATEGY_COMPONENTS
from src.strategy.composition.config import config, fail
from src.strategy.composition.contracts import Frame
from src.strategy.composition.store import PipelineStore
from src.strategy.composition.validation import digest


class AgentGateway:
    def __init__(self, request: dict[str, Any], store: PipelineStore, emit, namespace: str):
        self.request, self.store, self.emit, self.namespace = request, store, emit, namespace
        self.research_request = {
            **request,
            "_agent_strategy_scope": str(
                request.get("resolved_digest")
                or (store.version(request["version_id"])["digest"] if request.get("version_id") else "unpublished")
            )
            + ":"
            + namespace,
        }
        self.decisions: list[dict[str, Any]] = []

    def __call__(self, node: dict[str, Any], frame: Frame, observations: dict):
        candidates = sorted(observations)
        holdings = sorted(frame.account.get("positions") or {})
        evidence = {
            "E1": {"scores": [asdict(observations[s]) for s in candidates]},
            "E2": {
                "as_of": frame.as_of,
                "history_digest": digest(frame.mutable_history()),
                "observations": {s: len(frame.history.get(s, ())) for s in candidates},
                "history": {
                    s: [
                        dict(row) for row in frame.history.get(s, ())[-config()["defaults"]["agent"]["evidence_bars"] :]
                    ]
                    for s in set(candidates) | set(holdings)
                },
            },
            "E3": {"account": frame.account, "metadata": {s: dict(frame.metadata.get(s, {})) for s in candidates}},
        }
        fingerprint = digest(
            {"as_of": frame.as_of, "candidates": candidates, "holdings": holdings, "evidence": evidence}
        )
        directory = self.store.root / "decisions"
        directory.mkdir(exist_ok=True)
        if self.request.get("agent_mode") == "replay":
            matches = []
            for key in self.request.get("agent_replay") or []:
                try:
                    canonical = UUID(key).hex
                except (ValueError, TypeError) as exc:
                    raise fail("no_replay") from exc
                path = directory / (canonical + ".json")
                if path.is_file():
                    value = json.loads(path.read_text(encoding="utf-8"))
                    if (
                        value.get("input_digest") == fingerprint
                        and value.get("node") == self.namespace + ":" + node["id"]
                    ):
                        matches.append(value)
            if len(matches) != 1:
                raise fail("no_replay", frame.as_of)
            decision = matches[0]
            archived = decision.get("model") or {}
            for requested, recorded in (
                ("backend", "backend"),
                ("model_id", "model_id"),
                ("model_name", "model_name"),
                ("reasoning_effort", "reasoning_effort"),
            ):
                if (
                    self.request.get(requested)
                    and archived.get(recorded)
                    and self.request[requested] != archived[recorded]
                ):
                    raise fail("no_replay", "请求的后端身份与归档决定不一致：" + requested)
            generated = datetime.fromisoformat(decision["generated_at"].replace("Z", "+00:00"))
            cutoff = datetime.fromisoformat(frame.as_of + "T23:59:59+00:00")
            if generated > cutoff or datetime.fromisoformat(decision["valid_until"]) < cutoff:
                raise fail("lookahead")
            validate_decision(json.dumps(decision), candidates, holdings, evidence)
            self.emit("agent_replay", node["id"], {"decision_id": decision["id"], "input_digest": fingerprint})
        else:

            def scoped_emit(kind, text, data=None):
                self.emit(
                    kind,
                    text,
                    {**(data if isinstance(data, dict) else {}), "node": node["id"], "scope": self.namespace},
                )

            if node.get("component") in AGENT_STRATEGY_COMPONENTS:
                decision = strategy_stage(node, frame, observations, self.research_request, scoped_emit)
                decision["input_digest"] = fingerprint
            else:
                decision = DecisionTeam(self.request, scoped_emit).decide(
                    frame.as_of, candidates, holdings, evidence, node["params"]["workflow"]
                )
            decision.update(id=uuid4().hex, node=self.namespace + ":" + node["id"])
            if decision["input_digest"] != fingerprint:
                raise fail("invalid_agent", "fingerprint")
            (directory / (decision["id"] + ".json")).write_text(
                json.dumps(decision, ensure_ascii=False, allow_nan=False), encoding="utf-8"
            )
        self.decisions.append(decision)
        return decision
