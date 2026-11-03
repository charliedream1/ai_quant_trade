"""Native Skill adapters execute all three real alpha-domain lifecycles with explicit LLM doubles."""

import pytest

from src.agent.skill_runner.service import LocalSkillService
from src.alpha_mining.contracts import ModelSelection
from src.alpha_mining.service import AlphaService
from src.core.exceptions import BusinessError
from src.core.timeutil import utc_now_iso


@pytest.mark.parametrize(
    "mode,skill",
    [("alpha", "quant-alpha-mining"), ("theme", "quant-theme-refine"), ("regime", "quant-regime-research")],
)
def test_local_skill_reuses_alpha_services(client, fixture_llm, market_payload, workflow_fixture, mode, skill):
    service = AlphaService()
    kind, payload = {
        "alpha": ("market", market_payload),
        "theme": ("documents", {"documents": workflow_fixture["documents"], "is_mock": True}),
        "regime": ("macro", {"observations": workflow_fixture["macro"], "is_mock": True}),
    }[mode]
    dataset = service.register_dataset("explicit-local-protocol-fixture", kind, payload)
    request = {
        "name": "explicit-local-protocol-fixture",
        "dataset_id": dataset["id"],
        "policy": workflow_fixture["policy"],
        "batch_size": 1,
        "cutoff": "2019-05-01T00:00:00+00:00",
        "theme": "云计算",
    }
    if mode == "regime":
        request.update(configurations=[{"model_id": 1}], asset_mapping={"equity": "AAA", "bond": "BBB"})
    result = LocalSkillService().run(
        {"skill": skill, "provider": {"backend": "api", "model_id": 1}, "request": request}
    )
    assert result["status"] == ("discovered" if mode == "alpha" else "completed"), result
    assert result["result"]["event_chain_valid"]
    assert fixture_llm.calls and result["outer_cli_usage"] is None


def test_cli_api_ids_cannot_fake_independent_configurations():
    with pytest.raises(ValueError, match="不接受API"):
        ModelSelection(backend="qoder", model_id=1, model_name="auto")


def test_different_api_ids_with_same_effective_model_are_not_independent(client, workflow_fixture):
    service = AlphaService()
    dataset = service.register_dataset(
        "explicit-config-test", "macro", {"observations": workflow_fixture["macro"], "is_mock": True}
    )
    models = [
        service.store.repo.insert(
            "llm_models",
            {
                **workflow_fixture["browser_model"],
                "name": name,
                "created_at": utc_now_iso(),
                "updated_at": utc_now_iso(),
            },
        )["id"]
        for name in ("same-provider-a", "same-provider-b")
    ]
    with pytest.raises(BusinessError, match="实际后端"):
        service.create(
            {
                "name": "duplicate-effective-model",
                "mode": "regime",
                "dataset_id": dataset["id"],
                "cutoff": "2019-05-01T00:00:00+00:00",
                "policy": workflow_fixture["policy"],
                "configurations": [{"model_id": value} for value in models],
                "asset_mapping": {"equity": "AAA", "bond": "BBB"},
            }
        )
