"""Browser acceptance checks for the AI console; run against an isolated mock server."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from time import perf_counter
from typing import Any
from uuid import uuid4

from loguru import logger
from playwright.sync_api import expect, sync_playwright


def _open_section(frame: Any, name: str, heading: str, checks: list[dict[str, Any]]) -> None:
    started = perf_counter()
    frame.get_by_role("button", name=name, exact=True).click()
    expect(frame.locator(".ai-shell-page-head strong")).to_have_text(heading)
    expect(frame.locator("#ai-console-chat-page")).not_to_be_visible()
    checks.append({"action": name, "heading": heading, "duration_ms": round((perf_counter() - started) * 1000)})


def _check_chat(frame: Any, checks: list[dict[str, Any]]) -> str:
    frame.get_by_role("button", name="＋ 新任务", exact=True).click()
    expect(frame.locator(".status-strip").first).to_contain_text("已新建会话")
    expect(frame.locator("#ai-console-attachments")).to_be_visible()
    attachment_input = frame.locator("#ai-console-attachments input[type=file]")
    if attachment_input.count():
        attachment_input.set_input_files(str(Path("README.md").resolve()))
        expect(frame.locator("#ai-console-attachments")).to_contain_text("README.md")
    frame.get_by_label("输入任务", exact=True).fill("请给出量化研究工作台的使用建议。")
    frame.get_by_label("输入任务", exact=True).press("Enter")
    expect(frame.locator(".status-strip").first).to_contain_text("已回答", timeout=60_000)
    expect(frame.locator("#ai-console-chat-history")).to_contain_text("测试模式回答")
    expect(frame.get_by_label("输入任务", exact=True)).to_have_value("")
    selected = frame.locator("#ai-console-session-list input:checked")
    expect(selected).to_have_count(1)
    previous_id = selected.get_attribute("value")
    frame.get_by_role("button", name="＋ 新任务", exact=True).click()
    expect(frame.locator("#ai-console-chat-history")).not_to_contain_text("测试模式回答")
    frame.locator(f'#ai-console-session-list input[value="{previous_id}"]').check()
    expect(frame.locator(".status-strip").first).to_contain_text("已载入会话")
    expect(frame.locator("#ai-console-chat-history")).to_contain_text("测试模式回答")
    for label, provider in (("Codex CLI", "codex"), ("Trae CLI", "trae"), ("WorkBuddy CLI", "workbuddy")):
        frame.locator("#ai-console-backend input").click()
        frame.get_by_role("option", name=label, exact=True).click()
        frame.get_by_label("输入任务", exact=True).fill("请生成一个低换手策略骨架，用于界面验收。")
        frame.get_by_role("button", name="发送", exact=True).click()
        expected = "mock 模式未执行真实 Codex CLI" if provider == "codex" else "未接入真实对话"
        expect(frame.locator("#ai-console-status")).to_contain_text(expected, timeout=30_000)
        expect(frame.locator("#ai-console-chat-history")).to_contain_text(expected)
    checks.append({"action": "switch_all_cli_adapters", "result": "ok"})
    checks.append({"action": "new_send_reload_session", "result": "ok"})
    assert previous_id is not None
    return previous_id


def _check_files(frame: Any, checks: list[dict[str, Any]]) -> None:
    frame.get_by_role("button", name=re.compile("项目文件浏览")).click()
    frame.get_by_role("button", name="刷新目录", exact=True).click()
    expect(frame.get_by_text(re.compile("项目目录.*项"))).to_be_visible()
    frame.get_by_role("button", name="打开文件面板", exact=True).click()
    frame.get_by_label("相对路径", exact=True).fill("README.md")
    frame.get_by_role("button", name="打开文件", exact=True).click()
    expect(frame.locator(".ai-shell-context .cm-content")).to_contain_text("AIQuant", timeout=15_000)
    frame.get_by_role("button", name="关闭文件面板", exact=True).click()
    frame.get_by_role("button", name=re.compile("项目文件浏览")).click()
    checks.append({"action": "project_tree_and_readme_preview", "result": "ok"})


def _check_automation(frame: Any, checks: list[dict[str, Any]]) -> None:
    _open_section(frame, "⏱ 自动化", "定时任务", checks)
    frame.get_by_role("button", name=re.compile("新增自动化任务")).click()
    frame.get_by_label("任务名称", exact=True).fill(f"界面验收定时任务-{uuid4().hex[:8]}")
    frame.get_by_label("Cron", exact=True).fill("0 0 1 1 *")
    frame.get_by_label("启用", exact=True).uncheck()
    frame.get_by_role("button", name="创建任务", exact=True).click()
    status = frame.locator(".status-strip").last
    expect(status).to_contain_text("任务已创建", timeout=30_000)
    job_id = re.search(r"ID=(\d+)", status.inner_text())
    assert job_id, status.inner_text()
    frame.get_by_label("任务 ID", exact=True).fill(job_id.group(1))
    for name, state in (("开启任务", "1"), ("关闭任务", "0")):
        frame.get_by_role("button", name=name, exact=True).click()
        expect(status).to_contain_text(f'"enabled": {state}')
    checks.append({"action": "create_enable_disable_automation", "job_id": int(job_id.group(1)), "result": "ok"})


def _check_registrations(frame: Any, checks: list[dict[str, Any]]) -> None:
    _open_section(frame, "⌁ MCP 服务", "MCP 服务", checks)
    frame.get_by_role("button", name="刷新 MCP", exact=True).click()
    expect(frame.get_by_role("button", name="测试连接", exact=True)).to_be_visible()
    frame.get_by_role("button", name=re.compile("新增 MCP 服务")).click()
    frame.get_by_label("服务名称", exact=True).fill(f"ui_acceptance_mcp_{uuid4().hex[:8]}")
    frame.get_by_role("button", name="登记服务", exact=True).click()
    expect(frame.locator(".status-strip").last).to_contain_text("MCP 服务已创建", timeout=30_000)
    _open_section(frame, "◇ Skill", "Skill 包", checks)
    frame.get_by_role("button", name=re.compile("登记 Skill")).first.click()
    frame.get_by_label("Skill 名称", exact=True).fill(f"ui_acceptance_skill_{uuid4().hex[:8]}")
    frame.get_by_label("说明", exact=True).fill("界面验收，仅登记参数契约")
    frame.get_by_role("button", name="登记 Skill", exact=True).click()
    expect(frame.locator(".status-strip").last).to_contain_text("不执行上传代码", timeout=30_000)
    _open_section(frame, "▤ 知识库", "知识库", checks)
    frame.get_by_label("分类名称", exact=True).fill(f"界面验收知识-{uuid4().hex[:8]}")
    frame.get_by_role("button", name="新增分类", exact=True).click()
    status = frame.locator(".status-strip").last
    expect(status).to_contain_text("分类已创建", timeout=30_000)
    category_id = re.search(r"ID=(\d+)", status.inner_text())
    assert category_id, status.inner_text()
    frame.get_by_label("分类 ID", exact=True).first.fill(category_id.group(1))
    frame.get_by_label("笔记标题", exact=True).fill("界面验收笔记")
    frame.get_by_label("笔记内容", exact=True).fill("记录工作台的同页导航、文件预览与会话功能。")
    frame.get_by_role("button", name="保存笔记", exact=True).click()
    expect(frame.locator(".status-strip").last).to_contain_text("笔记", timeout=30_000)
    checks.append({"action": "mcp_registration_skill_registration_knowledge_note", "result": "ok"})


def _layout(frame: Any) -> dict[str, Any]:
    return frame.locator("#ai-console-shell").evaluate(
        """(shell) => ({
          viewportWidth: innerWidth,
          viewportHeight: innerHeight,
          documentWidth: document.documentElement.scrollWidth,
          documentHeight: document.documentElement.scrollHeight,
          columns: Array.from(shell.children).filter(el => el.getClientRects().length).map(el => {
            const r = el.getBoundingClientRect();
            return {x: Math.round(r.x), y: Math.round(r.y), width: Math.round(r.width)};
          }),
          navHeights: Array.from(shell.querySelectorAll('.ai-shell-nav button'))
            .map(el => Math.round(el.getBoundingClientRect().height)),
          chatTop: Math.round(shell.querySelector('#ai-console-chat-history').getBoundingClientRect().top),
          chatHeight: Math.round(shell.querySelector('#ai-console-chat-history').getBoundingClientRect().height),
          composer: (() => {const r = shell.querySelector('#ai-console-composer').getBoundingClientRect();
            return {top:r.top, bottom:r.bottom, height:r.height, width:r.width};})(),
          input: (() => {const r = shell.querySelector('#ai-console-input textarea').getBoundingClientRect();
            return {x:r.x, right:r.right, height:r.height};})(),
          backend: (() => {const r = shell.querySelector('#ai-console-backend').getBoundingClientRect();
            return {x:r.x, y:r.y, bottom:r.bottom, width:r.width};})(),
          chatVisible: !!shell.querySelector('#ai-console-chat-history').getClientRects().length,
        })"""
    )


def _check_layout(layout: dict[str, Any], viewport: tuple[int, int]) -> None:
    assert layout["documentWidth"] <= layout["viewportWidth"] + 2, layout
    assert layout["documentHeight"] <= layout["viewportHeight"] + 2, layout
    assert layout["composer"]["bottom"] <= layout["viewportHeight"], layout
    assert layout["input"]["height"] <= 84, layout
    if viewport[0] >= 1280:
        assert len({col["y"] for col in layout["columns"]}) == 1, layout
        assert layout["columns"][0]["y"] >= 0, layout
        assert max(layout["navHeights"]) <= 48, layout
        assert layout["chatHeight"] > viewport[1] * 0.45, layout
        assert layout["backend"]["y"] >= layout["input"]["height"], layout


def _check_window_controls(page: Any, frame: Any, wide: bool) -> None:
    expect(page.locator(".workspace-external-links a")).to_have_count(3)
    expect(page.get_by_role("link", name="GitHub", exact=True)).to_have_attribute(
        "href", re.compile("github.com/charliedream1/ai_quant_trade")
    )
    for name in ("收起工作栏", "展开工作栏") if wide else ("展开工作栏", "关闭工作栏"):
        frame.get_by_role("button", name=name, exact=True).click()
    if wide:
        expect(frame.locator("#ai-console-sidebar")).to_be_visible()
    else:
        expect(frame.locator("#ai-console-sidebar")).not_to_be_visible()
    toggle = page.locator("#workspace-sidebar-toggle")
    initial = toggle.get_attribute("aria-expanded")
    toggle.click()
    expect(toggle).to_have_attribute("aria-expanded", "false" if initial == "true" else "true")
    toggle.click()
    expect(toggle).to_have_attribute("aria-expanded", initial)


def _contrast_ratio(foreground: str, background: str) -> float:
    def luminance(color: str) -> float:
        channels = [float(value) / 255 for value in re.findall(r"[\d.]+", color)[:3]]
        linear = [value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4 for value in channels]
        return sum(value * weight for value, weight in zip(linear, (0.2126, 0.7152, 0.0722), strict=True))

    first, second = sorted((luminance(foreground), luminance(background)))
    return (second + 0.05) / (first + 0.05)


def _capture_dark_theme(page: Any, frame: Any, output: Path) -> tuple[list[dict[str, Any]], float]:
    page.locator("#app-theme-toggle").click()
    expect(page.locator("html")).to_have_attribute("data-theme", "dark")
    expect(frame.locator("html")).to_have_attribute("data-theme", "dark")
    page.wait_for_timeout(350)
    controls = page.locator(".workspace-actions button, #workspace-sidebar-toggle").evaluate_all(
        """els => els.map(el => ({text: el.innerText, color: getComputedStyle(el).color,
          children: Array.from(el.querySelectorAll('*')).map(n => ({tag:n.tagName,
            color:getComputedStyle(n).color}))}))"""
    )
    assert all(child["color"] == control["color"] for control in controls for child in control["children"]), controls
    surfaces = frame.locator("#ai-console-session-list label, #ai-console-chat-history .message").evaluate_all(
        """els => els.map(el => ({color: getComputedStyle(el).color,
          background: getComputedStyle(el).backgroundColor}))"""
    )
    minimum_contrast = min((_contrast_ratio(item["color"], item["background"]) for item in surfaces), default=21.0)
    assert minimum_contrast >= 4.5, surfaces
    page.screenshot(path=str(output))
    return controls, round(minimum_contrast, 2)


def run_audit(base_url: str, output: Path, viewport: tuple[int, int], operations: bool) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    errors: list[str] = []
    external_errors: list[str] = []
    output.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": viewport[0], "height": viewport[1]})

        def record_console(message: Any) -> None:
            if message.type == "error":
                (external_errors if "ERR_NETWORK_ACCESS_DENIED" in message.text else errors).append(message.text)

        page.on("console", record_console)
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on(
            "response",
            lambda response: (
                errors.append(f"HTTP {response.status} {response.url}") if response.status >= 500 else None
            ),
        )
        page.goto(base_url, wait_until="domcontentloaded", timeout=60_000)
        expect(page.locator("#quant-workspace-shell")).to_have_attribute("data-initialized", "1")
        if viewport[0] <= 880:
            page.locator("#workspace-sidebar-toggle").click()
        page.locator("[data-workspace-module='ai']").click()
        page.locator("[data-workspace-view-module='ai'][data-workspace-view='main']").click()
        if viewport[0] <= 880:
            page.locator("#workspace-sidebar-toggle").click()
        active = page.locator("iframe.workspace-frame.active")
        frame = active.content_frame
        expect(frame.get_by_role("button", name="发送", exact=True)).to_be_visible(timeout=60_000)
        if not frame.locator("#ai-console-sidebar").is_visible():
            frame.get_by_role("button", name="展开工作栏", exact=True).click()
        chat_session_id = None
        if operations:
            chat_session_id = _check_chat(frame, checks)
            _check_files(frame, checks)
            _check_automation(frame, checks)
            _check_registrations(frame, checks)
            frame.get_by_role("button", name="＋ 新任务", exact=True).click()
            frame.locator(f'#ai-console-session-list input[value="{chat_session_id}"]').check()
            expect(frame.locator("#ai-console-toolbar")).to_be_visible()
        else:
            for name, heading in (
                ("⏱ 自动化", "定时任务"),
                ("⌁ MCP 服务", "MCP 服务"),
                ("◇ Skill", "Skill 包"),
                ("▤ 知识库", "知识库"),
            ):
                _open_section(frame, name, heading, checks)
            frame.get_by_role("button", name="＋ 新任务", exact=True).click()
            expect(frame.locator("#ai-console-toolbar")).to_be_visible()
        page.reload(wait_until="domcontentloaded")
        expect(frame.get_by_role("button", name="发送", exact=True)).to_be_visible(timeout=60_000)
        if not frame.locator("#ai-console-sidebar").is_visible():
            frame.get_by_role("button", name="展开工作栏", exact=True).click()
        expect(frame.locator("#ai-console-session-list input[type='radio']").first).to_be_visible(timeout=15_000)
        if chat_session_id:
            frame.locator(f'#ai-console-session-list input[value="{chat_session_id}"]').check()
            expect(frame.locator("#ai-console-chat-history")).to_contain_text("codex cli 执行结果")
        checks.append({"action": "sessions_reload_on_open", "result": "ok"})
        sidebar_overlay = frame.locator("body").evaluate("() => innerWidth <= 760")
        if sidebar_overlay:
            frame.get_by_role("button", name="关闭工作栏", exact=True).click()
        frame.locator("body").evaluate("() => scrollTo(0, 0)")
        layout = _layout(frame)
        logger.info("AI viewport layout | {}", layout)
        light = output / f"ai-{viewport[0]}-light.png"
        page.screenshot(path=str(light))
        _check_layout(layout, viewport)
        _check_window_controls(page, frame, not sidebar_overlay)
        dark = output / f"ai-{viewport[0]}-dark.png"
        dark_controls, dark_surface_contrast = _capture_dark_theme(page, frame, dark)
        assert "module=ai" in page.url, page.url
        assert page.locator("iframe.workspace-frame.active").count() == 1
        browser.close()
    return {
        "checks": checks,
        "layout": layout,
        "errors": errors,
        "external_errors": external_errors,
        "dark_controls": dark_controls,
        "dark_surface_contrast": dark_surface_contrast,
        "screenshots": [str(light), str(dark)],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--width", type=int, default=1440)
    parser.add_argument("--height", type=int, default=1000)
    parser.add_argument(
        "--operations", action="store_true", help="Create test records only on an isolated mock server."
    )
    args = parser.parse_args()
    summary = run_audit(args.base_url, args.output, (args.width, args.height), args.operations)
    report = args.output / f"ai-{args.width}-report.json"
    report.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    logger.info(
        "AI console browser audit | checks={} errors={} report={}",
        len(summary["checks"]),
        len(summary["errors"]),
        report,
    )
    if summary["errors"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
