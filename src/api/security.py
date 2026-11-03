"""One access boundary around REST, Gradio, static data and WebSocket mounts."""

import hashlib
import hmac
import html
import ipaddress
import time
from collections import deque
from urllib.parse import parse_qs, urlsplit

from starlette.datastructures import Headers
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, RedirectResponse

from src.core.env_file import resolve_env_value
from src.core.security_config import security_config


def access_options(settings) -> dict:
    cfg = security_config()["access"]
    mode = resolve_env_value(cfg["mode_env"]) or cfg["default_mode"]
    token = resolve_env_value(cfg["token_env"])
    if (
        mode not in {"local", "token"}
        or mode == "token"
        and (len(token) < cfg["minimum_token_chars"] or not token.isascii())
    ):
        raise ValueError("远程访问需要token模式和足够长度的ALL_IN_ONE_ACCESS_TOKEN")
    hosts = set(cfg["allowed_hosts"])
    hosts.update(item.strip().lower() for item in resolve_env_value(cfg["hosts_env"]).split(",") if item.strip())
    if "*" in hosts:
        raise ValueError("访问主机不能使用通配符")
    if settings.data_mode == "mock":
        hosts.add(cfg["test_host"])
    return {**cfg, "mode": mode, "token": token, "hosts": hosts, "mock": settings.data_mode == "mock"}


class AccessControl:
    def __init__(self, app, options: dict):
        self.app, self.options = app, options
        self.attempts: dict[str, deque] = {}

    async def __call__(self, scope, receive, send):
        if scope["type"] not in {"http", "websocket"}:
            await self.app(scope, receive, send)
            return
        headers = Headers(scope=scope)
        try:
            host = urlsplit("//" + headers.get("host", "")).hostname
        except ValueError:
            host = None
        if host not in self.options["hosts"] or not self._origin_allowed(scope, headers):
            await self._deny(scope, receive, send, 403)
            return
        path = scope.get("path", "")
        if (
            self.options["mode"] == "token"
            and self.options["remote_require_tls"]
            and scope.get("scheme") not in {"https", "wss"}
        ):
            peer = (scope.get("client") or ("", 0))[0]
            try:
                local = ipaddress.ip_address(peer).is_loopback
            except ValueError:
                local = self.options["mock"] and peer == self.options["test_peer"]
            if not local:
                await self._deny(scope, receive, send, 403)
                return
        if scope["type"] == "http" and scope.get("method") not in {"GET", "HEAD", "OPTIONS"}:
            maximum = security_config()["uploads"]["default_bytes"]
            try:
                if int(headers.get("content-length", "0")) > maximum:
                    await JSONResponse(
                        {"code": 413, "message": security_config()["messages"]["too_large"], "data": None},
                        status_code=413,
                    )(scope, receive, send)
                    return
            except ValueError:
                await self._deny(scope, receive, send, 403)
                return
            original_receive, count = receive, 0

            async def limited_receive():
                nonlocal count
                message = await original_receive()
                count += len(message.get("body", b""))
                if count > maximum:
                    raise HTTPException(413, security_config()["messages"]["too_large"])
                return message

            receive = limited_receive
        if path == self.options["health_path"] and scope["type"] == "http":
            await JSONResponse({"status": "ok"})(scope, receive, send)
            return
        if scope["type"] == "http" and path == self.options["login_path"] and self.options["mode"] == "token":
            await self._login(scope, receive, send)
            return
        if not self._authorized(scope, headers):
            await self._deny(scope, receive, send, 401)
            return
        if scope["type"] == "http" and path == self.options["logout_path"] and scope["method"] == "POST":
            response = RedirectResponse(self.options["login_path"], status_code=303)
            response.delete_cookie(self.options["cookie_name"])
            await response(scope, receive, send)
            return
        await self.app(scope, receive, send)

    def _origin_allowed(self, scope, headers) -> bool:
        if headers.get("sec-fetch-site") == "cross-site" and headers.get("sec-fetch-dest") != "document":
            return False
        origin = headers.get("origin")
        if not origin:
            return True  # CLI bearer and trusted local processes have no browser Origin.
        scheme = scope.get("scheme", "http").replace("ws", "http")
        return origin.rstrip("/") == scheme + "://" + headers.get("host", "")

    def _authorized(self, scope, headers) -> bool:
        peer = (scope.get("client") or ("", 0))[0]
        if self.options["mode"] == "local":
            try:
                return ipaddress.ip_address(peer).is_loopback
            except ValueError:
                return self.options["mock"] and peer == self.options["test_peer"]
        if self.options["remote_require_tls"] and scope.get("scheme") not in {"https", "wss"}:
            try:
                if not ipaddress.ip_address(peer).is_loopback:
                    return False
            except ValueError:
                if not self.options["mock"]:
                    return False
        bearer = headers.get("authorization", "")
        if bearer.startswith("Bearer ") and hmac.compare_digest(bearer[7:].encode(), self.options["token"].encode()):
            return True
        request = Request({**scope, "type": "http"})
        cookie = request.cookies.get(self.options["cookie_name"], "")
        try:
            expiry, signature = cookie.split(".", 1)
            expected = hmac.new(self.options["token"].encode(), expiry.encode(), hashlib.sha256).hexdigest()
            return int(expiry) > time.time() and hmac.compare_digest(signature.encode(), expected.encode())
        except ValueError:
            return False

    async def _deny(self, scope, receive, send, status):
        if scope["type"] == "websocket":
            await send({"type": "websocket.close", "code": 1008})
            return
        message = security_config()["messages"]["unauthorized" if status == 401 else "forbidden"]
        response = (
            self._form(status)
            if status == 401 and "text/html" in Headers(scope=scope).get("accept", "")
            else JSONResponse({"code": status, "message": message, "data": None}, status_code=status)
        )
        await response(scope, receive, send)

    def _form(self, status=200):
        ui = security_config()["ui"]
        text = (
            "<!doctype html><html lang='zh-CN'><meta charset='utf-8'><title>"
            + html.escape(ui["title"])
            + "</title><body><h1>"
            + html.escape(ui["title"])
            + "</h1><p>"
            + html.escape(ui["description"])
            + "</p><form method='post' action='"
            + self.options["login_path"]
            + "'><label>"
            + html.escape(ui["token"])
            + "<input type='password' name='token' autocomplete='current-password'></label><button>"
            + html.escape(ui["submit"])
            + "</button></form></body></html>"
        )
        return HTMLResponse(
            text,
            status_code=status,
            headers={
                "Cache-Control": "no-store",
                "Content-Security-Policy": "default-src 'none'; form-action 'self'; frame-ancestors 'none'",
            },
        )

    async def _login(self, scope, receive, send):
        if scope["method"] == "GET":
            await self._form()(scope, receive, send)
            return
        peer = (scope.get("client") or ("", 0))[0]
        if peer not in self.attempts and len(self.attempts) >= self.options["max_attempt_peers"]:
            self.attempts.pop(next(iter(self.attempts)))
        queue = self.attempts.setdefault(peer, deque(maxlen=self.options["max_attempts"]))
        now = time.monotonic()
        while queue and now - queue[0] > self.options["attempt_window_seconds"]:
            queue.popleft()
        if len(queue) >= self.options["max_attempts"]:
            await JSONResponse({"code": 429, "message": "访问验证尝试过多", "data": None}, status_code=429)(
                scope, receive, send
            )
            return
        queue.append(now)
        body = bytearray()
        async for chunk in Request(scope, receive).stream():
            body.extend(chunk)
            if len(body) > self.options["max_login_bytes"]:
                await self._deny(scope, receive, send, 403)
                return
        token = parse_qs(body.decode("utf-8", errors="replace")).get("token", [""])[0]
        if not hmac.compare_digest(token.encode(), self.options["token"].encode()):
            await self._deny(scope, receive, send, 401)
            return
        expiry = str(int(time.time() + self.options["session_seconds"]))
        signature = hmac.new(self.options["token"].encode(), expiry.encode(), hashlib.sha256).hexdigest()
        response = RedirectResponse("/app/", status_code=303)
        response.set_cookie(
            self.options["cookie_name"],
            expiry + "." + signature,
            httponly=True,
            samesite="strict",
            secure=scope.get("scheme") == "https",
            max_age=self.options["session_seconds"],
        )
        queue.clear()
        await response(scope, receive, send)
