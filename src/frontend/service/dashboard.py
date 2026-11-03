"""Dashboard frontend service callbacks."""

from __future__ import annotations

from .dashboard_views import (
    _dashboard_market_brief_html,
    _dashboard_monitor_tables,
    _dashboard_news_html,
)
from .foundation import (
    ACCOUNT_MODE_CHOICES,
    ACTION_COLUMNS,
    DASHBOARD_LAYOUT_FILE,
    DASHBOARD_MODULE_CHOICES,
    DASHBOARD_MODULE_KEYS,
    DASHBOARD_TRADE_COLUMNS,
    HOLDING_COLUMNS,
    INDEX_COLUMNS,
    MARKET_STYLE_COLUMNS,
    MONITOR_COLUMNS,
    RISK_COLUMNS,
    SCENARIO_COLUMNS,
    STRATEGY_DASHBOARD_COLUMNS,
    THEME_CHAIN_COLUMNS,
    WATCHLIST_COLUMNS,
    Any,
    BacktestRunner,
    Database,
    DataSourceManager,
    LiveTradingService,
    NewsAggregator,
    QuoteService,
    Repository,
    Sequence,
    _cache_badge,
    _choice_label,
    _daily_cached,
    _normalize_account_mode,
    _preset_by_id,
    _preset_items,
    escape,
    go,
    json,
    pd,
    to_frame,
)
from .home_charts import account_trend
from .home_dashboard import account_status, home_account, home_market, home_news, home_operations
from .home_data import account_snapshot
from .home_tables import home_styled_frame
from .home_views import account_kpis, risk_summary
from .visuals import (
    _format_display_time,
    _money,
    _pct_points,
    _percent,
    _safe_float,
    market_bar_figure,
)


class DashboardServiceMixin:
    """Callbacks owned by the dashboard frontend domain."""

    def home_account(self, account_mode: str = "paper", force_refresh: bool = False) -> tuple:
        return home_account(_normalize_account_mode(account_mode), force_refresh)

    def home_market(self, account_mode: str = "paper", force_refresh: bool = False) -> tuple:
        return home_market(_normalize_account_mode(account_mode), force_refresh)

    def home_news(self, account_mode: str = "paper", force_refresh: bool = False) -> str:
        return home_news(_normalize_account_mode(account_mode), force_refresh)

    def home_operations(self, account_mode: str = "paper", force_refresh: bool = False) -> tuple[str, str, str]:
        mode = _normalize_account_mode(account_mode)
        snapshot = account_snapshot(mode)
        rows = self._dashboard_action_rows(
            Repository(),
            mode,
            bool(snapshot.account),
            snapshot.exposure or 0,
            snapshot.concentration or 0,
            snapshot.pending,
        )
        if snapshot.account and snapshot.total_asset is None:
            rows.insert(
                0,
                {
                    "priority": "高",
                    "category": "实盘" if mode == "live" else "账户",
                    "item": "账户估值未提供，风险无法判定",
                    "next_step": "检查账户回传或持仓行情，补齐估值来源",
                },
            )
        return home_operations(rows)

    def load_dashboard_layout(self) -> list[str]:
        """Return visible module keys in saved order, falling back to all modules."""
        if not DASHBOARD_LAYOUT_FILE.exists():
            return list(DASHBOARD_MODULE_KEYS)
        try:
            loaded = json.loads(DASHBOARD_LAYOUT_FILE.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return list(DASHBOARD_MODULE_KEYS)
        saved = loaded.get("modules") if isinstance(loaded, dict) else None
        if not isinstance(saved, list):
            return list(DASHBOARD_MODULE_KEYS)
        visible = [str(key) for key in saved if str(key) in DASHBOARD_MODULE_KEYS]
        return visible or list(DASHBOARD_MODULE_KEYS)

    def save_dashboard_layout(self, selected: Any) -> str:
        keys = [str(key) for key in (selected or []) if str(key) in DASHBOARD_MODULE_KEYS]
        if not keys:
            raise ValueError("至少保留一个仪表盘模块")
        DASHBOARD_LAYOUT_FILE.parent.mkdir(parents=True, exist_ok=True)
        DASHBOARD_LAYOUT_FILE.write_text(json.dumps({"modules": keys}, ensure_ascii=False, indent=2), encoding="utf-8")
        labels = [dict(DASHBOARD_MODULE_CHOICES).get(key, key) for key in keys]
        return f"布局已保存（{len(keys)} 个模块）：{'、'.join(labels)}。刷新页面后按新布局排列。"

    def dashboard(
        self,
        account_mode: str = "paper",
        force_refresh: bool = False,
    ) -> tuple[
        str,
        str,
        pd.DataFrame,
        pd.DataFrame,
        pd.DataFrame,
        pd.DataFrame,
        pd.DataFrame,
        pd.DataFrame,
        pd.DataFrame,
        go.Figure,
        pd.DataFrame,
        pd.DataFrame,
        pd.DataFrame,
        go.Figure,
    ]:
        mode = _normalize_account_mode(account_mode)
        payload, cache_hit, refreshed_at = _daily_cached(
            ("dashboard", mode),
            lambda: self._build_dashboard(account_mode=mode, force_refresh=force_refresh),
            force_refresh=force_refresh,
        )
        status = f"{payload[0]}  ·  {_cache_badge(cache_hit, refreshed_at)}"
        return (status, *payload[1:])

    def dashboard_summary(self, account_mode: str = "paper", force_refresh: bool = False) -> tuple[str, str]:
        mode = _normalize_account_mode(account_mode)
        if force_refresh:
            account_snapshot(mode, force_refresh=True)
        payload, cache_hit, refreshed_at = _daily_cached(
            ("dashboard_summary", mode),
            lambda: self._build_dashboard_summary(mode),
            force_refresh=force_refresh,
        )
        status = f"{payload[0]}  ·  {_cache_badge(cache_hit, refreshed_at)}"
        return status, payload[1]

    def _build_dashboard_summary(self, account_mode: str) -> tuple[str, str]:
        mode = _normalize_account_mode(account_mode)
        snapshot = account_snapshot(mode)
        account_label = _choice_label(ACCOUNT_MODE_CHOICES, mode)
        status = f"系统状态：正常 · 当前视角 {account_label} · 分块加载账户、市场与任务"
        return f"{status} · {account_status(snapshot)}", account_kpis(snapshot)

    def dashboard_ai_workbench_entry(self, account_mode: str = "paper") -> str:
        mode = _normalize_account_mode(account_mode)
        account_label = _choice_label(ACCOUNT_MODE_CHOICES, mode)
        repo = Repository()
        latest_run = repo.db.query_one(
            "SELECT * FROM quant_workflow_runs WHERE mode = ? ORDER BY created_at DESC LIMIT 1",
            (mode,),
        )
        total_runs = int(repo.db.scalar("SELECT COUNT(*) FROM quant_workflow_runs WHERE mode = ?", (mode,)) or 0)
        recent_advice = "先生成一次闭环快照，沉淀当前策略和账户证据。"
        if latest_run and latest_run.get("summary"):
            recent_advice = str(latest_run["summary"])
        cards = [
            ("账户视角", account_label, "当前分析口径"),
            ("闭环记录", str(total_runs), "已保存运行"),
            ("专家", str(len(_preset_items("experts"))), "单专家入口"),
            ("专家团", str(len(_preset_items("team_presets"))), "多角色协作"),
        ]
        metric_html = "".join(
            "<article><small>"
            + escape(label)
            + "</small><strong>"
            + escape(value)
            + "</strong><span>"
            + escape(note)
            + "</span></article>"
            for label, value, note in cards
        )
        return (
            "<section class='ai-dashboard-entry'>"
            "<div class='ai-dashboard-entry-copy'><span>AI 工作台</span>"
            "<strong>把投研、策略和归因放到同一个控制台</strong>"
            "<p>"
            + escape(recent_advice)
            + "</p><button type='button' class='ai-workbench-entry-action'>进入 AI 工作台</button></div>"
            "<div class='ai-dashboard-entry-metrics'>" + metric_html + "</div></section>"
        )

    def dashboard_account_focus(
        self, account_mode: str = "paper", force_refresh: bool = False
    ) -> tuple[str, go.Figure]:
        mode = _normalize_account_mode(account_mode)
        payload, _, _ = _daily_cached(
            ("dashboard_account_focus", mode),
            lambda: self._build_dashboard_account_focus(mode),
            force_refresh=force_refresh,
        )
        return payload

    def _build_dashboard_account_focus(self, account_mode: str) -> tuple[str, go.Figure]:
        snapshot = account_snapshot(_normalize_account_mode(account_mode))
        return f"<section class='dashboard-focus-panel'>{risk_summary(snapshot)}</section>", account_trend(snapshot)

    def dashboard_market(
        self, account_mode: str = "paper", force_refresh: bool = False
    ) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, Any, Any, go.Figure]:
        mode = _normalize_account_mode(account_mode)
        payload, _, _ = _daily_cached(
            ("dashboard_market", mode),
            lambda: self._build_dashboard_market(mode, force_refresh),
            force_refresh=force_refresh,
        )
        monitor, style_rows, theme, paths, indices, watchlist, figure = payload
        return (
            monitor,
            style_rows,
            theme,
            paths,
            home_styled_frame(indices),
            home_styled_frame(watchlist),
            figure,
        )

    def _build_dashboard_market(
        self, account_mode: str, force_refresh: bool
    ) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, go.Figure]:
        db = Database()
        repo = Repository(db)
        quotes = QuoteService()
        indices = quotes.indices(refresh=force_refresh)
        sectors = quotes.sectors(limit=8)
        watchlist = quotes.watchlist_quotes(None)
        account = (
            repo.db.query_one("SELECT * FROM paper_accounts ORDER BY updated_at DESC, id DESC LIMIT 1")
            if account_mode == "paper"
            else repo.db.query_one("SELECT * FROM live_configs ORDER BY updated_at DESC, id DESC LIMIT 1")
        )
        snapshot = account_snapshot(account_mode)
        exposure, concentration = snapshot.exposure or 0, snapshot.concentration or 0
        pending_orders = self._dashboard_pending_orders(repo, account_mode, account)
        running_live = int(repo.db.scalar("SELECT COUNT(*) FROM live_runs WHERE status = 'running'") or 0)
        action_rows = self._dashboard_action_rows(
            repo, account_mode, bool(account), exposure, concentration, pending_orders
        )
        monitor_rows, style_rows, theme_chain_rows, paths_rows = _dashboard_monitor_tables(
            indices,
            sectors,
            watchlist,
            action_rows,
            exposure,
            concentration,
            pending_orders,
            running_live,
        )
        return (
            to_frame(monitor_rows, MONITOR_COLUMNS),
            to_frame(style_rows, MARKET_STYLE_COLUMNS),
            to_frame(theme_chain_rows, THEME_CHAIN_COLUMNS),
            to_frame(paths_rows, SCENARIO_COLUMNS),
            to_frame(indices, INDEX_COLUMNS),
            to_frame(watchlist, WATCHLIST_COLUMNS),
            market_bar_figure(sectors),
        )

    def dashboard_market_brief(self, account_mode: str = "paper", force_refresh: bool = False) -> tuple[str, str]:
        mode = _normalize_account_mode(account_mode)
        payload, _, _ = _daily_cached(
            ("dashboard_market_brief", mode),
            lambda: self._build_dashboard_market_brief(force_refresh),
            force_refresh=force_refresh,
        )
        return payload

    def _build_dashboard_market_brief(self, force_refresh: bool) -> tuple[str, str]:
        quotes = QuoteService()
        indices = quotes.indices(refresh=force_refresh)
        sectors = quotes.sectors(limit=12)
        watchlist = quotes.watchlist_quotes(None)
        news_result = NewsAggregator().list_news(None, None, None, 1, 5, refresh=force_refresh)
        news_items = news_result.get("items") if isinstance(news_result, dict) else []
        return _dashboard_market_brief_html(indices, sectors, watchlist), _dashboard_news_html(news_items or [])

    def dashboard_account(
        self, account_mode: str = "paper", force_refresh: bool = False
    ) -> tuple[pd.DataFrame, Any, go.Figure]:
        mode = _normalize_account_mode(account_mode)
        if force_refresh:
            account_snapshot(mode, force_refresh=True)
        payload, _, _ = _daily_cached(
            ("dashboard_account", mode),
            lambda: self._build_dashboard_account(mode),
            force_refresh=force_refresh,
        )
        risk, holdings, figure = payload
        return (
            risk,
            home_styled_frame(holdings),
            figure,
        )

    def _build_dashboard_account(self, account_mode: str) -> tuple[pd.DataFrame, pd.DataFrame, go.Figure]:
        mode = _normalize_account_mode(account_mode)
        snapshot = account_snapshot(mode)
        repo = Repository()
        paper = repo.db.query_one("SELECT * FROM paper_accounts ORDER BY updated_at DESC, id DESC LIMIT 1")
        live = repo.db.query_one("SELECT * FROM live_configs ORDER BY updated_at DESC, id DESC LIMIT 1")
        rows = self._dashboard_risk_rows(
            mode,
            _choice_label(ACCOUNT_MODE_CHOICES, mode),
            snapshot.account,
            paper,
            live,
            str(snapshot.account.get("status") or "-"),
            snapshot.total_asset or 0,
            snapshot.cash or 0,
            sum(row["market_value"] or 0 for row in snapshot.holdings),
            snapshot.exposure or 0,
            snapshot.concentration or 0,
            {"position_count": len(snapshot.holdings)},
            snapshot.pending,
        )
        if snapshot.total_asset is None:
            for row in rows:
                if row["metric"] not in {"当前视角", "模拟账户", "实盘账户"}:
                    row.update(value="—", status="未提供", note=snapshot.basis)
        return to_frame(rows, RISK_COLUMNS), to_frame(snapshot.holdings, HOLDING_COLUMNS), account_trend(snapshot)

    def dashboard_trade_history(self, account_mode: str = "paper", force_refresh: bool = False) -> pd.DataFrame:
        mode = _normalize_account_mode(account_mode)
        frame, _, _ = _daily_cached(
            ("dashboard_trade_history", mode),
            lambda: self._build_dashboard_trade_history(mode),
            force_refresh=force_refresh,
        )
        return frame

    def _build_dashboard_trade_history(self, account_mode: str) -> pd.DataFrame:
        repo = Repository()
        mode = _normalize_account_mode(account_mode)
        account_label = _choice_label(ACCOUNT_MODE_CHOICES, mode)
        if mode == "paper":
            account = repo.db.query_one("SELECT * FROM paper_accounts ORDER BY updated_at DESC, id DESC LIMIT 1")
            rows = self._dashboard_paper_trade_rows(repo, account, account_label)
        else:
            account = repo.db.query_one("SELECT * FROM live_configs ORDER BY updated_at DESC, id DESC LIMIT 1")
            rows = self._dashboard_live_trade_rows(repo, account, account_label)
        return to_frame(rows, DASHBOARD_TRADE_COLUMNS)

    def _dashboard_paper_trade_rows(
        self,
        repo: Repository,
        account: dict[str, Any] | None,
        account_label: str,
    ) -> list[dict[str, Any]]:
        if not account:
            return [self._empty_dashboard_trade_row(account_label, "未创建模拟账户", "paper_trades")]
        account_id = int(account["id"])
        rows = repo.db.query(
            """
            SELECT t.symbol,
                   COALESCE(p.name, t.symbol) AS name,
                   t.direction,
                   t.price,
                   t.quantity,
                   t.fee,
                   t.traded_at,
                   o.status,
                   o.order_type
              FROM paper_trades t
              LEFT JOIN paper_orders o ON o.id = t.order_id
              LEFT JOIN paper_positions p ON p.account_id = t.account_id AND p.symbol = t.symbol
             WHERE t.account_id = ?
             ORDER BY t.traded_at DESC, t.id DESC
             LIMIT 30
            """,
            (account_id,),
        )
        if not rows:
            return self._dashboard_recent_order_rows(repo, account, account_label)
        return [
            {
                "account_mode": account_label,
                "account_name": account.get("name") or "-",
                "symbol": row.get("symbol") or "-",
                "name": row.get("name") or row.get("symbol") or "-",
                "direction": row.get("direction") or "-",
                "price": round(_safe_float(row.get("price")), 4),
                "quantity": int(_safe_float(row.get("quantity"))),
                "fee": round(_safe_float(row.get("fee")), 4),
                "status": row.get("status") or "已成交",
                "order_type": row.get("order_type") or "-",
                "traded_at": _format_display_time(row.get("traded_at")),
                "source": "paper_trades",
            }
            for row in rows
        ]

    def _dashboard_recent_order_rows(
        self,
        repo: Repository,
        account: dict[str, Any],
        account_label: str,
    ) -> list[dict[str, Any]]:
        rows = repo.db.query(
            """
            SELECT symbol, direction, order_type, price, quantity, filled_qty, status, created_at
              FROM paper_orders
             WHERE account_id = ?
             ORDER BY created_at DESC, id DESC
             LIMIT 30
            """,
            (account.get("id"),),
        )
        if not rows:
            return [self._empty_dashboard_trade_row(account_label, "暂无模拟交易记录", "paper_orders")]
        return [
            {
                "account_mode": account_label,
                "account_name": account.get("name") or "-",
                "symbol": row.get("symbol") or "-",
                "name": row.get("symbol") or "-",
                "direction": row.get("direction") or "-",
                "price": round(_safe_float(row.get("price")), 4),
                "quantity": int(_safe_float(row.get("quantity"))),
                "fee": 0.0,
                "status": f"{row.get('status') or '-'} / 已成 {int(_safe_float(row.get('filled_qty')))}",
                "order_type": row.get("order_type") or "-",
                "traded_at": _format_display_time(row.get("created_at")),
                "source": "paper_orders",
            }
            for row in rows
        ]

    def _dashboard_live_trade_rows(
        self,
        repo: Repository,
        account: dict[str, Any] | None,
        account_label: str,
    ) -> list[dict[str, Any]]:
        if not account:
            return [self._empty_dashboard_trade_row(account_label, "未配置实盘账户", "live_orders")]
        latest_run = repo.db.query_one(
            """
            SELECT r.id, c.name, c.channel
              FROM live_runs r
              JOIN live_configs c ON c.id = r.config_id
             WHERE r.config_id = ?
             ORDER BY r.started_at DESC, r.id DESC
             LIMIT 1
            """,
            (account.get("id"),),
        )
        if not latest_run:
            return [self._empty_dashboard_trade_row(account_label, "暂无实盘运行记录", "live_orders")]
        rows = repo.db.query(
            """
            SELECT symbol, direction, price, quantity, status, created_at
              FROM live_orders
             WHERE run_id = ?
             ORDER BY created_at DESC, id DESC
             LIMIT 30
            """,
            (latest_run.get("id"),),
        )
        if not rows:
            return [self._empty_dashboard_trade_row(account_label, "暂无实盘订单记录", "live_orders")]
        return [
            {
                "account_mode": account_label,
                "account_name": latest_run.get("name") or account.get("name") or "-",
                "symbol": row.get("symbol") or "-",
                "name": row.get("symbol") or "-",
                "direction": row.get("direction") or "-",
                "price": round(_safe_float(row.get("price")), 4),
                "quantity": int(_safe_float(row.get("quantity"))),
                "fee": 0.0,
                "status": row.get("status") or "-",
                "order_type": f"实盘通道 {latest_run.get('channel') or '-'}",
                "traded_at": _format_display_time(row.get("created_at")),
                "source": "live_orders",
            }
            for row in rows
        ]

    @staticmethod
    def _empty_dashboard_trade_row(account_label: str, message: str, source: str) -> dict[str, Any]:
        return {
            "account_mode": account_label,
            "account_name": message,
            "symbol": "-",
            "name": "-",
            "direction": "-",
            "price": 0.0,
            "quantity": 0,
            "fee": 0.0,
            "status": "待产生",
            "order_type": "-",
            "traded_at": "-",
            "source": source,
        }

    def dashboard_strategy(
        self, account_mode: str = "paper", force_refresh: bool = False
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        mode = _normalize_account_mode(account_mode)
        payload, _, _ = _daily_cached(
            ("dashboard_strategy", mode),
            lambda: self._build_dashboard_strategy(mode),
            force_refresh=force_refresh,
        )
        return payload

    def _build_dashboard_strategy(self, account_mode: str) -> tuple[pd.DataFrame, pd.DataFrame]:
        db = Database()
        repo = Repository(db)
        account = (
            repo.db.query_one("SELECT * FROM paper_accounts ORDER BY updated_at DESC, id DESC LIMIT 1")
            if account_mode == "paper"
            else repo.db.query_one("SELECT * FROM live_configs ORDER BY updated_at DESC, id DESC LIMIT 1")
        )
        total_asset = self._dashboard_estimated_asset(repo, account_mode, account)
        exposure, concentration = self._dashboard_estimated_risk(repo, account_mode, account, total_asset)
        pending_orders = self._dashboard_pending_orders(repo, account_mode, account)
        action_rows = self._dashboard_action_rows(
            repo, account_mode, bool(account), exposure, concentration, pending_orders
        )
        strategy_rows = self._dashboard_strategy_rows(repo)
        return to_frame(action_rows, ACTION_COLUMNS), to_frame(strategy_rows, STRATEGY_DASHBOARD_COLUMNS)

    def _dashboard_pending_orders(self, repo: Repository, account_mode: str, account: dict[str, Any] | None) -> int:
        if not account:
            return 0
        if account_mode == "paper":
            return int(
                repo.db.scalar(
                    "SELECT COUNT(*) FROM paper_orders WHERE account_id = ? AND status NOT IN ('已成交', '已撤销')",
                    (account.get("id"),),
                )
                or 0
            )
        latest_run = repo.db.query_one(
            "SELECT id FROM live_runs WHERE config_id = ? ORDER BY started_at DESC, id DESC LIMIT 1",
            (account.get("id"),),
        )
        if not latest_run:
            return 0
        return int(
            repo.db.scalar(
                "SELECT COUNT(*) FROM live_orders WHERE run_id = ? AND status NOT IN ('已成交', '已撤销', 'cancelled')",
                (latest_run.get("id"),),
            )
            or 0
        )

    def _dashboard_estimated_asset(self, repo: Repository, account_mode: str, account: dict[str, Any] | None) -> float:
        if not account:
            return 0.0
        if account_mode == "paper":
            market_value = float(
                repo.db.scalar(
                    "SELECT COALESCE(SUM(avg_cost * quantity), 0) FROM paper_positions WHERE account_id = ?",
                    (account.get("id"),),
                )
                or 0
            )
            return float(account.get("current_cash") or 0) + market_value
        return float(account.get("capital") or 0)

    def _dashboard_estimated_risk(
        self, repo: Repository, account_mode: str, account: dict[str, Any] | None, total_asset: float
    ) -> tuple[float, float]:
        if not account or total_asset <= 0:
            return 0.0, 0.0
        if account_mode == "paper":
            rows = repo.db.query(
                """SELECT quantity, avg_cost
                   FROM paper_positions
                   WHERE account_id = ? AND quantity > 0""",
                (account.get("id"),),
            )
            values = [_safe_float(row.get("avg_cost")) * _safe_float(row.get("quantity")) for row in rows]
            market_value = sum(values)
            return market_value / total_asset, max(values, default=0.0) / total_asset
        return 0.0, 0.0

    def _dashboard_position_count(self, repo: Repository, account_mode: str, account: dict[str, Any] | None) -> int:
        if not account:
            return 0
        if account_mode == "paper":
            return int(
                repo.db.scalar(
                    "SELECT COUNT(*) FROM paper_positions WHERE account_id = ? AND quantity > 0",
                    (account.get("id"),),
                )
                or 0
            )
        latest_run = repo.db.query_one(
            "SELECT id FROM live_runs WHERE config_id = ? ORDER BY started_at DESC, id DESC LIMIT 1",
            (account.get("id"),),
        )
        if not latest_run:
            return 0
        positions = LiveTradingService(repo=repo).positions(int(latest_run["id"]))
        return len(
            [
                item
                for item in positions
                if str(item.get("symbol") or "").upper() != "CASH" and _safe_float(item.get("quantity")) > 0
            ]
        )

    def _dashboard_estimated_market_value(
        self, repo: Repository, account_mode: str, account: dict[str, Any] | None
    ) -> float:
        if not account:
            return 0.0
        if account_mode == "paper":
            return float(
                repo.db.scalar(
                    "SELECT COALESCE(SUM(avg_cost * quantity), 0) FROM paper_positions WHERE account_id = ?",
                    (account.get("id"),),
                )
                or 0
            )
        latest_run = repo.db.query_one(
            "SELECT id FROM live_runs WHERE config_id = ? ORDER BY started_at DESC, id DESC LIMIT 1",
            (account.get("id"),),
        )
        if not latest_run:
            return 0.0
        positions = LiveTradingService(repo=repo).positions(int(latest_run["id"]))
        return sum(
            _safe_float(item.get("market_value"))
            for item in positions
            if str(item.get("symbol") or "").upper() != "CASH"
        )

    def _dashboard_estimated_pnl(
        self,
        repo: Repository,
        account_mode: str,
        account: dict[str, Any] | None,
        total_asset: float,
    ) -> tuple[float, float]:
        if not account:
            return 0.0, 0.0
        if account_mode != "paper":
            return 0.0, 0.0
        initial_cash = _safe_float(account.get("initial_cash"))
        total_pnl = total_asset - initial_cash if initial_cash > 0 else 0.0
        rows = repo.db.query(
            "SELECT net_value FROM paper_nav_history WHERE account_id = ? ORDER BY nav_date DESC LIMIT 2",
            (account.get("id"),),
        )
        if len(rows) >= 2 and initial_cash > 0:
            daily_pnl = (_safe_float(rows[0].get("net_value")) - _safe_float(rows[1].get("net_value"))) * initial_cash
        else:
            daily_pnl = 0.0
        return total_pnl, daily_pnl

    def _dashboard_action_rows(
        self,
        repo: Repository,
        account_mode: str,
        has_account: bool,
        exposure: float,
        concentration: float,
        pending_orders: int,
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        strategy_count = int(repo.db.scalar("SELECT COUNT(*) FROM strategies") or 0)
        watchlist_count = int(repo.db.scalar("SELECT COUNT(*) FROM watchlist") or 0)
        failed_backtests = int(
            repo.db.scalar("SELECT COUNT(*) FROM backtest_tasks WHERE status IN ('失败', 'failed', 'error')") or 0
        )
        failed_jobs = int(
            repo.db.scalar("SELECT COUNT(*) FROM job_executions WHERE status IN ('失败', 'failed', 'error')") or 0
        )
        enabled_models = int(repo.db.scalar("SELECT COUNT(*) FROM llm_models WHERE enabled = 1") or 0)
        if not has_account:
            rows.append(
                {
                    "priority": "高",
                    "category": "账户",
                    "item": "尚未创建模拟账户" if account_mode == "paper" else "尚未配置实盘账户",
                    "status": "待配置",
                    "next_step": "进入策略仿真 / 模拟交易创建账户"
                    if account_mode == "paper"
                    else "进入实盘页保存配置并确认通道",
                    "updated_at": "-",
                }
            )
        if exposure > 0.9:
            rows.append(
                {
                    "priority": "高",
                    "category": "风险",
                    "item": "账户仓位暴露过高",
                    "status": _percent(exposure),
                    "next_step": "检查持仓和策略风控阈值",
                    "updated_at": "-",
                }
            )
        if concentration > 0.35:
            rows.append(
                {
                    "priority": "中",
                    "category": "风险",
                    "item": "单票集中度偏高",
                    "status": _percent(concentration),
                    "next_step": "评估是否需要分散持仓",
                    "updated_at": "-",
                }
            )
        if pending_orders:
            rows.append(
                {
                    "priority": "中",
                    "category": "交易",
                    "item": "存在未完成委托",
                    "status": f"{pending_orders} 笔",
                    "next_step": "进入模拟交易查看委托状态" if account_mode == "paper" else "进入实盘页查看订单状态",
                    "updated_at": "-",
                }
            )
        if failed_backtests:
            rows.append(
                {
                    "priority": "中",
                    "category": "回测",
                    "item": "存在失败回测任务",
                    "status": f"{failed_backtests} 个",
                    "next_step": "进入回测任务列表查看错误",
                    "updated_at": "-",
                }
            )
        if failed_jobs:
            rows.append(
                {
                    "priority": "中",
                    "category": "定时任务",
                    "item": "存在失败任务执行",
                    "status": f"{failed_jobs} 次",
                    "next_step": "查看任务历史和错误信息",
                    "updated_at": "-",
                }
            )
        if watchlist_count == 0:
            rows.append(
                {
                    "priority": "中",
                    "category": "市场",
                    "item": "自选列表为空",
                    "status": "待配置",
                    "next_step": "添加关注标的用于首页监控",
                    "updated_at": "-",
                }
            )
        if strategy_count == 0:
            rows.append(
                {
                    "priority": "中",
                    "category": "策略",
                    "item": "策略库为空",
                    "status": "待配置",
                    "next_step": "上传策略或使用 CLI 工作台生成策略",
                    "updated_at": "-",
                }
            )
        if enabled_models == 0:
            rows.append(
                {
                    "priority": "低",
                    "category": "模型",
                    "item": "未启用 LLM 模型",
                    "status": "可选配置",
                    "next_step": "配置后可使用问答、摘要和模型报告",
                    "updated_at": "-",
                }
            )
        if not rows:
            rows.append(
                {
                    "priority": "正常",
                    "category": "总览",
                    "item": "当前没有需要优先处理的事项",
                    "status": "正常",
                    "next_step": "继续监控市场与策略运行",
                    "updated_at": "-",
                }
            )
        return rows

    def _dashboard_holding_rows(
        self,
        account_mode: str,
        positions: Sequence[dict[str, Any]],
        manager: DataSourceManager,
        live_channel: str,
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        if account_mode == "paper":
            for position in positions:
                symbol = str(position.get("symbol") or "").strip()
                if not symbol:
                    continue
                quote = manager.stock_quote(symbol)
                latest_price = _safe_float(quote.get("latest_price"), _safe_float(position.get("latest_price")))
                avg_cost = _safe_float(position.get("avg_cost"))
                quantity = _safe_float(position.get("quantity"))
                market_value_row = latest_price * quantity
                float_pnl = (
                    (latest_price - avg_cost) * quantity if avg_cost > 0 else _safe_float(position.get("float_pnl"))
                )
                float_pnl_pct = float_pnl / (avg_cost * quantity) if avg_cost > 0 and quantity > 0 else 0.0
                rows.append(
                    {
                        "symbol": symbol,
                        "name": quote.get("name") or position.get("name") or symbol,
                        "quantity": int(quantity),
                        "available_qty": int(_safe_float(position.get("available_qty"), quantity)),
                        "latest_price": round(latest_price, 2),
                        "change_pct": _pct_points(quote.get("change_pct")),
                        "market_value": round(market_value_row, 2),
                        "float_pnl": round(float_pnl, 2),
                        "float_pnl_pct": _percent(float_pnl_pct),
                        "data_source": quote.get("data_source") or manager.source_name,
                    }
                )
        else:
            for position in positions:
                symbol = str(position.get("symbol") or "").strip()
                if not symbol:
                    continue
                latest_price = _safe_float(position.get("latest_price"), _safe_float(position.get("avg_cost")))
                quantity = _safe_float(position.get("quantity"))
                market_value_row = _safe_float(position.get("market_value"), latest_price * quantity)
                rows.append(
                    {
                        "symbol": symbol,
                        "name": position.get("name") or symbol,
                        "quantity": int(quantity),
                        "available_qty": int(_safe_float(position.get("available_qty"), quantity)),
                        "latest_price": round(latest_price, 2),
                        "change_pct": "-",
                        "market_value": round(market_value_row, 2),
                        "float_pnl": round(_safe_float(position.get("float_pnl")), 2),
                        "float_pnl_pct": _percent(_safe_float(position.get("float_pnl_pct"))),
                        "data_source": f"实盘通道 {live_channel}",
                    }
                )
        if not rows:
            rows.append(
                {
                    "symbol": "-",
                    "name": "暂无模拟持仓" if account_mode == "paper" else "暂无实盘持仓",
                    "quantity": 0,
                    "available_qty": 0,
                    "latest_price": "-",
                    "change_pct": "-",
                    "market_value": 0,
                    "float_pnl": 0,
                    "float_pnl_pct": "-",
                    "data_source": manager.source_name if account_mode == "paper" else f"实盘通道 {live_channel}",
                }
            )
        return rows

    def _dashboard_risk_rows(
        self,
        account_mode: str,
        account_label: str,
        account: dict[str, Any] | None,
        paper_account: dict[str, Any] | None,
        live_config: dict[str, Any] | None,
        live_config_status: str,
        total_asset: float,
        cash: float,
        market_value: float,
        exposure: float,
        concentration: float,
        account_overview: dict[str, Any],
        pending_orders: int,
    ) -> list[dict[str, Any]]:
        paper_status = f"已接入 / ID {paper_account.get('id')}" if paper_account else "未创建"
        live_status = f"已配置 / ID {live_config.get('id')}" if live_config else "未接入"
        return [
            {
                "metric": "当前视角",
                "value": account_label,
                "status": "已选择",
                "note": _preset_by_id("account_modes", account_mode).get("summary", ""),
            },
            {
                "metric": "模拟账户",
                "value": paper_status,
                "status": "当前" if account_mode == "paper" and account else "可用" if paper_account else "待配置",
                "note": f"最近更新：{paper_account.get('name', '-')}" if paper_account else "进入模拟交易创建账户",
            },
            {
                "metric": "实盘账户",
                "value": live_status,
                "status": live_config_status
                if account_mode == "live" and account
                else "可用"
                if live_config
                else "待配置",
                "note": (
                    f"通道：{live_config.get('channel', '-')}"
                    if live_config
                    else "实盘页当前只提供 paper/broker 配置占位，真实券商通道需单独接入"
                ),
            },
            {
                "metric": "总资产",
                "value": _money(total_asset) if account else "-",
                "status": "正常" if account else "待配置",
                "note": "",
            },
            {"metric": "可用资金", "value": _money(cash) if account else "-", "status": "正常", "note": ""},
            {"metric": "持仓市值", "value": _money(market_value) if account else "-", "status": "正常", "note": ""},
            {
                "metric": "仓位暴露",
                "value": _percent(exposure) if account else "-",
                "status": "高风险" if exposure > 0.9 else "关注" if exposure > 0.7 else "正常",
                "note": "持仓市值 / 总资产",
            },
            {
                "metric": "单票集中度",
                "value": _percent(concentration) if account else "-",
                "status": "关注" if concentration > 0.35 else "正常",
                "note": "最大单票市值 / 总资产",
            },
            {
                "metric": "持仓数量",
                "value": str(account_overview.get("position_count", 0)) if account else "-",
                "status": "正常",
                "note": "",
            },
            {
                "metric": "未完成委托",
                "value": str(pending_orders) if account else "-",
                "status": "关注" if pending_orders else "正常",
                "note": "",
            },
        ]

    def _dashboard_strategy_rows(self, repo: Repository) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        runner = BacktestRunner()
        for task in runner.list(page=1, page_size=3).get("items") or []:
            metric = "-"
            if str(task.get("status")) in {"完成", "completed", "success", "finished"}:
                try:
                    metrics = runner.performance(int(task["task_id"]))
                    metric = (
                        f"收益 {_percent(metrics.get('total_return'))} / 回撤 {_percent(metrics.get('max_drawdown'))}"
                    )
                except Exception:
                    metric = "绩效读取失败"
            rows.append(
                {
                    "module": "回测",
                    "name": f"任务 {task.get('task_id')}",
                    "status": task.get("status", "-"),
                    "key_metric": metric,
                    "updated_at": task.get("finished_at") or task.get("created_at") or "-",
                    "next_step": "查看结果" if metric != "-" else "检查任务",
                }
            )
        live_rows = repo.db.query(
            """SELECT r.id, r.status, r.heartbeat_at, r.error_msg, c.name, c.channel
               FROM live_runs r
               JOIN live_configs c ON c.id = r.config_id
               ORDER BY r.started_at DESC, r.id DESC
               LIMIT 3"""
        )
        for row in live_rows:
            rows.append(
                {
                    "module": "实盘/模拟",
                    "name": row.get("name") or f"运行 {row.get('id')}",
                    "status": row.get("status", "-"),
                    "key_metric": f"通道 {row.get('channel', '-')}",
                    "updated_at": row.get("heartbeat_at") or "-",
                    "next_step": row.get("error_msg") or "监控订单与持仓",
                }
            )
        for job in repo.list("scheduled_jobs", where="enabled = ?", params=(1,), order_by="next_run_at ASC", limit=3):
            rows.append(
                {
                    "module": "定时任务",
                    "name": job.get("name", "-"),
                    "status": "启用",
                    "key_metric": job.get("job_type", "-"),
                    "updated_at": job.get("next_run_at") or "-",
                    "next_step": "等待调度",
                }
            )
        if not rows:
            rows.append(
                {
                    "module": "策略闭环",
                    "name": "暂无回测、实盘或定时任务",
                    "status": "待启动",
                    "key_metric": "-",
                    "updated_at": "-",
                    "next_step": "从策略构建或策略仿真开始",
                }
            )
        return rows

    def _build_dashboard(
        self,
        account_mode: str = "paper",
        force_refresh: bool = False,
    ) -> tuple[
        str,
        str,
        pd.DataFrame,
        pd.DataFrame,
        pd.DataFrame,
        pd.DataFrame,
        pd.DataFrame,
        pd.DataFrame,
        pd.DataFrame,
        go.Figure,
        pd.DataFrame,
        pd.DataFrame,
        pd.DataFrame,
        go.Figure,
    ]:
        summary, kpi_html = self._build_dashboard_summary(account_mode)
        monitor, style, theme, paths, indices, watchlist, sector_figure = self._build_dashboard_market(
            account_mode,
            force_refresh,
        )
        risk, holdings, account_figure = self._build_dashboard_account(account_mode)
        actions, strategies = self._build_dashboard_strategy(account_mode)
        return (
            summary,
            kpi_html,
            monitor,
            style,
            theme,
            paths,
            actions,
            risk,
            holdings,
            account_figure,
            strategies,
            indices,
            watchlist,
            sector_figure,
        )
