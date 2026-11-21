"""Every mapped view offers its scoped task without running a model on entry."""

from playwright.sync_api import expect, sync_playwright

from src.core.page_analysis_snapshot import analysis_config


def test_all_registered_view_tasks_mount_without_generation(cli_command, monkeypatch, tmp_path):
    from src.engine.insights import execution

    called = []
    monkeypatch.setattr(execution, "generate_text", lambda *args: called.append(True))
    routes = {}
    for row in analysis_config()["presets"].values():
        if not row.get("show_panel", True):
            continue
        routes.setdefault((row["module"], row["views"][0]), row["label"])
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1500, "height": 1050})
        page.add_init_script("localStorage.setItem('all-in-one-ui-lang', 'en')")
        try:
            previous = None
            for (module, view), label in routes.items():
                if previous is None:
                    page.goto(
                        cli_command.base_url + f"/app/?module={module}&view={view}", wait_until="domcontentloaded"
                    )
                else:
                    if previous != module:
                        page.locator(f'[data-workspace-module="{module}"]').click()
                    page.locator(f'[data-workspace-view-module="{module}"][data-workspace-view="{view}"]').click()
                previous = module
                frame = page.frame_locator("iframe.workspace-frame.active")
                page.locator("#workspace-page-report").click(timeout=90000)
                frame.get_by_text("Analysis options", exact=True).click(timeout=90000)
                expect(frame.locator("#page-skill-task input")).to_have_value(label, timeout=20000)
                assert called == []
            page.screenshot(path=str(tmp_path / "page-analysis-route-matrix.png"))
        finally:
            browser.close()
