"""Real owned-process cancellation, deadlines, deduplication and immutable export."""

import copy
import sys
from contextlib import nullcontext
from pathlib import Path
from time import monotonic, sleep

import pytest
from filelock import FileLock

from src.engine.market import rule_graph_jobs as module
from src.engine.market.rule_graph_jobs import RuleGraphJobs


def finished(service, key, seconds=35):
    deadline = monotonic() + seconds
    while monotonic() < deadline:
        row = service.detail(key)
        if row["status"] not in {"queued", "running"}:
            return row
        sleep(0.05)
    raise AssertionError("Graph worker did not release the task")


def test_actual_rule_worker_and_saved_result(client):
    service = RuleGraphJobs()
    row = service.start("600519", 1, ["industry"], "CN")
    terminal = finished(service, row["run_id"])
    assert terminal["status"] == "completed", terminal
    graph = service.store.result(row["run_id"])
    assert graph["mode"] == "rules" and graph["market"] == "CN" and graph["is_mock"]
    assert graph["edges"] and graph["run_id"] == row["run_id"]
    before = (service.store.directory(row["run_id"]) / "graph.json").read_bytes()
    assert service.store.result(row["run_id"]) == graph
    assert (service.store.directory(row["run_id"]) / "graph.json").read_bytes() == before


def test_source_failure_provenance_survives_local_task_augmentation(client, monkeypatch):
    from src.engine.market.relation_graph import RelationGraphService

    service = RelationGraphService()
    monkeypatch.setattr(service, "_task_relation_rows", lambda symbol: [])
    source = {
        "nodes": [{"id": "600519", "name": "Explicit fixture", "type": "stock"}],
        "edges": [],
        "source_gaps": ["ReadTimeout"],
    }
    augmented = service._augment_task_relations(source, "600519", {"task"})
    result = service._finalize_graph(augmented, "600519", {"task"})
    assert result["source_gaps"] == ["ReadTimeout"]


@pytest.mark.parametrize("cancel,locked", [(False, False), (True, False), (False, True)])
def test_stalled_process_is_stopped_and_partial_is_honest(client, monkeypatch, cancel, locked):
    policy = copy.deepcopy(module.diagnostics_config())
    policy["rules"].update(timeout_seconds=10 if cancel else 1, poll_seconds=0.05)
    monkeypatch.setattr(module, "diagnostics_config", lambda: policy)
    real = module.subprocess.Popen
    owned = []

    def spawn(command, **kwargs):
        if len(command) > 2 and command[1:3] == ["-m", "src.engine.market.rule_graph_worker"]:
            command = [sys.executable, str(Path(__file__).with_name("rule_graph_worker_fixture.py")), command[-1]]
            if locked:
                command.append("locked")
            process = real(command, **kwargs)
            owned.append(process)
            return process
        return real(command, **kwargs)

    monkeypatch.setattr(module.subprocess, "Popen", spawn)
    service = RuleGraphJobs()
    gate = service.store.root.parent / "provider_locks/eastmoney.lock"
    gate.parent.mkdir(parents=True, exist_ok=True)
    with FileLock(str(gate)) if locked else nullcontext():
        row = service.start("600519", 1, ["industry"], "CN")
        assert service.start("600519", 1, ["industry"], "CN")["run_id"] == row["run_id"]
        if cancel:
            service.store.cancel(row["run_id"])
        result = finished(service, row["run_id"], 10)
    assert result["status"] == ("cancelled" if cancel else "partial"), result
    assert owned and all(process.poll() is not None for process in owned)
    if cancel:
        with pytest.raises(ValueError):
            service.store.result(row["run_id"])
    else:
        graph = service.store.result(row["run_id"])
        assert graph["partial_reason"] == "deadline" and not graph["edges"]
