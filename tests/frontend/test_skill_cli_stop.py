"""Stop real silent CLI process trees, release resources and allow immediate restart."""

import sys
from time import monotonic, sleep

import pytest
from filelock import FileLock

from src.core.config import PROJECT_ROOT
from src.core.page_analysis_snapshot import capture
from src.core.page_work import activate, context, deactivate
from src.core.task_control import lease_alive
from src.engine.insights import page_analysis, page_generation
from src.engine.insights.store import InsightStore
from src.strategy.codex_cli import CodexCliRunner


def wait_for(function, timeout=10):
    started = monotonic()
    while monotonic() - started < timeout:
        if function():
            return
        sleep(0.025)
    raise AssertionError("Owned work did not finish before deadline")


@pytest.mark.parametrize("action", ["cancel", "navigate"])
def test_real_cli_child_stops_and_lease_is_reusable(client, monkeypatch, tmp_path, action):
    class BlockedRunner(CodexCliRunner):
        def command(self, *args, **kwargs):
            return [sys.executable, str(PROJECT_ROOT / "tests/frontend/blocked_skill_cli.py"), str(tmp_path)]

    monkeypatch.setenv("ALL_IN_ONE_ENABLE_REAL_CLI", "1")
    monkeypatch.setattr(page_generation, "CodexCliRunner", BlockedRunner)
    monkeypatch.setattr(page_generation, "require_native", lambda *args, **kwargs: {"backend": "codex"})
    page = activate(("a" if action == "cancel" else "b") * 32, 1)

    def stock(symbol="600519"):
        return [{"price": 12, "source": "declared"}]

    with context(page):
        capture("stock", stock, (), {}, stock())
        row = page_analysis.start("technical", {"backend": "codex"}, {})
    wait_for((tmp_path / "child-ready").exists)
    began = monotonic()
    if action == "cancel":
        assert "Stopping" in page_analysis.cancel(row["run_id"])
    else:
        deactivate(page.owner, page.revision)
    wait_for(lambda: not lease_alive("insight", row["run_id"]))
    result = InsightStore().detail(row["run_id"])
    assert result["status"] == "cancelled" and not result.get("error")
    assert monotonic() - began < 8
    with FileLock(str(tmp_path / "child.lock"), timeout=0.2):
        pass
    assert not InsightStore().directory(row["run_id"]).joinpath("report.html").exists()
    assert any(event["kind"] == "cancellation" for event in InsightStore().events(row["run_id"]))
    assert page_analysis.cancel(row["run_id"]) == "cancelled"

    # An accepted later task gets a new producer; cancelled work never blocks its slot.
    def complete(run, store, cfg, **kwargs):
        run["status"] = "partial"
        store.save(run)

    monkeypatch.setattr(page_analysis, "execute", complete)
    new_page = activate(page.owner, 2) if action == "navigate" else page
    with context(new_page):
        capture("stock", stock, (), {}, stock())
        later = page_analysis.start("technical", {"backend": "codex"}, {})
    wait_for(lambda: not lease_alive("insight", later["run_id"]))
