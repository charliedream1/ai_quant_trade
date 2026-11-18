"""Current-observation commentary is distinct from strict historical research roles."""

import os

from src.agent.providers.registry import require_native
from src.core.config import get_settings
from src.core.page_analysis_snapshot import analysis_config
from src.observability.instrumentation import traced
from src.strategy.codex_cli import CodexCliRunner


def current_commentary(task, backend):
    return backend == "codex" and analysis_config()["presets"][task]["method"] != "experiment"


def capability(task, selection):
    if get_settings().data_mode == "mock" and os.environ.get("ALL_IN_ONE_ENABLE_REAL_CLI", "").lower() not in {
        "1",
        "true",
        "yes",
    }:
        from .config import insight_config

        raise ValueError(insight_config()["messages"]["mock_cli_disabled"])
    if not current_commentary(task, selection["backend"]):
        return require_native(selection)
    state = require_native(selection, strict=False)
    state["research_mode"] = "current_observation_commentary"
    state["historical_validation"] = False
    return state


@traced("llm.page_commentary", "generation")
def commentary(prompt, payload, cfg, emit):
    from .store import InsightStore

    capability(payload["page_task"], payload)
    runner = CodexCliRunner(
        project_root=InsightStore().directory(payload["page_run_id"]),
        access_mode="read-only",
        timeout_seconds=cfg["defaults"]["read_timeout"],
    )
    text = []
    size = 0
    for event in runner.stream(
        prompt,
        model=payload.get("model_name", ""),
        reasoning_effort=payload.get("reasoning_effort", ""),
        stdin_prompt=True,
        cancelled=payload.get("_cancelled"),
    ):
        if event.kind == "error":
            raise ValueError(event.text)
        emit(event.kind, event.text)
        if event.kind == "message":
            size += len(event.text)
            if size > cfg["defaults"]["max_output_chars"]:
                raise ValueError("Page commentary exceeds response limit")
            text.append(event.text)
    if not text:
        raise ValueError("CLI returned no commentary")
    return "".join(text)
