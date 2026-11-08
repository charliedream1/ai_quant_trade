"""Real browser helpers; strategy actions use visible Gradio controls."""

from __future__ import annotations

import json
import re
import subprocess
import sys
import traceback
from collections.abc import Callable
from pathlib import Path
from time import perf_counter
from typing import Any

import requests
import yaml
from loguru import logger
from playwright.sync_api import Page, expect

from src.core.config import PROJECT_ROOT
from src.strategy.composition.validation import compile_plan, digest


class GraphBrowser:
    def __init__(self, page: Page, config: dict, output: Path):
        self.page, self.config, self.output = page, config, output
        self.base = config["base_url"].rstrip("/")
        self.frame = page.frame_locator("iframe.workspace-frame.active")
        self.results: list[dict[str, Any]] = []
        self.errors: list[dict[str, str]] = []
        self.http_errors: list[str] = []
        self.external_http_errors: list[str] = []
        self.run_ids: list[str] = []
        self.output.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.trust_env = False
        page.on("pageerror", lambda error: self.errors.append({"kind": "pageerror", "message": str(error)}))
        page.on("console", self.console)
        page.on("response", self.response)

    def console(self, message):
        if message.type in {"error", "warning"}:
            self.errors.append(
                {"kind": message.type, "message": message.text, "url": str(message.location.get("url", ""))}
            )

    def response(self, response):
        if response.status >= 400 and response.url.startswith(self.base):
            self.http_errors.append(f"{response.status} {response.url}")
        elif response.status >= 400:
            self.external_http_errors.append(f"{response.status} {response.url}")

    def api(self, path: str):
        response = self.session.get(self.base + "/api/v1" + path, timeout=30)
        response.raise_for_status()
        value = response.json()
        assert value["code"] == 0, value
        return value["data"]

    def save(self, name: str, value: Any):
        (self.output / name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")

    def scenario(self, name: str, action: Callable[[], Any]):
        started = perf_counter()
        try:
            detail = action()
            result = {"name": name, "passed": True, "detail": detail}
        except Exception as exc:
            result = {"name": name, "passed": False, "error": str(exc), "traceback": traceback.format_exc()}
            logger.warning("Browser scenario {}: {}", name, exc)
            try:
                self.save(
                    name + "-state.json",
                    {
                        "graph": self.frame.locator(".graph-breadcrumb").inner_text(),
                        "footer": self.frame.locator(".graph-footer").inner_text(),
                        "yaml": self.textbox("方案定义（YAML）").input_value(timeout=500)
                        if self.textbox("方案定义（YAML）").count()
                        else None,
                        "nodes": self.nodes().evaluate_all("es=>es.map(e=>e.dataset.id)"),
                    },
                )
            except Exception as capture_error:
                result["state_capture_error"] = str(capture_error)
        result["seconds"] = round(perf_counter() - started, 3)
        shot = name + ".jpg"
        try:
            self.page.screenshot(path=str(self.output / shot), type="jpeg", quality=85)
            result["screenshot"] = shot
        except Exception as exc:
            result["screenshot_error"] = str(exc)
        self.results.append(result)
        self.flush()
        logger.info("Browser {} passed={} seconds={}", name, result["passed"], result["seconds"])

    def flush(self):
        self.save(
            "browser.json",
            {
                "results": self.results,
                "console": self.errors,
                "http_errors": self.http_errors,
                "external_http_errors": self.external_http_errors,
                "run_ids": self.run_ids,
            },
        )

    def button(self, name: str):
        return self.frame.get_by_role("button", name=name, exact=True)

    def textbox(self, name: str):
        return self.frame.get_by_role("textbox", name=name, exact=True)

    def nodes(self):
        return self.frame.locator(".svelte-flow__node")

    def node(self, node_id: str):
        return self.frame.locator(f'.svelte-flow__node[data-id="{node_id}"]')

    def start(self):
        self.page.goto(self.base + "/app/?module=strategy&view=workshop", wait_until="domcontentloaded")
        expect(self.frame.locator(".strategy-graph-app")).to_be_visible(timeout=90_000)

    def dropdown(self, label: str, option: str):
        self.frame.get_by_role("listbox", name=label, exact=True).click()
        self.frame.get_by_role("option", name=option, exact=True).click()

    def preset(self, name: str):
        if self.button("退出全屏").is_visible():
            self.button("退出全屏").click()
        prior = self.frame.locator(".strategy-graph-app").get_attribute("data-doc-id")
        assert prior is not None, "The mounted graph must expose its current document identity"
        self.dropdown("预置方案", "预置 / " + name)
        self.button("载入方案").click()
        expect(self.frame.locator(".strategy-graph-app")).not_to_have_attribute("data-doc-id", prior)
        expect(self.frame.locator(".graph-breadcrumb button").first).to_have_text(name)

    def yaml_field(self):
        field = self.textbox("方案定义（YAML）")
        if not field.is_visible():
            self.button("方案定义（YAML） ▼").click()
        return field

    def definition(self):
        return yaml.safe_load(self.yaml_field().input_value())

    def compiled_digest(self):
        return digest(compile_plan(self.definition()))

    def apply(self):
        if not self.button("退出全屏").is_visible():
            self.button("全屏画布").click()
        self.button("应用到策略草稿").click()
        expect(self.frame.locator(".graph-footer")).to_contain_text("图形与草稿一致")
        self.button("退出全屏").click()

    def edit_number(self, node: str, label: str, value: str):
        self.node(node).click()
        self.frame.get_by_role("spinbutton", name=label, exact=True).fill(value)
        self.frame.locator(".graph-properties > button.graph-primary").click()

    def drag(self, source, target):
        source.scroll_into_view_if_needed()
        a, b = source.bounding_box(), target.bounding_box()
        assert a and b
        self.page.mouse.move(a["x"] + a["width"] / 2, a["y"] + a["height"] / 2)
        self.page.mouse.down()
        self.page.mouse.move(b["x"] + b["width"] / 2, b["y"] + b["height"] / 2, steps=18)
        self.page.mouse.up()

    def run_ui(self, mode="纯量化回测", end=None, backend="模型API", wait=True):
        if self.button("退出全屏").is_visible():
            self.button("退出全屏").click()
        self.dropdown("运行模式", mode)
        self.dropdown("Agent后端", backend)
        field = self.textbox("开始日期")
        if not field.is_visible():
            self.button("日期、模型与模拟账户 ▼").click()
        field.fill(self.config["start_date"])
        self.textbox("截止日期（留空为今天）").fill(end or self.config["end_date"])
        self.textbox("行情快照ID（可选；重用已归档真实行情）").fill(self.config["snapshot_id"])
        prior = self.textbox("运行ID").input_value()
        self.button("执行当前方案").click()
        expect(self.textbox("运行ID")).not_to_have_value(prior, timeout=60_000)
        run_id = self.textbox("运行ID").input_value()
        assert re.fullmatch(r"[a-f0-9]{32}", run_id), run_id
        self.run_ids.append(run_id)
        if not wait:
            return run_id
        expect(self.textbox("实际运行状态")).to_have_value(re.compile("已完成|失败|已取消"), timeout=300_000)
        row = self.api("/strategy-pipeline-runs/" + run_id)
        self.save("ui-run-" + run_id + ".json", row)
        assert row["status"] == "finished", row
        assert row["result"]["is_mock"] is False
        expect(self.frame.locator(".graph-footer")).to_contain_text(run_id)
        return row

    def cli_replay(self, row, filename="ui-version-cli-replay.json"):
        path = self.output / filename
        command = [
            sys.executable,
            "egs/entrypoints/cli.py",
            "--base-url",
            self.base,
            "--format",
            "json",
            "--require-real",
            "--output",
            str(path),
            "pipeline",
            "run",
            "--version-id",
            str(row["version_id"]),
            "--mode",
            "backtest",
            "--agent-mode",
            "off",
            "--snapshot-id",
            self.config["snapshot_id"],
            "--start-date",
            self.config["start_date"],
            "--end-date",
            self.config["end_date"],
        ]
        run = subprocess.run(command, cwd=PROJECT_ROOT, capture_output=True, text=True, encoding="utf-8", timeout=300)
        assert run.returncode == 0, run.stderr + run.stdout[:1000]
        other = json.loads(path.read_text(encoding="utf-8"))["data"]
        equal = {
            key: row["result"][key] == other["result"][key]
            for key in ("metrics", "curve", "trades", "orders", "targets")
        }
        assert all(equal.values()), equal
        return {"ui": row["id"], "cli": other["id"], "equal": equal}
