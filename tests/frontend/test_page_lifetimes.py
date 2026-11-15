"""Navigation scopes stop actual owned processes and retain independent work."""

import json
import os
from concurrent.futures import ThreadPoolExecutor
from time import monotonic, sleep
from uuid import uuid4

import pytest
from filelock import FileLock

from src.core import page_work


@pytest.fixture(autouse=True)
def isolated_lifetimes():
    page_work.shutdown()
    yield
    page_work.shutdown()


def test_navigation_order_and_two_documents():
    owner, other = uuid4().hex, uuid4().hex
    first = page_work.activate(owner, 1)
    second = page_work.activate(other, 1)
    third = page_work.activate(owner, 3)
    assert first.is_set() and not second.is_set() and not third.is_set()
    assert page_work.activate(owner, 2).is_set()
    page_work.deactivate(owner, 1)
    assert not third.is_set()
    page_work.deactivate(owner, 3)
    assert page_work.activate(owner, 3).is_set()
    assert not page_work.activate(owner, 4).is_set()


def test_graph_consumers_and_independent_subscriber():
    cancelled = []
    first = page_work.activate(uuid4().hex, 1)
    second = page_work.activate(uuid4().hex, 1)
    for page in (first, second):
        with page_work.context(page):
            page_work.own_run("rules", "same", lambda: cancelled.append(True))
    page_work.deactivate(first.owner, 1)
    assert not cancelled
    page_work.deactivate(second.owner, 1)
    assert cancelled == [True]
    with page_work.context(first if not first.is_set() else page_work.activate(first.owner, 2)):
        page_work.own_run("rules", "durable", lambda: cancelled.append(False))
    page_work.own_run("rules", "durable", lambda: cancelled.append(False))
    page_work.deactivate(first.owner, 2)
    assert cancelled == [True]


def test_lifetime_route_and_early_script(client):
    owner = uuid4().hex
    path = "/api/v1/workspace/lifetime"
    body = {"owner": owner, "revision": 1, "action": "activate"}
    assert client.post(path, json=body).status_code == 403
    assert client.post(path, json=body, headers={"Origin": "https://foreign.invalid"}).status_code == 403
    assert client.post(path, json=body, headers={"Origin": "http://testserver"}).json() == {"active": True}
    assert client.get("/api/v1/workspace/lifetime.js").status_code == 200
    body["owner"] = "invalid"
    assert client.post(path, json=body, headers={"Origin": "http://testserver"}).status_code == 400
    assert client.post(path, content="x" * 257, headers={"Origin": "http://testserver"}).status_code == 413


def wait_for(predicate, seconds=20):
    deadline = monotonic() + seconds
    while monotonic() < deadline:
        result = predicate()
        if result:
            return result
        sleep(0.025)
    raise AssertionError("Timed out waiting for owned work")


@pytest.fixture
def reads(monkeypatch, tmp_path):
    from src.core import config
    from src.frontend import page_reads
    from tests.frontend.page_worker_fixture import serve

    page_reads.shutdown()
    monkeypatch.setenv("ALL_IN_ONE_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("ALL_IN_ONE_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("ALL_IN_ONE_DATA_MODE", "mock")
    monkeypatch.setattr(config, "_SETTINGS", None)
    monkeypatch.setattr(page_reads, "serve", serve)
    page_reads.start()
    yield page_reads
    page_reads.shutdown()


def run_read(reads, page, name, args=()):
    with page_work.context(page):
        return reads.read(name, args, {})


def test_last_consumer_kills_blocked_worker_and_releases_lock(reads, tmp_path):
    page = page_work.activate(uuid4().hex, 1)
    with ThreadPoolExecutor() as executor:
        pending = executor.submit(run_read, reads, page, "stock", ("SLOW",))
        marker = tmp_path / "worker-started.json"
        wait_for(marker.exists)
        pid = json.loads(marker.read_text(encoding="utf-8"))["pid"]
        assert pid != os.getpid()
        started = monotonic()
        page_work.activate(page.owner, 2)
        with pytest.raises(page_work.PageCancelled):
            pending.result(timeout=3)
        wait_for(lambda: not reads.BUSY, 8)
        with FileLock(str(tmp_path / "source.lock"), timeout=0.1):
            pass
        assert monotonic() - started < 8
        assert not reads.JOBS


def test_shared_query_survives_one_window_leaving(reads, tmp_path):
    first = page_work.activate(uuid4().hex, 1)
    second = page_work.activate(uuid4().hex, 1)
    with ThreadPoolExecutor() as executor:
        a = executor.submit(run_read, reads, first, "home_news")
        wait_for((tmp_path / "worker-started.json").exists)
        duplicate = executor.submit(run_read, reads, first, "home_news")
        b = executor.submit(run_read, reads, second, "home_news")
        wait_for(lambda: len(next(iter(reads.JOBS.values())).consumers) == 2)
        wait_for(lambda: next(iter(reads.JOBS.values())).consumers.get(first) == 2)
        page_work.deactivate(first.owner, 1)
        with pytest.raises(page_work.PageCancelled):
            a.result(timeout=3)
        with pytest.raises(page_work.PageCancelled):
            duplicate.result(timeout=3)
        assert not b.done() and len(reads.BUSY) == 1
        (tmp_path / "release-source").touch()
        assert b.result(timeout=3) == "shared result"


def test_worker_preserves_table_metadata():
    import gradio as gr
    import pandas as pd

    from src.frontend.read_worker import transferable

    styled = pd.DataFrame({"pnl": [-2.0, 3.0]}).style.map(lambda value: "color:red" if value < 0 else "color:green")
    table = gr.Dataframe(interactive=False)
    expected = table.postprocess(styled).model_dump()
    actual = table.postprocess(transferable(styled)).model_dump()
    assert actual == expected


def test_stopped_worker_releases_only_its_concurrency(client):
    from src.agent.model_rate_limit import release_worker_slots
    from src.core.database import Database

    db = Database()
    for token, pid in (("owned", 12345), ("other", 12346)):
        db.execute(
            "INSERT INTO llm_request_slots(token,scope,admitted_at,lease_until,owner_pid) VALUES(?,?,?,?,?)",
            (token, "test", 10, 1000, pid),
        )
    release_worker_slots(db.db_path, 12345)
    rows = {row["token"]: row for row in db.query("SELECT * FROM llm_request_slots")}
    assert rows["owned"]["lease_until"] == 0 and rows["owned"]["admitted_at"] == 10
    assert rows["other"]["lease_until"] == 1000


def test_page_leave_cancels_owned_rule_run_but_not_independent_run(client, monkeypatch):
    import sys
    from pathlib import Path

    from src.engine.market import rule_graph_jobs as module
    from src.engine.market.rule_graph_jobs import RuleGraphJobs
    from tests.engine.test_rule_graph_jobs import finished

    real = module.subprocess.Popen

    def spawn(command, **kwargs):
        if len(command) > 2 and command[1:3] == ["-m", "src.engine.market.rule_graph_worker"]:
            fixture = Path(__file__).parents[1] / "engine/rule_graph_worker_fixture.py"
            command = [sys.executable, str(fixture), command[-1]]
        return real(command, **kwargs)

    monkeypatch.setattr(module.subprocess, "Popen", spawn)
    service = RuleGraphJobs()
    page = page_work.activate(uuid4().hex, 1)
    with page_work.context(page):
        owned = service.start("600519", 1, ["industry"], "CN")
    independent = service.start("000001", 1, ["industry"], "CN")
    page_work.activate(page.owner, 2)
    assert finished(service, owned["run_id"], 10)["status"] == "cancelled"
    assert service.detail(independent["run_id"])["status"] in {"queued", "running"}
    service.store.cancel(independent["run_id"])
    assert finished(service, independent["run_id"], 10)["status"] == "cancelled"


def test_model_graph_source_process_stops_before_any_model_call(client, monkeypatch):
    from src.core.config import get_settings
    from src.engine.market.model_graph.service import GraphResearchService
    from src.frontend import page_reads
    from tests.frontend.page_worker_fixture import serve

    page_reads.shutdown()
    monkeypatch.setattr(page_reads, "serve", serve)
    page_reads.start()
    page = page_work.activate(uuid4().hex, 1)
    service = GraphResearchService()
    with page_work.context(page):
        row = service.start({"symbol": "600519", "market": "CN", "backend": "qoder", "urls": ["https://example.org"]})
    folder = get_settings().data_dir
    wait_for((folder / "worker-started.json").exists)
    page_work.activate(page.owner, 2)
    wait_for(lambda: service.detail(row["run_id"])["status"] == "cancelled", 10)
    wait_for(lambda: not page_reads.BUSY, 8)
    with FileLock(str(folder / "source.lock"), timeout=0.1):
        pass
    assert not (service.store.directory(row["run_id"]) / "completion-1.json").exists()


def test_only_known_windows_disconnect_noise_is_demoted():
    from types import SimpleNamespace

    from src.core.asyncio_diagnostics import expected_client_reset

    def _call_connection_lost():
        pass

    _call_connection_lost.__module__ = "asyncio.proactor_events"
    reset = ConnectionResetError("Controlled client close")
    reset.winerror = 10054
    handle = SimpleNamespace(_callback=_call_connection_lost)
    assert expected_client_reset({"exception": reset, "handle": handle})
    assert not expected_client_reset({"exception": ValueError("Application failure"), "handle": handle})
    assert not expected_client_reset({"exception": reset})


def test_linux_descendant_discovery_includes_separate_sessions(tmp_path, monkeypatch):
    from src.core import process_control

    for pid, parent in ((100, 1), (101, 100), (102, 101), (200, 1)):
        folder = tmp_path / str(pid)
        folder.mkdir()
        (folder / "stat").write_text(f"{pid} (explicit fixture) S {parent} 0 0", encoding="utf-8")
    monkeypatch.setattr(process_control, "Path", lambda _: tmp_path)
    assert process_control._linux_descendants(100) == [101, 102]


def test_preview_process_waits_for_its_last_window(client, monkeypatch):
    import subprocess
    import sys
    from pathlib import Path

    from src.documents import conversion
    from src.documents.store import PreviewStore

    owned = []

    def convert(row, cache):
        cache.mkdir(parents=True, exist_ok=True)
        fixture = Path(__file__).with_name("preview_worker_fixture.py")
        with subprocess.Popen(
            [sys.executable, str(fixture), str(cache)],
            start_new_session=sys.platform != "win32",
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        ) as process:
            with conversion._LOCK:
                conversion._PROCESSES[str(cache)] = process
            owned.append(process)
            process.wait(timeout=30)
        if conversion._CANCEL[str(cache)].is_set():
            raise InterruptedError("Controlled preview cancelled")
        return cache / "document.pdf"

    monkeypatch.setattr(conversion, "executable", lambda: sys.executable)
    monkeypatch.setattr(conversion, "_convert_inner", convert)
    first = page_work.activate(uuid4().hex, 1)
    second = page_work.activate(uuid4().hex, 1)
    row = {"id": uuid4().hex, "revision": uuid4().hex}
    with page_work.context(first):
        state = conversion.request_pdf(row)
    with page_work.context(second):
        assert conversion.request_pdf(row)["cache_key"] == state["cache_key"]
    cache = PreviewStore().root / "converted" / state["cache_key"]
    wait_for((cache / "preview-started.json").exists)
    page_work.deactivate(first.owner, 1)
    assert owned[0].poll() is None
    page_work.deactivate(second.owner, 1)
    wait_for(lambda: owned[0].poll() is not None, 8)
    wait_for(lambda: conversion._JOBS[str(cache)].done(), 3)
    with FileLock(str(cache / "preview-source.lock"), timeout=0.1):
        pass


def test_accepted_backtest_finishes_after_its_page_leaves(client, monkeypatch):
    from threading import Event

    from src.engine.backtest import BacktestRunner
    from src.engine.backtest.jobs import ACTIVE, submit
    from src.strategy import StrategyStore
    from tests.engine.test_workspace_backtest import request

    strategy = StrategyStore().import_example("egs/examples/strategy_examples/standard_port_strategy.py")
    entered, release, finished = Event(), Event(), Event()
    original = BacktestRunner.execute

    def paused(self, *args, **kwargs):
        entered.set()
        assert release.wait(10)
        try:
            return original(self, *args, **kwargs)
        finally:
            finished.set()

    monkeypatch.setattr(BacktestRunner, "execute", paused)
    page = page_work.activate(uuid4().hex, 1)
    with page_work.context(page):
        task = submit(request(strategy["id"]))
    try:
        assert entered.wait(5)
        page_work.activate(page.owner, 2)
        assert ACTIVE and all(not stop.is_set() for _, stop in ACTIVE.values())
    finally:
        release.set()
        assert finished.wait(15)
    assert BacktestRunner().detail(task["task_id"])["status"] == "finished"


def test_policy_lists_registered_reads_and_excludes_job_submission():
    from src.frontend.service_dispatch import callback_registry

    methods = set(page_work.policy()["read_methods"])
    assert methods <= callback_registry().keys()
    assert not methods.intersection({"create_backtest", "quant_workflow_create_run", "create_paper_account"})


def test_worker_error_diagnostics_preserve_type_and_redact_secrets(client, monkeypatch):
    from src.core.config import get_settings
    from src.frontend.read_worker import invoke
    from src.frontend.service.home_service import HomeServiceMixin

    secret = "worker-private-marker"
    monkeypatch.setenv("WORKER_TEST_API_KEY", secret)

    def fail(*args, **kwargs):
        raise RuntimeError("Controlled worker failure: " + secret)

    monkeypatch.setattr(HomeServiceMixin, "home_news", fail)
    success, payload = invoke(("home_news", (), {}, get_settings(), "CN"))
    assert not success and payload["error_type"] == "RuntimeError"
    assert secret not in payload["message"] and secret not in payload["diagnostic"]
