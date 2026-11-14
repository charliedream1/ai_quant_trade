"""Same-origin page lifetime control and early Gradio transport instrumentation."""

import json
from html import escape
from pathlib import Path
from urllib.parse import parse_qs

from fastapi import APIRouter, HTTPException, Request
from starlette.datastructures import Headers
from starlette.responses import Response

from src.core.page_work import PageCancelled, activate, context, deactivate, policy, resolve

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
        if payload["action"] == "activate":
            page = activate(payload["owner"], payload["revision"])
            return {"active": not page.is_set()}
        if payload["action"] == "deactivate":
            deactivate(payload["owner"], payload["revision"])
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
