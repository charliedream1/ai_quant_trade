"""Reviewed worker ports preserve signals without running custom source in the host."""

import pytest

from src.core.exceptions import BusinessError
from src.strategy.loader import StrategyLoader
from src.strategy.ports import MarketEvent, StrategyContext
from src.strategy.strategy_store import StrategyStore


def test_custom_source_requires_review_and_runs_in_worker(client):
    code = "class Strategy:\n    def on_bar(self, event, context):\n        return {'symbol': event['symbol'], 'side': 'buy', 'quantity': 100}\n"
    store = StrategyStore()
    item = store.create({"name": "worker-normal", "code": code})
    with pytest.raises(BusinessError, match="尚未复核"):
        StrategyLoader(store.storage).load_from_file(item["file_path"])
    store.review(item["id"], item["source_sha256"], "explicit-test-reviewer")
    loaded = StrategyLoader(store.storage).load_from_file(item["file_path"])
    context = StrategyContext(symbols=["600519"])
    try:
        loaded.adapter.on_start(context)
        result = loaded.adapter.on_bar(MarketEvent("600519", "2026-01-05", 10, 11, 9, 10), context)
        assert result[0].quantity == 100 and result[0].symbol == "600519"
        assert loaded.adapter.process.pid
    finally:
        loaded.adapter.on_stop(context)
    assert loaded.adapter.process.poll() is not None


def test_review_does_not_grant_host_filesystem_access(client, tmp_path):
    target = tmp_path / "outside-worker.txt"
    code = (
        "import builtins\nbuiltins.open("
        + repr(str(target))
        + ", 'w').write('denied')\ndef on_bar(event, context):\n    return []\n"
    )
    store = StrategyStore()
    item = store.create({"name": "worker-denied", "code": code})
    store.review(item["id"], item["source_sha256"], "explicit-test-reviewer")
    with pytest.raises(ValueError, match="写入工作目录"):
        StrategyLoader(store.storage).load_from_file(item["file_path"])
    assert not target.exists()


def test_source_change_invalidates_review(client):
    store = StrategyStore()
    item = store.create({"name": "worker-changing", "code": "def on_bar(event, context):\n    return []\n"})
    store.review(item["id"], item["source_sha256"], "explicit-test-reviewer")
    store.update(item["id"], {"code": "def on_bar(event, context):\n    return None\n"})
    with pytest.raises(BusinessError, match="尚未复核"):
        StrategyLoader(store.storage).load_from_file(item["file_path"])


def test_same_name_and_version_do_not_overwrite_previous_source(client):
    store = StrategyStore()
    first = store.create({"name": "same-name", "code": "def on_bar(event,context):\n    return []\n"})
    with pytest.raises(BusinessError, match="同名同版本"):
        store.create({"name": "same-name", "code": "def on_bar(event,context):\n    return None\n"})
    assert store.get(first["id"])["code"] == first["code"]


def test_relative_strategy_path_cannot_leave_project(client):
    with pytest.raises(BusinessError, match="位于本项目"):
        StrategyLoader().load_from_file("../outside.py")
