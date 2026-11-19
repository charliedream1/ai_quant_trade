"""Daily reuse, cross-process ownership, refresh and privacy without vendor calls."""

import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from threading import Event
from types import SimpleNamespace

import pytest

from src.agent import cli_catalog
from src.agent import cli_catalog_cache as cache
from src.core.page_work import PageCancelled, PageWork, context


@pytest.fixture()
def daily(monkeypatch, tmp_path):
    monkeypatch.setattr(cache, "get_settings", lambda: SimpleNamespace(data_dir=tmp_path))
    monkeypatch.setattr(cache, "day", lambda policy: "2026-11-19")
    policy = {**cli_catalog.catalog_config()["cache"], "max_bytes": 10000, "max_models": 10}
    return policy, tmp_path


def result(model="first", status="ready"):
    return {
        "backend": "codex",
        "rows": [{"id": model, "name": model, "billing": "Price unknown", "efforts": None}],
        "status": status,
        "updated": "2026-11-19T00:00:00Z",
        "source": "Declared metadata",
        "available": True,
    }


def test_same_day_refresh_and_next_day(daily, monkeypatch):
    policy, _ = daily
    calls = []

    def load():
        calls.append(1)
        return result(str(len(calls)))

    first = cache.reuse(["profile"], "codex", False, policy, load)
    assert not first["cache_reused"]
    assert cache.reuse(["profile"], "codex", False, policy, load)["cache_reused"]
    assert len(calls) == 1
    assert cache.reuse(["profile"], "codex", True, policy, load)["rows"][0]["id"] == "2"
    monkeypatch.setattr(cache, "day", lambda policy: "2026-11-20")
    assert cache.reuse(["profile"], "codex", False, policy, load)["rows"][0]["id"] == "3"


def test_restart_reads_disk_without_discovery(daily):
    policy, root = daily
    cache.reuse(["profile"], "codex", False, policy, result)
    script = """import json,sys
from pathlib import Path
from types import SimpleNamespace
from src.agent import cli_catalog_cache as c
c.get_settings=lambda:SimpleNamespace(data_dir=Path(sys.argv[1]))
c.day=lambda p:'2026-11-19'
def forbidden():raise AssertionError('Discovery repeated')
assert c.reuse(['profile'],'codex',False,json.loads(sys.argv[2]),forbidden)['cache_reused']
"""
    subprocess.run([sys.executable, "-c", script, str(root), json.dumps(policy)], check=True, timeout=30)


def test_two_processes_share_one_discovery(daily):
    policy, root = daily
    script = """import json,sys
from pathlib import Path
from threading import Event
from types import SimpleNamespace
from src.agent import cli_catalog_cache as c
root=Path(sys.argv[1])
c.get_settings=lambda:SimpleNamespace(data_dir=root)
c.day=lambda p:'2026-11-19'
def load():
 with (root/'queries.txt').open('a',encoding='utf-8') as f:f.write('query\\n')
 Event().wait(0.4)
 return json.loads(sys.argv[3])
assert c.reuse(['process-profile'],'codex',False,json.loads(sys.argv[2]),load)['status']=='ready'
"""
    with ThreadPoolExecutor(2) as pool:
        futures = [
            pool.submit(
                subprocess.run,
                [sys.executable, "-c", script, str(root), json.dumps(policy), json.dumps(result())],
                check=True,
                timeout=30,
            )
            for _ in range(2)
        ]
        for future in futures:
            future.result()
    assert (root / "queries.txt").read_text().splitlines() == ["query"]


def test_scope_change_does_not_reuse_another_profile(daily):
    policy, _ = daily
    cache.reuse(["codex", "one"], "codex", False, policy, result)
    assert not cache.reuse(["codex", "two"], "codex", False, policy, result)["cache_reused"]
    value = {**result(), "backend": "qoder"}
    assert not cache.reuse(["qoder", "one"], "qoder", False, policy, lambda: value)["cache_reused"]


@pytest.mark.parametrize("refresh", [False, True])
def test_concurrent_discovery_and_refresh_are_collapsed(daily, monkeypatch, refresh):
    policy, _ = daily
    if refresh:
        cache.reuse(["profile"], "codex", False, policy, result)
    started, release, waiter = Event(), Event(), Event()
    original = cache.read
    calls = []

    def read(*args):
        value = original(*args)
        if started.is_set():
            waiter.set()
        return value

    def load():
        calls.append(1)
        started.set()
        assert release.wait(5)
        return result("new")

    monkeypatch.setattr(cache, "read", read)
    with ThreadPoolExecutor(2) as pool:
        first = pool.submit(cache.reuse, ["profile"], "codex", refresh, policy, load)
        assert started.wait(3)
        second = pool.submit(cache.reuse, ["profile"], "codex", refresh, policy, load)
        assert waiter.wait(3)
        release.set()
        assert first.result()["rows"] == second.result()["rows"]
    assert len(calls) == 1


def test_failed_refresh_preserves_rows_and_suppresses_repeated_failure(daily):
    policy, _ = daily
    first = cache.reuse([], "codex", False, policy, result)
    failed = cache.reuse([], "codex", True, policy, lambda: result("", "failed"))
    assert failed["stale"] and failed["rows"] == first["rows"] and failed["status"] == "failed"
    assert cache.reuse([], "codex", False, policy, lambda: pytest.fail("Repeated discovery"))["stale"]
    assert cache.reuse([], "codex", True, policy, lambda: result("recovered"))["status"] == "ready"


def test_first_failure_and_corrupt_cache_recovery(daily):
    policy, root = daily
    failed = {**result(status="failed"), "rows": []}
    cache.reuse([], "codex", False, policy, lambda: failed)
    assert cache.reuse([], "codex", False, policy, lambda: pytest.fail("Repeated failure"))["status"] == "failed"
    path = next(root.rglob("*.json"))
    path.write_text("not valid JSON", encoding="utf-8")
    assert cache.reuse([], "codex", False, policy, result)["status"] == "ready"
    path.write_text("x" * (policy["max_bytes"] + 1), encoding="utf-8")
    assert cache.reuse([], "codex", False, policy, result)["status"] == "ready"


def test_cancelled_owner_is_not_cached_and_waiter_can_continue(daily):
    policy, root = daily

    def cancel():
        raise InterruptedError("Declared cancellation")

    with pytest.raises(InterruptedError):
        cache.reuse([], "codex", False, policy, cancel)
    assert not list(root.rglob("*.json"))
    assert cache.reuse([], "codex", False, policy, result)["status"] == "ready"


def test_waiting_page_can_cancel_without_stopping_owner(daily, monkeypatch):
    policy, _ = daily
    started, release, waiting = Event(), Event(), Event()
    page = PageWork("a" * 32, 1)
    original = cache.read

    def read(*args):
        value = original(*args)
        if started.is_set():
            waiting.set()
        return value

    def load():
        started.set()
        assert release.wait(5)
        return result()

    def wait():
        with context(page):
            return cache.reuse([], "codex", False, policy, result)

    monkeypatch.setattr(cache, "read", read)
    with ThreadPoolExecutor(2) as pool:
        owner = pool.submit(cache.reuse, [], "codex", False, policy, load)
        assert started.wait(3)
        waiter = pool.submit(wait)
        assert waiting.wait(3)
        page.stopped.set()
        with pytest.raises(PageCancelled):
            waiter.result(timeout=2)
        release.set()
        assert owner.result()["status"] == "ready"


def test_persistent_cache_excludes_secrets_and_private_paths(daily, monkeypatch):
    policy, root = daily
    monkeypatch.setenv("DECLARED_PRIVATE_API_KEY", "declared-canary-long-value")
    value = result("declared-canary-long-value")
    value["rows"][0].update(name="label C:/Users/private/file", api_key="must-not-persist")
    cache.reuse(["credential-in-scope", "C:/Users/private/profile"], "codex", False, policy, lambda: value)
    raw = next(root.rglob("*.json")).read_text()
    for secret in ("declared-canary-long-value", "must-not-persist", "C:/Users", "credential-in-scope"):
        assert secret not in raw


def test_calendar_uses_configured_timezone(monkeypatch):
    instant = datetime(2026, 11, 19, 18, tzinfo=timezone.utc)
    monkeypatch.setattr(cache, "datetime", SimpleNamespace(now=lambda zone: instant.astimezone(zone)))
    assert cache.day({"timezone": "Asia/Shanghai"}) == "2026-11-20"
    assert cache.day({"timezone": "UTC"}) == "2026-11-19"


def test_malformed_rows_and_unwritable_cache_are_safe(daily, monkeypatch):
    policy, root = daily
    cache.reuse([], "codex", False, policy, result)
    path = next(root.rglob("*.json"))
    entry = json.loads(path.read_text())
    entry["result"]["rows"] = [{"id": "incomplete"}]
    path.write_text(json.dumps(entry), encoding="utf-8")
    assert not cache.reuse([], "codex", False, policy, result)["cache_reused"]

    def denied(*args, **kwargs):
        raise PermissionError

    monkeypatch.setattr(Path, "mkdir", denied)
    assert cache.reuse([], "codex", True, policy, result)["status"] == "ready"
