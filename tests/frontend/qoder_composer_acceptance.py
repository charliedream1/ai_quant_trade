"""Visible keyboard, permission and layout checks against an isolated Gradio server."""

import argparse
import json
import re
from pathlib import Path
from time import perf_counter

import requests
from loguru import logger
from playwright.sync_api import expect, sync_playwright


def main(base, output):
    output.mkdir(parents=True, exist_ok=True)
    results, errors = [], []
    http = requests.Session()
    http.trust_env = False

    def messages():
        sessions = http.get(base + "/api/v1/ai-workspace/sessions?page_size=100", timeout=20).json()["data"]["items"]
        return sum(
            len(http.get(base + f"/api/v1/ai-workspace/sessions/{row['id']}", timeout=20).json()["data"]["messages"])
            for row in sessions
        )

    def choose(frame, prefix, field, label):
        frame.locator(f"#{prefix}-{field} input").click()
        frame.get_by_role("option", name=label, exact=True).click()

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1600, "height": 1050})
        page.on("pageerror", lambda error: errors.append(error.stack or str(error)))
        try:
            started = perf_counter()
            page.goto(base + "/app/?module=ai&view=main")
            frame = page.frame_locator("iframe.workspace-frame.active")
            expect(frame.locator("#ai-console-input textarea")).to_be_visible(timeout=90000)
            results.append({"initial_ready_seconds": round(perf_counter() - started, 3)})

            def check(prefix):
                field = frame.locator(f"#{prefix}-input textarea")
                expect(field).to_have_attribute("placeholder", re.compile("Enter 发送，Ctrl\\+Enter 换行"))
                field.fill("")
                assert field.evaluate("e=>e.matches(':placeholder-shown')")
                before = messages()
                field.fill("甲乙")
                assert not field.evaluate("e=>e.matches(':placeholder-shown')")
                fixture = Path(__file__).parents[1] / "agent/fixtures/qoder_protocol.yaml"
                with page.expect_file_chooser() as chooser:
                    frame.locator(f"#{prefix}-composer .composer-attach").click()
                chooser.value.set_files(str(fixture.resolve()))
                expect(frame.locator(f"#{prefix}-composer")).to_contain_text(re.compile(r"qoder_protocol\s*\.yaml"))
                frame.locator(f"#{prefix}-composer").evaluate(
                    """(el,text)=>{
                    const transfer=new DataTransfer();
                    transfer.items.add(new File([text],'drag-protocol.txt',{type:'text/plain'}));
                    el.dispatchEvent(new DragEvent('drop',{bubbles:true,cancelable:true,dataTransfer:transfer}));
                }""",
                    fixture.read_text(encoding="utf-8"),
                )
                expect(frame.locator(f"#{prefix}-composer")).to_contain_text(re.compile(r"drag-protocol\s*\.txt"))
                field.evaluate("e=>e.setSelectionRange(1,1)")
                field.press("Control+Enter")
                expect(field).to_have_value("甲\n乙")
                field.press("Shift+Enter")
                expect(field).to_have_value("甲\n\n乙")
                field.dispatch_event("keydown", {"key": "Enter", "code": "Enter", "isComposing": True})
                field.dispatch_event("keydown", {"key": "Enter", "code": "Enter", "repeat": True})
                assert messages() == before
                field.fill("明确使用测试后台验证输入框")
                field.press("Enter")
                expect(field).to_have_value("", timeout=30000)
                history = "ai-console-chat-history" if prefix == "ai-console" else "ai-chat-history"
                expect(frame.locator("#" + history)).to_contain_text("测试模式回答", timeout=60000)
                assert messages() == before + 2
                choose(frame, prefix, "backend", "Qoder CLI")
                expect(frame.locator(f"#{prefix}-model input")).to_have_value("默认模型", timeout=30000)
                choose(frame, prefix, "permission", "项目编辑")
                choose(frame, prefix, "reasoning", "高")
                frame.locator(f"#{prefix}-reasoning input").press("Escape")
                field.click()
                page.wait_for_timeout(300)
                controls = [
                    frame.locator(f"#{prefix}-{name}").bounding_box()
                    for name in ("backend", "permission", "model", "reasoning", "send")
                ]
                assert all(controls)
                assert all(control["height"] >= 30 and control["width"] >= 35 for control in controls), controls
                assert all(
                    left["x"] + left["width"] <= right["x"] + 2
                    for left, right in zip(controls, controls[1:], strict=False)
                )
                toolbar = frame.locator(f"#{prefix}-composer-footer").bounding_box()
                assert toolbar["height"] <= 48, toolbar
                page.screenshot(path=str(output / (prefix + "-light.jpg")), type="jpeg", quality=90)
                before_auth = messages()
                field.fill("你好，请仅回复你好")
                field.press("Enter")
                expect(frame.locator("#" + history)).to_contain_text(
                    re.compile("尚未登录|认证状态检查失败"), timeout=30000
                )
                expect(field).to_have_value("你好，请仅回复你好")
                assert messages() == before_auth + 2
                page.screenshot(path=str(output / (prefix + "-auth-required.jpg")), type="jpeg", quality=90)
                field.fill("")
                choose(frame, prefix, "backend", "模型 API")
                expect(frame.locator(f"#{prefix}-permission input")).to_have_value("只读", timeout=30000)
                assert frame.locator(f"#{prefix}-input textarea").evaluate("e=>e.matches(':placeholder-shown')")
                results.append(
                    {
                        "prefix": prefix,
                        "keyboard": True,
                        "single_send": True,
                        "permissions_reset": True,
                        "attachments_and_drop": True,
                        "native_qoder_auth_failure_visible": True,
                        "toolbar": toolbar,
                        "controls": controls,
                    }
                )

            check("ai-console")
            page.locator("#app-theme-toggle").click()
            page.screenshot(path=str(output / "workbench-dark.jpg"), type="jpeg", quality=90)
            page.locator("#app-theme-toggle").click()
            page.goto(base + "/app/?module=strategy&view=etf")
            frame = page.frame_locator("iframe.workspace-frame.active")
            expect(frame.locator('#ai-floating-button[data-drag-ready="1"]')).to_be_visible(timeout=90000)
            frame.locator("#ai-floating-button").click()
            expect(frame.locator("#ai-chat-input textarea")).to_be_visible(timeout=30000)
            check("ai-chat")
            page.locator("#app-theme-toggle").click()
            page.screenshot(path=str(output / "floating-dark.jpg"), type="jpeg", quality=90)
            page.set_viewport_size({"width": 1180, "height": 900})
            page.wait_for_timeout(600)
            panel = frame.locator("#ai-floating-panel").bounding_box()
            assert panel["x"] >= 0 and panel["x"] + panel["width"] <= 1180, panel
            assert frame.locator("#ai-chat-composer-footer").bounding_box()["height"] <= 48
            page.screenshot(path=str(output / "floating-compact.jpg"), type="jpeg", quality=90)
            assert not errors, errors
        except Exception:
            page.screenshot(path=str(output / "failure.jpg"), type="jpeg", quality=90)
            raise
        finally:
            (output / "browser.json").write_text(
                json.dumps(
                    {"results": results, "page_errors": errors, "model_scope": "explicit_mock_no_real_reply_claim"},
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            browser.close()
        logger.info("Composer browser acceptance passed for both inputs")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    main(args.base, args.output)
