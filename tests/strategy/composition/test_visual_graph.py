"""Graph round trips and layout/evidence contracts preserve actual strategy semantics."""

import json
from copy import deepcopy
from uuid import uuid4

import pytest
import yaml

from src.frontend.service.composition import CompositionServiceMixin
from src.frontend.service.composition_graph import CompositionGraphMixin
from src.frontend.service.graph_documents import document_payload, materialize, scoped, validate_submission
from src.frontend.service.graph_evidence import evidence
from src.frontend.service.graph_storage import GraphLayouts
from src.strategy.composition.config import template, templates
from src.strategy.composition.contracts import Frame
from src.strategy.composition.runtime import PipelineRuntime
from src.strategy.composition.service import PipelineService
from src.strategy.composition.validation import compile_plan, digest


@pytest.mark.parametrize("preset", [row["id"] for row in templates()])
def test_graph_materialization_round_trip_preserves_compiled_strategy(preset):
    source = template(preset)
    text = yaml.safe_dump(source, allow_unicode=True)
    payload = document_payload(text)
    assert not payload["issues"]
    assert digest(compile_plan(source)) == digest(compile_plan(payload["document"]))
    assert validate_submission(payload, text) == payload["document"]


def test_layout_and_selection_do_not_change_computation_digest():
    source = template("rule_trend")
    payload = document_payload(yaml.safe_dump(source))
    before = digest(compile_plan(payload["document"]))
    payload["layout"] = {"main": {"positions": {"trend": {"x": 900, "y": -80}}, "selected": "trend"}}
    assert before == digest(compile_plan(payload["document"]))
    payload["document"]["risk"]["max_weight"] = 0.1
    assert before != digest(compile_plan(payload["document"]))


def test_stale_graph_cannot_overwrite_a_newer_yaml_draft():
    source = template("rule_trend")
    payload = document_payload(yaml.safe_dump(source))
    source["risk"]["max_exposure"] = 0.5
    with pytest.raises(ValueError, match="Stale"):
        validate_submission(payload, yaml.safe_dump(source))


def test_graph_cannot_bypass_risk_schema_or_introduce_arbitrary_components():
    text = yaml.safe_dump(template("rule_trend"))
    value = document_payload(text)
    value["document"]["risk"]["max_exposure"] = 9
    with pytest.raises(ValueError):
        validate_submission(value, text)
    value = document_payload(text)
    value["document"]["nodes"][0]["component"] = "python_exec"
    with pytest.raises(ValueError):
        validate_submission(value, text)


def test_sub_strategy_expansion_preserves_scope_and_rejects_unknown_paths():
    document = materialize(template("multi_sleeve"))
    assert scoped(document, ["etf"])["name"] == template("etf_allocation")["name"]
    with pytest.raises(ValueError):
        scoped(document, ["../data"])


def test_layout_compare_and_swap_prevents_cross_session_overwrite(client):
    store = GraphLayouts()
    key = "draft:" + uuid4().hex
    before = digest(template("rule_trend"))
    saved = store.save(key, before, {"main": {"positions": {"trend": {"x": 20, "y": 30}}}}, 0)
    assert saved["revision"] == 1
    with pytest.raises(ValueError, match="another session"):
        store.save(key, before, {}, 0)
    assert store.load(key)["layout"]["main"]["positions"]["trend"]["x"] == 20
    with pytest.raises(ValueError):
        store.save("../../outside", before, {}, 0)
    with pytest.raises(ValueError):
        store.save(key, before, {"x": float("nan")}, 1)


def test_layout_api_does_not_change_published_definition(client):
    service = PipelineService()
    draft = service.store.save_draft(template("rule_trend"))
    version = service.store.publish(draft["id"])
    source = deepcopy(version["compiled"])
    response = client.put(
        f"/api/v1/strategy-pipelines/{draft['id']}/layout",
        json={
            "definition_digest": digest(draft["definition"]),
            "layout": {"main": {"selected": "trend"}},
            "revision": 0,
        },
    ).json()
    assert response["code"] == 0 and response["data"]["revision"] == 1
    assert service.store.version(version["id"], True)["compiled"] == source
    assert (
        client.get(f"/api/v1/strategy-pipelines/{draft['id']}/layout").json()["data"]["layout"]["main"]["selected"]
        == "trend"
    )


def test_actual_run_events_are_readable_by_visual_node_without_rerunning(client):
    service = PipelineService()
    job = service.start(
        {
            "template": "multi_sleeve",
            "mode": "backtest",
            "start_date": "2026-04-01",
            "end_date": "2026-10-22",
            "agent_mode": "off",
        }
    )
    run = list(service.follow(job["id"]))[-1]["run"]
    assert run["status"] == "finished", run["result"]
    before = len(service.store.runs())
    details = evidence(job["id"])
    assert any(key.startswith("main/trend/") for key in details["nodes"])
    assert any(key.startswith("main/etf/") for key in details["nodes"])
    assert any(value["events"] for value in details["nodes"].values())
    assert client.get(f"/api/v1/strategy-pipeline-runs/{job['id']}/nodes").json()["code"] == 0
    incremental = evidence(job["id"], details["cursor"])
    assert not any(value["events"] for value in incremental["nodes"].values())
    assert len(service.store.runs()) == before


def test_gradio_callback_applies_graph_to_yaml_and_invalidates_version_only_after_valid_change(client):
    service = CompositionGraphMixin()
    text = yaml.safe_dump(template("rule_trend"))
    payload = document_payload(text)
    payload["document"]["risk"]["max_exposure"] = 0.5
    updated, status, version_id, applied = service.pipeline_graph_apply(payload, text)
    assert yaml.safe_load(updated)["risk"]["max_exposure"] == 0.5 and version_id is None
    assert status and applied["patch"]["payload"]["applied_revision"] == 1


def test_unapplied_graph_changes_cannot_silently_run_older_yaml(client):
    source = template("rule_trend")
    text = yaml.safe_dump(source)
    payload = document_payload(text)
    payload["document"]["risk"]["max_exposure"] = 0.5
    before = len(PipelineService().store.runs())
    pending = CompositionServiceMixin().pipeline_run(
        text,
        "{}",
        "baseline",
        None,
        "",
        "backtest",
        "codex_cli",
        None,
        "",
        "",
        "2026-05-04",
        "2026-10-22",
        None,
        False,
        graph_value=payload,
    )
    with pytest.raises(ValueError, match="图形修改尚未应用"):
        next(pending)
    assert len(PipelineService().store.runs()) == before


def test_failed_component_is_identified_in_actual_stage_events(monkeypatch):
    def broken_rule(*args):
        raise ValueError("controlled failure")

    monkeypatch.setattr("src.strategy.composition.runtime.evaluate", broken_rule)
    plan = compile_plan(template("rule_trend"))
    events = []
    runtime = PipelineRuntime(plan, lambda *args: events.append(args))
    with pytest.raises(ValueError, match="controlled failure"):
        runtime.evaluate(Frame.create("2026-10-22", {}))
    failure = next(data for kind, text, data in events if kind == "stage" and data.get("status") == "failed")
    assert failure["node"] == "eligibility" and failure["as_of"] == "2026-10-22"


def test_cli_layout_and_node_evidence_use_the_registered_http_contract(cli_command):
    service = PipelineService()
    draft = service.store.save_draft(template("rule_trend"))
    first = cli_command("pipeline", "layout", "show", draft["id"])["data"]
    assert first["revision"] == 0
    updated = cli_command(
        "pipeline",
        "layout",
        "save",
        draft["id"],
        "--definition-digest",
        digest(draft["definition"]),
        "--layout",
        json.dumps({"main": {"selected": "trend"}}),
        "--revision",
        0,
    )["data"]
    assert updated["revision"] == 1
    job = service.start({"template": "rule_trend", "mode": "targets", "agent_mode": "off"})
    assert list(service.follow(job["id"]))[-1]["run"]["status"] == "finished"
    nodes = cli_command("pipeline", "nodes", job["id"], "--after", 0)["data"]
    assert "main/trend" in nodes["nodes"] and nodes["cursor"] > 0


def test_explicit_load_separates_template_layouts_and_resets_only_editable_drafts(client):
    service = CompositionServiceMixin()
    initial = document_payload(yaml.safe_dump(template("rule_trend")))
    first = service.pipeline_graph_load("rule_trend", initial)[-1]["patch"]["payload"]
    saved = GraphLayouts().save(first["layout_key"], first["base_digest"], {"main": {"selected": "trend"}}, 0)
    first["layout_revision"] = saved["revision"]
    first["document"]["risk"]["max_exposure"] = 0.5
    first["edit_revision"] = 1
    reloaded = service.pipeline_graph_load("rule_trend", first)[-1]["patch"]["payload"]
    other = service.pipeline_graph_load("cascade_pattern_ml_agent", reloaded)[-1]["patch"]["payload"]
    assert reloaded["doc_id"] != first["doc_id"] and reloaded["edit_revision"] == 0
    assert not reloaded["document"]["risk"]
    assert reloaded["layout"]["main"]["selected"] == "trend"
    assert reloaded["layout_key"] != other["layout_key"] and not other["layout"]


def test_graph_evidence_transport_updates_props_without_replacing_the_editable_value(client, monkeypatch):
    from gradio.blocks import postprocess_update_dict

    from src.frontend.components.strategy_graph import StrategyGraph

    value = document_payload(yaml.safe_dump(template("rule_trend")))
    monkeypatch.setattr("src.frontend.service.composition_graph.evidence", lambda run_id: {"run_id": run_id})
    update = CompositionGraphMixin().pipeline_graph_results("actual-run", value)
    transported = postprocess_update_dict(StrategyGraph(value=value), update)
    assert "value" not in transported
    message = transported["props"]["patch"]
    assert message["kind"] == "evidence" and message["doc_id"] == value["doc_id"]
    assert message["evidence"] == {"run_id": "actual-run"} and "document" not in message
