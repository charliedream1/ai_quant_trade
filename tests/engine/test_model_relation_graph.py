"""Grounding, immutable export and lifecycle checks with explicit synthetic fixtures."""

import copy
import json
from datetime import date
from pathlib import Path
from time import monotonic, sleep

import pytest
import yaml

from src.engine.market.model_graph.evidence import EvidenceCorpus
from src.engine.market.model_graph.service import GraphResearchService
from src.engine.market.model_graph.validation import apply_review, validate_graph


@pytest.fixture
def values():
    return yaml.safe_load(Path(__file__).with_name("model_graph_fixtures.yaml").read_text(encoding="utf-8"))


def request(values):
    return {"symbol": values["target"], "company_name": "Alpha", "as_of": date.today().isoformat(), "depth": 2}


def original(values):
    corpus = EvidenceCorpus(request(values))
    corpus.add("Original", values["text"])
    return corpus


def test_exact_original_and_edge_direction_survive_validation(values):
    graph = validate_graph(values, original(values), request(values))
    assert graph["edges"][0]["source"] == values["target"] and graph["edges"][0]["target"] == "beta"
    assert graph["nodes"][0]["name"] == "Alpha"
    assert graph["nodes"][1]["identity_status"] == "unresolved_name"


@pytest.mark.parametrize("changed", ["source", "quote", "type", "endpoint"])
def test_invented_evidence_and_entities_fail(values, changed):
    payload = copy.deepcopy(values)
    if changed == "source":
        payload["edges"][0]["evidence"][0]["source_id"] = "unknown"
    elif changed == "quote":
        payload["edges"][0]["evidence"][0]["quote"] += " invented"
    elif changed == "type":
        payload["edges"][0]["relation_type"] = "causation"
    else:
        payload["edges"][0]["target"] = "missing"
    with pytest.raises(ValueError):
        validate_graph(payload, original(values), request(values))


def test_future_source_is_rejected(values):
    with pytest.raises(ValueError, match="publication"):
        original(values).add("Future", values["text"], published_at="2999-01-01")


def test_missing_and_duplicate_review_decisions_are_rejected(values):
    graph = validate_graph(values, original(values), request(values))
    with pytest.raises(ValueError):
        apply_review(graph, {"decisions": []})
    edge = graph["edges"][0]["edge_id"]
    decision = {"edge_id": edge, "decision": "infer", "reason": "Only indirect evidence"}
    reviewed = apply_review(graph, {"decisions": [decision]})
    assert reviewed["edges"][0]["classification"] == "inference"
    with pytest.raises(ValueError):
        apply_review(graph, {"decisions": [decision, decision]})


class FixtureGeneration:
    values = None
    fail_review = False

    def __init__(self, selection, directory, cancelled):
        self.calls = []
        self.cancelled = cancelled

    def complete(self, prompt):
        self.calls.append({"model": "explicit-fixture"})
        if len(self.calls) == 1:
            return copy.deepcopy(self.values)
        if self.fail_review:
            raise ValueError("Controlled reviewer failure")
        graph = json.loads(prompt.split("Proposed graph: ", 1)[1].split("\n", 1)[0])
        return {
            "decisions": [
                {"edge_id": row["edge_id"], "decision": "accept", "reason": "Exact original business link"}
                for row in graph["edges"]
            ]
        }


def wait(service, key):
    deadline = monotonic() + 15
    while monotonic() < deadline:
        row = service.detail(key)
        if row["status"] not in {"queued", "running"}:
            return row
        sleep(0.02)
    raise AssertionError("Graph fixture task did not finish")


def start(client, monkeypatch, values, fail=False):
    result = client.post(
        "/api/v1/kb/notes",
        json={"title": "Company relationship original", "content": values["text"], "library_name": values["library"]},
    ).json()
    assert result["code"] == 0
    FixtureGeneration.values, FixtureGeneration.fail_review = values, fail
    from src.engine.market.model_graph import service as module

    monkeypatch.setattr(module, "GraphGeneration", FixtureGeneration)
    service = GraphResearchService()
    row = service.start(
        {
            "symbol": values["target"],
            "market": "CN",
            "backend": "qoder",
            "depth": 1,
            "library_name": values["library"],
            "document_ids": [result["data"]["doc_id"]],
        }
    )
    return service, row


def test_background_run_view_and_export_are_same_artifact(client, monkeypatch, values):
    service, row = start(client, monkeypatch, values)
    assert wait(service, row["run_id"])["status"] == "completed"
    graph = service.result(row["run_id"])
    assert graph["edges"] and graph["skill_sha256"]
    before = (service.store.directory(row["run_id"]) / "graph.json").read_bytes()
    response = client.get(f"/api/v1/relations/research/runs/{row['run_id']}/export")
    assert response.status_code == 200 and response.content == before
    assert service.result(row["run_id"]) == graph
    assert len(graph["calls"]) == 2


def test_failed_review_never_publishes_unreviewed_facts(client, monkeypatch, values):
    service, row = start(client, monkeypatch, values, fail=True)
    assert wait(service, row["run_id"])["status"] == "failed"
    with pytest.raises(ValueError):
        service.result(row["run_id"])


def test_private_document_cannot_enter_another_session(client, values):
    from src.core.repository import Repository

    result = client.post(
        "/api/v1/kb/notes", json={"title": "Private", "content": values["text"], "library_name": values["library"]}
    ).json()["data"]
    Repository().update("kb_documents", result["doc_id"], {"attachment_session": "owner"})
    corpus = EvidenceCorpus(
        {
            **request(values),
            "library_name": values["library"],
            "session_id": "other",
            "document_ids": [result["doc_id"]],
        }
    )
    with pytest.raises(ValueError, match="outside"):
        corpus.load_local()
