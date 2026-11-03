"""Opt-in economical live checks; secrets never enter acceptance artifacts."""

import argparse
import json
import os
from pathlib import Path
from time import perf_counter

import yaml
from dotenv import dotenv_values
from loguru import logger

from src.agent.llm_client import LLMClient
from src.agent.providers import provider_catalog
from src.agent.providers.native import NativeCliRunner
from src.agent.research_protocol import run_role
from src.agent.research_team import CONFIG_PATH
from src.core.config import PROJECT_ROOT
from src.core.repository import Repository
from src.core.timeutil import utc_now_iso
from src.strategy.codex_cli import CodexCliRunner


def main(output: Path, credentials: str, api_only: bool = False):
    output.mkdir(parents=True, exist_ok=True)
    config = yaml.safe_load((PROJECT_ROOT / "egs/agent_provider_validation.yaml").read_text(encoding="utf-8"))
    summary = {"scope": "real_model_with_explicitly_missing_financial_evidence_no_performance_claim", "checks": []}
    summary["providers"] = provider_catalog(probe=not api_only)
    values = dotenv_values(credentials)
    os.environ["ALL_IN_ONE_ACCEPTANCE_MODEL_KEY"] = str(values.get("LLM_API_KEY") or values.get("OPENAI_API_KEY") or "")
    repo = Repository()
    model = repo.insert(
        "llm_models",
        {
            "name": "isolated-live-provider-acceptance",
            "model_name": values["LLM_MODEL_NAME"],
            "base_url": values.get("LLM_BASE_URL") or values["OPENAI_BASE_URL"],
            "api_key_env": "ALL_IN_ONE_ACCEPTANCE_MODEL_KEY",
            "enabled": 1,
            "is_default": 1,
            "api_key": "",
            "purpose": "isolated protocol acceptance",
            "created_at": utc_now_iso(),
            "updated_at": utc_now_iso(),
            "max_tokens": config["max_tokens"],
        },
    )
    llm = LLMClient(repo=repo)
    role_config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    role_config["max_turns"] = config["max_turns"]
    evidence = dict.fromkeys(role_config["roles"][config["role"]]["required_evidence"], config["evidence"])
    events = []
    started = perf_counter()
    try:
        result = run_role(
            config["role"],
            config["objective"],
            evidence,
            {},
            role_config,
            llm,
            selection={"backend": "api", "model_id": model["id"], "enable_thinking": False},
            emit=lambda kind, value: events.append({"kind": kind, "data": value}),
        )
        assert result["verdict"] in {"watch", "reject"}, result
        summary["checks"].append(
            {
                "backend": "api",
                "status": "passed",
                "result": result,
                "duration_ms": round((perf_counter() - started) * 1000),
            }
        )
    except Exception as exc:
        summary["checks"].append({"backend": "api", "status": "failed", "error": str(exc)})
    finally:
        llm.session.close()
        (output / "api-events.json").write_text(json.dumps(events, ensure_ascii=False, indent=2), encoding="utf-8")
    for backend in () if api_only else ("codex", "trae"):
        try:
            runner = CodexCliRunner(output, 60) if backend == "codex" else NativeCliRunner(backend, output, 60)
            result = runner.run_once(config["native_prompt"])
            summary["checks"].append(
                {
                    "backend": backend,
                    "scope": "ordinary_conversation_only_not_strict_research",
                    "status": result.status,
                    "text": result.text,
                    "error": result.error,
                    "duration_ms": result.duration_ms,
                }
            )
            (output / (backend + "-events.json")).write_text(
                json.dumps(result.events, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception as exc:
            summary["checks"].append({"backend": backend, "status": "failed", "error": str(exc)})
    (output / "live-summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Live provider checks finished; no tuning or automatic retries")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--credentials", required=True)
    parser.add_argument("--api-only", action="store_true")
    args = parser.parse_args()
    main(args.output.resolve(), args.credentials, args.api_only)
