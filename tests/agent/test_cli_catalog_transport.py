"""Exercise real subprocess metadata framing, timeout and output bounds."""

import os
import sys

import pytest

from src.agent.cli_catalog_transport import metadata


def test_native_rpc_only_initializes_and_lists(tmp_path):
    script = tmp_path / "metadata.py"
    script.write_text(
        """import json,sys
request=json.loads(sys.stdin.readline())
assert request['method']=='initialize'
sys.stdout.write(json.dumps({'id':1,'result':{}})+'\\n');sys.stdout.flush()
assert json.loads(sys.stdin.readline())['method']=='initialized'
request=json.loads(sys.stdin.readline())
assert request['method']=='model/list'
sys.stdout.write(json.dumps({'id':2,'result':{'data':[{'id':'declared','model':'declared-model'}]}})+'\\n');sys.stdout.flush()
sys.stdin.read()
""",
        encoding="utf-8",
    )
    value = metadata(
        [sys.executable, "-u", str(script)],
        dict(os.environ),
        tmp_path,
        {"max_bytes": 4096, "timeout_seconds": 3, "max_models": 20},
        rpc=True,
    )
    assert value["data"][0]["model"] == "declared-model"


def test_metadata_timeout_stops_owned_process(tmp_path):
    with pytest.raises(TimeoutError):
        metadata(
            [sys.executable, "-c", "import time; time.sleep(30)"],
            dict(os.environ),
            tmp_path,
            {"max_bytes": 4096, "timeout_seconds": 0.2},
        )


def test_metadata_output_is_bounded(tmp_path):
    with pytest.raises(ValueError, match="limit"):
        metadata(
            [sys.executable, "-c", "import sys; sys.stdout.write('x'*10000)"],
            dict(os.environ),
            tmp_path,
            {"max_bytes": 200, "timeout_seconds": 3},
        )


def test_metadata_respects_page_cancellation(tmp_path, monkeypatch):
    from src.agent import cli_catalog_transport

    monkeypatch.setattr(cli_catalog_transport, "stream_cancelled", lambda: True)
    with pytest.raises(InterruptedError):
        metadata(
            [sys.executable, "-c", "import time; time.sleep(30)"],
            dict(os.environ),
            tmp_path,
            {"max_bytes": 4096, "timeout_seconds": 3},
        )
