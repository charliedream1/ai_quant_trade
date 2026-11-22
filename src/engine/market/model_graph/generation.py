"""Graph-specific text-only CLI profile; existing strict provider contracts stay intact."""

import json
import math
import subprocess
from pathlib import Path
from time import perf_counter
from typing import Any

from json_repair import repair_json

from src.agent.providers.config import provider_config
from src.agent.providers.events import collect_response
from src.agent.providers.native import runner_for
from src.agent.providers.registry import require_native
from src.core.env_file import resolve_env_value
from src.core.paths import SOURCE_ROOT
from src.core.process_env import process_environment
from src.core.redaction import redact_text
from src.observability.instrumentation import traced

from .config import config
from .transport import text_only_process


def availability():
    try:
        workbuddy_paths()
        configured = True
    except (OSError, ValueError):
        configured = False
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
        cfg = config()
        return complete_workbuddy(
            prompt,
            model=self.selection.get("model_name") or cfg["workbuddy"]["model"],
            directory=self.directory,
            cancelled=self.cancelled,
            system_prompt=cfg["prompts"]["system"],
        )


def workbuddy_paths():
    """Resolve the configured desktop profile without exposing its paths to callers."""
    cfg = config()["workbuddy"]
    paths = tuple(
        Path(resolve_env_value(cfg[key])) for key in ("installation_env", "authentication_env", "product_env")
    )
    installation, authentication, product = paths
    if (
        not all(path.is_absolute() for path in paths)
        or not (installation / "WorkBuddy.exe").is_file()
        or not (installation / "resources/app.asar").is_file()
        or not authentication.is_file()
        or not product.is_file()
    ):
        raise ValueError(cfg["messages"]["configuration"])
    return installation, authentication, product


def complete_workbuddy(prompt, *, model, directory, cancelled, system_prompt, max_output_chars=None):
    """Run the shared text-only desktop CLI with a private working profile."""
    cfg = config()["workbuddy"]
    limits = dict(config()["limits"])
    if max_output_chars is not None:
        limits["output_chars"] = min(limits["output_chars"], max_output_chars)
    installation, authentication, product = workbuddy_paths()
    try:
        if product.stat().st_size > cfg["catalog_max_bytes"]:
            raise ValueError
        catalogue = json.loads(product.read_text(encoding="utf-8-sig"))["models"]
        if not isinstance(catalogue, list):
            raise ValueError
    except (OSError, KeyError, ValueError, TypeError):
        raise ValueError(cfg["messages"]["catalogue"]) from None
    if (
        not model
        or model.startswith("-")
        or any(ord(char) < 32 for char in model)
        or not any(
            isinstance(item, dict)
            and item.get("id") == model
            and not item.get("hidden")
            and item.get("enabled") is not False
            for item in catalogue
        )
    ):
        raise ValueError(cfg["messages"]["model"])
    if cancelled():
        raise InterruptedError("WorkBuddy request cancelled")
    environment = process_environment("document")
    environment["ELECTRON_RUN_AS_NODE"] = "1"
    helper = SOURCE_ROOT / "src/agent/providers/workbuddy_login.cjs"
    try:
        login = subprocess.run(
            [str(installation / "WorkBuddy.exe"), str(helper), str(installation), str(authentication)],
            env=environment,
            capture_output=True,
            timeout=cfg["authentication_timeout_seconds"],
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        raise ValueError(cfg["messages"]["login"]) from None
    if login.returncode:
        raise ValueError(cfg["messages"]["login"])
    try:
        account = json.loads(login.stdout)
        token, uid = account["auth"]["accessToken"], account["account"]["uid"]
        if not isinstance(token, str) or not token or not isinstance(uid, str) or not uid:
            raise ValueError
    except (ValueError, TypeError, KeyError):
        raise ValueError(cfg["messages"]["login"]) from None
    if cancelled():
        raise InterruptedError("WorkBuddy request cancelled")
    profile = directory / "cli_profile"
    profile.mkdir(parents=True, exist_ok=True)
    environment.update(
        CODEBUDDY_AUTH_TOKEN=token,
        CODEBUDDY_CUSTOM_HEADERS="X-User-Id: " + uid,
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
        system_prompt,
    ]
    started = perf_counter()

    def observe(event):
        if event.get("type") == "system" and event.get("subtype") == "init":
            if event.get("model") != model:
                raise ValueError("WorkBuddy initialized an unexpected model")
            (directory / "capabilities.json").write_text(
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

    final: dict[str, Any] = text_only_process(command, environment, profile, prompt, limits, cancelled, observe)
    if final.get("is_error") or not isinstance(final.get("result"), str):
        raise ValueError(cfg["messages"]["response"])
    if set(final.get("modelUsage", {})) != {model}:
        raise ValueError("WorkBuddy returned an unexpected model identity")
    if len(final["result"]) > limits["output_chars"]:
        raise ValueError("WorkBuddy completion exceeds output budget")
    raw_usage = final.get("usage")
    usage = {}
    if isinstance(raw_usage, dict):
        for key in cfg["usage_fields"]:
            value = raw_usage.get(key)
            if type(value) is int and value >= 0:
                usage[key] = value
    cost = final.get("total_cost_usd")
    if not isinstance(cost, (int, float)) or isinstance(cost, bool) or not math.isfinite(cost) or cost < 0:
        cost = None
    return {
        "text": redact_text(final["result"], secrets=(token,)),
        "model": model,
        "backend": "workbuddy",
        "usage": usage,
        "reported_cost": cost,
        "duration_ms": round((perf_counter() - started) * 1000),
    }
