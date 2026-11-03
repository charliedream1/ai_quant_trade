"""Isolated browser service: real UI/domain/ledger, explicitly labelled fixture LLM."""

import json
import os
import sys
from pathlib import Path

import uvicorn

ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ROOT / ".pytest_tmp/alpha-mining-20261027/browser-runtime-release"


def main():
    RUNTIME.mkdir(parents=True, exist_ok=True)
    os.environ.update(
        ALL_IN_ONE_DATA_DIR=str(RUNTIME / "data"),
        ALL_IN_ONE_DB_PATH=str(RUNTIME / "platform.db"),
        ALL_IN_ONE_DATA_MODE="mock",
        ALL_IN_ONE_HELP_DOCS_AUTO_BUILD="false",
        GRADIO_TEMP_DIR=str(RUNTIME / "uploads"),
    )
    sys.path.insert(0, str(Path(__file__).parent))
    from conftest import FIXTURE, FixtureLLM, market_payload

    import src.alpha_mining.agents as agents
    from src.alpha_mining.service import AlphaService
    from src.api.app import create_app
    from src.core.repository import Repository
    from src.core.timeutil import utc_now_iso

    agents.LLMClient = FixtureLLM
    app = create_app()
    service = AlphaService()
    repo = Repository()
    if not repo.list("llm_models"):
        repo.insert(
            "llm_models", {**FIXTURE["browser_model"], "created_at": utc_now_iso(), "updated_at": utc_now_iso()}
        )
    fixtures = [
        ("market", market_payload.__wrapped__()),
        ("documents", {"documents": FIXTURE["documents"], "is_mock": True, "source": "explicit_test_fixture"}),
        ("macro", {"observations": FIXTURE["macro"], "is_mock": True, "source": "explicit_test_fixture"}),
    ]
    if not service.store.list("alpha_datasets"):
        rows = [service.register_dataset("界面验收 " + kind, kind, payload) for kind, payload in fixtures]
        for kind, payload in fixtures:
            (RUNTIME / (kind + ".json")).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        (RUNTIME / "datasets.json").write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
    uvicorn.run(app, host="127.0.0.1", port=8897, access_log=False)


if __name__ == "__main__":
    main()
