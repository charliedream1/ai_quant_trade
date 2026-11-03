"""Execute one persisted Skill report, with actual stage and backend events."""

import json
from time import monotonic
from typing import Any

from loguru import logger

from src.core.timeutil import utc_now_iso

from .backend import generate_text, validate_backend
from .config import load_skill
from .evidence import EvidenceCollector
from .rendering import render_report
from .research import run_research
from .store import InsightStore


def execute(run: dict[str, Any], store: InsightStore, config: dict[str, Any], cancelled=None) -> None:
    started = monotonic()
    directory = store.directory(run["run_id"])

    def emit(kind: str, text: str, data: Any = None) -> None:
        if cancelled and cancelled():
            raise ValueError("洞察研究已取消")
        if monotonic() - started > config["defaults"]["deadline_seconds"]:
            raise TimeoutError(config["messages"]["timeout"])
        store.append(run["run_id"], kind, text, data)

    def save_json(name: str, value: Any) -> None:
        (directory / name).write_text(
            json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2), encoding="utf-8"
        )

    def save_prompt(text: str) -> None:
        (directory / "prompt.txt").write_text(text, encoding="utf-8")

    try:
        payload = run["request"]
        save_json("request.json", payload)
        run["model"] = validate_backend(payload, config)
        payload["_provider_snapshot"] = run["model"]
        save_json("request.json", payload)
        skill, resources = load_skill(payload["kind"], config)
        run["skills"] = {name: item["sha256"] for name, item in resources.items()}
        emit("skill", config["messages"]["skill_loaded"], run["skills"])
        emit("stage", config["messages"]["collecting"])
        evidence = EvidenceCollector(payload, config, emit).collect()
        save_json("evidence.json", evidence)
        emit("stage", config["messages"]["collected"], {"sources": len(evidence["sources"]), "gaps": evidence["gaps"]})
        report = run_research(
            payload,
            evidence,
            skill,
            resources,
            config,
            emit,
            save_prompt,
            lambda prompt, payload, cfg, callback: generate_text(
                prompt, {**payload, "_cancelled": cancelled}, cfg, callback
            ),
        )
        emit("stage", config["messages"]["rendering"])
        save_json("report.json", report)
        (directory / "report.html").write_text(render_report(report, evidence, run, config), encoding="utf-8")
        run.update(status="partial", title=report["title"], gaps=evidence["gaps"] + report["missing"])
        emit("artifact", config["messages"]["saved"], {"file": "report.html"})
    except Exception as exc:
        run.update(status="failed", error=str(exc))
        store.append(run["run_id"], "error", str(exc))
        logger.warning("insight report failed | run={} error={}", run["run_id"], exc)
    finally:
        run.update(finished_at=utc_now_iso(), duration_ms=round((monotonic() - started) * 1000))
        store.save(run)
