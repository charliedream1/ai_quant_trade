"""Semantic color scales for homepage and custom-dashboard tables."""

from __future__ import annotations

from typing import Any

import pandas as pd

from src.data import current_market

from .home_config import color, home_config
from .home_data import number

SIGNED_COLUMNS = frozenset({"change_pct", "float_pnl", "float_pnl_pct", "daily_pnl", "total_pnl", "score"})
SIZE_COLUMNS = frozenset({"market_value", "amount", "volume", "turnover_rate"})
STATUS_COLUMNS = frozenset({"priority", "status"})


def _cell_style(accent: str, strength: float) -> str:
    config = home_config()["colors"]
    intensity = float(config["scale_min_intensity"]) + strength * (
        float(config["scale_max_intensity"]) - float(config["scale_min_intensity"])
    )
    # Gradio preserves custom properties in the Styler metadata. CSS uses theme-local surfaces for contrast.
    return f"--home-cell-color: {accent}; --home-cell-strength: {intensity:.1f}%;"


def home_styled_frame(frame: pd.DataFrame, *, extra_signed_columns=(), scale_group=None) -> Any:
    if frame.empty:
        return frame
    styles = pd.DataFrame("", index=frame.index, columns=frame.columns)
    signed_columns = SIGNED_COLUMNS | set(extra_signed_columns)
    gain, loss = ("loss", "gain") if current_market() == "US" else ("gain", "loss")
    for column in frame.columns:
        if column in signed_columns | SIZE_COLUMNS:
            values = pd.to_numeric(frame[column].map(number), errors="coerce")
            bounds = values.abs().groupby(frame[scale_group]).transform("max") if scale_group else None
            maximum = values.abs().max()
            for index, value in values.items():
                bound = maximum if bounds is None else bounds.loc[index]
                if pd.isna(value) or not bound or value == 0:
                    continue
                accent = color(gain if value > 0 else loss) if column in signed_columns else color("blue")
                styles.loc[index, column] = _cell_style(accent, min(abs(value) / bound, 1))
        if column in STATUS_COLUMNS:
            for index, value in frame[column].items():
                text = str(value)
                if text in {"高", "失败", "failed", "error", "超限", "高风险"}:
                    styles.loc[index, column] = _cell_style(color("gain"), 1)
                elif text in {"中", "关注", "待配置", "paused", "待处理"}:
                    styles.loc[index, column] = _cell_style(color("amber"), 0.7)
                elif text in {"正常", "完成", "completed", "running", "运行中", "success", "启用"}:
                    styles.loc[index, column] = _cell_style(color("blue"), 0.5)
    formats = {}
    for column in frame.select_dtypes(include="number").columns:
        if column in {"change_pct", "float_pnl_pct", "turnover_rate"}:
            formats[column] = "{:+,.2f}%"
        elif column in signed_columns:
            formats[column] = "{:+,.2f}"
        elif column in SIZE_COLUMNS | {"latest_price", "price"}:
            formats[column] = "{:,.2f}"
        elif column in {"quantity", "available_qty"}:
            formats[column] = "{:,.0f}"
    return frame.style.apply(lambda _: styles, axis=None).format(formats, na_rep="—")
