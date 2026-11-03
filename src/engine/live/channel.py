"""Live broker channel event handling."""

from __future__ import annotations

from typing import Any

from src.core.exceptions import BusinessError, ErrorCode
from src.core.repository import Repository
from src.core.timeutil import utc_now_iso
from src.engine.live.runner import TERMINAL_RUN_STATUSES, LiveTradingService
from src.integration.broker import (
    BROKER_EVENT_ERROR,
    BROKER_EVENT_HEARTBEAT,
    BrokerAdapterRegistry,
    default_broker_registry,
)


class LiveBrokerEventService:
    def __init__(
        self,
        repo: Repository | None = None,
        registry: BrokerAdapterRegistry | None = None,
    ) -> None:
        self.repo = repo or Repository()
        self.registry = registry or default_broker_registry()
        self.live_service = LiveTradingService(repo=self.repo)

    def adapters(self) -> list[dict[str, Any]]:
        return [info.to_dict() for info in self.registry.list()]

    def handle_event(self, run_id: int, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        event = payload or {}
        run = self.repo.get("live_runs", run_id)
        config = self.live_service.detail_config(int(run["config_id"]))
        adapter = self.registry.describe(str(config.get("channel") or "paper"))
        event_type = _event_type(event)
        if event_type not in adapter.event_types:
            raise BusinessError(
                ErrorCode.INVALID_PARAM,
                f"通道 {adapter.channel} 不支持事件类型：{event_type}",
                {"supported": list(adapter.event_types)},
            )

        status = str(run.get("status") or "")
        if status in TERMINAL_RUN_STATUSES:
            raise BusinessError(ErrorCode.LIVE_STATE_ERROR, f"运行 {run_id} 已停止，不能写入通道事件")
        if not adapter.available and event_type != BROKER_EVENT_ERROR:
            raise BusinessError(
                ErrorCode.LIVE_STATE_ERROR, f"通道 {adapter.channel} 未接入，不能写入 {event_type} 事件"
            )

        if event_type == BROKER_EVENT_HEARTBEAT:
            self.repo.update("live_runs", run_id, {"heartbeat_at": utc_now_iso()})
            result = self.live_service.status(run_id)
        elif event_type == BROKER_EVENT_ERROR:
            result = self.live_service.mark_error(run_id, _event_message(event, adapter.channel))
        else:
            raise BusinessError(ErrorCode.INVALID_PARAM, f"不支持的通道事件类型：{event_type}")

        result["event_type"] = event_type
        result["adapter_channel"] = adapter.channel
        result["adapter_status"] = adapter.status
        result["adapter_available"] = adapter.available
        return result


def _event_type(payload: dict[str, Any]) -> str:
    raw = payload.get("event_type") or payload.get("type") or payload.get("event") or BROKER_EVENT_HEARTBEAT
    return str(raw).strip().lower() or BROKER_EVENT_HEARTBEAT


def _event_message(payload: dict[str, Any], channel: str) -> str:
    raw = payload.get("message") or payload.get("reason") or payload.get("error_msg") or "通道异常事件"
    return f"{channel} 通道事件冻结：{str(raw).strip() or '通道异常事件'}"
