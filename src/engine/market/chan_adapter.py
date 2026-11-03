"""Adapter for optional Chan theory analysis integration."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from src.core.config import get_settings
from src.core.process_env import process_environment

_SUBPROCESS_TIMEOUT_SECONDS = 8
_FALLBACK_LOOKBACK = 20


class ChanAnalysisAdapter:
    """Run the external Chan analyzer in isolation, falling back to local K-line scoring."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or get_settings().chan_analyzer_root

    def analyze(self, symbol: str, name: str, kline: list[dict[str, Any]]) -> dict[str, Any]:
        """Return a compact score payload for recommendation ranking."""
        fallback = self._fallback_analysis(symbol, kline)
        if not self._is_external_available():
            return fallback
        external = self._external_analysis(symbol, name, kline)
        if external is None:
            return fallback
        fallback.update(external)
        return fallback

    def _is_external_available(self) -> bool:
        if self.root is None:
            return False
        root = Path(self.root)
        return (root / "src" / "chan" / "engine.py").exists() and (root / "src" / "gates" / "gate_engine.py").exists()

    def _external_analysis(self, symbol: str, name: str, kline: list[dict[str, Any]]) -> dict[str, Any] | None:
        if self.root is None or len(kline) < 30:
            return None
        root = Path(self.root)
        payload = {"root": str(root), "symbol": symbol, "name": name, "kline": kline}
        script = r"""
import contextlib
import io
import json
import sys

payload = json.loads(sys.stdin.read())
sys.path.insert(0, payload["root"])

import pandas as pd
from src.chan.engine import ChanEngine
from src.gates.gate_engine import GateEngine

df = pd.DataFrame(payload["kline"])
required = ["date", "open", "high", "low", "close", "volume"]
for column in required:
    if column not in df.columns:
        df[column] = 0
df = df[required]
with contextlib.redirect_stdout(io.StringIO()):
    chan_result = ChanEngine(config={}).analyze(df, payload["symbol"], "daily", payload.get("name") or "")
    report = GateEngine().run(chan_result)
report_data = report.to_dict()
state = getattr(chan_result, "current_state", {}) or {}
output = {
    "external_available": True,
    "source": "external_chan_analyzer",
    "output_level": report_data.get("output_level"),
    "signal": (report_data.get("current_signal") or {}).get("signal_type") or state.get("latest_signal") or "none",
    "trend": report_data.get("trend_type") or state.get("trend") or "unknown",
    "verdict": report_data.get("verdict") or "",
    "gate_passed": report_data.get("all_passed"),
    "failure_point": report_data.get("failure_point"),
    "target_price": report_data.get("target_price"),
    "risk_reward_ratio": report_data.get("risk_reward_ratio"),
    "structure_counts": {
        "fractals": len(getattr(chan_result, "fractals", []) or []),
        "bis": len(getattr(chan_result, "bis", []) or []),
        "segments": len(getattr(chan_result, "segments", []) or []),
        "hubs": len(getattr(chan_result, "hubs", []) or []),
        "signals": len(getattr(chan_result, "signals", []) or []),
    },
}
sys.stdout.write(json.dumps(output, ensure_ascii=False, default=str))
"""
        env = process_environment("model")
        env["PYTHONIOENCODING"] = "utf-8"
        env.pop("PYTHONPATH", None)
        try:
            completed = subprocess.run(
                [sys.executable, "-c", script],
                cwd=str(root),
                input=json.dumps(payload, ensure_ascii=False, default=str),
                text=True,
                encoding="utf-8",
                capture_output=True,
                timeout=_SUBPROCESS_TIMEOUT_SECONDS,
                check=False,
                env=env,
            )
        except (OSError, subprocess.SubprocessError, subprocess.TimeoutExpired):
            return None
        if completed.returncode != 0 or not completed.stdout.strip():
            return None
        try:
            result = json.loads(completed.stdout)
        except json.JSONDecodeError:
            return None
        return self._score_external(result)

    def _score_external(self, result: dict[str, Any]) -> dict[str, Any]:
        output_level = str(result.get("output_level") or "observe")
        signal = str(result.get("signal") or "none")
        trend = str(result.get("trend") or "unknown")
        base_by_level = {
            "confirmed_buy": 92.0,
            "strong_observe": 78.0,
            "observe": 64.0,
            "confirmed_sell": 28.0,
        }
        score = base_by_level.get(output_level, 58.0)
        if signal.startswith("buy"):
            score += 5.0
        elif signal.startswith("sell"):
            score -= 12.0
        if trend in {"up_trend", "breakout_up", "bullish"}:
            score += 3.0
        elif trend in {"down_trend", "breakout_down", "bearish"}:
            score -= 4.0
        counts = result.get("structure_counts") or {}
        if int(counts.get("hubs") or 0) > 0:
            score += 2.0
        score = round(max(0.0, min(100.0, score)), 2)
        return {
            **result,
            "score": score,
            "reason": self._external_reason(result),
        }

    def _external_reason(self, result: dict[str, Any]) -> str:
        output_level = str(result.get("output_level") or "observe")
        signal = str(result.get("signal") or "none")
        verdict = str(result.get("verdict") or "").strip()
        counts = result.get("structure_counts") or {}
        structure = (
            f"分型{int(counts.get('fractals') or 0)} / 笔{int(counts.get('bis') or 0)} / "
            f"线段{int(counts.get('segments') or 0)} / 中枢{int(counts.get('hubs') or 0)}"
        )
        if verdict:
            return f"外部缠论门控：{output_level}，信号 {signal}；{structure}；{verdict}"
        return f"外部缠论门控：{output_level}，信号 {signal}；{structure}"

    def _fallback_analysis(self, symbol: str, kline: list[dict[str, Any]]) -> dict[str, Any]:
        closes = [self._safe_float(item.get("close")) for item in kline if self._safe_float(item.get("close")) > 0]
        highs = [self._safe_float(item.get("high")) for item in kline if self._safe_float(item.get("high")) > 0]
        lows = [self._safe_float(item.get("low")) for item in kline if self._safe_float(item.get("low")) > 0]
        if len(closes) < 8:
            return {
                "external_available": False,
                "source": "fallback_kline_structure",
                "score": 50.0,
                "signal": "observe",
                "trend": "unknown",
                "reason": "缠论分析器未配置或K线不足，暂按观察处理",
            }
        lookback = min(_FALLBACK_LOOKBACK, len(closes) - 1)
        recent_return = (closes[-1] / closes[-lookback - 1] - 1) * 100
        recent_high = max(highs[-lookback:]) if highs else closes[-1]
        recent_low = min(lows[-lookback:]) if lows else closes[-1]
        position = (closes[-1] - recent_low) / max(recent_high - recent_low, 0.01)
        swings = self._swing_count(closes[-min(len(closes), 40) :])
        score = 52.0 + recent_return * 1.6 + (position - 0.5) * 18.0 + min(swings, 8) * 1.2
        score = round(max(0.0, min(100.0, score)), 2)
        if recent_return > 6 and position > 0.62:
            signal = "buy2_observe"
            trend = "up_trend"
            reason = "K线结构偏强，近段涨幅与区间位置支持类二买观察"
        elif recent_return < -6 and position < 0.38:
            signal = "sell_observe"
            trend = "down_trend"
            reason = "K线结构走弱，近段回撤与区间位置提示卖点风险观察"
        else:
            signal = "hub_observe"
            trend = "consolidation"
            reason = "K线结构以震荡为主，适合等待中枢方向重新选择"
        return {
            "external_available": False,
            "source": "fallback_kline_structure",
            "score": score,
            "signal": signal,
            "trend": trend,
            "reason": f"{symbol}：{reason}；外部缠论门控未启用或执行失败，使用轻量结构评分",
        }

    @staticmethod
    def _safe_float(value: Any) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _swing_count(values: list[float]) -> int:
        count = 0
        for index in range(1, len(values) - 1):
            previous_value = values[index - 1]
            current_value = values[index]
            next_value = values[index + 1]
            if (current_value > previous_value and current_value > next_value) or (
                current_value < previous_value and current_value < next_value
            ):
                count += 1
        return count
