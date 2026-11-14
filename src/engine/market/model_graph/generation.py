"""Graph-specific text-only CLI profile; existing strict provider contracts stay intact."""

import json
import subprocess
from pathlib import Path
from time import perf_counter
from typing import Any

from json_repair import repair_json

from src.agent.providers.config import provider_config
from src.agent.providers.events import collect_response
from src.agent.providers.native import runner_for
from src.agent.providers.registry import require_native
from src.core.config import PROJECT_ROOT
from src.core.env_file import resolve_env_value
from src.core.process_env import process_environment
from src.observability.instrumentation import traced

from .config import config
from .transport import text_only_process


def availability():
    cfg = config()
    buddy = cfg["workbuddy"]
    configured = all(resolve_env_value(buddy[key]) for key in ("installation_env", "authentication_env", "product_env"))
    result = [
        {
            "backend": "workbuddy",
            "available": bool(configured),
            "network_checked": False,
            "reason": "Explicit existing WorkBuddy paths required"
            if not configured
            else "Configured; runtime preflight required",
        }
    ]
    try:
        state = require_native({"backend": "qoder"})
        result.append({"backend": "qoder", "available": True, "version": state.get("version", "")})
    except (ValueError, OSError, subprocess.SubprocessError):
        result.append(
            {"backend": "qoder", "available": False, "reason": "Verified text-only Qoder profile unavailable"}
        )
    return result


class GraphGeneration:
    def __init__(self, selection, directory, cancelled):
        self.selection, self.directory, self.cancelled = selection, directory, cancelled
        self.calls = []

    @traced("llm.relation_graph_cli", "generation")
    def complete(self, prompt):
        if self.cancelled():
            raise InterruptedError("Graph research cancelled")
        if self.selection["backend"] == "workbuddy":
            result = self._workbuddy(prompt)
        elif self.selection["backend"] == "qoder":
            state = require_native(self.selection)
            runner = runner_for("qoder", self.directory, config()["limits"]["model_seconds"])
            stream = runner.stream(
                prompt,
                model=self.selection.get("model_name", ""),
                reasoning_effort=self.selection.get("reasoning_effort", ""),
                stdin_prompt=True,
                cancelled=self.cancelled,
            )
            try:
                result = collect_response(
                    stream, "qoder", provider_config(), None, self.cancelled, config()["limits"]["output_chars"], []
                )
                result["backend"] = "qoder"
                result["provider_version"] = state.get("version")
            finally:
                stream.close()
        else:
            raise ValueError("Graph generation requires an available text-only CLI profile")
        self.calls.append({key: value for key, value in result.items() if key != "text"})
        if self.cancelled():
            raise InterruptedError("Graph research cancelled")
        value = repair_json(result["text"], return_objects=True)
        if not isinstance(value, dict):
            raise ValueError("Graph model response must contain an ordinary JSON object")
        (self.directory / f"completion-{len(self.calls)}.json").write_text(
            json.dumps(value, ensure_ascii=False), encoding="utf-8"
        )
        return value

    def _workbuddy(self, prompt):
        cfg, limits = config()["workbuddy"], config()["limits"]
        installation = Path(resolve_env_value(cfg["installation_env"]))
        authentication = Path(resolve_env_value(cfg["authentication_env"]))
        product = Path(resolve_env_value(cfg["product_env"]))
        if not all(path.is_absolute() and path.exists() for path in (installation, authentication, product)):
            raise ValueError("WorkBuddy paths must be explicitly configured existing absolute paths")
        model = self.selection.get("model_name") or cfg["model"]
        catalogue = json.loads(product.read_text(encoding="utf-8")).get("models", [])
        if not any(item.get("id") == model for item in catalogue):
            raise ValueError("Requested WorkBuddy model is not in its installed catalogue")
        environment = process_environment("document")
        environment["ELECTRON_RUN_AS_NODE"] = "1"
        helper = PROJECT_ROOT / "src/agent/providers/workbuddy_login.cjs"
        login = subprocess.run(
            [str(installation / "WorkBuddy.exe"), str(helper), str(installation), str(authentication)],
            env=environment,
            capture_output=True,
            timeout=limits["model_seconds"],
            check=False,
        )
        if login.returncode:
            raise ValueError("Existing WorkBuddy login could not be read using its native codec")
        account = json.loads(login.stdout)
        profile = self.directory / "cli_profile"
        profile.mkdir(parents=True, exist_ok=True)
        environment.update(
            CODEBUDDY_AUTH_TOKEN=account["auth"]["accessToken"],
            CODEBUDDY_CUSTOM_HEADERS="X-User-Id: " + account["account"]["uid"],
            CODEBUDDY_CONFIG_DIR=str(profile),
            WORKBUDDY_CONFIG_DIR=str(profile),
            CODEBUDDY_FORCE_LITE_WB_BUNDLE="1",
            DISABLE_AUTOUPDATER="1",
            DISABLE_TELEMETRY="1",
            ACC_PRODUCT_CONFIG_PATH=str(product),
        )
        environment["ALL_IN_ONE_PROVIDER_DEPTH"] = str(provider_config()["defaults"]["max_provider_depth"])
        command = [
            str(installation / "WorkBuddy.exe"),
            str(installation / "resources/app.asar/cli/bin/codebuddy"),
            *cfg["arguments"],
            "--model",
            model,
            "--system-prompt",
            config()["prompts"]["system"],
        ]
        started = perf_counter()

        def observe(event):
            if event.get("type") == "system" and event.get("subtype") == "init":
                (self.directory / "capabilities.json").write_text(
                    json.dumps(
                        {
                            "tools": [
                                item if isinstance(item, str) else item.get("name", "unknown")
                                for item in event.get("tools", [])
                            ],
                            "model": event.get("model"),
                            "skills_count": len(event["skills"]) if "skills" in event else None,
                            "plugins_count": len(event["plugins"]) if "plugins" in event else None,
                            "mcp_count": len(event.get("mcp_servers", [])),
                        }
                    ),
                    encoding="utf-8",
                )

        final: dict[str, Any] = text_only_process(
            command, environment, profile, prompt, limits, self.cancelled, observe
        )
        if final.get("is_error") or not isinstance(final.get("result"), str):
            raise ValueError("WorkBuddy returned no successful graph response")
        if set(final.get("modelUsage", {})) != {model}:
            raise ValueError("WorkBuddy returned an unexpected model identity")
        if len(final["result"]) > limits["output_chars"]:
            raise ValueError("Graph completion exceeds output budget")
        return {
            "text": final["result"],
            "model": model,
            "backend": "workbuddy",
            "usage": final.get("usage"),
            "reported_cost": final.get("total_cost_usd"),
            "duration_ms": round((perf_counter() - started) * 1000),
        }
