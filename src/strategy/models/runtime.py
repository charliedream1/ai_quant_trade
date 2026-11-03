"""Daily cross-sectional model strategies with delayed, point-in-time decisions."""

from __future__ import annotations

from importlib import import_module
from time import perf_counter
from typing import Any

import numpy as np

from src.core.exceptions import BusinessError, ErrorCode
from src.core.logger import get_logger

from .config import BACKEND_MODULES, model_config
from .features import FeatureRow, build_panel, time_split

LOG = get_logger("strategy.models")


class ModelStrategy:
    """Train on matured labels, rank yesterday's features, execute today."""

    required_order_type = "open"
    history: dict[str, list[dict[str, Any]]]

    def warmup(self, history: dict[str, list[dict[str, Any]]]) -> None:
        """Seed observations only; no historical orders, fits or account mutations."""
        calendars = {
            tuple(str(row.get("date") or row.get("timestamp"))[:10] for row in rows) for rows in history.values()
        }
        if len(calendars) > 1:
            raise ValueError("模型预热日历不一致，请补齐历史数据")
        self.history = {
            symbol: [dict(row, timestamp=str(row.get("date") or row.get("timestamp"))) for row in rows][
                -int(self.config["history_limit"]) :
            ]
            for symbol, rows in history.items()
        }
        self.day = max((str(row["timestamp"])[:10] for rows in self.history.values() for row in rows), default="")

    def __init__(self, profile: str, params: dict[str, Any] | None = None) -> None:
        self.profile = profile
        self.config = model_config(profile, params)
        self.history = {}
        self.day = ""
        self.model: Any = None
        self.cycles = 0
        self.last_fit_cycle = -int(self.config["retrain_interval"])
        self.decisions: dict[str, dict[str, Any]] = {}
        self.fits: list[dict[str, Any]] = []
        self.predictions: list[dict[str, Any]] = []
        self.total_fit_ms = 0.0
        self.signal_count = 0

    def on_start(self, context: dict[str, Any]) -> None:
        order_type = (context.get("metadata") or {}).get("order_type")
        if context.get("mode") == "backtest" and order_type != "open":
            raise ValueError("模型策略使用上一交易日信号，请将订单类型选择为开盘价（open）")
        if context.get("mode") == "backtest" and len(context.get("symbols") or []) < 2:
            raise ValueError("截面模型至少需要两个标的")
        context["metadata"]["requires_aligned_calendar"] = True
        context["metadata"]["model_diagnostics"] = {"profile": self.profile, "status": "warming_up"}

    def on_bar(self, bar: dict[str, Any], context: dict[str, Any]) -> list[dict[str, Any]]:
        day = str(bar.get("timestamp") or bar.get("date") or "")[:10]
        if self.day and day < self.day:
            raise ValueError("模型策略要求行情按日期递增")
        if day != self.day:
            self._prepare_decisions()
            self.day = day
        symbol = str(bar["symbol"])
        values = self.history.setdefault(symbol, [])
        if values and str(values[-1]["timestamp"])[:10] == day:
            raise ValueError("模型策略不接受同标的同日期重复行情")
        values.append(dict(bar))
        del values[: -int(self.config["history_limit"])]
        decision = self.decisions.get(symbol)
        if decision is None:
            return []
        if decision["forecast_date"] >= day:
            raise ValueError("预测日期必须早于执行日期")
        self.signal_count += 1
        return [
            {
                "symbol": symbol,
                "side": decision["side"],
                "quantity": int(self.config["quantity"]) if decision["side"] == "buy" else 0,
                "reason": f"{self.profile}:{decision['forecast_date']}",
                "model_score": decision["score"],
                "forecast_date": decision["forecast_date"],
            }
        ]

    def _prepare_decisions(self) -> None:
        self.decisions = {}
        if not self.history:
            return
        self.cycles += 1
        panel = build_panel(self.history, self.config)
        train, validation = time_split(panel, self.config)
        if not train:
            return
        if self.model is None or self.cycles - self.last_fit_cycle >= int(self.config["retrain_interval"]):
            self._fit(train, validation)
        current = [row for row in panel if row.date == self.day]
        if not current:
            return
        scores = np.asarray(self.model.predict(np.asarray([row.values for row in current], dtype=float)))
        if scores.shape != (len(current),) or not np.isfinite(scores).all():
            raise ValueError("模型预测包含非法数值或维度不匹配")
        ranked = sorted(zip(current, scores, strict=True), key=lambda item: (-float(item[1]), item[0].symbol))
        leaders = {
            row.symbol
            for row, score in ranked[: int(self.config["top_n"])]
            if float(score) > float(self.config["min_score"])
        }
        for row, score in ranked:
            self.decisions[row.symbol] = {
                "side": "buy" if row.symbol in leaders else "sell",
                "score": float(score),
                "forecast_date": row.date,
            }
            self.predictions.append({"symbol": row.symbol, "date": row.date, "score": float(score)})

    def _fit(self, train: list[FeatureRow], validation: list[FeatureRow]) -> None:
        started = perf_counter()
        try:
            backend = import_module(BACKEND_MODULES[self.config["backend"]])
        except ImportError as exc:
            raise BusinessError(
                ErrorCode.CONFIG_DEPENDENCY,
                f"模型依赖 {self.config['backend']} 不可用，请使用 requirements-models.txt 对应环境",
            ) from exc
        model = backend.build_model(dict(self.config["model_params"]))
        x = np.asarray([row.values for row in train], dtype=float)
        y = np.asarray([row.target for row in train], dtype=float)
        model.fit(x, y)
        validation_prediction = np.asarray(model.predict(np.asarray([row.values for row in validation])))
        validation_targets = np.asarray([row.target for row in validation], dtype=float)
        if not np.isfinite(validation_prediction).all():
            raise ValueError("模型验证预测包含非法数值")
        elapsed = (perf_counter() - started) * 1000
        self.total_fit_ms += elapsed
        self.model = model
        self.last_fit_cycle = self.cycles
        self.fits.append(
            {
                "as_of": self.day,
                "train_start": min(row.date for row in train),
                "train_end": max(row.date for row in train),
                "label_end": max(row.target_date for row in train),
                "validation_start": min(row.date for row in validation),
                "validation_end": max(row.target_date for row in validation),
                "train_samples": len(train),
                "validation_samples": len(validation),
                "validation_mse": float(np.mean((validation_prediction - validation_targets) ** 2)),
                "duration_ms": round(elapsed, 2),
            }
        )
        LOG.info(
            "model fitted | profile={} samples={} as_of={} duration_ms={:.1f}",
            self.profile,
            len(train),
            self.day,
            elapsed,
        )

    def on_stop(self, context: dict[str, Any]) -> None:
        report = self.diagnostics()
        context["metadata"]["model_diagnostics"] = report
        if context.get("mode") == "backtest" and not self.fits:
            raise BusinessError(ErrorCode.INVALID_PARAM, "有效训练样本不足，模型未完成拟合；请扩大股票池或日期范围")

    def diagnostics(self) -> dict[str, Any]:
        panel = build_panel(self.history, self.config)
        labels = {(row.symbol, row.date): row.target for row in panel if row.target is not None}
        paired = [
            (row["score"], labels[(row["symbol"], row["date"])])
            for row in self.predictions
            if (row["symbol"], row["date"]) in labels
        ]
        mse = float(np.mean([(score - float(target)) ** 2 for score, target in paired])) if paired else None
        return {
            "profile": self.profile,
            "title": self.config["title"],
            "backend": self.config["backend"],
            "status": "fitted" if self.fits else "warming_up",
            "fit_count": len(self.fits),
            "prediction_count": len(self.predictions),
            "evaluated_prediction_count": len(paired),
            "oos_mse": mse,
            "signal_count": self.signal_count,
            "fit_duration_ms": round(self.total_fit_ms, 2),
            "fit_history": self.fits,
            "execution": "previous_close_features_next_open",
            "config": self.config,
        }
