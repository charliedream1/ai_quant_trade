"""Monitoring callbacks share one asynchronous result contract across pages."""

from __future__ import annotations

from typing import Any

import pandas as pd

from src.engine.research.factor_monitor import FactorMonitorService
from src.engine.research.monitor_jobs import monitor_job, start_monitor

from .dashboard_views import _dashboard_kpis_html
from .foundation import FACTOR_ALERT_COLUMNS, FACTOR_METRIC_COLUMNS, FACTOR_SNAPSHOT_COLUMNS, styled_frame, to_frame
from .visuals import (
    factor_correlation_figure,
    factor_diagnostic_figure,
    factor_ic_figure,
    factor_quantile_figure,
    factor_quantile_history_figure,
    factor_style_exposure_figure,
)


class MonitoringUIMixin:
    def factor_ui_settings(self) -> dict[str, Any]:
        config = FactorMonitorService()._config()
        return {name: config[name] for name in ("ui_poll_seconds", "ui_event_lines", "default_universe_id")}

    def factor_universe_options(self) -> list[tuple[str, str]]:
        return [(row["label"], row["id"]) for row in FactorMonitorService().universes()]

    def factor_start_job(
        self,
        text: str,
        universe_id: str,
        resource_id: Any,
        backend: str,
        as_of: str,
        membership_version: str,
        refresh: bool,
        compare: list[str],
        owner: str,
    ) -> str:
        return start_monitor(
            {
                "universe_text": text or "",
                "universe_id": universe_id,
                "resource_id": int(resource_id) if resource_id else None,
                "backend": backend,
                "as_of": str(as_of or "").strip(),
                "membership_version": str(membership_version or "").strip(),
                "force_refresh": bool(refresh),
                "compare_universes": compare or [],
            },
            owner,
        )

    def factor_job(self, identifier: str, owner: str) -> dict[str, Any]:
        return monitor_job(identifier, owner)

    def factor_result_values(self, payload: dict[str, Any]) -> tuple[Any, ...]:
        status = payload["status"] + (" 命中缓存。" if payload["cache_hit"] else " 已重新计算。")
        status += " 更新时间：" + payload["refreshed_at"]
        qlib = payload["qlib"]
        qstatus = f"内置监控可用 · Qlib信号分析：{'可用' if qlib['status'] == 'available' else '未配置'} · 版本 {qlib['version']}\n\n{qlib['next_step']}"
        qstatus += "\n\n" + "\n\n".join(payload["limitations"])
        coverage = payload["coverage"]
        rows = [{"item": key, "value": coverage[key]} for key in ("requested", "loaded", "failed")]
        rows.extend({"item": row["symbol"], "value": row["error"]} for row in coverage["failures"])
        return (
            status,
            _dashboard_kpis_html(payload["kpis"]),
            factor_ic_figure(payload["ic_history"]),
            factor_quantile_figure(payload["quantile_returns"]),
            factor_diagnostic_figure(payload["ic_decay"], payload["metrics"]),
            factor_quantile_history_figure(payload["quantile_history"]),
            factor_style_exposure_figure(payload["style_exposure"]),
            styled_frame(
                payload["metrics"], FACTOR_METRIC_COLUMNS, gradient=["rank_ic_mean", "ic", "icir", "coverage"]
            ),
            to_frame(payload["alerts"], FACTOR_ALERT_COLUMNS),
            styled_frame(payload["snapshots"], FACTOR_SNAPSHOT_COLUMNS, gradient=["value"]),
            factor_correlation_figure(payload["correlation"]),
            qstatus,
            pd.DataFrame(rows),
            pd.DataFrame(payload["rolling"]),
            pd.DataFrame(payload["stability"]),
            pd.DataFrame(payload.get("comparison") or []),
        )
