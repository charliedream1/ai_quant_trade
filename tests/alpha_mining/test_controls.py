"""Controls fail closed under manipulated evidence, repeat use and resource limits."""

from copy import deepcopy
from threading import Event
from time import monotonic

import pytest

from src.alpha_mining.approvals import approve
from src.alpha_mining.components import AlphaRuntime
from src.alpha_mining.config import config
from src.alpha_mining.discovery import reserve_holdout
from src.alpha_mining.export import export_draft
from src.alpha_mining.families import check_unseen_validation
from src.alpha_mining.regime import classify
from src.alpha_mining.service import AlphaService
from src.alpha_mining.studies import add_candidate
from src.alpha_mining.theme import run_theme
from src.core.exceptions import BusinessError
from src.strategy.composition.contracts import Frame
from src.strategy.composition.validation import compile_plan


def study(service, payload, fixture):
    dataset = service.register_dataset("测试母池", "market", payload)
    return service.create(
        {
            "name": "测试研究",
            "dataset_id": dataset["id"],
            "policy": fixture["policy"],
            "batch_size": 2,
            "models": {"default": {"model_id": 1}},
        }
    )


def test_invalid_candidate_is_retained_and_counts_against_budget(client, market_payload, workflow_fixture):
    service = AlphaService()
    registered = study(service, market_payload, workflow_fixture)
    hypothesis = workflow_fixture["idea"]["ideas"][0]
    bad = deepcopy(workflow_fixture["implement"])
    bad["direction"] = -1
    failed = add_candidate(service.store, registered["id"], hypothesis, bad, "ai")
    assert failed["status"] == "technical_failed"
    successful = add_candidate(service.store, registered["id"], hypothesis, workflow_fixture["implement"], "human")
    assert successful["status"] == "implemented"
    with pytest.raises(BusinessError):
        add_candidate(service.store, registered["id"], hypothesis, workflow_fixture["implement"], "human")
    assert len(service.store.list("alpha_candidates", registered["id"])) == 2


def test_holdout_is_single_use_across_projects(client, market_payload, workflow_fixture):
    service = AlphaService()
    first = study(service, market_payload, workflow_fixture)
    candidate = add_candidate(
        service.store, first["id"], workflow_fixture["idea"]["ideas"][0], workflow_fixture["implement"], "human"
    )
    # This fixture only drives the reservation transaction; it is not an actual
    # statistical pass and is never used as production acceptance evidence.
    service.store.transition(
        first["id"], {"draft"}, "validated", {"validation": [{"candidate_id": candidate["id"], "passed": True}]}
    )
    reserve_holdout(service.store, first["id"], candidate["id"])
    with pytest.raises(BusinessError):
        reserve_holdout(service.store, first["id"], candidate["id"])
    second = study(service, market_payload, workflow_fixture)
    other = add_candidate(
        service.store, second["id"], workflow_fixture["idea"]["ideas"][0], workflow_fixture["implement"], "human"
    )
    service.store.transition(
        second["id"], {"draft"}, "validated", {"validation": [{"candidate_id": other["id"], "passed": True}]}
    )
    with pytest.raises(BusinessError, match="已经消费"):
        reserve_holdout(service.store, second["id"], other["id"])


def test_validation_reuse_is_rejected_across_families(client, market_payload, workflow_fixture):
    service = AlphaService()
    first = study(service, market_payload, workflow_fixture)
    service.store.transition(first["id"], {"draft"}, "validating")
    second = study(service, market_payload, workflow_fixture)
    with pytest.raises(BusinessError, match="验证已被读取"):
        check_unseen_validation(service.store, second)


def test_event_tampering_detected(client, market_payload, workflow_fixture):
    service = AlphaService()
    registered = study(service, market_payload, workflow_fixture)
    assert service.store.verify_events(registered["id"])
    service.store.repo.db.execute("UPDATE alpha_events SET payload='{}' WHERE study_id=?", (registered["id"],))
    assert not service.store.verify_events(registered["id"])


def test_false_theme_quote_is_rejected(client, workflow_fixture):
    service = AlphaService()
    dataset = service.register_dataset(
        "资料", "documents", {"documents": workflow_fixture["documents"], "is_mock": True}
    )
    registered = service.create(
        {"name": "主题", "mode": "theme", "dataset_id": dataset["id"], "cutoff": "2019-05-01T00:00:00+00:00"}
    )

    class BadSession:
        cancelled = staticmethod(lambda: False)

        def run(self, *args):
            result = deepcopy(workflow_fixture["theme"])
            result["associations"][0]["quote"] = "不存在的原文"
            return result

    with pytest.raises(BusinessError, match="摘录"):
        run_theme(service.store, registered, BadSession(), lambda *args: None)


def test_demo_policy_cannot_promote_mock_to_workshop(client, market_payload, workflow_fixture):
    service = AlphaService()
    registered = study(service, market_payload, workflow_fixture)
    candidate = add_candidate(
        service.store, registered["id"], workflow_fixture["idea"]["ideas"][0], workflow_fixture["implement"], "human"
    )
    service.store.transition(
        registered["id"],
        {"draft"},
        "reviewed",
        {
            "final": {
                "candidate_id": candidate["id"],
                "passed": True,
                "data_is_mock": True,
                "source": {"verified": True},
            }
        },
    )
    for track in ("economic", "technical"):
        approve(
            service.store,
            registered["id"],
            candidate["id"],
            track,
            "approve",
            "explicit-test-fixture",
            {"reason": "control-test"},
        )
    with pytest.raises(BusinessError, match="合成"):
        export_draft(service.store, registered["id"], candidate["id"])


def test_artifact_paths_and_configurations_are_bounded(client, market_payload, workflow_fixture):
    service = AlphaService()
    registered = study(service, market_payload, workflow_fixture)
    with pytest.raises(BusinessError):
        service.store.artifact(registered["id"], "../outside.py")
    with pytest.raises(BusinessError):
        service.store.artifact(registered["id"], ".secret")


def test_regime_label_cannot_contradict_numeric_framework(workflow_fixture):
    values = [
        {"id": "g1", "period": -1, "series": "growth", "value": 2.5},
        {"id": "g2", "period": 0, "series": "growth", "value": 2.2},
        {"id": "i1", "period": -1, "series": "inflation", "value": 3.3},
        {"id": "i2", "period": 0, "series": "inflation", "value": 3.7},
    ]

    class ContradictorySession:
        def run(self, *args):
            return {
                "regime": "Reflation",
                "confidence": 0.8,
                "evidence_ids": ["g2", "i2"],
                "rationale": "增长下降且通胀上升，对应Stagflation",
            }

    framework = {**config()["regime_defaults"], "min_observations": 2}
    with pytest.raises(BusinessError, match="不一致"):
        classify(ContradictorySession(), values, framework, {"model_id": 1})


def test_two_tracks_export_a_frozen_workshop_component_without_execution_bypass(
    client, market_payload, workflow_fixture
):
    service = AlphaService()
    registered = study(service, market_payload, workflow_fixture)
    candidate = add_candidate(
        service.store, registered["id"], workflow_fixture["idea"]["ideas"][0], workflow_fixture["implement"], "human"
    )
    # State fixture exercises the positive authorization boundary; it is not
    # statistical or real-market acceptance evidence and makes no alpha claim.
    service.store.transition(
        registered["id"],
        {"draft"},
        "reviewed",
        {
            "final": {
                "candidate_id": candidate["id"],
                "passed": True,
                "data_is_mock": False,
                "source": {"verified": True, "method": "explicit_authorization_state_fixture"},
            }
        },
    )
    approve(
        service.store,
        registered["id"],
        candidate["id"],
        "economic",
        "approve",
        "test-economic",
        {"reason": "state-fixture"},
    )
    with pytest.raises(BusinessError, match="两轨"):
        export_draft(service.store, registered["id"], candidate["id"])
    approve(
        service.store,
        registered["id"],
        candidate["id"],
        "technical",
        "approve",
        "test-technical",
        {"reason": "state-fixture"},
    )
    exported = export_draft(service.store, registered["id"], candidate["id"])
    assert exported["pipeline_id"] and not exported["automatic_live_trading"]
    compiled = compile_plan(exported["definition"])
    assert compiled["nodes"][0]["component"] == "alpha_factor"
    assert compiled["nodes"][0]["params"]["artifact_digest"] == candidate["digest"]
    history = market_payload["history"]
    day = max(row["date"] for rows in history.values() for row in rows)
    values = AlphaRuntime().evaluate(compiled["nodes"][0], sorted(history), Frame.create(day, history))
    assert all(row.status == "pass" for row in values.values())
    manipulated = deepcopy(compiled["nodes"][0])
    manipulated["params"]["artifact_digest"] = "changed"
    with pytest.raises(BusinessError, match="摘要"):
        AlphaRuntime().evaluate(manipulated, sorted(history), Frame.create(day, history))


def test_cancel_stops_after_current_observed_call(client, market_payload, workflow_fixture):
    entered, release = Event(), Event()

    class SlowLLM:
        def complete(self, *args, **kwargs):
            entered.set()
            assert release.wait(5)
            return {"model": "explicit-cancellation-test-double", "text": "{}"}

    service = AlphaService(llm=SlowLLM())
    registered = study(service, market_payload, workflow_fixture)
    service.start(registered["id"], "discover")
    assert entered.wait(5)
    assert service.cancel(registered["id"])["cancel_requested"]
    release.set()
    deadline = monotonic() + 5
    while service.detail(registered["id"])["status"] == "discovering":
        assert monotonic() < deadline
        Event().wait(0.01)
    result = service.detail(registered["id"])
    assert result["status"] == "cancelled"
    assert not result["candidates"] and result["event_chain_valid"]
