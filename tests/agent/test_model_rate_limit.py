"""Rolling-window, thread/process sharing, deadline and permit recovery behavior."""

import json
import sqlite3
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from time import monotonic

import pytest

from src.agent.model_budget import CallBudget
from src.agent.model_options import model_options
from src.agent.model_rate_limit import ModelRateLimiter
from src.core.exceptions import BusinessError
from src.core.repository import Repository
from src.core.stream_control import STREAM_STOP


def limiter(**options):
    return ModelRateLimiter(Repository().db.db_path, {"id": 900, **model_options(options)})


def test_window_boundary_and_instance_sharing(client, monkeypatch):
    clock = [1000.0]
    monkeypatch.setattr("src.agent.model_rate_limit.time.time", lambda: clock[0])
    cfg = {"rpm": 1, "wait_on_limit": False}
    with limiter(**cfg).permit(CallBudget(5)):
        pass
    with pytest.raises(BusinessError, match="限流"):
        with limiter(**cfg).permit(CallBudget(5)):
            pass
    clock[0] += 60
    with limiter(**cfg).permit(CallBudget(5)):
        pass


def test_quota_group_shared_across_models_and_backends(client):
    first = ModelRateLimiter(
        Repository().db.db_path, {"id": 1, **model_options({"rpm": 1, "wait_on_limit": False, "quota_group": "shared"})}
    )
    second = ModelRateLimiter(
        Repository().db.db_path,
        {
            "id": 2,
            **model_options({"rpm": 1, "wait_on_limit": False, "quota_group": "shared", "api_backend": "openai"}),
        },
    )
    with first.permit(CallBudget(5)):
        pass
    with pytest.raises(BusinessError):
        with second.permit(CallBudget(5)):
            pass


def test_concurrency_atomic_and_exception_releases(client):
    gate = Event()
    acquired = [Event(), Event()]

    def hold(index):
        with limiter(max_concurrency=2, wait_on_limit=False).permit(CallBudget(5)):
            acquired[index].set()
            gate.wait(3)
            raise RuntimeError("controlled request failure")

    with ThreadPoolExecutor(max_workers=2) as pool:
        jobs = [pool.submit(hold, i) for i in range(2)]
        try:
            assert all(event.wait(3) for event in acquired)
            with pytest.raises(BusinessError):
                with limiter(max_concurrency=2, wait_on_limit=False).permit(CallBudget(1)):
                    pass
        finally:
            gate.set()
        for job in jobs:
            with pytest.raises(RuntimeError):
                job.result()
    with limiter(max_concurrency=2, wait_on_limit=False).permit(CallBudget(1)):
        pass


def test_wait_obeys_deadline_and_cancel_without_admission(client):
    with limiter(rpm=1).permit(CallBudget(1)):
        pass
    started = monotonic()
    with pytest.raises(BusinessError, match="整体超时"):
        with limiter(rpm=1).permit(CallBudget(0.05)):
            pass
    assert monotonic() - started < 0.5
    stop = Event()
    stop.set()
    token = STREAM_STOP.set(stop)
    try:
        with pytest.raises(BusinessError, match="取消"):
            with limiter(rpm=1).permit(CallBudget(1)):
                pass
    finally:
        STREAM_STOP.reset(token)
    assert Repository().db.scalar("SELECT COUNT(*) FROM llm_request_slots") == 1


def test_crashed_process_lease_expires(client):
    import time

    repo = Repository()
    instance = limiter(max_concurrency=1, wait_on_limit=False)
    repo.db.execute(
        "INSERT INTO llm_request_slots VALUES(?,?,?,?,?)",
        ("abandoned", instance.scope, time.time(), time.time() - 1, 999999),
    )
    with instance.permit(CallBudget(1)):
        pass


def test_two_independent_processes_share_one_rpm(client):
    payload = {
        "path": str(Repository().db.db_path),
        "config": {"id": 123, **model_options({"rpm": 1, "wait_on_limit": False})},
    }
    code = """import sys,json
from pathlib import Path
from src.agent.model_budget import CallBudget
from src.agent.model_rate_limit import ModelRateLimiter
from src.core.exceptions import BusinessError
d=json.load(sys.stdin)
try:
 with ModelRateLimiter(Path(d['path']),d['config']).permit(CallBudget(3)):pass
except BusinessError:sys.exit(3)
"""

    def invoke(_):
        return subprocess.run(
            [sys.executable, "-X", "utf8", "-c", code],
            input=json.dumps(payload).encode(),
            capture_output=True,
            timeout=15,
        ).returncode

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(invoke, range(2))) == [0, 3]


def test_busy_database_wait_is_bounded_by_call_deadline(client):
    connection = sqlite3.connect(Repository().db.db_path)
    try:
        connection.execute("BEGIN IMMEDIATE")
        started = monotonic()
        with pytest.raises(BusinessError, match="整体超时"):
            with limiter(rpm=1).permit(CallBudget(0.04)):
                pass
        assert monotonic() - started < 0.5
    finally:
        connection.rollback()
        connection.close()
