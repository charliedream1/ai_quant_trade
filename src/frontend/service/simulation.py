"""Simulation frontend service callbacks."""

from __future__ import annotations

from .foundation import (
    BACKTEST_COMPARE_COLUMNS,
    BACKTEST_PARAM_COMPARE_COLUMNS,
    ORDER_COLUMNS,
    POSITION_COLUMNS,
    TRADE_COLUMNS,
    Any,
    BacktestRunner,
    PaperAccountService,
    Repository,
    compact_json,
    get_settings,
    go,
    parse_csv,
    parse_json,
    pd,
    re,
    require_id,
    require_text,
    resolve_stock_symbol,
    to_frame,
    ui_error_message,
)
from .visuals import (
    _backtest_constraint_text,
    _backtest_execution_config,
    _format_display_time,
    _money,
    _percent,
    _safe_float,
    backtest_attribution_figure,
    backtest_attribution_frame,
    backtest_compare_figure,
    backtest_explanation,
    backtest_exposure_figure,
    backtest_monthly_figure,
    backtest_rolling_figure,
    backtest_trade_figure,
    empty_figure,
    equity_figure,
    metrics_frame,
    nav_figure,
)


class SimulationServiceMixin:
    """Callbacks owned by the simulation frontend domain."""

    def backtests(self) -> pd.DataFrame:
        try:
            tasks = BacktestRunner().list(page=1, page_size=100)
            for item in tasks.get("items", []):
                item.pop("parameter_snapshot", None)
            return to_frame(tasks)
        except Exception as exc:
            return to_frame([{"状态": f"回测任务读取失败：{ui_error_message(exc)}"}])

    def create_backtest(
        self,
        strategy_id: Any,
        symbols: str,
        start_date: str,
        end_date: str,
        capital: Any,
        params: str,
        engine: str = "auto",
        order_type: str = "market",
        price_adjustment: str = "qfq",
        max_position_count: Any = 5,
        max_position_weight: Any = 0.3,
        lot_size: Any = 100,
        slippage_rate: Any = 0.0,
        parameter_profile: str = "",
        execution_costs: dict[str, Any] | None = None,
    ) -> tuple[str, int, pd.DataFrame, pd.DataFrame, go.Figure, pd.DataFrame, go.Figure, pd.DataFrame]:
        payload = {
            "strategy_id": require_id(strategy_id, "策略 ID"),
            "engine": engine or "auto",
            "symbols": parse_csv(require_text(symbols, "标的代码")),
            "start_date": require_text(start_date, "开始日期"),
            "end_date": require_text(end_date, "结束日期"),
            "initial_capital": float(capital or 1000000),
            "params": parse_json(params, "回测参数"),
            "parameter_profile": parameter_profile or None,
            "order_type": order_type or "market",
            "price_adjustment": price_adjustment or "qfq",
            "max_position_count": max(1, int(float(max_position_count or 5))),
            "max_position_weight": min(max(_safe_float(max_position_weight, 0.3), 0.01), 1.0),
            "lot_size": max(1, int(float(lot_size or 100))),
            "slippage_rate": max(_safe_float(slippage_rate, 0.0), 0.0),
            "execution_costs": execution_costs,
        }
        runner = BacktestRunner()
        task = runner.create(payload)
        task_id = int(task["task_id"])
        metrics = runner.performance(task_id)
        curve = runner.equity_curve(task_id)
        trades = runner.trades(task_id, page=1, page_size=100)
        attribution = runner.attribution(task_id)
        return (
            f"回测任务 {task_id} 已完成；订单类型 {payload['order_type']}，复权 {payload['price_adjustment']}",
            task_id,
            self.backtests(),
            metrics_frame(metrics),
            equity_figure(curve),
            to_frame(trades, TRADE_COLUMNS),
            backtest_attribution_figure(attribution),
            backtest_attribution_frame(attribution),
        )

    def backtest_detail(self, task_id: Any) -> tuple[pd.DataFrame, go.Figure, pd.DataFrame, go.Figure, pd.DataFrame]:
        value = require_id(task_id, "回测任务 ID")
        runner = BacktestRunner()
        attribution = runner.attribution(value)
        return (
            metrics_frame(runner.performance(value)),
            equity_figure(runner.equity_curve(value)),
            to_frame(runner.trades(value, 1, 100), TRADE_COLUMNS),
            backtest_attribution_figure(attribution),
            backtest_attribution_frame(attribution),
        )

    def backtest_analysis(self, task_id: Any) -> tuple[str, go.Figure, go.Figure, go.Figure, go.Figure]:
        value = require_id(task_id, "回测任务 ID")
        runner = BacktestRunner()
        metrics = runner.performance(value)
        curve = runner.equity_curve(value)
        trades = runner.trades(value, page=1, page_size=100000).get("items") or []
        return (
            backtest_explanation(metrics, curve),
            backtest_monthly_figure(curve),
            backtest_rolling_figure(curve),
            backtest_trade_figure(trades),
            backtest_exposure_figure(curve),
        )

    def empty_backtest_analysis(self) -> tuple[str, go.Figure, go.Figure, go.Figure, go.Figure]:
        return (
            "- 尚未选择已完成的回测任务。",
            backtest_monthly_figure({}),
            backtest_rolling_figure({}),
            backtest_trade_figure([]),
            backtest_exposure_figure({}),
        )

    def backtest_param_snapshot(self, task_id: Any) -> str:
        value = require_id(task_id, "回测任务 ID")
        task = BacktestRunner().detail(value)
        evidence = task.get("parameter_snapshot") or {}
        strategy = evidence.get("strategy") or Repository().get("strategies", int(task["strategy_id"]))
        symbols = "、".join(str(item) for item in task.get("symbols") or []) or "-"
        params = compact_json(evidence or task.get("params") or {})
        execution = _backtest_execution_config(task)
        constraint = _backtest_constraint_text(execution)
        created_at = _format_display_time(task.get("created_at"))
        finished_at = _format_display_time(task.get("finished_at"))
        return (
            "### 回测参数快照\n\n"
            f"- 任务 ID：`{value}`\n"
            f"- 策略：`{strategy.get('name', '-')}` / 版本 `{strategy.get('version', '-')}` / ID `{task.get('strategy_id')}`\n"
            f"- 参数方案：{(evidence.get('profile') or {}).get('label') or '继承策略默认'}；"
            f"证据：{'运行时完整快照' if evidence else '历史原始参数（未保存完整解析证据）'}\n"
            f"- 引擎：`{task.get('engine') or 'simple'}`；状态：`{task.get('status') or '-'}`\n"
            f"- 标的池：{symbols}\n"
            f"- 区间：`{task.get('start_date')}` 至 `{task.get('end_date')}`；基准：`{task.get('benchmark') or '-'}`\n"
            f"- 初始资金：`{float(task.get('initial_cash') or 0):,.2f}`；佣金率：`{task.get('commission_rate')}`\n"
            f"- 成交假设：订单类型 `{execution.get('order_type')}`；复权 `{execution.get('price_adjustment')}`；"
            f"滑点 `{execution.get('slippage_rate')}`；组合约束 `{constraint}`\n"
            f"- 创建时间：`{created_at}`；完成时间：`{finished_at}`\n\n"
            "```json\n"
            f"{params}\n"
            "```"
        )

    def export_backtest_trades(self, task_id: Any) -> tuple[str, str | None]:
        value = require_id(task_id, "回测任务 ID")
        runner = BacktestRunner()
        runner.detail(value)
        trades = runner.trades(value, page=1, page_size=100000)
        frame = to_frame(trades, TRADE_COLUMNS)
        if frame.empty:
            return f"回测任务 {value} 暂无可导出的交易日志", None
        export_dir = get_settings().data_dir / "reports" / "backtest" / "exports"
        export_dir.mkdir(parents=True, exist_ok=True)
        export_path = export_dir / f"backtest_{value}_trades.csv"
        frame.to_csv(export_path, index=False, encoding="utf-8-sig")
        return f"回测任务 {value} 交易日志已导出：`{export_path}`", str(export_path)

    def backtest_to_paper_account(
        self,
        task_id: Any,
        account_name: str,
        capital: Any,
    ) -> tuple[str, int, str, pd.DataFrame, pd.DataFrame, go.Figure]:
        value = require_id(task_id, "回测任务 ID")
        task = BacktestRunner().detail(value)
        name = str(account_name or "").strip() or f"回测{value}模拟账户"
        initial_cash = float(capital or task.get("initial_cash") or 1000000)
        return self.create_paper_account(name, task.get("strategy_id"), initial_cash)

    def compare_backtests(self, task_ids: str, latest_count: Any) -> tuple[str, pd.DataFrame, go.Figure, pd.DataFrame]:
        runner = BacktestRunner()
        ids = [int(item) for item in re.findall(r"\d+", str(task_ids or ""))]
        if not ids:
            count = max(1, min(int(float(latest_count or 5)), 10))
            items = runner.list(status="finished", page=1, page_size=count).get("items") or []
            ids = [int(item["task_id"]) for item in items if item.get("task_id")]
        if not ids:
            return (
                "暂无可对比的已完成回测任务",
                to_frame([], BACKTEST_COMPARE_COLUMNS),
                backtest_compare_figure([]),
                to_frame([], BACKTEST_PARAM_COMPARE_COLUMNS),
            )
        compare_rows: list[dict[str, Any]] = []
        metric_rows: list[dict[str, Any]] = []
        param_rows: list[dict[str, Any]] = []
        for task_id in ids[:10]:
            task = runner.detail(task_id)
            metrics = runner.performance(task_id)
            symbols = task.get("symbols") or []
            symbol_text = ",".join(str(item) for item in symbols) or "-"
            evidence = task.get("parameter_snapshot") or {}
            params = evidence.get("resolved_params") or task.get("params") or {}
            execution = _backtest_execution_config(task)
            params_text = compact_json(params)
            if len(params_text) > 120:
                params_text = params_text[:117] + "..."
            metric_rows.append(
                {
                    "task_id": task_id,
                    "total_return": metrics.get("total_return"),
                    "max_drawdown": metrics.get("max_drawdown"),
                    "sharpe": metrics.get("sharpe"),
                }
            )
            compare_rows.append(
                {
                    "任务ID": task_id,
                    "策略ID": task.get("strategy_id"),
                    "引擎": task.get("engine") or "simple",
                    "标的": symbol_text,
                    "区间": f"{task.get('start_date')} ~ {task.get('end_date')}",
                    "初始资金": _money(task.get("initial_cash")),
                    "总收益": _percent(metrics.get("total_return")),
                    "最大回撤": _percent(metrics.get("max_drawdown")),
                    "夏普": round(_safe_float(metrics.get("sharpe")), 3),
                    "胜率": _percent(metrics.get("win_rate")),
                    "交易数": int(_safe_float(metrics.get("trade_count"))),
                    "订单类型": execution.get("order_type") or "-",
                    "复权": execution.get("price_adjustment") or "-",
                    "参数摘要": params_text,
                }
            )
            param_rows.append(
                {
                    "任务ID": task_id,
                    "标的": symbol_text,
                    "订单类型": execution.get("order_type") or "-",
                    "复权": execution.get("price_adjustment") or "-",
                    "组合约束": _backtest_constraint_text(execution),
                    "参数": compact_json(params),
                    "佣金率": task.get("commission_rate"),
                    "基准": task.get("benchmark") or "-",
                    "创建时间": _format_display_time(task.get("created_at")),
                }
            )
        return (
            f"已对比 {len(compare_rows)} 个回测任务，可重点观察收益、回撤、夏普和参数差异。",
            to_frame(compare_rows, BACKTEST_COMPARE_COLUMNS),
            backtest_compare_figure(metric_rows),
            to_frame(param_rows, BACKTEST_PARAM_COMPARE_COLUMNS),
        )

    def delete_backtest(
        self, task_id: Any
    ) -> tuple[str, pd.DataFrame, pd.DataFrame, go.Figure, pd.DataFrame, go.Figure, pd.DataFrame]:
        value = require_id(task_id, "回测任务 ID")
        BacktestRunner().delete(value)
        return (
            f"回测任务 {value} 已删除",
            self.backtests(),
            metrics_frame({}),
            equity_figure({}),
            to_frame([], TRADE_COLUMNS),
            backtest_attribution_figure({}),
            backtest_attribution_frame({}),
        )

    def latest_backtest(self) -> tuple[Any, pd.DataFrame, go.Figure, pd.DataFrame, go.Figure, pd.DataFrame]:
        try:
            runner = BacktestRunner()
            items = runner.list(page=1, page_size=1).get("items") or []
            if not items:
                return (
                    None,
                    metrics_frame({}),
                    equity_figure({}),
                    to_frame([], TRADE_COLUMNS),
                    backtest_attribution_figure({}),
                    backtest_attribution_frame({}),
                )
            task_id = int(items[0]["task_id"])
            attribution = runner.attribution(task_id)
            return (
                task_id,
                metrics_frame(runner.performance(task_id)),
                equity_figure(runner.equity_curve(task_id)),
                to_frame(runner.trades(task_id, 1, 100), TRADE_COLUMNS),
                backtest_attribution_figure(attribution),
                backtest_attribution_frame(attribution),
            )
        except Exception as exc:
            return (
                None,
                to_frame(
                    [
                        {
                            "类别": "状态",
                            "指标": "最新回测读取失败",
                            "数值": ui_error_message(exc),
                            "解释": "请刷新任务列表后重试。",
                        }
                    ],
                    ["类别", "指标", "数值", "解释"],
                ),
                empty_figure("策略净值与回撤", "最新回测结果不完整，请刷新或重新运行", 460),
                to_frame([], TRADE_COLUMNS),
                backtest_attribution_figure({}),
                backtest_attribution_frame({}),
            )

    def create_paper_account(
        self,
        name: str,
        strategy_id: Any,
        capital: Any,
    ) -> tuple[str, int, str, pd.DataFrame, pd.DataFrame, go.Figure]:
        payload: dict[str, Any] = {"name": require_text(name, "账户名称"), "initial_capital": float(capital or 1000000)}
        if strategy_id not in (None, "", 0):
            payload["strategy_id"] = require_id(strategy_id, "策略 ID")
        service = PaperAccountService()
        account = service.create(payload)
        account_id = int(account["account_id"])
        return (
            f"模拟账户已创建，ID={account_id}",
            account_id,
            compact_json(service.overview(account_id)),
            to_frame(service.positions(account_id), POSITION_COLUMNS),
            to_frame([], ORDER_COLUMNS),
            nav_figure(service.equity_history(account_id)),
        )

    def paper_overview(self, account_id: Any) -> tuple[str, pd.DataFrame, pd.DataFrame, go.Figure]:
        value = require_id(account_id, "模拟账户 ID")
        service = PaperAccountService()
        return (
            compact_json(service.overview(value)),
            to_frame(service.positions(value), POSITION_COLUMNS),
            to_frame(service.orders(value, page=1, page_size=100), ORDER_COLUMNS),
            nav_figure(service.equity_history(value)),
        )

    def latest_paper_account(self) -> tuple[Any, str, pd.DataFrame, pd.DataFrame, go.Figure]:
        accounts = Repository().list("paper_accounts", order_by="updated_at DESC, id DESC", limit=1)
        if not accounts:
            return (
                None,
                compact_json({"status": "暂无模拟账户"}),
                to_frame([], POSITION_COLUMNS),
                to_frame([], ORDER_COLUMNS),
                nav_figure({}),
            )
        account_id = int(accounts[0]["id"])
        overview, positions, orders, figure = self.paper_overview(account_id)
        return account_id, overview, positions, orders, figure

    def paper_order(
        self, account_id: Any, symbol: str, side: str, order_type: str, price: Any, quantity: Any
    ) -> tuple[str, str, pd.DataFrame, pd.DataFrame, go.Figure]:
        value = require_id(account_id, "模拟账户 ID")
        payload: dict[str, Any] = {
            "symbol": resolve_stock_symbol(symbol, "股票代码/名称"),
            "side": side or "buy",
            "order_type": order_type or "market",
            "quantity": int(quantity or 0),
        }
        if payload["quantity"] <= 0:
            raise ValueError("委托数量必须大于 0")
        if price not in (None, "", 0):
            payload["price"] = float(price)
        service = PaperAccountService()
        order = service.order(value, payload)
        status = str(order.get("status") or "")
        return (
            f"委托{status or '已提交'}，订单 ID={order.get('order_id')}；{order.get('match_note') or ''}",
            compact_json(service.overview(value)),
            to_frame(service.positions(value), POSITION_COLUMNS),
            to_frame(service.orders(value, page=1, page_size=100), ORDER_COLUMNS),
            nav_figure(service.equity_history(value)),
        )

    def paper_match_orders(self, account_id: Any) -> tuple[str, str, pd.DataFrame, pd.DataFrame, go.Figure]:
        value = require_id(account_id, "模拟账户 ID")
        service = PaperAccountService()
        result = service.match_orders(value)
        return (
            f"挂单撮合完成：成交 {result['matched_count']} 笔，待观察 {len(result.get('skipped') or [])} 笔。",
            compact_json(service.overview(value) | {"match_result": result}),
            to_frame(service.positions(value), POSITION_COLUMNS),
            to_frame(service.orders(value, page=1, page_size=100), ORDER_COLUMNS),
            nav_figure(service.equity_history(value)),
        )

    def paper_cancel(self, account_id: Any, order_id: Any) -> tuple[str, str, pd.DataFrame, pd.DataFrame, go.Figure]:
        account_value = require_id(account_id, "模拟账户 ID")
        order_value = require_id(order_id, "订单 ID")
        service = PaperAccountService()
        result = service.cancel(account_value, order_value)
        return (
            f"委托 {order_value} 已撤销",
            compact_json(service.overview(account_value) | {"cancel_result": result}),
            to_frame(service.positions(account_value), POSITION_COLUMNS),
            to_frame(service.orders(account_value, page=1, page_size=100), ORDER_COLUMNS),
            nav_figure(service.equity_history(account_value)),
        )
