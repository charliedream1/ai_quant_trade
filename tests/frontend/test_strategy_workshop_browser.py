"""Exercise the graph-first workshop in both installed Gradio runtimes."""

import re

from playwright.sync_api import expect, sync_playwright


def test_workshop_opens_canvas_and_groups_actions(cli_command, tmp_path):
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width": 1440, "height": 1000})
            page.goto(cli_command.base_url + "/app/?module=strategy&view=workshop", wait_until="domcontentloaded")
            frame = page.frame_locator("iframe.workspace-frame.active")
            editor = frame.locator(".strategy-graph-app")
            expect(editor.locator(".svelte-flow__node").first).to_be_visible(timeout=90000)
            expect(editor.locator(".svelte-flow__edge").first).to_be_attached()
            expect(editor.locator(".graph-palette")).to_have_count(0)
            expect(editor.locator(".graph-properties")).to_have_count(0)
            execute = frame.get_by_role("button", name="执行当前方案", exact=True)
            expect(execute).not_to_be_visible()
            page.screenshot(path=str(tmp_path / "workshop-desktop.png"))

            edit = editor.get_by_role("button", name="编辑", exact=True)
            save_version = editor.get_by_role("button", name="保存版本", exact=True)
            expect(save_version).not_to_be_visible()
            edit.click()
            nodes = editor.locator(".svelte-flow__node")
            previous_nodes = nodes.count()
            universe = editor.locator('.svelte-flow__node[data-id="universe"]')
            expect(universe.locator(".node-expand")).to_have_count(4)
            universe.locator(".node-expand.top").click()
            editor.locator(".graph-palette button:enabled").first.click()
            expect(nodes).to_have_count(previous_nodes + 1)
            edge = editor.locator('.svelte-flow__edge[data-id="eligibility>trend"]')
            edge.dispatch_event("click")
            editor.locator(".remove-edge").click()
            expect(edge).to_have_count(0)
            source = editor.locator('.svelte-flow__node[data-id="eligibility"] .svelte-flow__handle.source')
            target = editor.locator('.svelte-flow__node[data-id="trend"] .svelte-flow__handle.target')
            source.drag_to(target)
            expect(edge).to_have_count(1)
            editor.get_by_role("button", name="取消编辑", exact=True).click()
            expect(editor.locator(".node-expand")).to_have_count(0)
            expect(nodes).to_have_count(previous_nodes)

            doc_id = editor.get_attribute("data-doc-id")
            assert doc_id is not None
            frame.locator("#pipeline-preset input").click()
            frame.get_by_role("option", name="预置 / 多策略总组合", exact=True).click()
            frame.get_by_role("button", name="载入方案", exact=True).click()
            expect(editor).not_to_have_attribute("data-doc-id", doc_id)
            sleeve = editor.locator('.svelte-flow__node[data-id="s:trend"]')
            expect(sleeve).to_be_visible()
            sleeve.dblclick()
            expect(editor.locator('.svelte-flow__node[data-id="trend"]')).to_be_visible()
            editor.locator('.svelte-flow__node[data-id="trend"]').click()
            expect(editor.locator(".graph-properties")).to_be_visible()
            edit.click()
            save_version.click()
            expect(editor.locator(".graph-note")).to_contain_text("已保存策略版本")
            expect(edit).to_be_visible()

            frame.locator("#strategy-workshop-run > .label-wrap").click()
            expect(execute).to_be_visible()
            expect(frame.locator("#strategy-workshop-history .dropdown")).not_to_be_visible()
            page.set_viewport_size({"width": 390, "height": 844})
            edit.click()
            add = editor.get_by_role("button", name="添加组件", exact=True)
            add.click()
            expect(editor.locator(".graph-palette")).to_be_visible()
            assert editor.evaluate("el => el.scrollWidth <= el.clientWidth + 2")
            page.screenshot(path=str(tmp_path / "workshop-mobile.png"))
        finally:
            browser.close()


def test_workshop_execution_opens_results_and_history(cli_command, monkeypatch):
    from src.core.config import get_settings
    from src.engine.composition import data
    from src.strategy.composition import model_artifacts

    # Keep archived inputs in the isolated fixture workspace.
    monkeypatch.setattr(data, "PROJECT_ROOT", get_settings().data_dir.parent)
    monkeypatch.setattr(model_artifacts, "PROJECT_ROOT", get_settings().data_dir.parent)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width": 1440, "height": 1000})
            page.goto(cli_command.base_url + "/app/?module=strategy&view=workshop", wait_until="domcontentloaded")
            frame = page.frame_locator("iframe.workspace-frame.active")
            expect(frame.locator(".graph-canvas .svelte-flow__node").first).to_be_visible(timeout=90000)
            frame.locator("#strategy-workshop-run > .label-wrap").click()
            frame.get_by_role("button", name="执行当前方案", exact=True).click()
            run_id = frame.locator("#strategy-workshop-results").get_by_role("textbox", name="运行ID", exact=True)
            expect(run_id).to_be_visible()
            expect(run_id).not_to_have_value("", timeout=60000)
            identifier = run_id.input_value()
            status = frame.get_by_role("textbox", name="实际运行状态", exact=True)
            expect(status).to_have_value(re.compile("已完成"), timeout=60000)
            frame.locator("#strategy-workshop-results > .label-wrap").click()
            frame.locator("#strategy-workshop-history > .label-wrap").click()
            frame.get_by_role("button", name="刷新历史", exact=True).click()
            frame.locator("#strategy-workshop-history input").click()
            frame.get_by_role("option", name=re.compile(r"^screen · .* · finished$")).click()
            frame.get_by_role("button", name="打开历史", exact=True).click()
            expect(run_id).to_be_visible()
            expect(run_id).to_have_value(identifier)
        finally:
            browser.close()
