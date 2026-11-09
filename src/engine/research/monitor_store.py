"""Version-scoped monitoring evidence, cached payloads and isolated alerts."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from src.core.repository import Repository
from src.core.timeutil import utc_now_iso


class MonitorStore:
    def __init__(self, repo: Repository):
        self.repo = repo

    def cached(self, key: str, seconds: int) -> dict[str, Any] | None:
        row = self.repo.db.query_one("SELECT * FROM monitor_reports WHERE cache_key = ?", (key,))
        if not row:
            return None
        age = (datetime.now(timezone.utc) - datetime.fromisoformat(row["refreshed_at"])).total_seconds()
        return json.loads(row["payload"]) if age < seconds else None

    def save(self, key: str, report: dict[str, Any], config: dict[str, Any]) -> None:
        payload = json.dumps(report, ensure_ascii=False, allow_nan=False)
        scope = hashlib.sha256(
            json.dumps(
                [
                    report["universe_metadata"]["id"],
                    report["universe_metadata"]["version"],
                    report["panel_metadata"]["definition_digest"],
                    report["backend"],
                    config["default_horizon_days"],
                ],
                sort_keys=True,
            ).encode()
        ).hexdigest()
        with self.repo.db.transaction():
            self.repo.db.execute(
                "INSERT OR REPLACE INTO monitor_reports(cache_key, payload, refreshed_at) VALUES (?, ?, ?)",
                (key, payload, report["refreshed_at"]),
            )
            for metric in report["metrics"]:
                self._metric(scope, metric, report)
            for alert in report["alerts"]:
                existing = self.repo.db.query_one(
                    "SELECT id FROM factor_alerts WHERE scope = ? AND factor_key = ? AND title = ? AND status = 'open'",
                    (scope, alert["factor_key"], alert["title"]),
                )
                if not existing:
                    self.repo.insert(
                        "factor_alerts",
                        {
                            **{
                                name: alert[name]
                                for name in ("factor_key", "severity", "title", "message", "triggered_at")
                            },
                            "scope": scope,
                            "status": "open",
                            "resolved_at": None,
                        },
                    )

    def _metric(self, scope: str, metric: dict[str, Any], report: dict[str, Any]) -> None:
        keys = [
            "ic",
            "rank_ic",
            "icir",
            "hit_rate",
            "long_short_return",
            "coverage",
            "turnover",
            "quantile_monotonicity",
            "sample_size",
        ]
        self.repo.db.execute(
            """INSERT OR REPLACE INTO factor_metrics_daily
            (factor_key, metric_date, universe, ic, rank_ic, icir, hit_rate, long_short_return,
             coverage, turnover, quantile_monotonicity, sample_size, metadata, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                metric["factor_key"],
                metric["latest_date"] or report["as_of"],
                scope,
                *(metric.get(name) for name in keys),
                json.dumps(
                    {
                        "metric": metric,
                        "universe": report["universe_metadata"],
                        "as_of": report["as_of"],
                        "backend": report["backend"],
                    },
                    ensure_ascii=False,
                    allow_nan=False,
                ),
                report["refreshed_at"],
            ),
        )

    @staticmethod
    def alerts(
        metrics: list[dict[str, Any]], definitions: list[dict[str, Any]], config: dict[str, Any]
    ) -> list[dict[str, Any]]:
        alerts = []
        thresholds = {row["factor_key"]: row for row in definitions}
        for metric in metrics:
            problems = []
            if metric["status"] == "样本不足":
                problems.append(("info", "样本不足", "有效历史或横截面样本不足，不能判断因子有效性"))
            if metric["coverage"] < thresholds[metric["factor_key"]]["threshold_coverage"]:
                problems.append(("warning", "覆盖率偏低", "覆盖率包含请求中加载失败的标的，请检查行情和股票池"))
            if metric["rank_ic"] is not None and metric["rank_ic"] < thresholds[metric["factor_key"]]["threshold_ic"]:
                problems.append(("warning", "RankIC偏弱", "最近已到期横截面低于阈值，需结合滚动和多池结果复核"))
            for severity, title, message in problems:
                alerts.append(
                    {
                        "factor_key": metric["factor_key"],
                        "factor_name": metric["factor_name"],
                        "severity": severity,
                        "title": title,
                        "message": message,
                        "triggered_at": utc_now_iso(),
                    }
                )
        return alerts
