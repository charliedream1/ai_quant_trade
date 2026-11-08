import json
import socket
import subprocess
import sys
import threading
from pathlib import Path
from time import monotonic

import pytest
import uvicorn
from fastapi.testclient import TestClient


@pytest.fixture()
def keyword_model(monkeypatch):
    """Controlled keyword planning; answer generation keeps the existing mock client."""
    from src.agent.llm_client import LLMClient
    from src.knowledge.config import knowledge_config

    original = LLMClient.complete
    prefix = knowledge_config()["search"]["planner_prompt"].splitlines()[0]

    def complete(self, prompt, *args, **kwargs):
        if prompt.startswith(prefix):
            return {
                "text": json.dumps({"keywords": ["动量", "回撤", "路由回归"], "sufficient": True}, ensure_ascii=False),
                "model": "fixture-planner",
            }
        return original(self, prompt, *args, **kwargs)

    monkeypatch.setattr(LLMClient, "complete", complete)


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db_path = tmp_path / "all_in_one_test.db"
    data_dir = tmp_path / "data"
    monkeypatch.setenv("ALL_IN_ONE_DB_PATH", str(db_path))
    monkeypatch.setenv("ALL_IN_ONE_DATA_DIR", str(data_dir))
    monkeypatch.setenv("ALL_IN_ONE_DATA_MODE", "mock")
    monkeypatch.setenv("ALL_IN_ONE_ACCESS_MODE", "local")
    monkeypatch.setenv("ALL_IN_ONE_HELP_DOCS_AUTO_BUILD", "false")
    monkeypatch.setenv("GRADIO_TEMP_DIR", str(tmp_path / "gradio_uploads"))

    import src.core.config as config_module
    import src.core.env_file as env_module
    from src.core.database import Database

    config_module._SETTINGS = None
    monkeypatch.setattr(env_module, "ENV_FILE", tmp_path / ".llm_env")
    Database.reset_instance()

    from src.api.app import create_app

    app = create_app()
    with TestClient(app) as test_client:
        yield test_client

    Database.reset_instance()
    config_module._SETTINGS = None


@pytest.fixture()
def cli_command(client):
    """Independent CLI processes share one isolated real HTTP listener."""
    root = Path(__file__).resolve().parents[1]
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    server = uvicorn.Server(uvicorn.Config(client.app, log_level="error", lifespan="off", access_log=False))
    thread = threading.Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
    thread.start()
    started = monotonic()
    while not server.started:
        assert thread.is_alive() and monotonic() - started < 10
        threading.Event().wait(0.01)
    address = f"http://127.0.0.1:{listener.getsockname()[1]}"

    def invoke(*args, expected=0, stream=False, timeout=60):
        run = subprocess.run(
            [
                sys.executable,
                "egs/entrypoints/cli.py",
                "--base-url",
                address,
                "--format",
                "jsonl" if stream else "json",
                *map(str, args),
            ],
            cwd=root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=timeout,
        )
        assert run.returncode == expected, (args, run.returncode, run.stdout, run.stderr)
        assert "\x1b[" not in run.stdout
        return [json.loads(line) for line in run.stdout.splitlines()] if stream else json.loads(run.stdout)

    invoke.base_url = address
    try:
        yield invoke
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        listener.close()
        assert not thread.is_alive(), "CLI HTTP test service did not stop"
