"""Quick/deep stock recommendation engine."""

import json
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from src.core.exceptions import BusinessError, ErrorCode
from src.core.repository import Repository
from src.core.timeutil import utc_now_iso
from src.data import DataSourceManager
from src.data.models import STOCKS
from src.engine.market.chan_adapter import ChanAnalysisAdapter

PLAN_PROFILES: dict[str, dict[str, Any]] = {
    "defensive": {
        "label": "稳健低波",
        "bias": 1.5,
        "reason": "低波动与风险暴露更适合先进入观察池",
        "factor_shift": {"momentum": -2, "liquidity": 2, "sentiment": 1},
    },
    "momentum": {
        "label": "趋势动量",
        "bias": 3.0,
        "reason": "价格强度和成交活跃度更符合趋势延续假设",
        "factor_shift": {"momentum": 5, "liquidity": 1, "sentiment": 0},
    },
    "quality": {
        "label": "价值质量",
        "bias": 2.0,
        "reason": "质量与估值约束更适合中长期候选池",
        "factor_shift": {"momentum": 0, "liquidity": 1, "sentiment": 2},
    },
    "event": {
        "label": "事件驱动",
        "bias": 2.5,
        "reason": "资讯、研报和产业催化具备主题跟踪价值",
        "factor_shift": {"momentum": 1, "liquidity": 0, "sentiment": 5},
    },
    "balanced": {
        "label": "均衡观察",
        "bias": 0.0,
        "reason": "趋势、质量、流动性和情绪综合排序",
        "factor_shift": {"momentum": 1, "liquidity": 1, "sentiment": 1},
    },
    "chan": {
        "label": "缠论结构",
        "bias": 1.0,
        "reason": "优先参考缠论结构、门控信号和K线位置，只作为研究候选",
        "factor_shift": {"momentum": 1, "liquidity": 0, "sentiment": 0},
    },
}

_REAL_KLINE_COUNT = 60
_CHAN_KLINE_COUNT = 140
_HOT_INDUSTRY_LIMIT = 8
_HOT_CONCEPT_LIMIT = 8
_HOT_POOL_LIMIT = 16


class Recommender:
    def __init__(self, repo: Repository | None = None, data: DataSourceManager | None = None) -> None:
        self.repo = repo or Repository()
        self.data = data or DataSourceManager()

    def create_task(self, payload: dict[str, Any]) -> dict[str, Any]:
        now = utc_now_iso()
        path = payload.get("path") or "quick"
        count = max(1, min(int(payload.get("count") or 10), 30))
        model_name = (
            "rule-deep-real" if path == "deep" and not self.data.is_mock else ("mock-deep" if path == "deep" else "")
        )
        task = self.repo.insert(
            "recommend_tasks",
            {
                "path": path,
                "conditions": json.dumps(payload, ensure_ascii=False),
                "model_name": model_name,
                "status": "finished",
                "progress": 100,
                "stage": "completed",
                "created_at": now,
                "started_at": now,
                "finished_at": now,
            },
        )
        if self.data.is_mock:
            rows = self._mock_rows(payload, count)
        else:
            rows = self._real_rows(payload, count, path)
        for rank, row in enumerate(rows[:count], start=1):
            self.repo.insert(
                "recommend_results",
                {
                    "task_id": task["id"],
                    "rank": rank,
                    "symbol": row["symbol"],
                    "name": row["name"],
                    "score": row["score"],
                    "reason": row["reason"],
                    "factors": json.dumps(row["factors"], ensure_ascii=False),
                    "created_at": now,
                },
            )
        return self.status(task["id"])

    def status(self, task_id: int) -> dict[str, Any]:
        task = self.repo.get("recommend_tasks", task_id)
        return {
            "task_id": task["id"],
            "path": task["path"],
            "status": task["status"],
            "progress": task["progress"],
            "stage": task.get("stage"),
            "created_at": task["created_at"],
            "elapsed_seconds": 0,
        }

    def result(self, task_id: int) -> list[dict[str, Any]]:
        self.repo.get("recommend_tasks", task_id)
        rows = self.repo.list("recommend_results", where="task_id = ?", params=(task_id,), order_by="rank ASC")
        for row in rows:
            row["factors"] = json.loads(row["factors"] or "{}")
            row["selected_at"] = row.pop("created_at")
        return rows

    # ── mock 模式：本地样例打分 ────────────────────────────────────────────
    def _mock_rows(self, payload: dict[str, Any], count: int) -> list[dict[str, Any]]:
        plan = str(payload.get("plan") or "balanced")
        path = payload.get("path") or "quick"
        profile = PLAN_PROFILES.get(plan, PLAN_PROFILES["balanced"])
        rows: list[dict[str, Any]] = []
        candidates = self._candidate_symbols(payload) or list(STOCKS.keys())
        chan_adapter = ChanAnalysisAdapter() if plan == "chan" else None
        for rank, symbol in enumerate(candidates[:count], start=1):
            stock = STOCKS.get(symbol, {"symbol": symbol, "name": symbol, "change_pct": 0})
            change_pct = abs(float(stock.get("change_pct", 0)))
            score = round(88 - rank * 3 + change_pct + float(profile["bias"]), 2)
            shift = profile["factor_shift"]
            factors = {
                "momentum": round(score - 6 + float(shift["momentum"]), 2),
                "liquidity": round(score - 4 + float(shift["liquidity"]), 2),
                "sentiment": round(70 + change_pct + float(shift["sentiment"]), 2),
            }
            reason = f"{profile['label']}方案：{profile['reason']}；规则过滤通过"
            if chan_adapter is not None:
                chan = chan_adapter.analyze(
                    symbol, str(stock.get("name") or symbol), self._safe_kline(symbol, _CHAN_KLINE_COUNT)
                )
                score = round(float(chan["score"]) - rank * 0.8 + float(profile["bias"]), 2)
                factors["chan"] = round(float(chan["score"]), 2)
                reason += f"；{chan['reason']}"
            if path == "deep":
                reason += "；深度分析同时参考行业景气、价格强度和新闻情绪"
            rows.append(
                {
                    "symbol": symbol,
                    "name": stock.get("name", symbol),
                    "score": score,
                    "reason": reason,
                    "factors": factors,
                }
            )
        return rows

    def _candidate_symbols(self, payload: dict[str, Any]) -> list[str]:
        universe = payload.get("universe")
        if isinstance(universe, dict) and isinstance(universe.get("symbols"), list):
            return [str(item) for item in universe["symbols"]]
        if isinstance(universe, list):
            return [str(item) for item in universe]
        return []

    # ── real 模式：真实行情+K线打分 ────────────────────────────────────────
    def _real_rows(self, payload: dict[str, Any], count: int, path: str) -> list[dict[str, Any]]:
        plan = str(payload.get("plan") or "balanced")
        profile = PLAN_PROFILES.get(plan, PLAN_PROFILES["balanced"])
        explicit = self._normalize_symbols(self._candidate_symbols(payload))
        symbols = explicit or self._hot_pool()
        if not symbols:
            raise BusinessError(
                ErrorCode.DATA_SOURCE_ERROR,
                "真实行情暂不可用，未能构建候选股票池，请稍后重试或手动指定股票池",
            )
        quotes = {str(item.get("symbol")): item for item in self._safe_quotes(symbols)}
        kline_count = _CHAN_KLINE_COUNT if plan == "chan" else _REAL_KLINE_COUNT
        with ThreadPoolExecutor(max_workers=4, thread_name_prefix="recommend-kline") as executor:
            klines = dict(
                zip(symbols, executor.map(lambda item: self._safe_kline(item, kline_count), symbols), strict=True)
            )
        rows: list[dict[str, Any]] = []
        chan_adapter = ChanAnalysisAdapter() if plan == "chan" else None
        for symbol in symbols:
            quote = quotes.get(symbol)
            if not quote or float(quote.get("price") or 0) <= 0:
                continue
            chan_analysis = (
                chan_adapter.analyze(symbol, str(quote.get("name") or symbol), klines.get(symbol) or [])
                if chan_adapter is not None
                else None
            )
            scored = self._score_real_quote(quote, klines.get(symbol) or [], profile, chan_analysis)
            reason = (
                f"{profile['label']}方案：{profile['reason']}；"
                f"基于真实行情，近20日涨幅 {scored['return_20d']:+.1f}%，"
                f"换手 {scored['turnover_rate']:.2f}%"
            )
            if chan_analysis:
                reason += f"；{chan_analysis['reason']}"
            if path == "deep":
                reason += "；深度分析叠加行业景气与资金面复核"
            rows.append(
                {
                    "symbol": symbol,
                    "name": quote.get("name") or symbol,
                    "score": scored["total"],
                    "reason": reason,
                    "factors": {
                        "momentum": scored["momentum"],
                        "liquidity": scored["liquidity"],
                        "sentiment": scored["sentiment"],
                        "chan": scored["chan"],
                    },
                }
            )
        rows.sort(key=lambda item: float(item["score"]), reverse=True)
        return rows[:count]

    @staticmethod
    def _normalize_symbols(symbols: list[str]) -> list[str]:
        normalized: list[str] = []
        for raw in symbols:
            for code in str(raw).replace("，", ",").replace(";", ",").split(","):
                code = code.strip()
                if code.isdigit() and len(code) == 6 and code not in normalized:
                    normalized.append(code)
        return normalized[:_HOT_POOL_LIMIT]

    def _hot_pool(self) -> list[str]:
        leaders: list[str] = []
        for board, limit in (("industry", _HOT_INDUSTRY_LIMIT), ("concept", _HOT_CONCEPT_LIMIT)):
            try:
                for item in self.data.sectors(board=board, limit=limit):
                    code = str(item.get("leader_code") or "").strip()
                    if code and code != "-" and code.isdigit() and len(code) == 6 and code not in leaders:
                        leaders.append(code)
            except BusinessError:
                continue
        return leaders[:_HOT_POOL_LIMIT]

    def _safe_quotes(self, symbols: list[str]) -> list[dict[str, Any]]:
        try:
            return self.data.stock_quotes(symbols)
        except BusinessError:
            return []

    def _safe_kline(self, symbol: str, count: int = _REAL_KLINE_COUNT) -> list[dict[str, Any]]:
        try:
            return self.data._kline(symbol, "daily", count)
        except (AttributeError, BusinessError):
            return []

    @staticmethod
    def _score_real_quote(
        quote: dict[str, Any],
        kline: list[dict[str, Any]],
        profile: dict[str, Any],
        chan_analysis: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        shift = profile["factor_shift"]
        closes = [float(item.get("close") or 0) for item in kline if float(item.get("close") or 0) > 0]
        return_20d = 0.0
        volume_ratio = 1.0
        if len(closes) >= 21:
            return_20d = (closes[-1] / closes[-21] - 1) * 100
        volumes = [float(item.get("volume") or 0) for item in kline if float(item.get("volume") or 0) > 0]
        if len(volumes) >= 21 and sum(volumes[-20:]) > 0:
            average_volume = sum(volumes[-20:]) / 20
            volume_ratio = volumes[-1] / average_volume if average_volume > 0 else 1.0
        change_pct = float(quote.get("change_pct") or 0)
        turnover_rate = float(quote.get("turnover_rate") or 0)
        momentum = max(0.0, min(100.0, 50 + return_20d * 2.2)) + float(shift["momentum"])
        liquidity = max(0.0, min(100.0, 46 + min(turnover_rate, 12) * 3.2 + (volume_ratio - 1) * 8)) + float(
            shift["liquidity"]
        )
        sentiment = max(0.0, min(100.0, 50 + change_pct * 3.5)) + float(shift["sentiment"])
        momentum = round(max(0.0, min(100.0, momentum)), 2)
        liquidity = round(max(0.0, min(100.0, liquidity)), 2)
        sentiment = round(max(0.0, min(100.0, sentiment)), 2)
        chan_score = float((chan_analysis or {}).get("score") or 0)
        if chan_analysis:
            total = round(
                momentum * 0.22 + liquidity * 0.16 + sentiment * 0.12 + chan_score * 0.38 + 8 + float(profile["bias"]),
                2,
            )
        else:
            total = round(momentum * 0.4 + liquidity * 0.25 + sentiment * 0.15 + 12 + float(profile["bias"]), 2)
        return {
            "total": min(99.0, total),
            "momentum": momentum,
            "liquidity": liquidity,
            "sentiment": sentiment,
            "chan": round(chan_score, 2),
            "return_20d": return_20d,
            "turnover_rate": turnover_rate,
        }
