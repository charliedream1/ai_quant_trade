"""Live frontend service callbacks."""

from __future__ import annotations

from .foundation import (
    LIVE_ALERT_COLUMNS,
    LIVE_BROKER_ADAPTER_COLUMNS,
    LIVE_DRY_RUN_ORDER_COLUMNS,
    LIVE_LOG_COLUMNS,
    LIVE_PRECHECK_COLUMNS,
    LIVE_RISK_COLUMNS,
    LIVE_RUN_COLUMNS,
    LIVE_VALIDATION_PARAM_KEY,
    ORDER_COLUMNS,
    POSITION_COLUMNS,
    Any,
    DataSourceManager,
    LiveBrokerEventService,
    LiveTradingService,
    Repository,
    _display_now,
    compact_json,
    parse_json,
    parse_stock_symbols,
    pd,
    require_id,
    require_text,
    to_frame,
)
from .visuals import (
    _duration_text,
    _format_display_time,
    _live_validation_config,
    _money,
    _percent,
    _safe_float,
    _seconds_since,
    _signed_money,
)


class LiveServiceMixin:
    """Callbacks owned by the live frontend domain."""

    def live_configs(self) -> pd.DataFrame:
        return to_frame(LiveTradingService().list_configs(page=1, page_size=100))

    def live_runs(self) -> pd.DataFrame:
        rows = Repository().db.query(
            """SELECT r.id AS run_id, r.config_id, c.name, c.channel, r.status,
                      r.started_at, r.stopped_at, r.heartbeat_at, r.error_msg
               FROM live_runs r
               JOIN live_configs c ON c.id = r.config_id
               ORDER BY r.started_at DESC, r.id DESC
               LIMIT 100"""
        )
        return to_frame(rows, LIVE_RUN_COLUMNS)

    def live_broker_adapters(self) -> pd.DataFrame:
        rows: list[dict[str, Any]] = []
        for item in LiveBrokerEventService().adapters():
            row = dict(item)
            row["event_types"] = " / ".join(str(value) for value in row.get("event_types") or [])
            rows.append(row)
        return to_frame(rows, LIVE_BROKER_ADAPTER_COLUMNS)

    def live_risk_summary(self, config_id: Any) -> pd.DataFrame:
        if config_id in (None, "", 0):
            return to_frame(
                [{"item": "配置选择", "value": "-", "status": "待选择", "note": "输入配置 ID 后查看风控阈值"}],
                LIVE_RISK_COLUMNS,
            )
        config = LiveTradingService().detail_config(require_id(config_id, "配置 ID"))
        return self._live_risk_frame(config)

    def create_live_config(
        self,
        name: str,
        strategy_id: Any,
        channel: str,
        capital: Any,
        params: str,
        risk: str,
        validation_backtest_id: Any = None,
        validation_account_id: Any = None,
    ) -> tuple[str, pd.DataFrame]:
        params_payload = parse_json(params, "策略参数")
        if not isinstance(params_payload, dict):
            raise ValueError("策略参数必须是 JSON 对象")
        validation_payload = _live_validation_config(validation_backtest_id, validation_account_id)
        if validation_payload:
            params_payload[LIVE_VALIDATION_PARAM_KEY] = validation_payload
        item = LiveTradingService().create_config(
            {
                "name": require_text(name, "配置名称"),
                "strategy_id": require_id(strategy_id, "策略 ID"),
                "channel": channel or "paper",
                "capital": float(capital or 100000),
                "params": params_payload,
                "risk_controls": parse_json(risk, "风控参数"),
            }
        )
        return f"实盘配置已创建，ID={item.get('config_id', item.get('id'))}", self.live_configs()

    def update_live_risk(self, config_id: Any, risk: str) -> tuple[str, pd.DataFrame, pd.DataFrame]:
        value = require_id(config_id, "配置 ID")
        risk_controls = parse_json(risk, "风控参数")
        if not isinstance(risk_controls, dict):
            raise ValueError("风控参数必须是 JSON 对象")
        LiveTradingService().patch_risk(value, risk_controls)
        return f"实盘配置 {value} 风控阈值已更新", self.live_configs(), self.live_risk_summary(value)

    def live_validation_summary(self, config_id: Any) -> pd.DataFrame:
        if config_id in (None, "", 0):
            return to_frame(
                [
                    {
                        "检查项": "配置选择",
                        "当前值": "-",
                        "状态": "待选择",
                        "说明": "输入配置 ID 后查看回测/模拟发布验证",
                    }
                ],
                LIVE_PRECHECK_COLUMNS,
            )
        value = require_id(config_id, "配置 ID")
        return to_frame(LiveTradingService().validation_checks(value), LIVE_PRECHECK_COLUMNS)

    def live_dry_run_plan(
        self,
        config_id: Any,
        symbols: str,
        side: str,
        order_type: str,
        target_weight: Any,
        max_orders: Any,
    ) -> tuple[str, pd.DataFrame, pd.DataFrame]:
        summary, orders, checks, _ = self._live_dry_run_payload(
            config_id,
            symbols,
            side,
            order_type,
            target_weight,
            max_orders,
        )
        return summary, to_frame(orders, LIVE_DRY_RUN_ORDER_COLUMNS), to_frame(checks, LIVE_PRECHECK_COLUMNS)

    def live_precheck_start(
        self,
        config_id: Any,
        symbols: str,
        side: str,
        order_type: str,
        target_weight: Any,
        max_orders: Any,
    ) -> tuple[str, int, str, pd.DataFrame, pd.DataFrame, str, pd.DataFrame, pd.DataFrame]:
        plan_summary, plan_orders, checks, blocked = self._live_dry_run_payload(
            config_id,
            symbols,
            side,
            order_type,
            target_weight,
            max_orders,
        )
        if blocked:
            blocked_items = [str(row["检查项"]) for row in checks if row.get("状态") == "拦截"]
            message = "运行前风控拦截：" + "、".join(blocked_items)
            return (
                message,
                0,
                compact_json({"status": "blocked", "reason": message}),
                to_frame([], ORDER_COLUMNS),
                to_frame([], POSITION_COLUMNS),
                plan_summary,
                to_frame(plan_orders, LIVE_DRY_RUN_ORDER_COLUMNS),
                to_frame(checks, LIVE_PRECHECK_COLUMNS),
            )
        start_message, run_id, run_status, orders, positions = self.live_start(config_id)
        return (
            f"{start_message}；运行前风控检查已通过",
            run_id,
            run_status,
            orders,
            positions,
            plan_summary,
            to_frame(plan_orders, LIVE_DRY_RUN_ORDER_COLUMNS),
            to_frame(checks, LIVE_PRECHECK_COLUMNS),
        )

    def live_start(self, config_id: Any) -> tuple[str, int, str, pd.DataFrame, pd.DataFrame]:
        service = LiveTradingService()
        value = require_id(config_id, "配置 ID")
        config = service.detail_config(value)
        blockers = self._live_config_start_blockers(config)
        if blockers:
            raise ValueError("运行前风控拦截：" + "；".join(blockers))
        result = service.start_run({"config_id": value})
        run_id = int(result["run_id"])
        return (
            f"运行 {run_id} 已启动",
            run_id,
            compact_json(result),
            to_frame(service.orders(run_id, page=1, page_size=100)),
            to_frame(service.positions(run_id)),
        )

    def live_status(self, run_id: Any) -> tuple[str, pd.DataFrame, pd.DataFrame]:
        value = require_id(run_id, "运行 ID")
        service = LiveTradingService()
        return (
            compact_json(service.status(value)),
            to_frame(service.orders(value, page=1, page_size=100)),
            to_frame(service.positions(value)),
        )

    def live_monitor(self, run_id: Any) -> tuple[str, pd.DataFrame, pd.DataFrame]:
        if run_id in (None, "", 0):
            return (
                "**运行监控**：请选择运行 ID 后刷新。\n\n最近心跳：`-`。",
                to_frame(
                    [
                        {
                            "severity": "info",
                            "title": "待选择运行",
                            "message": "输入运行 ID 后刷新异常告警。",
                            "triggered_at": _display_now(),
                        }
                    ],
                    LIVE_ALERT_COLUMNS,
                ),
                to_frame(
                    [
                        {
                            "time": "-",
                            "level": "info",
                            "event": "待刷新",
                            "detail": "输入运行 ID 后查看运行日志。",
                        }
                    ],
                    LIVE_LOG_COLUMNS,
                ),
            )
        value = require_id(run_id, "运行 ID")
        status = LiveTradingService().status(value)
        config = LiveTradingService().detail_config(int(status["config_id"]))
        alerts = self._live_alert_rows(status, config)
        logs = self._live_log_rows(status, config)
        heartbeat_age = _seconds_since(status.get("last_heartbeat_at"))
        status_label = status.get("status_label") or status.get("status") or "-"
        summary = (
            f"**运行监控**：运行 `{value}` / 配置 `{status.get('config_id')}` / 状态 `{status_label}`。\n\n"
            f"最近心跳：`{_format_display_time(status.get('last_heartbeat_at'))}`，"
            f"距今 `{_duration_text(heartbeat_age)}`；"
            f"今日成交 `{status.get('today_trade_count', 0)}` 笔，"
            f"今日盈亏 `{_signed_money(status.get('today_pnl'))}`。"
        )
        return summary, to_frame(alerts, LIVE_ALERT_COLUMNS), to_frame(logs, LIVE_LOG_COLUMNS)

    def live_stop(self, run_id: Any) -> tuple[str, str, pd.DataFrame, pd.DataFrame]:
        value = require_id(run_id, "运行 ID")
        service = LiveTradingService()
        result = service.stop_run(value, graceful=True)
        return (
            f"运行 {value} 已停止",
            compact_json(result),
            to_frame(service.orders(value, page=1, page_size=100)),
            to_frame(service.positions(value)),
        )

    def live_pause(self, run_id: Any) -> tuple[str, str, pd.DataFrame, pd.DataFrame]:
        value = require_id(run_id, "运行 ID")
        service = LiveTradingService()
        result = service.pause_run(value)
        return (
            f"运行 {value} 已暂停",
            compact_json(result),
            to_frame(service.orders(value, page=1, page_size=100)),
            to_frame(service.positions(value)),
        )

    def live_resume(self, run_id: Any) -> tuple[str, str, pd.DataFrame, pd.DataFrame]:
        value = require_id(run_id, "运行 ID")
        service = LiveTradingService()
        result = service.resume_run(value)
        return (
            f"运行 {value} 已恢复",
            compact_json(result),
            to_frame(service.orders(value, page=1, page_size=100)),
            to_frame(service.positions(value)),
        )

    def live_mark_error(self, run_id: Any, message: str) -> tuple[str, str, pd.DataFrame, pd.DataFrame]:
        value = require_id(run_id, "运行 ID")
        service = LiveTradingService()
        result = service.mark_error(value, require_text(message, "异常原因"))
        return (
            f"运行 {value} 已标记异常冻结",
            compact_json(result),
            to_frame(service.orders(value, page=1, page_size=100)),
            to_frame(service.positions(value)),
        )

    def live_broker_event(
        self, run_id: Any, event_type: str, message: str
    ) -> tuple[str, str, pd.DataFrame, pd.DataFrame]:
        value = require_id(run_id, "运行 ID")
        event = str(event_type or "heartbeat").strip().lower() or "heartbeat"
        payload = {"event_type": event}
        if event == "error":
            payload["message"] = require_text(message, "事件说明")
        elif str(message or "").strip():
            payload["message"] = str(message).strip()
        service = LiveBrokerEventService()
        result = service.handle_event(value, payload)
        live_service = LiveTradingService()
        action = "异常冻结" if result.get("frozen") else "心跳刷新"
        return (
            f"运行 {value} 通道事件已写入：{action}",
            compact_json(result),
            to_frame(live_service.orders(value, page=1, page_size=100)),
            to_frame(live_service.positions(value)),
        )

    def _live_dry_run_payload(
        self,
        config_id: Any,
        symbols: str,
        side: str,
        order_type: str,
        target_weight: Any,
        max_orders: Any,
    ) -> tuple[str, list[dict[str, Any]], list[dict[str, Any]], bool]:
        service = LiveTradingService()
        config = service.detail_config(require_id(config_id, "配置 ID"))
        risk = config.get("risk_controls") or {}
        channel = str(config.get("channel") or "paper")
        capital = _safe_float(config.get("capital"))
        side_value = "sell" if str(side or "").strip().lower() in {"sell", "卖出"} else "buy"
        order_type_value = "limit" if str(order_type or "").strip().lower() in {"limit", "限价"} else "market"
        weight = min(max(_safe_float(target_weight, 0.2), 0.01), 1.0)
        limit = min(max(int(_safe_float(max_orders, 5)), 1), 20)
        selected_symbols = parse_stock_symbols(symbols)[:limit]
        if not selected_symbols:
            raise ValueError("请输入至少 1 个股票代码、名称、拼音或别名用于 dry-run 订单计划")

        quotes = {str(item.get("symbol")): item for item in DataSourceManager().stock_quotes(selected_symbols)}
        per_symbol_budget = capital * weight / max(len(selected_symbols), 1)
        max_position_count = int(_safe_float(risk.get("max_position_count"), limit))
        single_limit = _safe_float(
            risk.get("single_position_limit") or risk.get("max_single_position_pct") or risk.get("max_position_weight"),
            0.0,
        )

        orders: list[dict[str, Any]] = []
        blocked_symbols = 0
        total_amount = 0.0
        for symbol in selected_symbols:
            quote = quotes.get(symbol) or {}
            price = _safe_float(quote.get("latest_price") or quote.get("price"))
            quantity = int(per_symbol_budget / price // 100 * 100) if price > 0 else 0
            amount = round(price * quantity, 2)
            total_amount += amount
            status = "通过"
            note = f"行情源 {quote.get('data_source') or '-'}，更新时间 {quote.get('updated_at') or '-'}"
            if price <= 0:
                status = "拦截"
                note = "缺少有效行情价格，不能生成订单计划"
                blocked_symbols += 1
            elif quantity <= 0:
                status = "拦截"
                note = "单只预算不足以买入 A 股最小一手，请提高资金或降低标的数量"
                blocked_symbols += 1
            elif single_limit > 0 and amount / max(capital, 1.0) > single_limit:
                status = "警告"
                note = f"单票计划权重超过风控上限 {_percent(single_limit)}，需人工复核"
            orders.append(
                {
                    "代码": symbol,
                    "名称": quote.get("name") or symbol,
                    "方向": "买入" if side_value == "buy" else "卖出",
                    "订单类型": "市价" if order_type_value == "market" else "限价",
                    "计划价格": round(price, 3),
                    "计划数量": quantity,
                    "计划金额": amount,
                    "目标权重": _percent(amount / max(capital, 1.0)),
                    "风控状态": status,
                    "说明": note,
                }
            )

        checks = self._live_precheck_rows(
            config=config,
            orders=orders,
            target_weight=weight,
            total_amount=total_amount,
            blocked_symbols=blocked_symbols,
            max_position_count=max_position_count,
        )
        blocked = any(row.get("状态") == "拦截" for row in checks)
        warning_count = sum(1 for row in checks if row.get("状态") == "警告")
        state = "拦截" if blocked else ("需复核" if warning_count else "通过")
        summary = (
            f"**dry-run订单计划**：配置 `{config.get('config_id')}` / 通道 `{channel}` / "
            f"方向 `{orders[0]['方向']}` / 计划资金 `{_money(total_amount)}` / "
            f"目标资金占比 `{_percent(weight)}`。\n\n"
            f"**运行前风控**：{state}；检查项 `{len(checks)}` 个，订单 `{len(orders)}` 笔，"
            f"拦截标的 `{blocked_symbols}` 个。该计划仅用于发布前校验，不会触发真实委托。"
        )
        return summary, orders, checks, blocked

    def _live_precheck_rows(
        self,
        config: dict[str, Any],
        orders: list[dict[str, Any]],
        target_weight: float,
        total_amount: float,
        blocked_symbols: int,
        max_position_count: int,
    ) -> list[dict[str, Any]]:
        capital = _safe_float(config.get("capital"))
        risk = config.get("risk_controls") or {}
        channel = str(config.get("channel") or "paper")
        adapter = LiveBrokerEventService().registry.describe(channel)
        rows = [
            {
                "检查项": "通道适配器",
                "当前值": channel,
                "状态": "通过" if adapter.available else "拦截",
                "说明": adapter.note,
            },
            {
                "检查项": "资金规模",
                "当前值": _money(capital),
                "状态": "通过" if capital > 0 else "拦截",
                "说明": "资金必须大于 0 才能启动运行",
            },
            {
                "检查项": "最大持仓数",
                "当前值": f"{len(orders)} / {max_position_count}",
                "状态": "通过" if len(orders) <= max_position_count and max_position_count > 0 else "拦截",
                "说明": "订单标的数量不能超过 max_position_count",
            },
            {
                "检查项": "单日亏损阈值",
                "当前值": _percent(risk.get("daily_loss_limit")) if risk.get("daily_loss_limit") is not None else "-",
                "状态": "通过" if _safe_float(risk.get("daily_loss_limit")) > 0 else "拦截",
                "说明": "启动前必须设置 daily_loss_limit，便于触发风控复核",
            },
            {
                "检查项": "计划资金占用",
                "当前值": f"{_money(total_amount)} / {_percent(target_weight)}",
                "状态": "通过" if 0 < total_amount <= capital else "拦截",
                "说明": "计划金额必须大于 0 且不超过配置资金",
            },
            {
                "检查项": "行情与手数",
                "当前值": f"拦截 {blocked_symbols} / {len(orders)}",
                "状态": "通过" if blocked_symbols == 0 else "拦截",
                "说明": "所有计划订单都需要有效行情，且买入数量满足 A 股一手规则",
            },
        ]
        config_id = int(config.get("config_id") or config.get("id") or 0)
        if config_id > 0:
            rows.extend(LiveTradingService().validation_checks(config_id))
        if any(row.get("风控状态") == "警告" for row in orders):
            rows.append(
                {
                    "检查项": "单票权重",
                    "当前值": "存在超限标的",
                    "状态": "警告",
                    "说明": "单票计划权重超过配置上限，当前不自动拦截，但需要人工复核",
                }
            )
        return rows

    def _live_config_start_blockers(self, config: dict[str, Any]) -> list[str]:
        risk = config.get("risk_controls") or {}
        blockers = []
        config_id = int(config.get("config_id") or config.get("id") or 0)
        if config_id > 0:
            blockers.extend(LiveTradingService().start_blockers(config_id))
            return blockers
        adapter_blocker = LiveBrokerEventService().registry.start_blocker(str(config.get("channel") or "paper"))
        if adapter_blocker:
            blockers.append(adapter_blocker)
        if _safe_float(config.get("capital")) <= 0:
            blockers.append("资金规模必须大于 0")
        if _safe_float(risk.get("max_position_count")) <= 0:
            blockers.append("缺少 max_position_count")
        if _safe_float(risk.get("daily_loss_limit")) <= 0:
            blockers.append("缺少 daily_loss_limit")
        return blockers

    def _live_risk_frame(self, config: dict[str, Any]) -> pd.DataFrame:
        risk = config.get("risk_controls") or {}
        capital = float(config.get("capital") or 0.0)
        config_id = int(config.get("config_id") or config.get("id") or 0)
        adapter = LiveBrokerEventService().registry.describe(str(config.get("channel") or "paper"))
        validation_rows = LiveTradingService().validation_checks(config_id) if config_id > 0 else []
        validation_blockers = [row for row in validation_rows if row.get("状态") == "拦截"]
        rows = [
            {
                "item": "资金规模",
                "value": _money(capital),
                "status": "已配置" if capital > 0 else "待配置",
                "note": "用于实盘运行资金上限展示，不代表真实券商资金已接入",
            },
            {
                "item": "最大持仓数",
                "value": risk.get("max_position_count", "-"),
                "status": "已配置" if risk.get("max_position_count") else "缺失",
                "note": "用于限制同时持仓数量",
            },
            {
                "item": "单日亏损阈值",
                "value": _percent(risk.get("daily_loss_limit")) if risk.get("daily_loss_limit") is not None else "-",
                "status": "已配置" if risk.get("daily_loss_limit") is not None else "缺失",
                "note": "超过阈值时需要人工复核",
            },
            {
                "item": "通道",
                "value": config.get("channel") or "-",
                "status": adapter.status,
                "note": adapter.note,
            },
            {
                "item": "发布验证",
                "value": f"{len(validation_rows) - len(validation_blockers)} / {len(validation_rows)}",
                "status": "已通过" if validation_rows and not validation_blockers else "待补齐",
                "note": "要求回测验证和模拟账户验证都不存在拦截项后才能启动",
            },
        ]
        return to_frame(rows, LIVE_RISK_COLUMNS)

    def _live_alert_rows(self, status: dict[str, Any], config: dict[str, Any]) -> list[dict[str, Any]]:
        now_text = _display_now()
        rows: list[dict[str, Any]] = []
        heartbeat_age = _seconds_since(status.get("last_heartbeat_at"))
        run_status = str(status.get("status") or "")
        if not status.get("last_heartbeat_at"):
            rows.append(
                {
                    "severity": "warning",
                    "title": "缺少最近心跳",
                    "message": "运行记录没有 heartbeat_at，建议确认执行器是否正常回写。",
                    "triggered_at": now_text,
                }
            )
        elif run_status == "running" and heartbeat_age is not None and heartbeat_age > 300:
            rows.append(
                {
                    "severity": "warning",
                    "title": "心跳可能滞后",
                    "message": f"最近心跳距今 {_duration_text(heartbeat_age)}，超过 5 分钟需复核。",
                    "triggered_at": now_text,
                }
            )
        adapter = LiveBrokerEventService().registry.describe(str(config.get("channel") or "paper"))
        if not adapter.available:
            rows.append(
                {
                    "severity": "warning",
                    "title": "通道适配器未接入",
                    "message": adapter.note,
                    "triggered_at": now_text,
                }
            )
        if status.get("last_error"):
            rows.append(
                {
                    "severity": "critical",
                    "title": "运行错误",
                    "message": str(status.get("last_error")),
                    "triggered_at": now_text,
                }
            )
        if not rows:
            rows.append(
                {
                    "severity": "ok",
                    "title": "暂无异常告警",
                    "message": "最近心跳和通道状态在当前占位实盘能力范围内正常。",
                    "triggered_at": now_text,
                }
            )
        return rows

    def _live_log_rows(self, status: dict[str, Any], config: dict[str, Any]) -> list[dict[str, Any]]:
        rows = [
            {
                "time": _format_display_time(config.get("updated_at")),
                "level": "info",
                "event": "配置更新",
                "detail": f"配置 {config.get('config_id')} / 通道 {config.get('channel')} / 资金 {_money(config.get('capital'))}",
            },
            {
                "time": _format_display_time(status.get("last_heartbeat_at")),
                "level": "info",
                "event": "最近心跳",
                "detail": f"运行 {status.get('run_id')} 状态 {status.get('status_label') or status.get('status')}",
            },
        ]
        if status.get("last_error"):
            rows.append(
                {
                    "time": _display_now(),
                    "level": "error",
                    "event": "运行错误",
                    "detail": str(status.get("last_error")),
                }
            )
        return rows
