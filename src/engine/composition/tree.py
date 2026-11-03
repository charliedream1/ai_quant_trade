"""Hierarchical capital budgets and actual group risk over one physical book."""

from typing import Any

from src.portfolio.allocation import allocate, strategy_budgets
from src.risk.policies import RiskManager
from src.strategy.composition.contracts import Frame
from src.strategy.composition.model_artifacts import ModelArtifacts
from src.strategy.composition.runtime import PipelineRuntime

from .agent_gateway import AgentGateway
from .book import GroupView, PortfolioBook


def aggregate(targets: dict[str, dict[str, float]]) -> dict[str, float]:
    combined: dict[str, float] = {}
    for values in targets.values():
        for symbol, value in values.items():
            combined[symbol] = combined.get(symbol, 0) + value
    return combined


def clipped(targets: dict[str, dict[str, float]], allowed: dict[str, float]) -> dict[str, dict[str, float]]:
    original = aggregate(targets)
    return {
        key: {
            s: weight * min(1.0, allowed.get(s, 0) / original[s]) if original.get(s, 0) > 0 else 0.0
            for s, weight in values.items()
        }
        for key, values in targets.items()
    }


class AllocationTree:
    def __init__(
        self,
        plan: dict[str, Any],
        store,
        request: dict[str, Any],
        emit,
        state: dict[str, Any] | None = None,
        key: str = "main",
        budget: float = 1.0,
        cancelled=None,
        capital: float | None = None,
    ):
        self.plan, self.key, self.budget, self.emit = plan, key, budget, emit
        self.universe_override = request.get("symbols") if key == "main" else None
        self.universe_limit = set(request["symbols"]) if request.get("resource_pool_id") else None
        root_capital = capital if capital is not None else plan["execution"]["initial_capital"]
        self.children = [
            AllocationTree(
                s["definition"],
                store,
                request,
                emit,
                state,
                key + "/" + s["id"],
                budget * s["budget"],
                cancelled,
                root_capital,
            )
            for s in plan["sleeves"]
        ]
        self.risk = RiskManager(plan["risk"], (state or {}).get("risk", {}).get(key))

        def scoped_emit(kind, text, data=None):
            emit(kind, text, {**(data if isinstance(data, dict) else {}), "scope": key})

        self.agent = AgentGateway(request, store, scoped_emit, key) if request.get("agent_mode") != "off" else None
        self.runtime = PipelineRuntime(
            plan,
            scoped_emit,
            self.agent,
            cancelled,
            ModelArtifacts() if store else None,
            research_permit=request.get("_alpha_permit"),
            agent_permit=request.get("_agent_strategy_permit"),
        )
        self.last_budget = (state or {}).get("budgets", {}).get(key) or {s["id"]: s["budget"] for s in plan["sleeves"]}
        self.runtime.research_history = (state or {}).get("agent_score_history", {}).get(key, [])
        self.diagnostics: list[dict[str, Any]] = []
        self.initial_capital = root_capital * budget

    def leaves(self) -> dict[str, float]:
        if not self.children:
            return {self.key: self.budget}
        result = {key: value for child in self.children for key, value in child.leaves().items()}
        residual = max(0.0, self.budget - sum(result.values()))
        if residual:
            result[self.key + "/cash"] = residual
        return result

    def groups(self) -> dict[str, list[str]]:
        result = {self.key: list(self.leaves())}
        for child in self.children:
            result.update(child.groups())
        return result

    def view(self, book: PortfolioBook) -> GroupView:
        return GroupView(book, self.key, self.initial_capital)

    def decide(self, frame: Frame, book: PortfolioBook) -> dict[str, dict[str, float]]:
        view = self.view(book)
        local = Frame(frame.as_of, frame.history, frame.metadata, view.snapshot())
        due = book.session % self.plan.get("rebalance_sessions", 1) == 0
        if self.children:
            if due and self.plan["portfolio"]["component"] == "strategy_risk_budget":
                histories = {
                    s["id"]: book.groups[child.key]["unit_history"]
                    for s, child in zip(self.plan["sleeves"], self.children, strict=True)
                }
                self.last_budget, diagnostic = strategy_budgets(
                    self.plan["sleeves"],
                    histories,
                    self.plan["portfolio"]["params"],
                    self.plan.get("budget_fallback", "none"),
                )
                self.diagnostics.append({"as_of": frame.as_of, **diagnostic})
            targets = {}
            for sleeve, child in zip(self.plan["sleeves"], self.children, strict=True):
                child_targets = child.decide(frame, book)
                fraction = self.last_budget[sleeve["id"]] if due else child.view(book).nav() / max(view.nav(), 1e-9)
                targets.update(
                    {key: {s: w * fraction for s, w in values.items()} for key, values in child_targets.items()}
                )
            if self.key + "/cash" in book.sleeves:
                targets[self.key + "/cash"] = {}
        elif due:
            names = set(self.universe_override or self.plan["universe"]["symbols"])
            if self.universe_limit is not None:
                names &= self.universe_limit
            histories = {s: rows for s, rows in local.history.items() if s in names}
            filtered = Frame(local.as_of, histories, local.metadata, local.account)
            observations = self.runtime.evaluate(filtered)
            if observations and all(row.status == "unknown" for row in observations.values()):
                weights = view.snapshot()["weights"]
                diagnostic = {"status": "unavailable_hold_existing"}
            else:
                weights, diagnostic = allocate(
                    self.plan["portfolio"]["component"], observations, filtered, self.plan["portfolio"]["params"]
                )
            for symbol in self.runtime.agent_exits:
                weights[symbol] = 0.0
            targets = {self.key: weights}
            self.diagnostics.append({"as_of": frame.as_of, "portfolio": diagnostic})
        else:
            targets = {self.key: view.snapshot()["weights"]}
        return self.apply_risk(targets, local, book, True)

    def apply_risk(
        self, targets: dict[str, dict[str, float]], frame: Frame, book: PortfolioBook, commit: bool
    ) -> dict[str, dict[str, float]]:
        allowed, diagnostic = self.risk.evaluate(aggregate(targets), frame, self.view(book), commit=commit)
        self.diagnostics.append({"as_of": frame.as_of, "phase": "close" if commit else "open", "risk": diagnostic})
        self.emit("risk", self.key, {"as_of": frame.as_of, "phase": "close" if commit else "open", **diagnostic})
        return clipped(targets, allowed)

    def budgets(self, fraction: float = 1.0) -> dict[str, float]:
        if not self.children:
            return {self.key: fraction}
        result = {}
        for sleeve, child in zip(self.plan["sleeves"], self.children, strict=True):
            result.update(child.budgets(fraction * self.last_budget[sleeve["id"]]))
        residual = fraction - sum(result.values())
        if residual > 0:
            result[self.key + "/cash"] = residual
        return result

    def due(self, session: int) -> bool:
        return session % self.plan.get("rebalance_sessions", 1) == 0 or any(
            child.due(session) for child in self.children
        )

    def risk_existing(self, frame: Frame, book: PortfolioBook) -> dict[str, dict[str, float]]:
        view = self.view(book)
        if self.children:
            targets = {}
            for child in self.children:
                fraction = child.view(book).nav() / max(view.nav(), 1e-9)
                targets.update(
                    {
                        key: {s: w * fraction for s, w in values.items()}
                        for key, values in child.risk_existing(frame, book).items()
                    }
                )
            if self.key + "/cash" in book.sleeves:
                targets[self.key + "/cash"] = {}
        else:
            targets = {self.key: view.snapshot()["weights"]}
        return self.apply_risk(targets, frame, book, True)

    def state(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "risk": {self.key: self.risk.state},
            "budgets": {self.key: self.last_budget},
            "agent_score_history": {self.key: self.runtime.research_history},
        }
        for child in self.children:
            value = child.state()
            result["risk"].update(value["risk"])
            result["budgets"].update(value["budgets"])
            result["agent_score_history"].update(value["agent_score_history"])
        return result

    def report(self) -> dict[str, Any]:
        return {
            "name": self.plan["name"],
            "model_diagnostics": self.runtime.diagnostics(),
            "factor_diagnostics": self.runtime.factors.diagnostics,
            "stages": self.runtime.trace,
            "research_scores": self.runtime.research_history,
            "decisions": self.agent.decisions if self.agent else [],
            "allocations": self.diagnostics,
            "children": {child.key: child.report() for child in self.children},
        }
