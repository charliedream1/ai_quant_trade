"""Process isolation, request boundaries and evidence visibility regression checks."""

import copy
import sys
from datetime import date, timedelta
from pathlib import Path
from threading import Event
from time import monotonic, sleep

import pytest
import yaml

from src.agent.skill_runner.catalog import preview
from src.agent.skill_runner.service import LocalSkillService
from src.engine.market.model_graph.config import config
from src.engine.market.model_graph.generation import GraphGeneration
from src.engine.market.model_graph.service import GraphResearchService
from src.engine.market.model_graph.transport import text_only_process
from src.engine.market.model_graph.validation import connected_view, validate_graph
from tests.engine.test_model_relation_graph import original, request, start, wait


@pytest.fixture
def values():
    return yaml.safe_load(Path(__file__).with_name("model_graph_fixtures.yaml").read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    "case", ["success", "native_capability", "missing_initialization", "native_tool_call", "waiting"]
)
def test_actual_subprocess_protocol_and_cancellation(tmp_path, monkeypatch, case):
    from src.engine.market.model_graph import transport

    real = transport.subprocess.Popen
    owned = []

    def popen(*args, **kwargs):
        process = real(*args, **kwargs)
        owned.append(process)
        return process

    monkeypatch.setattr(transport.subprocess, "Popen", popen)
    began = monotonic()
    command = [
        sys.executable,
        str(Path(__file__).with_name("model_graph_cli_fixture.py")),
        str(Path(__file__).with_name("model_graph_fixtures.yaml")),
        case,
    ]

    def cancelled():
        return case == "waiting" and monotonic() - began > 1

    if case == "success":
        result = text_only_process(command, None, tmp_path, "", config()["limits"], cancelled, lambda event: None)
        assert result["result"] == '{"available":true}'
    else:
        with pytest.raises((ValueError, InterruptedError)):
            text_only_process(command, None, tmp_path, "", config()["limits"], cancelled, lambda event: None)
    assert monotonic() - began < 5
    assert owned and all(process.poll() is not None for process in owned)


def test_ordinary_model_json_uses_repair(tmp_path, monkeypatch):
    generation = GraphGeneration({"backend": "workbuddy"}, tmp_path, lambda: False)
    monkeypatch.setattr(generation, "_workbuddy", lambda prompt: {"text": "{available: true,}", "backend": "fixture"})
    assert generation.complete("Controlled parser fixture") == {"available": True}


def test_hidden_bridge_removes_disconnected_facts(values):
    graph = validate_graph(values, original(values), request(values))
    graph["nodes"].append({"id": "gamma", "name": "Gamma"})
    graph["edges"] = [{**graph["edges"][0], "source": "beta", "target": "gamma"}]
    assert connected_view(graph)["edges"] == []
    assert [node["id"] for node in connected_view(graph)["nodes"]] == [values["target"]]


def test_quote_span_selection_preserves_exact_original_and_rejects_fabrication(values):
    corpus = original(values)
    assert "".join(corpus.sources[0]["quote_spans"].values()) == values["text"]
    payload = copy.deepcopy(values)
    payload["edges"][0]["evidence"] = [{"source_id": "E1", "quote_id": "E1:1"}]
    graph = validate_graph(payload, corpus, request(values))
    assert graph["edges"][0]["evidence_items"][0]["quote"] == values["text"]
    payload["edges"][0]["evidence"][0]["quote_id"] = "E1:invented"
    with pytest.raises(ValueError, match="span"):
        validate_graph(payload, corpus, request(values))
    payload["edges"][0]["evidence"][0].update(quote_id="E1:1", quote="Altered original")
    with pytest.raises(ValueError, match="altered"):
        validate_graph(payload, corpus, request(values))


def test_research_visual_preserves_labels_and_does_not_invent_price_metrics(values):
    from src.frontend.service.model_relation_visuals import model_relation_figure

    graph = validate_graph(values, original(values), request(values))
    figure = model_relation_figure(graph, values["target"])
    lines = [trace for trace in figure.data if trace.mode == "lines"]
    assert lines[0].name == graph["edges"][0]["relation_label"]
    assert "权重" not in str(lines[0].hovertext)
    assert all("涨跌" not in (trace.hovertemplate or "") for trace in figure.data)
    assert any(annotation.showarrow for annotation in figure.layout.annotations)


def test_historical_undated_source_is_candidate_and_bad_interval_fails(values):
    history = {**request(values), "as_of": (date.today() - timedelta(days=1)).isoformat()}
    graph = validate_graph(values, original(values), history)
    assert graph["edges"][0]["classification"] == "candidate"
    payload = copy.deepcopy(values)
    payload["edges"][0].update(valid_from="2025-02-01", valid_to="2025-01-01")
    with pytest.raises(ValueError, match="interval"):
        validate_graph(payload, original(values), request(values))


@pytest.mark.parametrize(
    "change",
    [
        {"backend": "api"},
        {"depth": 99},
        {"urls": ["file:///private"]},
        {"urls": ["https://example.com/?api_key=private"]},
        {"model_name": "--permission"},
    ],
)
def test_request_boundary(client, values, change):
    with pytest.raises(ValueError):
        GraphResearchService().normalize({"symbol": values["target"], "market": "CN", **change})


def test_graph_skill_preview_preserves_workbuddy_without_relaxing_other_families():
    result = preview(
        {
            "skill": "quant-stock-relations",
            "request": {"symbol": "600519", "market": "CN"},
            "provider": {"backend": "workbuddy", "model_name": "hy3"},
        }
    )
    assert result["family"] == "relation_graph" and result["provider"]["backend"] == "workbuddy"
    assert not result["model_called"]
    with pytest.raises(ValueError):
        preview(
            {"skill": "quant-stock-analysis", "request": {"symbol": "600519"}, "provider": {"backend": "workbuddy"}}
        )


def test_background_cancel_releases_slot_without_result(client, monkeypatch, values):
    from src.engine.market.model_graph import service as module

    entered = Event()

    class BlockingGeneration:
        def __init__(self, selection, directory, cancelled):
            self.cancelled, self.calls = cancelled, []

        def complete(self, prompt):
            entered.set()
            while not self.cancelled():
                sleep(0.02)
            raise InterruptedError("Controlled cancellation")

    service, first = start(client, monkeypatch, values)
    assert wait(service, first["run_id"])["status"] == "completed"
    monkeypatch.setattr(module, "GraphGeneration", BlockingGeneration)
    service = GraphResearchService()
    run = service.start({key: value for key, value in first["request"].items() if key != "company_name"})
    assert entered.wait(5)
    service.store.cancel(run["run_id"])
    assert wait(service, run["run_id"])["status"] == "cancelled"
    with pytest.raises(ValueError):
        service.result(run["run_id"])
    assert (str(service.store.root), run["run_id"]) not in module.ACTIVE


def test_unsafe_public_destinations_and_cross_origin_are_blocked(client):
    from src.core.network_policy import network_session

    with network_session(public_only=True) as session, pytest.raises(ValueError):
        session.get("http://127.0.0.1/", timeout=1)
    response = client.post("/api/v1/relations/research/runs", json={}, headers={"origin": "https://foreign.example"})
    assert response.status_code == 403


def test_unknown_id_cannot_escape_storage(client):
    with pytest.raises(ValueError):
        GraphResearchService().store.get("../private")


def test_registered_skill_executes_graph_workflow(client, monkeypatch, values):
    service, first = start(client, monkeypatch, values)
    assert wait(service, first["run_id"])["status"] == "completed"
    result = LocalSkillService().run(
        {
            "skill": "quant-stock-relations",
            "provider": {"backend": "qoder"},
            "request": {
                key: value for key, value in first["request"].items() if key not in {"company_name", "backend"}
            },
        }
    )
    assert result["status"] == "completed"
    assert result["result"]["graph"]["edges"]
    assert result["result"]["graph"]["skill"] == "quant-stock-relations"


def test_react_discovery_is_not_evidence_until_original_read(client, monkeypatch, values):
    from src.engine.market.model_graph import service as module
    from src.engine.market.model_graph.evidence import EvidenceCorpus
    from tests.engine.test_model_relation_graph import FixtureGeneration

    class PlanningGeneration(FixtureGeneration):
        def complete(self, prompt):
            if len(self.calls) < 2:
                self.calls.append({"model": "explicit-planning-fixture"})
                return (
                    {"action": "search", "query": "Original source"}
                    if len(self.calls) == 1
                    else {"action": "read", "url": "https://example.org/original"}
                )
            if len(self.calls) == 2:
                self.calls.append({"model": "explicit-planning-fixture"})
                return copy.deepcopy(values)
            return super().complete(prompt)

    def search(corpus, query):
        assert not corpus.sources
        corpus.candidates = [{"url": "https://example.org/original", "evidence": False}]
        return corpus.candidates

    monkeypatch.setattr(module, "GraphGeneration", PlanningGeneration)
    monkeypatch.setattr(EvidenceCorpus, "search", search)
    monkeypatch.setattr(EvidenceCorpus, "read", lambda corpus, url: corpus.add("Original", values["text"], url=url))
    service = GraphResearchService()
    run = service.start({"symbol": values["target"], "market": "CN"})
    assert wait(service, run["run_id"])["status"] == "completed"
    assert len(service.store.result(run["run_id"])["calls"]) == 4
