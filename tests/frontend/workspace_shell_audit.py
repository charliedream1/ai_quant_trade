"""Playwright audit for the persistent Gradio workspace shell."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from loguru import logger
from playwright.sync_api import sync_playwright

MODULE_SEQUENCE = ("dashboard", "market", "research", "ai", "strategy", "live", "knowledge", "admin", "simulation")
MODULE_VIEW = {
    "dashboard": "总览",
    "market": "行情看盘",
    "research": "研报与模型分析",
    "ai": "工作流中心",
    "strategy": "策略管理",
    "live": "发布策略",
    "knowledge": "资料库",
    "admin": "定时任务",
    "simulation": "模拟归因",
}
MODULE_EXPECTED_TEXT = {
    "dashboard": "刷新总览",
    "market": "刷新行情",
    "research": "检索",
    "ai": "工作台总览",
    "strategy": "生命周期",
    "live": "刷新配置",
    "knowledge": "刷新分类",
    "admin": "刷新任务",
    "simulation": "流程步骤",
}


def _wait_for_active_module(page: Any, module_key: str) -> None:
    page.wait_for_function(
        """
        (key) => {
          const frame = document.querySelector(`iframe.workspace-frame.active[data-module-key="${key}"]`);
          const status = document.querySelector('#workspace-frame-status');
          return Boolean(frame && status?.hidden);
        }
        """,
        arg=module_key,
        timeout=60_000,
    )


def _child_visibility(page: Any) -> dict[str, bool]:
    active_frame = page.frame_locator("iframe.workspace-frame.active")
    return {
        "header_hidden": not active_frame.locator(".app-header").is_visible(),
        "module_navigation_hidden": not active_frame.locator("#module-navigation").is_visible(),
        "root_tabs_hidden": not active_frame.locator("#main-navigation > .tab-wrapper").is_visible(),
        "module_tabs_hidden": not active_frame.locator(".module-tabs > .tab-wrapper").is_visible(),
    }


def run_audit(
    base_url: str,
    screenshot_path: Path,
    viewport: tuple[int, int] = (1440, 1000),
    final_theme: str = "light",
) -> dict[str, Any]:
    console_errors: list[str] = []
    ignored_console_errors: list[str] = []
    http_errors: list[str] = []
    checks: list[dict[str, Any]] = []
    screenshot_path.parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": viewport[0], "height": viewport[1]}, device_scale_factor=1)

        def record_console(message: Any) -> None:
            if message.type != "error":
                return
            if "ERR_NETWORK_ACCESS_DENIED" in message.text:
                ignored_console_errors.append(message.text)
            else:
                console_errors.append(message.text)

        page.on("console", record_console)
        page.on(
            "response",
            lambda response: (
                http_errors.append(f"{response.status} {response.url}") if response.status >= 400 else None
            ),
        )
        page.goto(base_url, wait_until="domcontentloaded", timeout=60_000)
        page.wait_for_selector("#quant-workspace-shell", timeout=60_000)

        theme_button = page.locator("#app-theme-toggle")
        theme_button.click()
        page.wait_for_function("document.documentElement.dataset.theme === 'dark'")
        dark_theme = page.locator("html").get_attribute("data-theme")
        theme_button.click()
        page.wait_for_function("document.documentElement.dataset.theme === 'light'")
        sidebar_collapsed = None
        sidebar_toggle = page.locator("#workspace-sidebar-toggle")
        if viewport[0] > 880:
            sidebar_toggle.click()
            page.wait_for_function(
                "document.querySelector('#quant-workspace-shell').classList.contains('sidebar-collapsed')"
            )
            sidebar_collapsed = page.locator("#quant-workspace-shell").evaluate(
                "(shell) => shell.classList.contains('sidebar-collapsed')"
            )
            sidebar_toggle.click()

        for module_key in MODULE_SEQUENCE:
            if viewport[0] <= 880:
                sidebar_toggle.click()
            page.locator(f"[data-workspace-module='{module_key}']").click()
            _wait_for_active_module(page, module_key)
            view_label = MODULE_VIEW[module_key]
            page.get_by_role("button", name=view_label, exact=True).click()
            if viewport[0] <= 880:
                sidebar_toggle.click()
            active_frame = page.frame_locator("iframe.workspace-frame.active")
            active_frame.get_by_text(MODULE_EXPECTED_TEXT[module_key], exact=True).first.wait_for(
                state="visible",
                timeout=15_000,
            )
            checks.append(
                {
                    "module": module_key,
                    "view": view_label,
                    "url": page.url,
                    "frame_count": page.locator("iframe.workspace-frame").count(),
                    "active_frame_count": page.locator("iframe.workspace-frame.active").count(),
                    "expected_text_visible": True,
                    **_child_visibility(page),
                }
            )

        layout = page.locator("#quant-workspace-shell").evaluate(
            """
            (shell) => ({
              viewportWidth: window.innerWidth,
              media880: window.matchMedia('(max-width: 880px)').matches,
              media520: window.matchMedia('(max-width: 520px)').matches,
              bodyGridRules: Array.from(document.styleSheets).flatMap((sheet) => {
                try {
                  return Array.from(sheet.cssRules).filter((rule) => rule.cssText && rule.cssText.includes('.workspace-body'))
                    .map((rule) => rule.cssText.slice(0, 800));
                } catch (_) { return []; }
              }).slice(-10),
              documentWidth: document.documentElement.scrollWidth,
              sidebarWidth: Math.round(shell.querySelector('.workspace-sidebar').getBoundingClientRect().width),
              activeModule: shell.querySelector('[data-workspace-module].active')?.dataset.workspaceModule || '',
              activeView: shell.querySelector('[data-workspace-view].active')?.dataset.workspaceView || '',
            })
            """
        )
        if final_theme == "dark":
            theme_button.click()
            page.wait_for_function("document.documentElement.dataset.theme === 'dark'")
            page.wait_for_timeout(400)
        page.screenshot(path=str(screenshot_path), full_page=False, timeout=60_000)
        browser.close()

    failures: list[str] = []
    for check in checks:
        if not check["url"].startswith(base_url):
            failures.append(f"{check['module']}: top-level URL left the workspace shell")
        if check["frame_count"] > 3:
            failures.append(f"{check['module']}: iframe cache exceeded 3")
        if check["active_frame_count"] != 1:
            failures.append(f"{check['module']}: expected exactly one active iframe")
        for key in ("header_hidden", "module_navigation_hidden", "root_tabs_hidden", "module_tabs_hidden"):
            if not check[key]:
                failures.append(f"{check['module']}: {key} is false")
    if layout["documentWidth"] > layout["viewportWidth"] + 2:
        failures.append("workspace shell has horizontal document overflow")
    if viewport[0] > 880 and layout["sidebarWidth"] < 180:
        failures.append("desktop workspace sidebar is narrower than expected")
    if dark_theme != "dark":
        failures.append("dark theme toggle did not set data-theme=dark")
    if viewport[0] > 880 and sidebar_collapsed is not True:
        failures.append("sidebar collapse toggle did not collapse the workspace")
    if console_errors:
        failures.extend(f"console: {message}" for message in console_errors[:10])
    if http_errors:
        failures.extend(f"http: {message}" for message in http_errors[:10])

    return {
        "base_url": base_url,
        "checks": checks,
        "layout": layout,
        "theme_checks": {"dark_theme": dark_theme, "sidebar_collapsed": sidebar_collapsed},
        "console_errors": console_errors,
        "ignored_console_errors": ignored_console_errors,
        "http_errors": http_errors,
        "failures": failures,
        "screenshot": screenshot_path.as_posix(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit the persistent Gradio workspace shell.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8013/app/")
    parser.add_argument("--screenshot", default="docs/audit/screenshots/workspace-shell.png")
    parser.add_argument("--json-out", default="docs/audit/workspace_shell_audit.json")
    parser.add_argument("--width", type=int, default=1440)
    parser.add_argument("--height", type=int, default=1000)
    parser.add_argument("--final-theme", choices=("light", "dark"), default="light")
    args = parser.parse_args()

    summary = run_audit(args.base_url, Path(args.screenshot), (args.width, args.height), args.final_theme)
    json_path = Path(args.json_out)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    logger.info("workspace shell audit completed | failures={} output={}", len(summary["failures"]), json_path)
    if summary["failures"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
