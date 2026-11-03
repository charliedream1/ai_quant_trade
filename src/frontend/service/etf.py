"""ETF research callbacks shared by the strategy workspace."""

from __future__ import annotations

import pandas as pd

from src.data.etf import ETFUniverseService

from .foundation import styled_frame, to_frame, ui_error_message

ETF_SNAPSHOT_COLUMNS = [
    "symbol",
    "name",
    "benchmark",
    "category",
    "expense_ratio",
    "latest_price",
    "change_pct",
    "average_amount",
    "history_points",
    "status",
    "data_source",
]


class ETFServiceMixin:
    def etf_universe_choices(self) -> list[tuple[str, str]]:
        return [(str(item["label"]), str(item["universe"])) for item in ETFUniverseService().list_universes()]

    def etf_universe_snapshot(self, universe: str) -> tuple[str, pd.DataFrame]:
        try:
            payload = ETFUniverseService().snapshot(str(universe or "cn_core"))
            status = (
                f"ETF池 `{payload['label']}`：可用 {payload['available_count']} / {len(payload['symbols'])}；"
                f"基准 `{payload.get('benchmark') or '-'}`；调仓 `{payload.get('rebalance_frequency') or '-'}`。"
                "缺失数据保持为空，不用零值替代。"
            )
            return status, styled_frame(
                payload["symbols"], ETF_SNAPSHOT_COLUMNS, gradient=["change_pct", "average_amount"]
            )
        except Exception as exc:
            return f"ETF池读取失败：{ui_error_message(exc)}", to_frame([], ETF_SNAPSHOT_COLUMNS)
