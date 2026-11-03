"""Real browser execution of routing scripts with controlled asynchronous DOM mounts."""

import json
import re
from pathlib import Path

import pytest
from playwright.sync_api import expect, sync_playwright

from src.frontend.common.navigation import navigation_config
from src.frontend.shell import SHELL_JS, shell_html


@pytest.fixture()
def routing_browser():
    config = navigation_config()
    routes = Path("src/frontend/assets/workspace_routes.js").read_text(encoding="utf-8")

    def document(route):
        url = route.request.url
        module = url.split("/app/")[1].split("/")[0].split("?")[0]
        if not module:
            body = shell_html() + f"<script>({SHELL_JS})();</script>"
        else:
            labels = config["modules"][module]
            buttons = "".join(
                f"<button role='tab' onclick='document.body.dataset.selected=this.textContent'>{label}</button>"
                for label in labels.values()
            )
            body = f"<div class='module-tabs'><div class='tab-wrapper'>{buttons}</div></div>"
            body += "<div id='route-backtest-task-id'><input value=''></div><div id='pipeline-route-version'><textarea></textarea></div>"
            body += f"<script>const WORKSPACE_ROUTING={json.dumps(config, ensure_ascii=False)};const isWorkspaceEmbedded=new URLSearchParams(location.search).get('embedded')==='1';{routes}</script>"
        route.fulfill(content_type="text/html; charset=utf-8", body="<!doctype html><meta charset='utf-8'>" + body)

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.context.route("http://routing.test/app/**", document)
        yield page
        browser.close()
        assert not errors


def test_context_does_not_leak_or_overwrite_cached_user_edits(routing_browser):
    page = routing_browser
    page.goto("http://routing.test/app/?module=simulation&view=backtest&task_id=17")
    frame = page.frame_locator("iframe.workspace-frame.active")
    field = frame.locator("#route-backtest-task-id input")
    expect(field).to_have_value("17")
    field.fill("99")
    expect(page).to_have_url(re.compile("task_id=99"))
    with page.context.expect_page() as task_popup:
        page.locator("#workspace-open-standalone").click()
    expect(task_popup.value.locator("#route-backtest-task-id input")).to_have_value("99")
    task_popup.value.close()
    page.locator("[data-workspace-module='strategy']").click()
    assert "task_id" not in page.url
    page.locator("[data-workspace-module='simulation']").click()
    expect(field).to_have_value("99")
    page.locator("[data-workspace-module='strategy']").click()
    page.locator("[data-workspace-view='etf']").click()
    with page.context.expect_page() as pending:
        page.locator("#workspace-open-standalone").click()
    popup = pending.value
    expect(popup).to_have_url(re.compile("/app/strategy/\\?view=etf$"))
    expect(popup.locator("body")).to_have_attribute("data-selected", "ETF研究")
    popup.close()


def test_cancelled_context_cannot_apply_to_a_late_mount(routing_browser):
    page = routing_browser
    page.goto("http://routing.test/app/?module=simulation&view=backtest")
    frame = page.locator("iframe.workspace-frame.active").content_frame
    expect(frame.locator("#route-backtest-task-id input")).to_be_visible()
    frame.locator("#route-backtest-task-id").evaluate("element => element.remove()")
    child = page.frames[1]
    child.evaluate(
        """() => parent.postMessage({type:'aiquant:navigate',module:'simulation',view:'backtest',context:{task_id:'71'}}, location.origin)"""
    )
    expect(page).to_have_url(re.compile("task_id=71"))
    page.locator("[data-workspace-module='strategy']").click()
    child.evaluate("""() => {
      const element=document.createElement('div');element.id='route-backtest-task-id';
      element.innerHTML='<input value="user-draft">';document.body.append(element);
    }""")
    # Two animation frames and a DOM mutation flush all pending observers, without a timing sleep.
    child.evaluate("() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))")
    assert child.locator("#route-backtest-task-id input").input_value() == "user-draft"


def test_history_clears_pipeline_target_in_other_views(routing_browser):
    page = routing_browser
    page.goto("http://routing.test/app/?module=strategy&view=workshop&pipeline_version=8")
    field = page.frame_locator("iframe.workspace-frame.active").locator("#pipeline-route-version textarea")
    expect(field).to_have_value("8")
    page.locator("[data-workspace-view='etf']").click()
    assert "pipeline_version" not in page.url
    page.go_back()
    assert "pipeline_version=8" in page.url
    page.go_forward()
    assert "pipeline_version" not in page.url
