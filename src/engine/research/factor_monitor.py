"""Unified monitoring facade over dated universes, causal panels and explicit backends."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import yaml

from src.core.repository import Repository
from src.core.timeutil import utc_now_iso
from src.data import DataSourceManager
from src.strategy.factors.cache import FactorCache
from src.strategy.factors.config import factor_set
from src.strategy.factors.statistics import correlation, information_ratio

from .monitor_analysis import monitor_analysis
from .monitor_data import load_history
from .monitor_store import MonitorStore
from .monitor_universe import MonitorUniverses
from .qlib_signal import signal_status

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "egs/factor_monitor.yaml"


class FactorMonitorService:
    def __init__(
        self, repo: Repository | None = None, data: DataSourceManager | None = None, config_path: Path | None = None
    ):
        self.repo, self.data = repo or Repository(), data or DataSourceManager()
        self.config_path = config_path or DEFAULT_CONFIG_PATH

    def _config(self) -> dict[str, Any]:
        return yaml.safe_load(self.config_path.read_text(encoding="utf-8"))

    def default_universe_text(self) -> str:
        return ",".join(self._config()["default_universe"])

    def universes(self) -> list[dict[str, Any]]:
        return [{"id": key, **value} for key, value in self._config()["universes"].items()]

    def definitions(self) -> list[dict[str, Any]]:
        config = self._config()
        thresholds = {row["factor_key"]: row for row in config["factors"]}
        rows = []
        now = utc_now_iso()
        for key, definition in factor_set(config["factor_set"]).items():
            row = {
                "factor_key": key,
                "name": definition["label"],
                "category": "price_volume",
                "expression_key": key,
                "description": definition["label"],
                "direction": "positive",
                "horizon_days": config["default_horizon_days"],
                "rebalance_frequency": "daily",
                "enabled": 1,
                "source": "egs/factor_research.yaml",
                "threshold_ic": thresholds.get(key, {}).get("threshold_ic", 0.0),
                "threshold_coverage": thresholds.get(key, {}).get("threshold_coverage", 0.7),
                "updated_at": now,
            }
            existing = self.repo.db.query_one("SELECT id FROM factor_definitions WHERE factor_key = ?", (key,))
            if existing:
                self.repo.update("factor_definitions", existing["id"], row)
            else:
                self.repo.insert("factor_definitions", {**row, "created_at": now})
            rows.append(row)
        return rows

    def qlib_status(self) -> dict[str, Any]:
        return {**signal_status(), "license": "MIT", "built_in_status": "available"}

    def monitor(
        self,
        universe_text: str = "",
        persist: bool = True,
        *,
        universe_id: str = "custom",
        resource_id: int | None = None,
        backend: str = "builtin",
        as_of: str = "",
        membership_version: str = "",
        force_refresh: bool = False,
        progress: Callable[[str], None] | None = None,
    ) -> dict[str, Any]:
        if backend not in {"builtin", "qlib"}:
            raise ValueError("监控后端仅支持 builtin/qlib，不会静默切换")
        config = self._config()
        universe = MonitorUniverses(self.repo, self.data, config).resolve(
            universe_text, universe_id, resource_id, as_of, membership_version
        )
        store = MonitorStore(self.repo)
        implementation = b"".join(
            path.read_bytes()
            for path in (
                Path(__file__),
                Path(__file__).with_name("monitor_analysis.py"),
                PROJECT_ROOT / "src/strategy/factors/research.py",
                PROJECT_ROOT / "src/strategy/factors/panel.py",
                PROJECT_ROOT / "egs/factor_research.yaml",
                Path(__file__).with_name("monitor_data.py"),
                Path(__file__).with_name("monitor_universe.py"),
                Path(__file__).with_name("qlib_signal.py"),
                Path(__file__).with_name("qlib_signal_worker.py"),
                PROJECT_ROOT / "src/strategy/factors/statistics.py",
            )
        )
        key = hashlib.sha256(
            json.dumps(
                [universe["version"], universe["as_of"], config, backend, self.data.source_name], sort_keys=True
            ).encode()
            + implementation
        ).hexdigest()
        cached = store.cached(key, config["cache_seconds"]) if persist and not force_refresh else None
        if cached:
            return {**cached, "cache_hit": True}
        definitions = self.definitions()
        if progress:
            progress("股票池已解析，开始读取行情")
        history, quotes, failures = load_history(self.data, universe, config, progress)
        if progress:
            progress("行情读取完成，计算日期对齐因子与已到期标签")
        report = monitor_analysis(history, quotes, universe, config, backend, FactorCache())
        alerts = store.alerts(report["metrics"], definitions, config)
        report.update(
            {
                "status": f"因子监控完成：{universe['label']}，请求{len(universe['symbols'])}只，加载{len(history)}只，后端{backend}；{universe['history_policy']}。",
                "definitions": definitions,
                "alerts": alerts,
                "universe": universe["symbols"],
                "universe_metadata": universe,
                "data_source": self.data.source_name,
                "qlib": self.qlib_status(),
                "cache_hit": False,
                "coverage": {
                    "requested": len(universe["symbols"]),
                    "loaded": len(history),
                    "failed": len(failures),
                    "failures": failures,
                },
                "as_of": universe["as_of"],
                "price_adjustment": config["price_adjustment"],
                "refreshed_at": utc_now_iso(),
                "calendar_source": "输入行情日期并集",
            }
        )
        report["kpis"] = _kpis(report)
        if persist:
            store.save(key, report, config)
        return report


def _kpis(report: dict[str, Any]) -> list[dict[str, Any]]:
    metrics = report["metrics"]
    coverage = report["coverage"]
    values = [float(row["rank_ic_mean"]) for row in metrics if row.get("rank_ic_mean") is not None]
    return [
        {
            "label": "请求 / 加载",
            "value": f"{coverage['requested']} / {coverage['loaded']}",
            "hint": "加载失败也计入覆盖率分母",
            "tone": "neutral",
        },
        {"label": "监控因子", "value": str(len(metrics)), "hint": "与策略工坊共用目录", "tone": "neutral"},
        {
            "label": "平均RankIC",
            "value": f"{sum(values) / len(values):.3f}" if values else "暂无",
            "hint": "已到期历史标签",
            "tone": "neutral",
        },
        {
            "label": "实际后端",
            "value": report["backend"],
            "hint": report["universe_metadata"]["history_policy"],
            "tone": "neutral",
        },
        {"label": "告警", "value": str(len(report["alerts"])), "hint": "仅表示需复核，不自动交易", "tone": "warning"},
    ]


def _pearson(left: list[float], right: list[float]) -> float | None:
    return correlation(left, right)


def _spearman(left: list[float], right: list[float]) -> float | None:
    return correlation(left, right, ranked=True)


def _icir(values: list[float]) -> float | None:
    return information_ratio(values)
