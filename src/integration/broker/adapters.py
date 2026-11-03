"""Broker adapter registry for live trading channels."""

from __future__ import annotations

from dataclasses import asdict, dataclass

BROKER_CHANNEL_PAPER = "paper"
BROKER_CHANNEL_BROKER = "broker"

BROKER_EVENT_HEARTBEAT = "heartbeat"
BROKER_EVENT_ERROR = "error"
SUPPORTED_BROKER_EVENTS = (BROKER_EVENT_HEARTBEAT, BROKER_EVENT_ERROR)


@dataclass(frozen=True)
class BrokerAdapterInfo:
    channel: str
    name: str
    available: bool
    status: str
    note: str
    event_types: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["event_types"] = list(self.event_types)
        return payload


@dataclass(frozen=True)
class StaticBrokerAdapter:
    channel: str
    name: str
    available: bool
    note: str
    event_types: tuple[str, ...] = SUPPORTED_BROKER_EVENTS

    def describe(self) -> BrokerAdapterInfo:
        return BrokerAdapterInfo(
            channel=self.channel,
            name=self.name,
            available=self.available,
            status="可用" if self.available else "未接入",
            note=self.note,
            event_types=self.event_types,
        )

    def start_blocker(self) -> str | None:
        if self.available:
            return None
        return self.note


class BrokerAdapterRegistry:
    def __init__(self, adapters: tuple[StaticBrokerAdapter, ...] | None = None) -> None:
        self._adapters = {adapter.channel: adapter for adapter in adapters or default_broker_adapters()}

    def list(self) -> list[BrokerAdapterInfo]:
        return [adapter.describe() for adapter in self._adapters.values()]

    def get(self, channel: str | None) -> StaticBrokerAdapter:
        key = str(channel or BROKER_CHANNEL_PAPER).strip() or BROKER_CHANNEL_PAPER
        adapter = self._adapters.get(key)
        if adapter:
            return adapter
        return StaticBrokerAdapter(
            channel=key,
            name=f"未知通道 {key}",
            available=False,
            note=f"未知实盘通道：{key}",
        )

    def describe(self, channel: str | None) -> BrokerAdapterInfo:
        return self.get(channel).describe()

    def start_blocker(self, channel: str | None) -> str | None:
        return self.get(channel).start_blocker()


def default_broker_adapters() -> tuple[StaticBrokerAdapter, ...]:
    return (
        StaticBrokerAdapter(
            channel=BROKER_CHANNEL_PAPER,
            name="Paper 模拟通道",
            available=True,
            note="内部模拟通道，可用于发布前 dry-run、心跳和异常事件演练，不触发真实委托。",
        ),
        StaticBrokerAdapter(
            channel=BROKER_CHANNEL_BROKER,
            name="真实券商通道",
            available=False,
            note="真实券商适配器尚未接入，启动会被运行前校验拦截。",
        ),
    )


def default_broker_registry() -> BrokerAdapterRegistry:
    return BrokerAdapterRegistry()
