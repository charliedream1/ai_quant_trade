"""Task ownership and timeout behavior stay correct across independent callers."""

import asyncio
import json
import os
import subprocess
import sys
import time
from threading import Event
from unittest.mock import patch

import pytest

from src.api.event_stream import sse_events
from src.core.repository import Repository
from src.core.stream_control import stream_pause
from src.core.task_control import TaskLease, cancel_lease, lease_alive
from src.core.timeutil import utc_now_iso
from src.scheduler import executor
from src.strategy.composition.config import template
from src.strategy.composition.store import PipelineStore


def test_lease_prevents_duplicate_owner_and_cancel_is_shared(client):
    first = TaskLease("test-task", "same", Repository())
    try:
        assert lease_alive("test-task", "same", Repository())
        with pytest.raises(ValueError, match="活动执行"):
            TaskLease("test-task", "same", Repository())
        assert cancel_lease("test-task", "same", Repository())
        assert first.cancelled()
    finally:
        first.close()
    assert not lease_alive("test-task", "same")


def test_failed_heartbeat_start_does_not_reserve_capacity(client):
    with patch("src.core.task_control.Thread.start", side_effect=RuntimeError("thread quota")):
        with pytest.raises(RuntimeError, match="thread quota"):
            TaskLease("test-start-failure", "same", Repository(), limit=1)
    assert not lease_alive("test-start-failure", "same")
    replacement = TaskLease("test-start-failure", "next", Repository(), limit=1)
    replacement.close()


def test_failed_insight_persistence_releases_lease(client, monkeypatch):
    from src.engine.insights.service import InsightReportService

    service = InsightReportService()

    def fail_save(run):
        raise OSError("disk failure")

    monkeypatch.setattr(service.store, "save", fail_save)
    with pytest.raises(OSError, match="disk failure"):
        service.start({"kind": "market_review"})
    assert not Repository().db.scalar("SELECT COUNT(*) FROM task_leases WHERE kind='insight' AND status='running'")


def test_expired_owner_can_be_replaced_without_stealing_live_task(client):
    repo = Repository()
    first = TaskLease("lease-test", "expired", repo)
    repo.db.execute("UPDATE task_leases SET expires=0 WHERE kind='lease-test'")
    replacement = TaskLease("lease-test", "expired", repo)
    try:
        assert first.cancelled()
        first.close()
        assert lease_alive("lease-test", "expired", repo)
    finally:
        replacement.close()


def test_soft_timeout_retains_actual_running_future(client):
    completed = Event()

    def worker(job):
        time.sleep(0.1)
        completed.set()
        return {}

    with patch.object(executor, "execute_scheduled_job", worker):
        with pytest.raises(TimeoutError) as error:
            executor._execute_with_timeout({"job_id": "test"}, 0.01, "thread")
        assert not error.value.pending_future.done()
        assert completed.wait(1)


def test_sse_disconnect_ends_wait_without_default_web_thread_pool(client):
    stopped = Event()

    def events():
        try:
            yield {"type": "status", "data": {"status": "ready"}}
            while True:
                stream_pause(0.01)
        finally:
            stopped.set()

    async def run():
        stream = sse_events(events())
        first = await anext(stream)
        assert json.loads(first[6:])["type"] == "status"
        await stream.aclose()

    asyncio.run(run())
    assert stopped.wait(1)


def test_independent_process_observes_live_pipeline_owner(client):
    store = PipelineStore()
    draft = store.save_draft(template("rule_trend"))
    version = store.publish(draft["id"])
    run_id = "abcdef0123456789abcdef0123456789"
    store.repo.db.execute(
        "INSERT INTO strategy_pipeline_runs(id,version_id,status,request,created_at) VALUES(?,?,?,?,?)",
        (run_id, version["id"], "running", "{}", utc_now_iso()),
    )
    guard = TaskLease("pipeline", run_id, store.repo)
    try:
        script = (
            "from src.strategy.composition.service import PipelineService; import sys; sys.stdout.write(PipelineService().detail('"
            + run_id
            + "')['status'])"
        )
        result = subprocess.run(
            [sys.executable, "-B", "-c", script],
            capture_output=True,
            encoding="utf-8",
            env=os.environ.copy(),
            timeout=30,
        )
        assert result.returncode == 0, result.stderr
        assert result.stdout == "running"
    finally:
        guard.close()


def test_independent_process_cannot_claim_existing_scheduler_leader(client):
    script = "from src.core.task_control import TaskLease\nimport sys\ntry:\n TaskLease('leader','scheduler')\nexcept ValueError:\n sys.stdout.write('standby')\n"
    result = subprocess.run([sys.executable, "-B", "-c", script], capture_output=True, encoding="utf-8", timeout=30)
    assert result.returncode == 0, result.stderr
    assert result.stdout == "standby"
