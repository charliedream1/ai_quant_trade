"""Run independent graph branches against one dated snapshot, never against accounts."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, replace
from time import perf_counter
from typing import Any

from src.agent_strategies.ports import COMPONENTS as AGENT_STRATEGY_COMPONENTS
from src.agent_strategies.ports import ShadowPermit
from src.alpha_mining.components import AlphaRuntime
from src.strategy.components.ensemble import combine
from src.strategy.components.models import ScoreModel
from src.strategy.components.rules import evaluate
from src.strategy.factors.runtime import FactorRuntime
from src.strategy.factors.validation import FACTOR_COMPONENTS

from .config import config, fail
from .contracts import Frame, Observation
from .validation import digest


class PipelineRuntime:
    def __init__(
        self,
        plan: dict[str, Any],
        emit,
        decide=None,
        cancelled=None,
        artifacts=None,
        research_permit=None,
        agent_permit=None,
    ):
        self.plan, self.emit, self.decide, self.cancelled = plan, emit, decide, cancelled
        self.models: dict[str, ScoreModel] = {}
        self.trace: list[dict[str, Any]] = []
        self.agent_exits: set[str] = set()
        self.artifacts = artifacts
        self.factors = FactorRuntime(persistent=artifacts is not None)
        self.alpha = AlphaRuntime(research_permit)
        self.agent_permit = agent_permit
        self.research_history: list[dict] = []

    def evaluate(self, frame: Frame) -> dict[str, Observation]:
        cfg = config()
        self.trace = []
        root = {symbol: Observation(symbol, cfg["defaults"]["rank_single"]) for symbol in frame.active()}
        outputs = {"universe": root}
        pending = list(self.plan["nodes"])
        self.agent_exits = set()
        with ThreadPoolExecutor(max_workers=cfg["defaults"]["max_workers"]) as executor:
            while pending:
                if self.cancelled and self.cancelled():
                    raise fail("cancelled")
                ready = [node for node in pending if all(parent in outputs for parent in node["inputs"])]
                futures = {
                    node["id"]: executor.submit(self._node, node, [outputs[parent] for parent in node["inputs"]], frame)
                    for node in ready
                }
                for node in ready:
                    try:
                        outputs[node["id"]] = futures[node["id"]].result()
                    except Exception as exc:
                        self.emit(
                            "stage",
                            node["id"],
                            {
                                "node": node["id"],
                                "component": node["component"],
                                "as_of": frame.as_of,
                                "status": "failed",
                                "error": str(exc),
                            },
                        )
                        raise
                    pending.remove(node)
        return outputs[self.plan["output"]]

    def _node(
        self, node: dict[str, Any], parents: list[dict[str, Observation]], frame: Frame
    ) -> dict[str, Observation]:
        started = perf_counter()
        symbols = sorted({s for branch in parents for s, row in branch.items() if row.status == "pass"})
        component = node["component"]
        self.emit(
            "stage",
            node["id"],
            {"status": "started", "as_of": frame.as_of, "component": component, "inputs": len(symbols)},
        )
        if component == "agent_shadow":
            if not isinstance(self.agent_permit, ShadowPermit):
                raise ValueError("影子目标只能通过内部有类型的凭据执行")
            result = {
                s: Observation(s, float(self.agent_permit.weights.get(s, 0)), semantics="target_weight")
                for s in symbols
            }
        elif component in AGENT_STRATEGY_COMPONENTS:
            result = self._research_node(node, parents[0], frame, symbols)
        elif component in {"alpha_factor", "alpha_theme", "alpha_regime"}:
            result = self.alpha.evaluate(node, symbols, frame)
        elif component in FACTOR_COMPONENTS:
            result = self.factors.evaluate(node, symbols, frame)
        elif node["kind"] == "ensemble":
            result = combine(component, parents, node["params"])
        elif component in config()["defaults"]["model_profiles"]:
            model = self.models.setdefault(
                node["id"], ScoreModel(component, node["params"], self.artifacts, node.get("factor_contract"))
            )

            def model_emit(kind, text, data=None):
                self.emit(kind, text, {**(data or {}), "node": node["id"]})

            result = model.predict(symbols, frame, model_emit) if symbols else {}
        elif component == "agent":
            if self.decide is None:
                self.emit("agent_mode", "off", {"reason": "explicit_quantitative_baseline"})
                result = dict(parents[0])
            elif not symbols:
                result = {}
            else:
                ranked = sorted(symbols, key=lambda s: (-float(parents[0][s].value or 0), s))
                limited = ranked[: config()["defaults"]["agent"]["max_candidates"]]
                decision = self.decide(node, frame, {s: parents[0][s] for s in limited})
                mapping = {row["symbol"]: row for row in decision["decisions"]}
                self.agent_exits.update(s for s, row in mapping.items() if row["action"] == "exit")
                result = {
                    s: replace(
                        row,
                        status="pass" if s in mapping and mapping[s]["action"] == "select" else "reject",
                        reason="agent_" + mapping.get(s, {"action": "budget"})["action"],
                        evidence={**row.evidence, "agent": mapping.get(s)},
                    )
                    for s, row in parents[0].items()
                }
        else:
            result = evaluate(component, symbols, frame, node["params"])
        if component != "agent":
            result = {
                s: replace(
                    row,
                    family=node["family"],
                    evidence={**row.evidence, "reference_universe": digest(symbols), "component_kind": node["kind"]},
                )
                for s, row in result.items()
            }
        event = {
            "as_of": frame.as_of,
            "node": node["id"],
            "component": component,
            "input_count": len(symbols),
            "passed": sum(row.status == "pass" for row in result.values()),
            "rejected": sum(row.status == "reject" for row in result.values()),
            "unknown": sum(row.status == "unknown" for row in result.values()),
            "observations": [asdict(row) for row in result.values()],
            "duration_ms": round((perf_counter() - started) * 1000, 2),
        }
        if component in FACTOR_COMPONENTS:
            detail = self.factors.diagnostics.get(node["id"], {})
            event["factor_research"] = {
                **{key: value for key, value in detail.items() if key != "research"},
                "research": {key: value for key, value in detail.get("research", {}).items() if key != "history"},
            }
        self.trace.append(event)
        self.emit("stage", node["id"], {"status": "completed", **event})
        return result

    def diagnostics(self) -> dict[str, Any]:
        return {node: model.diagnostics for node, model in self.models.items()}

    def _research_node(self, node, incoming, frame, symbols):
        if not self.decide:
            self.emit("agent_mode", "off", {"reason": "quantitative_baseline_only", "node": node["id"]})
            return {
                s: replace(
                    row,
                    value=1 / len(symbols) if node["component"] == "contest_research" and s in symbols else row.value,
                    semantics="target_weight" if node["component"] == "contest_research" else row.semantics,
                    evidence={**row.evidence, "agent_strategy_baseline_only": True},
                )
                for s, row in incoming.items()
            }
        if not symbols:
            return {}
        ranked = sorted(symbols, key=lambda s: (-float(incoming[s].value or 0), s))[
            : config()["defaults"]["agent"]["max_candidates"]
        ]
        decision = self.decide(node, frame, {s: incoming[s] for s in ranked})
        mapping = {row["symbol"]: row for row in decision["decisions"]}
        if node["component"] == "cn_debate":
            self.research_history.extend(
                {"node": node["id"], "date": frame.as_of, "symbol": s, "score": row["score"], "horizon": row["horizon"]}
                for s, row in mapping.items()
                if s in symbols
            )
        self.agent_exits.update(s for s, row in mapping.items() if row["action"] == "exit")
        return {
            s: replace(
                row,
                value=mapping.get(s, {}).get("score", 0),
                status="pass" if s in mapping and mapping[s]["action"] == "select" else "reject",
                semantics="target_weight" if node["component"] == "contest_research" else "relative_strength",
                horizon=mapping.get(s, {}).get("horizon", row.horizon),
                reason="agent_strategy_" + mapping.get(s, {}).get("action", "budget"),
                evidence={**row.evidence, "agent_strategy": decision["agent_strategy"], "agent": mapping.get(s)},
            )
            for s, row in incoming.items()
        }
