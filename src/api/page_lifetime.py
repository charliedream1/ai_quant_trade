"""Same-origin page lifetime control and early Gradio transport instrumentation."""

import json
import re
from html import escape
from pathlib import Path
from urllib.parse import parse_qs

from fastapi import APIRouter, HTTPException, Request
from starlette.datastructures import Headers
from starlette.responses import Response

from src.core.async_work import blocking_call
from src.core.logger import get_logger
from src.core.page_work import PageCancelled, activate, context, deactivate, policy, resolve
from src.frontend.common.navigation import navigation_config
from src.frontend.registry import MODULES

router = APIRouter(prefix="/workspace", tags=["workspace"])


def request_page(headers, query):
    owner = headers.get("x-aiquant-page") or query.get("page_owner", [""])[0]
    revision = headers.get("x-aiquant-revision") or query.get("page_revision", [""])[0]
    return resolve(owner, revision) if owner and revision else None


@router.post("/lifetime", include_in_schema=False)
async def lifetime(request: Request):
    if request.headers.get("origin") != str(request.base_url.replace(path="", query="")):
        raise HTTPException(403, "Same-origin lifetime control required")
    raw = b""
    async for chunk in request.stream():
        raw += chunk
        if len(raw) > policy()["lifetime_payload_bytes"]:
            raise HTTPException(413, "Lifetime payload too large")
    try:
        payload = json.loads(raw)
        module = str(payload.get("module") or "unknown")
        view = str(payload.get("view") or "unknown")
        if not all(re.fullmatch(r"[A-Za-z0-9_/-]{1,64}", value) for value in (module, view)):
            raise ValueError("Invalid page label")
        if payload["action"] == "activate":
            page = await blocking_call(activate, payload["owner"], payload["revision"], group="page_lifetime")
            if getattr(page, "view_label", None) != (module, view) and not page.is_set():
                page.view_label = (module, view)
                base, _, tab = view.partition("/")
                label = next(
                    (dict(item.views).get(base, item.title) for item in MODULES if item.key == module), "工作区"
                )
                group = navigation_config()["tab_groups"].get(f"{module}/{base}", {})
                section = group.get("tabs", {}).get(tab, {}).get("label")
                if section:
                    label = f"{label} / {section}"
                get_logger("ui.navigation").info("打开页面 · {}", label)
            return {"active": not page.is_set()}
        if payload["action"] == "deactivate":
            await blocking_call(deactivate, payload["owner"], payload["revision"], group="page_lifetime")
            return {"active": False}
    except (ValueError, TypeError, KeyError):
        raise HTTPException(400, "Invalid lifetime payload") from None
    raise HTTPException(400, "Invalid lifetime action")


@router.get("/lifetime.js", include_in_schema=False)
def lifetime_script():
    path = Path(__file__).resolve().parents[1] / "frontend/assets/page_lifetime.js"
    script = path.read_text(encoding="utf-8").replace("__HEARTBEAT_MS__", str(policy()["heartbeat_seconds"] * 1000))
    script = script.replace("__CANCELLED_MESSAGE__", json.dumps(policy()["messages"]["cancelled"]))
    script = script.replace("__EVENT_PREFIX_CHARS__", str(policy()["event_prefix_chars"]))
    return Response(script, media_type="application/javascript", headers={"Cache-Control": "no-store"})


class PageLifetimeMiddleware:
    def __init__(self, app, api_prefix):
        self.app = app
        self.script = f'<script src="{escape(api_prefix, quote=True)}/workspace/lifetime.js"></script>'.encode()
        self.previews = api_prefix + "/file-previews/"

    async def __call__(self, scope, receive, send):
        path = scope.get("path", "")
        if scope["type"] != "http" or not path.startswith(("/app/", self.previews)) or "/gradio_api/heartbeat/" in path:
            await self.app(scope, receive, send)
            return
        try:
            page = request_page(Headers(scope=scope), parse_qs(scope.get("query_string", b"").decode()))
        except ValueError:
            await Response(status_code=400)(scope, receive, send)
            return
        response_start = None
        chunks = []
        sent_start = False

        async def instrument(message):
            nonlocal response_start, sent_start
            if message["type"] == "http.response.start":
                headers = Headers(raw=message["headers"])
                if "text/html" in headers.get("content-type", ""):
                    response_start = message
                    return
            if message["type"] == "http.response.body" and response_start is not None:
                chunks.append(message.get("body", b""))
                if message.get("more_body"):
                    return
                body = b"".join(chunks).replace(b"<head>", b"<head>" + self.script, 1)
                response_start["headers"] = [
                    (key, value) for key, value in response_start["headers"] if key.lower() != b"content-length"
                ] + [(b"content-length", str(len(body)).encode())]
                await send(response_start)
                sent_start = True
                await send({"type": "http.response.body", "body": body})
                return
            if message["type"] == "http.response.start":
                sent_start = True
            await send(message)

        try:
            with context(page):
                await self.app(scope, receive, instrument)
        except PageCancelled:
            if not sent_start:
                await Response(status_code=204)(scope, receive, send)
