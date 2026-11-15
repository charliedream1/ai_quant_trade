"""Prevent cold-import regressions, serial homepage scheduling and duplicate source reads."""

import json
import multiprocessing
import os
import subprocess
import sys
from threading import Barrier
from unittest.mock import patch

import pandas as pd
import pytest


def test_homepage_import_does_not_initialize_unrelated_domains(tmp_path):
    code = """import time,sys,json
start=time.perf_counter()
import src.frontend.service.home_service
sys.stdout.write(json.dumps({'seconds':time.perf_counter()-start,'modules':list(sys.modules)}))
"""
    result = subprocess.run(
        [sys.executable, "-B", "-c", code],
        capture_output=True,
        text=True,
        env={**os.environ, "ALL_IN_ONE_DATA_DIR": str(tmp_path), "ALL_IN_ONE_DB_PATH": str(tmp_path / "app.db")},
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    record = json.loads(result.stdout)
    assert not {
        "gradio",
        "src.frontend.service.foundation",
        "src.agent.generic_agent_runtime",
        "src.engine.backtest",
    }.intersection(record["modules"])
    (tmp_path / "cold-import.json").write_text(json.dumps(record), encoding="utf-8")


def test_source_cache_coalesces_independent_processes(tmp_path, monkeypatch):
    from tests.frontend.observation_cache_fixture import acquire

    monkeypatch.setenv("ALL_IN_ONE_PAGE_CACHE_EPOCH", "declared-process-cache-test")
    ctx = multiprocessing.get_context("spawn")
    children = []
    pipes = []
    try:
        for _ in range(2):
            parent, child = ctx.Pipe()
            process = ctx.Process(target=acquire, args=(str(tmp_path), child))
            process.start()
            child.close()
            children.append(process)
            pipes.append(parent)
        results = []
        for pipe in pipes:
            assert pipe.poll(30)
            results.append(pipe.recv())
        assert results[0] == results[1]
        assert len((tmp_path / "acquisitions.jsonl").read_text(encoding="utf-8").splitlines()) == 1
    finally:
        for process in children:
            process.join(timeout=3)
            if process.is_alive():
                process.kill()
                process.join(timeout=3)
            process.close()
        for pipe in pipes:
            pipe.close()


def test_independent_market_sources_run_concurrently(client):
    from src.frontend.service.home_dashboard import _market_payload

    gate = Barrier(4, timeout=5)

    def read(*args, **kwargs):
        gate.wait()
        return []

    with (
        patch("src.frontend.service.home_dashboard.QuoteService") as quotes,
        patch("src.frontend.service.home_dashboard._news_items", read),
    ):
        quotes.return_value.indices.side_effect = read
        quotes.return_value.sector_rankings.side_effect = read
        quotes.return_value.watchlist_quotes.side_effect = read
        assert _market_payload(False)["errors"] == []


def test_shared_observation_refresh_and_runtime_scope(client, monkeypatch):
    from src.frontend.service.shared_observations import shared_observation

    calls = []

    def source():
        calls.append(True)
        return {"revision": len(calls)}

    assert shared_observation("refresh-test", source)["revision"] == 1
    assert shared_observation("refresh-test", source)["revision"] == 1
    assert shared_observation("refresh-test", source, refresh=True)["revision"] == 2
    monkeypatch.setenv("ALL_IN_ONE_PAGE_CACHE_EPOCH", "new-test-runtime")
    assert shared_observation("refresh-test", source)["revision"] == 3


@pytest.mark.parametrize("hide", [False, True])
def test_table_wire_preserves_formatting_and_styles(hide):
    import gradio as gr

    from src.frontend.table_wire import styled_table

    styled = (
        pd.DataFrame({"value": [-2.3, 4.1], "other": [1, 2]})
        .style.format({"value": "{:+.2f}%"})
        .map(lambda value: "color:red" if value < 0 else "color:green")
    )
    if hide:
        styled = styled.hide(["other"], axis="columns")
    table = gr.Dataframe(interactive=False)
    assert table.postprocess(styled).model_dump() == table.postprocess(styled_table(styled)).model_dump()
