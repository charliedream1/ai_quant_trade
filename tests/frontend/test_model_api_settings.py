"""Model API/CLI/form round trips preserve backend and shared quota policy."""

import json

from playwright.sync_api import expect, sync_playwright

from src.frontend.services import FrontendService


def test_model_policy_cli_and_form_roundtrip(cli_command):
    response = cli_command(
        "model",
        "create",
        "--name",
        "SDK settings",
        "--set",
        "base_url=http://127.0.0.1:12345/v1",
        "--model-name",
        "test-model",
        "--api-backend",
        "openai",
        "--rpm",
        "60",
        "--max-concurrency",
        "2",
        "--wait-on-limit",
        "false",
        "--quota-group",
        "team-a",
        "--max-retries",
        "2",
        "--extra-body",
        '{"top_p":0.8}',
    )
    model = response["data"]
    assert model["api_backend"] == "openai" and model["rpm"] == 60 and model["wait_on_limit"] is False
    form = FrontendService().model_form(model["id"])
    assert form[-7:-1] == ("openai", 60, 2, False, "team-a", 2)
    assert json.loads(form[-1]) == {"top_p": 0.8}
    cli_command("model", "update", model["id"], "--api-backend", "litellm", "--rpm", "30")
    latest = cli_command("model", "show", model["id"])["data"]
    assert latest["api_backend"] == "litellm" and latest["rpm"] == 30


def test_browser_loads_and_updates_model_policy(client, cli_command, tmp_path):
    model = client.post(
        "/api/v1/llm-models",
        json={
            "name": "Browser SDK",
            "base_url": "http://127.0.0.1:12345/v1",
            "model_name": "test-model",
            "api_backend": "litellm",
            "rpm": 40,
        },
    ).json()["data"]
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1500, "height": 1100})
        page.add_init_script("localStorage.setItem('all-in-one-ui-lang','zh')")
        page.goto(cli_command.base_url + "/app/?module=admin&view=settings", wait_until="domcontentloaded")
        frame = page.frame_locator("iframe.workspace-frame.active")
        frame.get_by_role("tab", name="模型管理", exact=True).click(timeout=90000)
        expect(frame.locator("#model-api-backend input")).to_be_visible(timeout=90000)
        frame.get_by_label("模型 ID", exact=True).fill(str(model["id"]))
        frame.get_by_role("button", name="载入配置", exact=True).click()
        expect(frame.locator("#model-api-backend input")).to_have_value("LiteLLM SDK", timeout=30000)
        expect(frame.locator("#model-rpm input")).to_have_value("40")
        frame.locator("#model-rpm input").fill("25")
        frame.get_by_role("button", name="更新所选模型", exact=True).click()
        expect(frame.get_by_text("模型配置已更新", exact=False)).to_be_visible(timeout=30000)
        result = client.get(f"/api/v1/llm-models/{model['id']}").json()["data"]
        assert result["rpm"] == 25 and result["api_backend"] == "litellm"
        page.screenshot(path=str(tmp_path / "model-api-settings.png"))
        browser.close()
