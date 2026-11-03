"""Malformed clients and cold UI construction must not block unrelated work."""

import asyncio
import time
from copy import deepcopy

from src.api import ws_hub as websocket_module
from src.core.config import Settings
from src.core.logger import get_logger
from src.frontend.mounting import LazyGradioASGI


def test_malformed_websocket_remains_usable_and_disconnects(client):
    hub = websocket_module.ws_hub
    initial = hub.client_count
    with client.websocket_connect("/ws") as websocket:
        websocket.send_json(["invalid-shape"])
        assert websocket.receive_json()["type"] == "error"
        websocket.send_json({"action": "ping", "seq": 7})
        pong = websocket.receive_json()
        assert pong["type"] == "pong" and pong["payload"]["seq"] == 7
    assert hub.client_count == initial


def test_slow_websocket_cannot_delay_fast_peer(monkeypatch):
    config = deepcopy(websocket_module.security_config())
    config["limits"]["websocket_send_seconds"] = 0.1
    monkeypatch.setattr(websocket_module, "security_config", lambda: config)

    async def measure():
        delivered = asyncio.Event()
        never = asyncio.Event()

        class Socket:
            def __init__(self, slow):
                self.slow = slow

            async def accept(self):
                pass

            async def send_text(self, value):
                if self.slow:
                    await never.wait()
                else:
                    delivered.set()

        hub = websocket_module.WebSocketHub()
        slow, fast = Socket(True), Socket(False)
        for peer in (slow, fast):
            await hub.connect(peer)
            hub.subscriptions[peer].add("market")
        broadcast = asyncio.create_task(hub.broadcast("market", "quote", {}))
        await asyncio.wait_for(delivered.wait(), timeout=0.5)
        await asyncio.wait_for(broadcast, timeout=0.5)
        assert fast in hub.active and slow not in hub.active
        hub.disconnect(fast)

    asyncio.run(measure())


def test_cold_gradio_build_leaves_event_loop_responsive(monkeypatch):
    async def measure():
        application = LazyGradioASGI(Settings(), get_logger("test.cold"), "/isolated", "ai")
        entered, completed = asyncio.Event(), asyncio.Event()

        async def inner(scope, receive, send):
            completed.set()

        def build():
            time.sleep(0.15)
            return inner

        async def startup():
            entered.set()

        monkeypatch.setattr(application, "_ensure_app", build)
        monkeypatch.setattr(application, "_ensure_started", startup)
        task = asyncio.create_task(application({"type": "http"}, None, None))
        started = time.perf_counter()
        await asyncio.sleep(0.02)
        elapsed = time.perf_counter() - started
        assert not entered.is_set() and elapsed < 0.1
        await task
        assert completed.is_set()

    asyncio.run(measure())
