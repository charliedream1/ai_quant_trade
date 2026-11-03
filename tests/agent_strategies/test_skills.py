"""Both native Agent strategy Skills retain the common two-phase research service."""

import pytest

from src.agent.skill_runner.service import LocalSkillService


@pytest.mark.parametrize("skill,recipe", [("quant-cn-debate", "cn_event"), ("quant-contest-trade", "contest_event")])
def test_agent_skill_preserves_actual_phase_events(client, workflow_data, fixture_llm, monkeypatch, skill, recipe):
    monkeypatch.setattr("src.agent_strategies.session.LLMClient", lambda **kwargs: fixture_llm)
    result = LocalSkillService().run(
        {
            "skill": skill,
            "request": {
                "recipe": recipe,
                "market_dataset_id": workflow_data["market_id"],
                "documents_dataset_id": workflow_data["documents_id"],
                "as_of": workflow_data["days"][-1],
                "validation_mode": "historical_research",
                "options": {"calls": 24},
            },
        }
    )
    assert result["status"] == "completed", result
    assert result["result"]["result"]["validation_mode"] == "historical_research"
    assert any(event["kind"] == "domain_event" for event in LocalSkillService().store.events(result["run_id"]))
