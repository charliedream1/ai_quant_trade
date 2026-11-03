"""Chronological batch simulation shared by backtests and persisted paper accounts."""

from copy import deepcopy
from datetime import date, timedelta
from typing import Any

from src.agent_strategies.config import settings as agent_strategy_settings
from src.agent_strategies.metrics import research_metrics
from src.agent_strategies.ports import CallBudget
from src.engine.execution.ledger import cost_summary
from src.engine.execution.policy import capability_gaps
from src.engine.execution.runtime import prepare_execution
from src.strategy.composition.config import config, fail
from src.strategy.composition.contracts import Frame

from .book import PortfolioBook
from .execution import execute_targets
from .metrics import performance
from .tree import AllocationTree, aggregate, clipped


class CompositionSimulation:
    def __init__(
        self,
        plan: dict[str, Any],
        snapshot: dict[str, Any],
        request: dict[str, Any],
        store,
        emit,
        state: dict[str, Any] | None = None,
        cancelled=None,
    ):
        plan = prepare_execution(plan, request)
        limit = request.get("agent_strategy_options", {}).get("calls", agent_strategy_settings()["defaults"]["calls"])
        request = {**request, "_agent_strategy_budget": CallBudget(limit)}
        self.plan, self.snapshot, self.request, self.emit = plan, snapshot, request, emit
        selected_history = {
            s: [row for row in rows if request.get("start_date", "") <= row["date"] <= request["end_date"]]
            for s, rows in snapshot["history"].items()
        }
        self.execution_gaps = capability_gaps(selected_history, plan["execution"]["_cost_policy"])
        self.cancelled = cancelled
        self.state = state or {}
        self.tree = AllocationTree(plan, store, request, emit, state, cancelled=cancelled)
        self.book = PortfolioBook(
            plan["execution"]["initial_capital"], self.tree.leaves(), self.state.get("book"), self.tree.groups()
        )
        self.pending = deepcopy(self.state.get("pending") or {})
        self.pending_due = bool(self.state.get("pending_due", False))
        self.pending_valid_until = self.state.get("pending_valid_until", "")
        self.curve = deepcopy(
            self.state.get("curve")
            or {key: [] for key in ("dates", "equity", "benchmark", "drawdown", "cash", "exposure", "position_count")}
        )
        self.orders = deepcopy(self.state.get("orders") or [])
        self.trades = deepcopy(self.state.get("trades") or [])
        self.transfers = deepcopy(self.state.get("transfers") or [])
        self.sleeve_curves = deepcopy(self.state.get("sleeve_curves") or {})
        self.decision_errors: list[dict[str, Any]] = []
        self.final_targets: dict[str, float] = {}
        self.initial_prices = deepcopy(self.state.get("initial_prices") or {})
        self.days = sorted(
            {row["date"] for rows in snapshot["history"].values() for row in rows if row["date"] <= request["end_date"]}
        )
        self.rows = {s: {row["date"]: row for row in rows} for s, rows in snapshot["history"].items()}

    def frame(self, day: str) -> Frame:
        return Frame.create(day, self.snapshot["history"], self.snapshot.get("metadata"), self.book.snapshot())

    def _held_targets(self) -> dict[str, dict[str, float]]:
        nav = self.book.nav()
        return (
            {
                key: {s: sleeve.quantity(s) * self.book.prices[s] / nav for s in sleeve.state["lots"]}
                for key, sleeve in self.book.sleeves.items()
            }
            if nav > 0
            else {}
        )

    def _preopen_risk(
        self, targets: dict[str, dict[str, float]], frame: Frame, commit: bool = False
    ) -> tuple[dict[str, dict[str, float]], set[str]]:
        emergency = set()

        def check(tree, scoped, fraction):
            local = {key: {s: w / max(fraction, 1e-9) for s, w in values.items()} for key, values in scoped.items()}
            local = tree.apply_risk(local, frame, self.book, commit)
            latest = tree.diagnostics[-1]["risk"]
            emergency.update(latest["emergency"])
            result = {key: {s: w * fraction for s, w in values.items()} for key, values in local.items()}
            for sleeve, child in zip(tree.plan["sleeves"], tree.children, strict=True):
                child_values = {key: values for key, values in result.items() if key in child.leaves()}
                child_fraction = sum(child.view(self.book).snapshot()["weights"].values())
                # The intended capital fraction, rather than current invested exposure, defines local caps.
                child_fraction = fraction * tree.last_budget[sleeve["id"]]
                result.update(check(child, child_values, child_fraction))
            allowed, _ = tree.risk.evaluate(
                aggregate(
                    {key: {s: w / max(fraction, 1e-9) for s, w in values.items()} for key, values in result.items()}
                ),
                frame,
                tree.view(self.book),
                commit=False,
            )
            return clipped(result, {s: w * fraction for s, w in allowed.items()})

        return check(self.tree, targets, 1.0), emergency

    def step(self, day: str, decide: bool = True, record: bool = True) -> None:
        if self.cancelled and self.cancelled():
            raise fail("cancelled")
        previous = [value for value in self.days if value < day]
        prior = previous[-1] if previous else day
        prior_frame = self.frame(prior)
        old_day = self.book.last_day
        self.book.advance(day)
        if old_day:
            self.book.session += max(0, len([value for value in self.days if old_day < value <= day]) - 1)
        opens = {s: values[day] for s, values in self.rows.items() if day in values}
        self.book.prices.update({s: float(row["open"]) for s, row in opens.items()})
        prior_frame = Frame(prior_frame.as_of, prior_frame.history, prior_frame.metadata, self.book.snapshot())
        if self.request["mode"] == "paper" and self.pending_valid_until and day > self.pending_valid_until:
            self.pending_due = False
        targets = self.pending if self.pending_due else self._held_targets()
        targets, emergency = self._preopen_risk(targets, prior_frame)
        fills = execute_targets(
            self.book,
            targets,
            self.tree.budgets(),
            opens,
            prior_frame,
            self.plan["execution"],
            emergency,
            self.plan["risk"],
        )
        self.orders.extend(fills["orders"])
        self.trades.extend(fills["trades"])
        self.transfers.extend(fills["internal_transfers"])
        if fills["orders"] or fills["capital_flows"]:
            self.emit("execution", day, fills)
        self.book.prices.update({s: float(row["close"]) for s, row in opens.items()})
        current = self.frame(day)
        if decide:
            try:
                self.pending = self.tree.decide(current, self.book)
                self.pending_due = self.tree.due(self.book.session)
                self.pending_valid_until = (
                    date.fromisoformat(max(day, self.request["end_date"]))
                    + timedelta(days=config()["defaults"]["agent"]["validity_days"])
                ).isoformat()
            except Exception as exc:
                # Risk still evaluates and paper state is persisted even when research fails.
                self.decision_errors.append({"as_of": day, "error": str(exc)})
                self.emit("decision_error", day, {"error": str(exc)})
                self.pending = self.tree.risk_existing(current, self.book)
                self.pending_due = False
        else:
            self.pending, _ = self._preopen_risk(
                self.pending if self.pending_due else self._held_targets(), current, commit=True
            )
        self.final_targets = aggregate(self.pending)
        unit_values = self.book.finish()
        if record:
            snapshot = self.book.snapshot()
            nav = snapshot["nav"]
            peak = max([self.book.capital, *self.curve["equity"], nav])
            for symbol, row in opens.items():
                self.initial_prices.setdefault(symbol, float(row["close"]))
            benchmark = (
                self.book.capital
                * sum(
                    self.book.prices[s] / self.initial_prices[s] if s in self.initial_prices else 1.0 for s in self.rows
                )
                / len(self.rows)
            )
            values = {
                "dates": day,
                "equity": nav,
                "benchmark": benchmark,
                "drawdown": nav / peak - 1,
                "cash": snapshot["cash"],
                "exposure": 1 - snapshot["cash"] / nav if nav > 0 else 0.0,
                "position_count": len(snapshot["positions"]),
            }
            for key, value in values.items():
                self.curve[key].append(value)
            for key, value in unit_values.items():
                self.sleeve_curves.setdefault(key, []).append(value)
        self.emit(
            "session",
            day,
            {
                "nav": self.book.nav(),
                "positions": self.book.positions(),
                "cash": self.book.cash(),
                "pending_targets": self.final_targets,
            },
        )

    def run(self) -> dict[str, Any]:
        mode = self.request["mode"]
        if mode == "paper" and self.pending_valid_until and self.request["end_date"] > self.pending_valid_until:
            self.pending_due = False
        if not self.days:
            raise fail("no_history")
        if mode in {"screen", "targets"}:
            day = self.days[-1]
            self.book.prices.update(
                {s: float(values[day]["close"]) for s, values in self.rows.items() if day in values}
            )
            self.book.advance(day)
            self.pending = self.tree.decide(self.frame(day), self.book)
            self.final_targets = aggregate(self.pending)
            self.pending_due = True
        elif mode == "paper":
            day = self.days[-1]
            if self.book.last_day == day:
                if self.request.get("risk_only"):
                    self.book.prices.update(
                        {s: float(values[day]["close"]) for s, values in self.rows.items() if day in values}
                    )
                    self.pending, _ = self._preopen_risk(
                        self.pending if self.pending_due else self._held_targets(), self.frame(day), commit=True
                    )
                    self.final_targets = aggregate(self.pending)
                elif self.request.get("refresh_decision"):
                    self.pending = self.tree.decide(self.frame(day), self.book)
                    self.final_targets = aggregate(self.pending)
                    self.pending_due = True
                    self.pending_valid_until = (
                        date.fromisoformat(self.request["end_date"])
                        + timedelta(days=config()["defaults"]["agent"]["validity_days"])
                    ).isoformat()
            else:
                self.step(day, decide=not self.request.get("risk_only", False))
        else:
            selected = [day for day in self.days if self.request["start_date"] <= day <= self.request["end_date"]]
            if not selected:
                raise fail("no_history")
            for day in selected:
                self.step(day)
                if self.decision_errors:
                    break
        return self.result()

    def result(self) -> dict[str, Any]:
        metrics = performance(self.curve, self.orders, self.trades, self.book.capital) if self.curve["dates"] else {}
        metrics.update(cost_summary(self.orders, self.book.capital, self.book.nav()))
        metrics.update(execution_costs=self.plan["execution"]["_cost_policy"], execution_gaps=self.execution_gaps)
        return {
            "metrics": metrics,
            "curve": self.curve,
            "trades": self.trades,
            "orders": self.orders,
            "internal_transfers": self.transfers,
            "targets": self.final_targets,
            "account": self.book.snapshot(),
            "sleeve_curves": self.sleeve_curves,
            "diagnostics": self.tree.report(),
            "agent_research_metrics": research_metrics(
                self.tree.runtime.research_history, self.snapshot["history"], self.request["end_date"]
            ),
            "agent_validation_mode": self.request.get("agent_mode", "off"),
            "agent_model_budget": {
                "used": self.request["_agent_strategy_budget"].used,
                "limit": self.request["_agent_strategy_budget"].limit,
            },
            "decision_errors": self.decision_errors,
            "source": self.snapshot["source"],
            "is_mock": self.snapshot["is_mock"],
            "limitations": self.snapshot.get("limitations", []),
            "ledger": self.serialize(),
        }

    def serialize(self) -> dict[str, Any]:
        return {
            **self.tree.state(),
            "book": self.book.serialize(),
            "pending": self.pending,
            "pending_due": self.pending_due,
            "pending_valid_until": self.pending_valid_until,
            "curve": self.curve,
            "orders": self.orders,
            "trades": self.trades,
            "transfers": self.transfers,
            "sleeve_curves": self.sleeve_curves,
            "initial_prices": self.initial_prices,
        }
