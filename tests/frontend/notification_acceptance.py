"""Click actual global reminders and avatar, with clearly labelled isolated fixtures."""

import argparse
import json
import os
import re
import uuid
from pathlib import Path
from threading import Event
from time import perf_counter

import requests as http_requests
import yaml
from loguru import logger
from playwright.sync_api import expect, sync_playwright

import src.core.config as settings_module
from src.core.config import get_settings
from src.core.database import Database
from src.notifications.config import target
from src.notifications.store import NotificationStore


def main(base, runtime, output):
    os.environ["ALL_IN_ONE_DATA_DIR"] = str(runtime / "data")
    os.environ["ALL_IN_ONE_DB_PATH"] = str(runtime / "platform.db")
    settings_module._SETTINGS = None
    Database.reset_instance()
    assert get_settings().db_path.resolve() == (runtime / "platform.db").resolve()
    store = NotificationStore()
    seed_path = runtime / "browser-seed.json"
    seed_deadline = perf_counter() + 30
    while not seed_path.is_file():
        assert perf_counter() < seed_deadline, "Isolated test fixture did not become ready"
        Event().wait(0.2)
    seed = json.loads(seed_path.read_text(encoding="utf-8"))
    output.mkdir(parents=True, exist_ok=True)
    results, errors, requests = {}, [], []
    deadline = perf_counter() + 30
    while True:
        try:
            response = http_requests.get(base + "/api/v1/notifications/config", timeout=2)
            response.raise_for_status()
            break
        except http_requests.RequestException:
            assert perf_counter() < deadline, "Isolated test service did not become ready"
            Event().wait(0.2)
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1600, "height": 1050})
        page.on("pageerror", lambda error: errors.append(error.stack or str(error)))
        page.on("request", lambda request: requests.append(request.url) if "/notifications" in request.url else None)
        try:
            started = perf_counter()
            page.goto(base + "/app/?module=strategy&view=etf")
            expect(page.locator("#workspace-notification-toggle")).to_be_visible(timeout=60000)

            def toast(identifier):
                return page.locator(f"#notification-toasts article[data-notification-id='{identifier}']")

            expect(toast(seed["warning"])).to_be_visible(timeout=60000)
            expect(toast(seed["critical"])).to_be_visible()
            frame = page.frame_locator("iframe.workspace-frame.active")
            expect(frame.get_by_label("ETF池", exact=True).filter(visible=True)).to_be_visible(timeout=60000)
            results["ready_seconds"] = round(perf_counter() - started, 3)
            page.screenshot(path=str(output / "87-global-notifications.jpg"), type="jpeg", quality=90)
            toast(seed["warning"]).get_by_role("button", name="关闭", exact=False).click()
            expect(toast(seed["warning"])).to_have_count(0)
            page.reload()
            expect(page.locator("#notification-critical")).to_be_visible(timeout=60000)
            expect(toast(seed["warning"])).to_have_count(0)
            page.locator("#workspace-notification-toggle").click()
            center = page.locator("#notification-center")
            expect(center).to_be_visible()
            dismissed = center.locator(f"article[data-notification-id='{seed['warning']}']")
            expect(dismissed).to_contain_text("已收起")
            center.get_by_role("button", name="全部标为已读", exact=True).click()
            expect(page.locator("#workspace-notification-toggle span")).to_have_text("")
            expect(page.locator("#notification-critical")).to_be_visible()
            page.screenshot(path=str(output / "88-notification-center.jpg"), type="jpeg", quality=90)
            results["dismiss_read_critical"] = True
            frame = page.frame_locator("iframe.workspace-frame.active")
            avatar = frame.locator("#ai-floating-button")
            expect(avatar).to_have_class(re.compile("assistant-avatar"), timeout=60000)
            center.get_by_label("AI助手外观").select_option("icon")
            expect(avatar).to_have_attribute("style", re.compile("assistant-simple.svg"))
            center.get_by_label("AI助手外观").select_option("robot")
            center.get_by_role("button", name="关闭", exact=True).click()
            expect(avatar).to_have_attribute("style", re.compile("assistant-robot.svg"))
            expect(frame.locator('#ai-floating-button[data-drag-ready="1"]')).to_be_visible(timeout=30000)
            box = avatar.bounding_box()
            page.mouse.move(box["x"] + 25, box["y"] + 25)
            page.mouse.down()
            page.mouse.move(box["x"] - 55, box["y"] - 35, steps=8)
            page.mouse.up()
            assert avatar.bounding_box()["x"] < box["x"] - 20
            page.screenshot(path=str(output / "89-assistant-robot.jpg"), type="jpeg", quality=90)
            avatar.screenshot(path=str(output / "assistant-avatar.png"))
            avatar.click()
            expect(frame.locator("#ai-chat-input textarea")).to_be_visible(timeout=30000)
            results["avatar_style_drag_open"] = True
            page.locator("#app-theme-toggle").click()
            page.set_viewport_size({"width": 1180, "height": 900})
            page.wait_for_timeout(500)
            page.screenshot(path=str(output / "assistant-dark-open.jpg"), type="jpeg", quality=90)
            panel = frame.locator("#ai-floating-panel").bounding_box()
            assert panel["x"] + panel["width"] <= 1180
            frame.locator("#ai-floating-close").click()
            page.locator("#workspace-notification-toggle").click()
            page.screenshot(path=str(output / "90-notification-dark.jpg"), type="jpeg", quality=90)
            dismissed.get_by_role("button", name="查看详情", exact=True).click()
            expect(page).to_have_url(re.compile("module=strategy&view=factors"))
            results["same_page_details"] = True
            sample = yaml.safe_load(Path("tests/notifications/fixtures.yaml").read_text(encoding="utf-8"))
            for index in range(6):
                store.publish(
                    "fixture",
                    uuid.uuid4().hex,
                    "success",
                    sample["title"] + str(index),
                    sample["message"],
                    target("factor"),
                )
            unsafe = store.publish(
                "fixture", uuid.uuid4().hex, "warning", sample["title"], sample["hostile"], target("factor")
            )
            page.evaluate("window.dispatchEvent(new Event('focus'))")
            expect(page.locator("#notification-toasts article")).to_have_count(3, timeout=15000)
            expect(page.locator("#notification-toasts article")).to_have_count(0, timeout=15000)
            page.locator("#workspace-notification-toggle").click()
            expect(center.locator(f"article[data-notification-id='{unsafe['id']}']")).to_contain_text(sample["hostile"])
            assert not page.evaluate("Boolean(window.__notificationInjection)")
            assert center.locator("img").count() == 0
            results["bounded_toasts_auto_hide_and_escaped_content"] = True
            center.get_by_role("button", name="关闭", exact=True).click()
            page.evaluate(
                "Object.defineProperty(document,'hidden',{configurable:true,value:true});document.dispatchEvent(new Event('visibilitychange'))"
            )
            request_count = len(requests)
            page.wait_for_timeout(16000)
            assert len(requests) == request_count
            page.evaluate("delete document.hidden;document.dispatchEvent(new Event('visibilitychange'))")
            results["hidden_pauses_global_poll"] = True
            count = store.db.scalar("SELECT COUNT(*) FROM notifications")
            assert count >= 2
            assert not errors, errors
        except Exception:
            page.screenshot(path=str(output / "failure.jpg"), type="jpeg", quality=90)
            raise
        finally:
            (output / "browser.json").write_text(
                json.dumps(
                    {
                        "results": results,
                        "errors": errors,
                        "requests": requests,
                        "scope": "explicit_fixture_notifications_and_mock_module_no_financial_performance",
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            browser.close()
        logger.info("Notifications and assistant browser acceptance passed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    main(args.base, args.runtime.resolve(), args.output)
