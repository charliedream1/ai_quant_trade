"""Single WebSocket endpoint with topic subscriptions."""

from __future__ import annotations

import asyncio
import json
from concurrent.futures import Future
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect

from src.core.logger import get_logger
from src.core.security_config import security_config
from src.core.timeutil import utc_now_iso


class WebSocketHub:
    def __init__(self) -> None:
        self.active: set[WebSocket] = set()
        self.subscriptions: dict[WebSocket, set[str]] = {}
        self._loop: asyncio.AbstractEventLoop | None = None
        self.log = get_logger("api.ws_hub")
        self.send_locks: dict = {}

    async def connect(self, websocket: WebSocket) -> None:
        if len(self.active) >= security_config()["limits"]["websocket_clients"]:
            await websocket.close(code=1013)
            return
        await websocket.accept()
        self._loop = asyncio.get_running_loop()
        self.active.add(websocket)
        self.subscriptions[websocket] = set()
        self.send_locks[websocket] = asyncio.Lock()

    def disconnect(self, websocket: WebSocket) -> None:
        self.active.discard(websocket)
        self.subscriptions.pop(websocket, None)
        self.send_locks.pop(websocket, None)

    @property
    def client_count(self) -> int:
        return len(self.active)

    async def send(self, websocket: WebSocket, topic: str, event_type: str, payload: dict[str, Any]) -> None:
        async def guarded_send():
            async with self.send_locks.setdefault(websocket, asyncio.Lock()):
                await websocket.send_text(
                    json.dumps(
                        {"topic": topic, "type": event_type, "payload": payload, "ts": utc_now_iso()},
                        ensure_ascii=False,
                    )
                )

        await asyncio.wait_for(guarded_send(), security_config()["limits"]["websocket_send_seconds"])

    async def broadcast(self, topic: str, event_type: str, payload: dict[str, Any]) -> None:
        sockets = [ws for ws, topics in list(self.subscriptions.items()) if topic in topics]
        results = await asyncio.gather(
            *(self.send(ws, topic, event_type, payload) for ws in sockets), return_exceptions=True
        )
        for ws, result in zip(sockets, results, strict=True):
            if isinstance(result, BaseException):
                self.disconnect(ws)

    def broadcast_nowait(self, topic: str, event_type: str, payload: dict[str, Any]) -> None:
        loop = self._loop
        if loop is None or loop.is_closed():
            self.log.debug("websocket broadcast skipped | topic={} type={} reason=no_loop", topic, event_type)
            return
        future = asyncio.run_coroutine_threadsafe(self.broadcast(topic, event_type, payload), loop)
        future.add_done_callback(self._log_broadcast_error)

    async def endpoint(self, websocket: WebSocket) -> None:
        await self.connect(websocket)
        if websocket not in self.active:
            return
        try:
            while True:
                raw = await websocket.receive_text()
                if len(raw) > security_config()["limits"]["websocket_message_chars"]:
                    await websocket.close(code=1009)
                    return
                try:
                    message = json.loads(raw)
                    if (
                        not isinstance(message, dict)
                        or not isinstance(message.get("params", {}), dict)
                        or not isinstance(message.get("topic", "system"), str)
                    ):
                        raise ValueError("消息必须为对象")
                except (ValueError, TypeError):
                    await self.send(websocket, "system", "error", {"message": "消息不是合法 JSON"})
                    continue
                action = message.get("action")
                topic = self._topic_name(message)
                seq = message.get("seq")
                if action == "subscribe":
                    if len(self.subscriptions.get(websocket, ())) >= security_config()["limits"]["websocket_topics"]:
                        await self.send(websocket, "system", "error", {"message": "订阅数已达上限"})
                        continue
                    self.subscriptions.setdefault(websocket, set()).add(topic)
                    await self.send(websocket, topic, "subscribed", {"seq": seq})
                elif action == "unsubscribe":
                    self.subscriptions.setdefault(websocket, set()).discard(topic)
                    await self.send(websocket, topic, "unsubscribed", {"seq": seq})
                elif action == "ping":
                    await self.send(websocket, topic or "system", "pong", {"seq": seq})
                else:
                    await self.send(websocket, topic or "system", "error", {"message": "不支持的 action", "seq": seq})
        except WebSocketDisconnect:
            pass
        finally:
            self.disconnect(websocket)

    def _topic_name(self, message: dict[str, Any]) -> str:
        topic = message.get("topic") or "system"
        params = message.get("params") or {}
        if topic == "backtest" and params.get("task_id"):
            return f"backtest:{params['task_id']}"
        if topic == "cli" and params.get("session_id"):
            return f"cli:{params['session_id']}"
        if topic == "paper" and params.get("account_id"):
            return f"paper:{params['account_id']}"
        if topic == "live" and params.get("run_id"):
            return f"live:{params['run_id']}"
        return topic

    def _log_broadcast_error(self, future: Future[None]) -> None:
        try:
            future.result()
        except Exception as exc:
            self.log.warning("websocket broadcast failed | error={}", exc)


ws_hub = WebSocketHub()
