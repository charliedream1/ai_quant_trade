"""Real-model acceptance transport; never persists desktop login credentials."""

import json
import os
import subprocess
import threading
import time
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from loguru import logger

from src.core.process_control import stop_process_tree
from src.core.process_env import process_environment


def desktop_login(installation: Path, authentication: Path) -> dict:
    """Read the existing login through WorkBuddy's own codec, only into memory."""
    environment = process_environment("document")
    environment["ELECTRON_RUN_AS_NODE"] = "1"
    result = subprocess.run(
        [
            str(installation / "WorkBuddy.exe"),
            str(Path(__file__).with_name("workbuddy_login.cjs")),
            str(installation),
            str(authentication),
        ],
        env=environment,
        capture_output=True,
        timeout=15,
        check=True,
    )
    return dict(json.loads(result.stdout))


def cli_environment(profile: Path, login: dict, product: Path) -> dict[str, str]:
    """Private process environment; no external configuration is changed."""
    environment = process_environment("document")
    environment.update(
        ELECTRON_RUN_AS_NODE="1",
        CODEBUDDY_FORCE_LITE_WB_BUNDLE="1",
        CODEBUDDY_CONFIG_DIR=str(profile),
        WORKBUDDY_CONFIG_DIR=str(profile),
        DISABLE_AUTOUPDATER="1",
        DISABLE_TELEMETRY="1",
        ACC_PRODUCT_CONFIG_PATH=str(product),
    )
    environment["CODEBUDDY_AUTH_TOKEN"] = login["auth"]["accessToken"]
    environment["CODEBUDDY_CUSTOM_HEADERS"] = "X-User-Id: " + login["account"]["uid"]
    return environment


class Hy3Runtime:
    def __init__(self, policy: dict, directory: Path):
        self.policy, self.directory = policy, directory
        settings = policy["runtime"]
        self.installation = Path(os.environ[settings["installation_env"]])
        self.authentication = Path(os.environ[settings["authentication_env"]])
        self.product = Path(os.environ[settings["product_env"]])
        model = next(
            item
            for item in json.loads(self.product.read_text(encoding="utf-8"))["models"]
            if item["id"] == policy["model"]
        )
        if model["id"] != "hy3" or not str(model.get("credits", "")).startswith("x0.00"):
            raise ValueError("Hy3 is not marked free in the current WorkBuddy model catalog")
        self.login = desktop_login(self.installation, self.authentication)
        self.profile = directory / "cli_profile"
        self.profile.mkdir(parents=True, exist_ok=True)
        self.environment = cli_environment(self.profile, self.login, self.product)
        self.records: list[dict] = []
        self.lock = threading.Lock()

    def complete(self, prompt: str) -> dict:
        with self.lock:
            return self._complete(prompt)

    def _complete(self, prompt: str) -> dict:
        settings = self.policy["runtime"]
        command = [
            str(self.installation / "WorkBuddy.exe"),
            str(self.installation / "resources/app.asar/cli/bin/codebuddy"),
            "--print",
            "--output-format",
            "stream-json",
            "--verbose",
            "--model",
            self.policy["model"],
            "--tools=",
            "--disallowedTools",
            ",".join(settings["denied_tools"]),
            "--strict-mcp-config",
            "--mcp-config",
            '{"mcpServers":{}}',
            "--setting-sources=",
            "--no-session-persistence",
            "--max-turns",
            str(settings["max_turns"]),
            "--system-prompt",
            settings["system_prompt"],
        ]
        started = time.perf_counter()
        with subprocess.Popen(
            command,
            cwd=self.profile,
            env=self.environment,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        ) as process:
            try:
                output, _ = process.communicate(prompt.encode("utf-8"), timeout=settings["timeout_seconds"])
            except subprocess.TimeoutExpired:
                stop_process_tree(process)
                process.communicate()
                raise RuntimeError("WorkBuddy hy3 request timed out") from None
        events = []
        for line in output.decode("utf-8").splitlines():
            try:
                events.append(json.loads(line))
            except ValueError:
                continue
        for event in events:
            if event.get("type") == "assistant" and any(
                item.get("type") == "tool_use" for item in event.get("message", {}).get("content", [])
            ):
                raise RuntimeError("Native tool use occurred; generation rejected")
            if event.get("subtype") == "init" and event.get("model") != "hy3":
                raise RuntimeError("Unexpected model selected")
        final: dict[str, Any] = next((item for item in reversed(events) if item.get("type") == "result"), {})
        if process.returncode or final.get("is_error") or not final.get("result"):
            raise RuntimeError("WorkBuddy hy3 did not return a successful text completion")
        usage = final.get("modelUsage", {})
        if set(usage) != {"hy3"}:
            raise RuntimeError("Unexpected billing model in response")
        record = {
            "index": len(self.records) + 1,
            "model": "hy3",
            "prompt": prompt,
            "text": final["result"],
            "duration_ms": round((time.perf_counter() - started) * 1000),
            "usage": final.get("usage", {}),
            "model_usage": usage,
            "cost_usd_reported": final.get("total_cost_usd"),
            "native_tool_calls": 0,
            "session_id": final.get("session_id"),
        }
        self.records.append(record)
        self.directory.joinpath("model-calls.json").write_text(
            json.dumps(self.records, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        logger.info("Hy3 real completion | call={} duration_ms={} model=hy3", record["index"], record["duration_ms"])
        return {"model": "hy3", "text": record["text"], "usage": record["usage"]}


@contextmanager
def openai_bridge(runtime: Hy3Runtime):
    """A loopback adapter so the application's real LLMClient remains unchanged."""

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):  # noqa: N802
            try:
                request = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                if request.get("model") != "hy3":
                    raise ValueError("Only hy3 is allowed")
                result = runtime.complete("\n\n".join(message["content"] for message in request["messages"]))
                body = {
                    "model": "hy3",
                    "choices": [{"message": {"role": "assistant", "content": result["text"]}}],
                    "usage": result["usage"],
                }
                status = 200
            except Exception as exc:
                logger.error("Hy3 bridge failed | error={}", type(exc).__name__)
                body, status = {"error": {"message": type(exc).__name__}}, 502
            raw = json.dumps(body, ensure_ascii=False).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def log_message(self, *args):
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/v1"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
