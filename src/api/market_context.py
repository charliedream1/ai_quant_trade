"""Per-request market selection, independent of the legacy UI default."""

from urllib.parse import parse_qs

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from src.data.manager import REQUEST_MARKET


class MarketContextMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        params = parse_qs(scope.get("query_string", b"").decode("utf-8", errors="replace"))
        selected = params.get("market", [""])[-1].upper()
        # Native Qlib also uses market names such as csi300.
        header = dict(scope.get("headers") or []).get(b"x-aiquant-market", b"").decode("ascii", errors="replace")
        if header and header.upper() not in {"CN", "US"}:
            response = JSONResponse({"code": 1002, "message": "市场必须为 CN 或 US", "data": None})
            await response(scope, receive, send)
            return
        token = REQUEST_MARKET.set(header.upper() or (selected if selected in {"CN", "US"} else None))
        try:
            await self.app(scope, receive, send)
        finally:
            REQUEST_MARKET.reset(token)
