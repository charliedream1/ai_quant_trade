"""Real domain execution with explicit model doubles and independently checked boundaries."""

from copy import deepcopy
from datetime import date, timedelta

import pytest

from src.agent_strategies.config import freeze
from src.agent_strategies.contest import select_information
from src.agent_strategies.contracts import decisions, observations
from src.agent_strategies.evidence import assemble, market_view
from src.agent_strategies.scores import mature
from src.agent_strategies.service import AgentStrategyService
from src.alpha_mining.service import AlphaService
from src.strategy.composition.config import template
from src.strategy.composition.contracts import Frame
from src.strategy.composition.validation import compile_plan


def request(data, recipe="cn_event", as_of=None):
    return {
        "recipe": recipe,
        "market_dataset_id": data["market_id"],
        "documents_dataset_id": data["documents_id"],
        "as_of": as_of or data["days"][-1],
        "validation_mode": "historical_research",
        "backend": "api",
        "model_id": 1,
        "execution_costs": {"profile": "cn_a"},
    }


@pytest.mark.parametrize(
    "recipe", ["cn_balanced", "cn_quality", "cn_event", "contest_event", "contest_quality", "contest_sector"]
)
def test_six_recipes_compile_and_run_actual_phases(workflow_data, frame, fixture_llm, recipe):
    plan = compile_plan(template("agent_" + recipe))
    assert plan["nodes"][-1]["component"] in {"cn_debate", "contest_research"}
    service = AgentStrategyService(llm=fixture_llm)
    run = service.prepare(request(workflow_data, recipe), frame)
    service.phase(run["id"], False, frame)
    result = service.phase(run["id"], True, frame)
    assert result["status"] == "completed", result["result"]
    assert service.store.artifact(run["id"], "report.html").is_file()
    assert result["result"]["decision"]["decisions"]
    if recipe.startswith("contest"):
        assert result["result"]["cold_start"] and result["result"]["cash"] == 1
        assert not result["result"]["targets"]
        assert all(value == 0 for value in result["result"]["budgets"].values())
    else:
        assert "bull:0" in result["result"]["roles"] and "bear:0" in result["result"]["roles"]
        assert any(row["action"] == "select" for row in result["result"]["decision"]["decisions"])


def test_required_missing_evidence_cannot_allocate(workflow_data, frame, fixture_llm):
    service = AgentStrategyService(llm=fixture_llm)
    req = request(workflow_data)
    req.pop("documents_dataset_id")
    run = service.prepare(req, frame)
    service.phase(run["id"], False, frame)
    done = service.phase(run["id"], True, frame)
    assert done["status"] == "partial" and done["evidence"]["missing"] == ["news"]
    assert all(row["action"] != "select" for row in done["result"]["decision"]["decisions"])


def test_global_actual_request_budget_and_stage_reentry(workflow_data, frame, fixture_llm):
    service = AgentStrategyService(llm=fixture_llm)
    run = service.prepare({**request(workflow_data), "options": {"calls": 1}}, frame)
    with pytest.raises(ValueError, match="调用预算"):
        service.phase(run["id"], False, frame)
    assert len(fixture_llm.calls) == 1
    assert service.store.get(run["id"])["status"] == "failed"
    with pytest.raises(ValueError, match="重复"):
        service.phase(run["id"], False, frame)


def test_observation_requires_exact_quote_and_company(frame, workflow_data):
    context = assemble(frame, frame.active(), freeze("contest_event"), workflow_data["documents_id"])
    key, document = next(iter(context["documents"].items()))
    row = {
        "symbol": document["symbols"][0],
        "direction": 1,
        "horizon": 5,
        "text": "explicit-test",
        "source_id": key,
        "quote": "invented quote",
    }
    value = {"observations": [row], "read_ids": ["market", "documents", *context["documents"]]}
    with pytest.raises(ValueError, match="准确原文"):
        observations(value, {"market": context["market"], "documents": context["documents"]}, "events")
    row["quote"] = document["text"]
    assert observations(value, {"market": context["market"], "documents": context["documents"]}, "events")
    row.update(quote="", quote_id="q0")
    resolved = observations(value, {"market": context["market"], "documents": context["documents"]}, "events")
    assert resolved[0]["quote"] in document["text"] and resolved[0]["quote_resolution"] == "source_fragment_id"
    row["symbol"] = next(symbol for symbol in frame.active() if symbol not in document["symbols"])
    with pytest.raises(ValueError, match="证券关联"):
        observations(value, {"market": context["market"], "documents": context["documents"]}, "events")


def test_nested_factor_ids_are_valid_only_after_actual_group_read(frame):
    context = {
        "market": {"candidates": ["AAA"], "holdings": [], "horizon": 5},
        "factors": [{"id": "context:0", "text": "explicit verified observation"}],
    }
    value = {
        "summary": "test",
        "read_ids": ["market", "factors", "context:0"],
        "decisions": [
            {
                "symbol": "AAA",
                "action": "watch",
                "score": 0.5,
                "horizon": 5,
                "reason": "test",
                "evidence_ids": ["context:0"],
            }
        ],
    }
    assert decisions(value, context)
    value["read_ids"].remove("context:0")
    with pytest.raises(ValueError, match="未实际读取"):
        decisions(value, context)


def test_future_cutoff_and_per_security_coverage(workflow_data, frame):
    future = (date.today() + timedelta(days=1)).isoformat()
    with pytest.raises(ValueError, match="未来"):
        assemble(Frame.create(future, workflow_data["history"]), list(workflow_data["history"]), freeze("cn_event"))
    alpha = AlphaService()
    docs = alpha.store.get("alpha_datasets", workflow_data["documents_id"])["payload"]["documents"]
    dataset = alpha.register_dataset(
        "explicit partial scope", "documents", {"documents": [row for row in docs if "AAA" in row["symbols"]]}
    )
    evidence = assemble(frame, frame.active(), freeze("cn_event"), dataset["id"])
    assert evidence["missing_by_symbol"]["AAA"] == [] and evidence["missing_by_symbol"]["BBB"] == ["news"]


def test_compact_model_context_keeps_causal_summary_and_full_archive(workflow_data, frame):
    cfg = freeze("cn_event")
    evidence = assemble(frame, frame.active(), cfg)
    compact = market_view(evidence["market"], cfg)
    assert len(compact["history"]["AAA"]) == cfg["limits"]["model_bars"]
    assert len(evidence["market"]["history"]["AAA"]) == cfg["limits"]["history_bars"]
    assert compact["history_summary"]["AAA"]["last_date"] == frame.as_of


def test_information_dedup_preserves_opposing_or_distinct_source_fragments():
    first = {
        "id": "a",
        "symbol": "AAA",
        "direction": 1,
        "source_id": "doc:one",
        "quote_id": "q0",
        "quote": "revenue improved",
        "text": "revenue improved",
        "actor": "events",
    }
    duplicate = {**first, "id": "b", "actor": "context"}
    opposing = {**first, "id": "c", "direction": -1, "text": "revenue improved"}
    distinct = {**first, "id": "d", "quote_id": "q1", "quote": "margin contracted", "text": "margin contracted"}
    result = select_information([first, duplicate, opposing, distinct], {}, freeze("contest_event"))
    assert [row["id"] for row in result["selected"]] == ["a", "c", "d"]
    assert result["dropped"] == [{"id": "b", "reason": "redundant_evidence"}]


def test_role_model_override_is_used_and_audited(workflow_data, frame, fixture_llm, monkeypatch):
    captured = []
    original = fixture_llm.complete

    def complete(*args, **kwargs):
        captured.append(kwargs)
        return original(*args, **kwargs)

    monkeypatch.setattr(fixture_llm, "complete", complete)
    service = AgentStrategyService(llm=fixture_llm)
    run = service.prepare(
        {
            **request(workflow_data),
            "options": {"role_models": {"technical": {"model_id": 2, "reasoning_effort": "low"}}},
        },
        frame,
    )
    service.phase(run["id"], False, frame)
    assert [row["model_id"] for row in captured] == [2, 2, 1, 1]
    assert all(row["reasoning_effort"] == "low" for row in captured[:2])
    requests = [row["payload"] for row in service.all_events(run["id"]) if row["kind"] == "llm_request"]
    assert requests[0]["model_id"] == 2 and requests[-1]["model_id"] == 1
    with pytest.raises(ValueError, match="字段不合法"):
        freeze("cn_event", {"role_models": {"invented_role": {"model_id": 2}}})


def test_maturity_waits_for_prices_then_uses_actual_ledger_once(workflow_data, fixture_llm):
    service = AgentStrategyService(llm=fixture_llm)
    first_day = workflow_data["days"][30]
    prior_frame = Frame.create(first_day, workflow_data["history"], workflow_data["metadata"])
    first = service.prepare(request(workflow_data, "contest_event", first_day), prior_frame)
    service.phase(first["id"], False, prior_frame)
    service.phase(first["id"], True, prior_frame)
    premature_frame = Frame.create(workflow_data["days"][34], workflow_data["history"], workflow_data["metadata"])
    current = service.prepare(request(workflow_data, "contest_event", premature_frame.as_of), premature_frame)
    assert mature(service.store, current, premature_frame) == []
    mature_frame = Frame.create(workflow_data["days"][40], workflow_data["history"], workflow_data["metadata"])
    current = service.prepare(request(workflow_data, "contest_event", mature_frame.as_of), mature_frame)
    updates = mature(service.store, current, mature_frame)
    assert {row["channel"] for row in updates} == {"data", "research"}
    assert mature(service.store, current, mature_frame) == []
    shadow = service.store.artifact(first["id"], "shadow-continuation.json").read_text(encoding="utf-8")
    assert '"orders"' in shadow and '"net_excess"' in shadow and '"baseline_metrics"' in shadow
    assert all(row["effective_at"][:10] < mature_frame.as_of for row in updates)


def test_frozen_content_and_parent_graph_connections(workflow_data, frame, fixture_llm):
    service = AgentStrategyService(llm=fixture_llm)
    run = service.prepare(request(workflow_data), frame)
    service.store.repo.db.execute("UPDATE agent_strategy_runs SET config='{}' WHERE id=?", (run["id"],))
    with pytest.raises(ValueError, match="摘要"):
        service.store.get(run["id"])
    plan = deepcopy(template("agent_contest_event"))
    plan["nodes"] = [row for row in plan["nodes"] if row["id"] != "analysis"]
    plan["nodes"][-1]["inputs"] = ["eligibility"]
    with pytest.raises(ValueError, match="证据阶段"):
        compile_plan(plan)


def test_positive_matured_utility_allocates_and_quality_cannot_rescue_negative(workflow_data, frame, fixture_llm):
    service = AgentStrategyService(llm=fixture_llm)
    cfg_request = request(workflow_data, "contest_event")
    current = service.prepare(cfg_request, frame)
    minimum = current["config"]["policy"]["min_history"]
    for index in range(minimum):
        day = workflow_data["days"][index]
        previous = service.prepare(
            {**cfg_request, "as_of": day}, Frame.create(day, workflow_data["history"], workflow_data["metadata"])
        )
        for channel, actor, direction in (
            ("research", "continuation", 1),
            ("research", "defensive", -1),
            ("data", "events", 1),
            ("data", "context", 1),
        ):
            service.store.repo.insert(
                "agent_strategy_scores",
                {
                    "run_id": previous["id"],
                    "lineage": current["lineage"],
                    "channel": channel,
                    "actor": actor,
                    "value": direction * (0.01 + index * 0.001),
                    "effective_at": day + "T00:00:00+00:00",
                    "evidence": {"scope": "explicit_statistical_state_fixture_not_actual_market_performance"},
                },
            )
    service.phase(current["id"], False, frame)
    run = service.phase(current["id"], True, frame)
    assert run["result"]["budgets"]["continuation"] > 0
    assert run["result"]["budgets"]["defensive"] == 0
    assert run["result"]["targets"] and 0 < run["result"]["cash"] < 1
