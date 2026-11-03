"""Isolated fixture UI service; environment must be set before importing the app factory."""

import json
from threading import Event

import uvicorn
from conftest import FIXTURE, FixtureLLM, seed_workflow_data

import src.agent_strategies.session as session_module
from src.alpha_mining.config import digest
from src.api.app import app
from src.core.config import PROJECT_ROOT, get_settings


class BrowserLLM(FixtureLLM):
    def complete(self, *args, **kwargs):
        Event().wait(FIXTURE["browser"]["model_delay_seconds"])
        return super().complete(*args, **kwargs)


def main():
    runtime = (PROJECT_ROOT / FIXTURE["browser"]["runtime"]).resolve()
    assert get_settings().db_path.resolve() == runtime / "platform.db", "Browser service must use the task database"
    session_module.LLMClient = BrowserLLM
    data = seed_workflow_data()
    snapshot = {
        "history": data["history"],
        "metadata": data["metadata"],
        "market": "CN",
        "source": "explicit-browser-fixture",
        "is_mock": True,
        "limitations": ["explicit_fixture_not_real_market_acceptance"],
    }
    identity = digest(snapshot)
    directory = get_settings().data_dir / "pipeline_snapshots"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / (identity[:24] + ".json")).write_text(json.dumps(snapshot, ensure_ascii=False), encoding="utf-8")
    (runtime / "browser.json").write_text(
        json.dumps({"snapshot_id": identity, **data}, ensure_ascii=False), encoding="utf-8"
    )
    uvicorn.run(app, host="127.0.0.1", port=FIXTURE["browser"]["port"], access_log=False)


if __name__ == "__main__":
    main()
