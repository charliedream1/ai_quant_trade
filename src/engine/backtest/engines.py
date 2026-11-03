"""Backtest engine registry and optional integration diagnostics."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from importlib import import_module
from importlib.metadata import PackageNotFoundError, version
from importlib.util import find_spec
from typing import Any, Protocol

from src.core.exceptions import BusinessError, ErrorCode
from src.data import DataSourceManager
from src.engine.execution.costs import slipped_price
from src.engine.execution.ledger import cost_summary
from src.engine.execution.policy import capability_gaps, policy_for
from src.strategy import MarketEvent, StrategyContext, StrategyPort, StrategySignal

from .experiments import ohlcv_digest
from .fills import fill_details, record_rejection, reduce_position

SymbolList = list[str]
PositionBook = dict[str, dict[str, Any]]

DEFAULT_ENGINE = "simple"
QLIB_ENGINE = "qlib"
SUPPORTED_ENGINE_KEYS = {DEFAULT_ENGINE, QLIB_ENGINE, "composition"}
DEFAULT_COMMISSION_RATE = 0.0003
DEFAULT_SLIPPAGE_RATE = 0.0
DEFAULT_HISTORY_BARS = 120
TRADING_DAYS_PER_YEAR = 252
DEFAULT_ORDER_TYPE = "market"
DEFAULT_PRICE_ADJUSTMENT = "qfq"
SUPPORTED_ORDER_TYPES = {"market", "open", "limit"}
SUPPORTED_PRICE_ADJUSTMENTS = {"qfq", "hfq", "none"}


class BacktestEngine(Protocol):
    key: str
    label: str
    description: str

    def run(
        self,
        payload: dict[str, Any],
        symbols: SymbolList,
        initial_cash: float,
        strategy: StrategyPort | None = None,
        data: DataSourceManager | None = None,
    ) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
        """Run a backtest and return metrics, equity curve and trades."""


@dataclass(slots=True)
class EngineDiagnostic:
    key: str
    label: str
    status: str
    version: str
    license: str
    description: str
    next_step: str

    def to_dict(self) -> dict[str, str]:
        return {
            "key": self.key,
            "label": self.label,
            "status": self.status,
            "version": self.version,
            "license": self.license,
            "description": self.description,
            "next_step": self.next_step,
        }


class SimpleBacktestEngine:
    key = DEFAULT_ENGINE
    label = "内置轻量回测"
    description = "使用日 K 线逐根驱动标准策略端口的轻量事件回测引擎。"

    def run(
        self,
        payload: dict[str, Any],
        symbols: SymbolList,
        initial_cash: float,
        strategy: StrategyPort | None = None,
        data: DataSourceManager | None = None,
    ) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
        if strategy is None:
            raise BusinessError(ErrorCode.STRATEGY_INVALID, "内置回测引擎需要可执行的策略端口")
        return _run_event_backtest(payload, symbols, initial_cash, strategy, data or DataSourceManager())


class QlibBacktestEngine:
    key = QLIB_ENGINE
    label = "Qlib 投研引擎"
    description = "面向因子、模型、信号评估和组合回测的可选外部投研引擎。"

    def run(
        self,
        payload: dict[str, Any],
        symbols: SymbolList,
        initial_cash: float,
        strategy: StrategyPort | None = None,
        data: DataSourceManager | None = None,
    ) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
        from src.engine.research.qlib_workflow import QlibWorkflowService

        service = QlibWorkflowService()
        config = service.config()
        run = service.create_run(
            {
                "run_type": "backtest",
                "workflow_path": payload.get("workflow_path") or config.get("workflow_path"),
                "provider_uri": payload.get("provider_uri") or config.get("provider_uri"),
                "params": {
                    **dict(payload.get("params") or {}),
                    "market": payload.get("market") or config.get("market") or "",
                    "benchmark": payload.get("benchmark") or config.get("benchmark") or "",
                },
            }
        )
        if run.get("status") != "finished":
            raise BusinessError(
                ErrorCode.CONFIG_DEPENDENCY,
                str(run.get("error_msg") or "Qlib workflow 未完成"),
                {"run": run, "symbols": symbols, "initial_cash": initial_cash},
            )
        run_metrics = dict(run.get("metrics") or {})
        metrics = dict(run_metrics.get("portfolio_metrics") or {})
        metrics.update(
            {
                "qlib_status": run_metrics.get("qlib_status") or run.get("status"),
                "qlib_version": run_metrics.get("qlib_version") or "-",
                "engine_mode": "qlib_qrun",
                "data_source": "qlib",
                "trade_count": 0,
                "result_scope": "Qlib 指标摘要（未提供逐日组合曲线）",
                "curve_available": False,
            }
        )
        curve = run.get("equity_curve") or run.get("curve") or {}
        if not isinstance(curve, dict):
            curve = {}
        dates = list(curve.get("dates") or [])
        equity = list(curve.get("equity") or [])
        curve_available = len(dates) >= 2 and len(dates) == len(equity)
        metrics["curve_available"] = curve_available
        metrics["result_scope"] = (
            "Qlib 指标与逐日组合曲线" if curve_available else "Qlib 指标摘要（未提供逐日组合曲线）"
        )
        return (
            metrics,
            {
                **curve,
                "dates": dates,
                "equity": equity,
                "benchmark": list(curve.get("benchmark") or []),
                "drawdown": list(curve.get("drawdown") or []),
                "message": "" if curve_available else "Qlib 已完成指标运行，但没有可用的逐日组合净值产物。",
            },
            [],
        )


def normalize_engine_key(value: Any) -> str:
    key = str(value or DEFAULT_ENGINE).strip().lower()
    if key not in SUPPORTED_ENGINE_KEYS:
        raise BusinessError(ErrorCode.INVALID_PARAM, f"不支持的回测引擎：{key}")
    return key


def get_backtest_engine(key: str | None = None) -> BacktestEngine:
    normalized = normalize_engine_key(key)
    if normalized == "composition":
        return import_module("src.engine.composition.bridge").CompositionBacktestEngine()
    if normalized == QLIB_ENGINE:
        return QlibBacktestEngine()
    return SimpleBacktestEngine()


def engine_diagnostics() -> list[dict[str, str]]:
    return [
        EngineDiagnostic(
            key=DEFAULT_ENGINE,
            label=SimpleBacktestEngine.label,
            status="available",
            version="built-in",
            license="project",
            description=SimpleBacktestEngine.description,
            next_step="可直接运行日 K 策略回测；组合约束、行业中性和模型工作流建议接入 Qlib。",
        ).to_dict(),
        qlib_diagnostic().to_dict(),
        EngineDiagnostic(
            key="composition",
            label="组合目标权重引擎",
            status="available",
            version="built-in",
            license="project",
            description="日期批次、资金预算和共享风险的日线研究引擎",
            next_step="在策略工坊发布方案后选择此引擎",
        ).to_dict(),
    ]


def qlib_diagnostic() -> EngineDiagnostic:
    if find_spec("qlib") is None:
        return EngineDiagnostic(
            key=QLIB_ENGINE,
            label=QlibBacktestEngine.label,
            status="missing",
            version="-",
            license="MIT",
            description=QlibBacktestEngine.description,
            next_step="在独立环境安装 pyqlib，并配置 qlib provider_uri 与 workflow YAML。",
        )
    return EngineDiagnostic(
        key=QLIB_ENGINE,
        label=QlibBacktestEngine.label,
        status="available",
        version=_package_version("pyqlib"),
        license="MIT",
        description=QlibBacktestEngine.description,
        next_step="已检测到 qlib；下一步配置 workflow YAML 后接入 qlib 运行记录。",
    )


def _package_version(package_name: str) -> str:
    try:
        return version(package_name)
    except PackageNotFoundError:
        return "installed"


def _run_event_backtest(
    payload: dict[str, Any],
    symbols: SymbolList,
    initial_cash: float,
    strategy: StrategyPort,
    data: DataSourceManager,
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    runtime = getattr(getattr(strategy, "instance", None), "runtime", None)
    policy = policy_for(
        payload,
        {
            "commission_rate": payload.get("commission_rate", DEFAULT_COMMISSION_RATE),
            "slippage_rate": payload.get("slippage_rate", 0),
            "lot_size": _lot_size(payload),
        },
    )
    payload["lot_size"] = int(policy["lot_size"])
    payload["_warmup"] = callable(getattr(runtime, "warmup", None))
    payload["_history_warmup"] = payload["_warmup"] or policy["max_participation"] < 1
    events_by_symbol = _load_events(data, symbols, payload)
    gaps = capability_gaps({s: [event.raw for event in values] for s, values in events_by_symbol.items()}, policy)
    if _normalize_price_adjustment(payload.get("price_adjustment")) != "none":
        if policy["validation_mode"] == "strict":
            raise BusinessError(ErrorCode.INVALID_PARAM, "严格账户校验需要未复权行情及权益事件确认")
        gaps.append("复权价格研究：费用按研究成交额计算，不等于原始现金与公司行为账本")
    payload["_past_events"] = {s: list(payload.get("_warmup_history", {}).get(s, [])) for s in symbols}
    if not any(events_by_symbol.values()):
        raise BusinessError(ErrorCode.DATA_SOURCE_ERROR, "没有可用于回测的历史 K 线")

    context = StrategyContext(
        params=dict(payload.get("params") or {}),
        symbols=symbols,
        mode="backtest",
        metadata={
            "engine": DEFAULT_ENGINE,
            "data_source": data.source_name,
            "start_date": payload["start_date"],
            "end_date": payload["end_date"],
            "order_type": _normalize_order_type(payload.get("order_type")),
            "price_adjustment": _normalize_price_adjustment(payload.get("price_adjustment")),
            "max_position_count": _max_position_count(payload),
            "max_position_weight": _max_position_weight(payload),
            "lot_size": _lot_size(payload),
        },
    )
    cash = float(initial_cash)
    positions: PositionBook = {}
    trades: list[dict[str, Any]] = []
    curve_dates: list[str] = []
    equity: list[float] = []
    benchmark: list[float] = []
    drawdown: list[float] = []
    cash_curve: list[float] = []
    exposure: list[float] = []
    position_count: list[int] = []
    latest_prices: dict[str, float] = {}
    first_prices = _first_prices(events_by_symbol)
    peak = max(initial_cash, 0.01)

    strategy.on_start(context)
    try:
        if payload.get("_warmup_history") and runtime:
            runtime.warmup(payload["_warmup_history"])
        if context.metadata.get("requires_composition"):
            raise BusinessError(ErrorCode.INVALID_PARAM, "组合策略需要composition引擎，不能作为单标的策略运行")
        if context.metadata.get("requires_aligned_calendar"):
            calendars = {tuple(event.timestamp for event in events_by_symbol.get(symbol) or []) for symbol in symbols}
            if len(calendars) != 1:
                raise BusinessError(ErrorCode.INVALID_PARAM, "截面模型需要标的日期完全对齐，请补齐或筛选历史行情")
        by_date = {symbol: {event.timestamp: event for event in values} for symbol, values in events_by_symbol.items()}
        calendar = sorted({stamp for values in by_date.values() for stamp in values})
        for session, stamp in enumerate(calendar):
            payload["_session_index"] = session
            if payload.get("_checkpoint"):
                payload["_checkpoint"]()
            current_date = ""
            for symbol in symbols:
                event = by_date[symbol].get(stamp)
                if event is None:
                    continue
                current_date = current_date or event.timestamp
                latest_prices[event.symbol] = event.close
                _sync_context(context, cash, positions, latest_prices, current_date, initial_cash)
                signals = strategy.on_bar(event, context)
                cash = _apply_signals(cash, positions, trades, signals, event, payload)
                payload["_past_events"][symbol].append(event.raw)

            if current_date:
                market_value = _market_value(positions, latest_prices)
                total_equity = cash + market_value
                peak = max(peak, total_equity)
                curve_dates.append(current_date)
                equity.append(round(total_equity, 2))
                benchmark.append(round(_dated_benchmark(initial_cash, first_prices, latest_prices), 2))
                drawdown.append(round((total_equity - peak) / peak, 4))
                cash_curve.append(round(cash, 2))
                exposure.append(round(market_value / total_equity, 4) if total_equity else 0.0)
                position_count.append(len(positions))

        cash = _close_open_positions(cash, positions, trades, events_by_symbol, payload)
        if equity:
            final_equity = _portfolio_value(cash, positions, latest_prices)
            final_peak = max(max(equity), final_equity, 0.01)
            equity[-1] = round(final_equity, 2)
            drawdown[-1] = round((final_equity - final_peak) / final_peak, 4)
        if cash_curve:
            cash_curve[-1] = round(cash, 2)
        if exposure:
            exposure[-1] = _market_value(positions, latest_prices) / final_equity if final_equity else 0.0
        if position_count:
            position_count[-1] = len(positions)
    finally:
        _sync_context(context, cash, positions, latest_prices, curve_dates[-1] if curve_dates else "", initial_cash)
        strategy.on_stop(context)

    if not equity:
        equity = [round(initial_cash, 2)]
        benchmark = [round(initial_cash, 2)]
        drawdown = [0.0]
        curve_dates = [payload["start_date"]]

    curve = {
        "dates": curve_dates,
        "equity": equity,
        "benchmark": benchmark,
        "drawdown": drawdown,
        "cash": cash_curve,
        "exposure": exposure,
        "position_count": position_count,
    }
    metrics = _metrics(initial_cash, equity, benchmark, drawdown, trades, data.source_name, payload, curve)
    asset_type = str(context.metadata.get("asset_type") or "")
    if asset_type == "etf":
        metrics.update(
            {
                "asset_type": "etf",
                "strategy_family": context.metadata.get("etf_strategy") or "etf",
                "etf_universe": (payload.get("params") or {}).get("universe") or "",
                "tracking_error": _tracking_error(equity, benchmark),
                "etf_rebalance_frequency": (payload.get("params") or {}).get("rebalance_days"),
            }
        )
    metrics["data_fingerprint"] = ohlcv_digest(events_by_symbol)
    metrics["date_coverage"] = payload.get("_coverage", {})
    metrics.update(cost_summary(payload.get("_execution_orders", []), initial_cash, equity[-1]))
    metrics.update(execution_costs=policy, execution_gaps=gaps)
    metrics["bars_by_symbol"] = {symbol: len(events) for symbol, events in events_by_symbol.items()}
    if context.metadata.get("model_diagnostics"):
        metrics["model_diagnostics"] = context.metadata["model_diagnostics"]
    return metrics, curve, trades


def _load_events(
    data: DataSourceManager,
    symbols: SymbolList,
    payload: dict[str, Any],
) -> dict[str, list[MarketEvent]]:
    from src.data.backtest_history import load_history

    adjustment = _normalize_price_adjustment(payload.get("price_adjustment"))
    events: dict[str, list[MarketEvent]] = {}
    for symbol in symbols:
        if payload.get("_checkpoint"):
            payload["_checkpoint"]()
        try:
            detail = load_history(
                data,
                symbol,
                payload["start_date"],
                payload["end_date"],
                adjustment,
                warmup=payload.get("_history_warmup", payload.get("_warmup", False)),
            )
        except Exception as exc:
            raise BusinessError(ErrorCode.DATA_SOURCE_ERROR, f"{symbol} 历史行情加载失败：{exc}") from exc
        rows = detail.get("kline") or []
        if payload.get("_history_warmup", payload.get("_warmup")) and detail.get("coverage"):
            payload.setdefault("_warmup_history", {})[symbol] = [
                row for row in rows if row["date"] < payload["start_date"]
            ]
        payload.setdefault("_coverage", {})[symbol] = detail.get("coverage") or {
            "calendar_source": "mock-weekdays" if data.source_name.startswith("mock-local") else "provider-dates"
        }
        events[symbol] = _filter_events(symbol, rows, payload["start_date"], payload["end_date"])
        if not events[symbol] and rows and data.source_name.startswith("mock-local"):
            events[symbol] = _mock_events_in_range(
                symbol,
                rows,
                payload["start_date"],
                payload["end_date"],
            )
    return events


def _history_count(payload: dict[str, Any]) -> int:
    requested = payload.get("history_bars")
    if requested:
        return max(20, min(int(requested), 240))
    start = _parse_date(payload["start_date"])
    end = _parse_date(payload["end_date"])
    if start and end:
        return max(30, min((end - start).days + 1, 240))
    return DEFAULT_HISTORY_BARS


def _filter_events(symbol: str, rows: list[dict[str, Any]], start_date: str, end_date: str) -> list[MarketEvent]:
    events = []
    start = _parse_date(start_date)
    end = _parse_date(end_date)
    has_calendar_dates = all(_parse_date(str(row.get("date") or row.get("timestamp") or "")) for row in rows)
    for row in rows:
        timestamp = str(row.get("date") or row.get("timestamp") or "")
        row_date = _parse_date(timestamp)
        if has_calendar_dates and row_date and start and end and not (start <= row_date <= end):
            continue
        value = dict(row, symbol=symbol, timestamp=timestamp)
        event = MarketEvent.from_mapping(value)
        if min(event.open, event.high, event.low, event.close) <= 0:
            continue
        events.append(event)
    # Synthetic rows do not carry a trustworthy calendar date. They are
    # handled explicitly by ``_mock_events_in_range``; never silently reuse
    # out-of-range rows for a date-bounded backtest.
    return events if has_calendar_dates else []


def _mock_events_in_range(
    symbol: str,
    rows: list[dict[str, Any]],
    start_date: str,
    end_date: str,
) -> list[MarketEvent]:
    """Give deterministic mock bars real weekday dates inside the request."""
    start = _parse_date(start_date)
    end = _parse_date(end_date)
    if start is None or end is None or start > end:
        return []
    trading_dates: list[date] = []
    current = start
    while current <= end:
        if current.weekday() < 5:
            trading_dates.append(current)
        current += timedelta(days=1)
    if not trading_dates:
        return []
    events: list[MarketEvent] = []
    for row, timestamp in zip(rows, trading_dates, strict=False):
        value = dict(row, symbol=symbol, timestamp=timestamp.isoformat(), date=timestamp.isoformat())
        event = MarketEvent.from_mapping(value)
        if min(event.open, event.high, event.low, event.close) > 0:
            events.append(event)
    return events


def _normalize_events(symbol: str, rows: list[dict[str, Any]]) -> list[MarketEvent]:
    events = []
    for row in rows:
        timestamp = str(row.get("date") or row.get("timestamp") or "")
        event = MarketEvent.from_mapping(dict(row, symbol=symbol, timestamp=timestamp))
        if min(event.open, event.high, event.low, event.close) > 0:
            events.append(event)
    return events


def _apply_signals(
    cash: float,
    positions: PositionBook,
    trades: list[dict[str, Any]],
    signals: list[StrategySignal],
    event: MarketEvent,
    payload: dict[str, Any],
) -> float:
    commission_rate = float(
        payload["commission_rate"] if payload.get("commission_rate") is not None else DEFAULT_COMMISSION_RATE
    )
    slippage = float(payload.get("slippage_rate") or DEFAULT_SLIPPAGE_RATE)
    for signal in signals:
        if signal.symbol and signal.symbol != event.symbol:
            continue
        if signal.side == "buy":
            cash = _open_long(cash, positions, signal, event, payload, commission_rate, slippage)
        elif signal.side == "sell":
            cash = _close_long(cash, positions, trades, signal, event, payload, commission_rate, slippage)
    return cash


def _open_long(
    cash: float,
    positions: PositionBook,
    signal: StrategySignal,
    event: MarketEvent,
    payload: dict[str, Any],
    commission_rate: float,
    slippage: float,
) -> float:
    existing = positions.get(event.symbol, {})
    if existing.get("quantity", 0.0) > 0 and not signal.metadata.get("order_id"):
        return cash
    if not existing and len(positions) >= _max_position_count(payload):
        return cash
    execution = _execution_price(signal, event, payload=payload, buy=True, slippage=slippage)
    if execution is None:
        record_rejection(payload, event, signal, "limit_or_price_constraint")
        return cash
    price, order_type, fill_note = execution
    if price <= 0:
        return cash
    quantity = _buy_quantity(cash, signal, price, commission_rate, payload)
    if quantity <= 0:
        return cash
    payload["_fill_price"] = price
    quantity, fees = fill_details(signal, event, payload, cash, quantity, True, commission_rate, slippage)
    if quantity <= 0:
        return cash
    turnover = price * quantity
    commission = fees["total"]
    previous_quantity = float(existing.get("quantity", 0))
    total_quantity = previous_quantity + quantity
    previous_value = float(existing.get("open_value", 0))
    lots = list(existing.get("lots", []))
    lots.append(
        {
            "quantity": quantity,
            "unlock_session": payload.get("_session_index", 0) + payload["_cost_policy"]["settlement_sessions"],
        }
    )
    positions[event.symbol] = {
        "quantity": total_quantity,
        "avg_price": (previous_value + turnover) / total_quantity,
        "open_time": existing.get("open_time") or event.timestamp,
        "open_price": (previous_value + turnover) / total_quantity,
        "cost_basis": float(existing.get("cost_basis", 0)) + turnover + commission,
        "open_commission": float(existing.get("open_commission", 0)) + fees["commission"],
        "open_value": previous_value + turnover,
        "lots": lots,
        "open_costs": {key: float(existing.get("open_costs", {}).get(key, 0)) + value for key, value in fees.items()},
        "order_type": order_type,
        "fill_note": fill_note,
        "signal": signal.reason or signal.signal_type or "buy",
    }
    return cash - turnover - commission


def _close_long(
    cash: float,
    positions: PositionBook,
    trades: list[dict[str, Any]],
    signal: StrategySignal,
    event: MarketEvent,
    payload: dict[str, Any],
    commission_rate: float,
    slippage: float,
) -> float:
    position = positions.get(event.symbol)
    if not position or position.get("quantity", 0.0) <= 0:
        return cash
    available = float(position["quantity"])
    quantity = available if signal.quantity <= 0 else min(float(signal.quantity), available)
    unlocked = (
        sum(
            lot["quantity"]
            for lot in position.get("lots", [])
            if lot["unlock_session"] <= payload.get("_session_index", 0)
        )
        if position.get("lots")
        else available
    )
    quantity = min(quantity, unlocked)
    if quantity < available:
        quantity = int(quantity) // int(payload["_cost_policy"]["lot_size"]) * int(payload["_cost_policy"]["lot_size"])
    if quantity <= 0:
        record_rejection(payload, event, signal, "unsettled_position")
        return cash
    execution = _execution_price(signal, event, payload=payload, buy=False, slippage=slippage)
    if execution is None:
        record_rejection(payload, event, signal, "limit_or_price_constraint")
        return cash
    price, order_type, fill_note = execution
    payload["_fill_price"] = price
    quantity, fees = fill_details(signal, event, payload, cash, quantity, False, commission_rate, slippage)
    if not quantity:
        return cash
    turnover = price * quantity
    commission = fees["total"]
    cash += turnover - commission
    position_ratio = quantity / available
    cost_basis = float(position["cost_basis"]) * position_ratio
    open_commission = float(position.get("open_commission") or 0.0) * position_ratio
    open_value = float(position.get("open_value") or cost_basis) * position_ratio
    pnl = turnover - commission - cost_basis
    trades.append(
        {
            "symbol": event.symbol,
            "open_time": position["open_time"],
            "open_price": round(float(position["open_price"]), 4),
            "close_time": event.timestamp,
            "close_price": round(price, 4),
            "direction": "long",
            "quantity": round(quantity, 4),
            "pnl": round(pnl, 2),
            "pnl_pct": round(pnl / cost_basis, 4) if cost_basis else 0.0,
            "commission": round(open_commission + fees["commission"], 2),
            "costs": {
                key: float(position.get("open_costs", {}).get(key, 0)) * position_ratio + value
                for key, value in fees.items()
            },
            "open_value": round(open_value, 2),
            "close_value": round(turnover, 2),
            "holding_days": _holding_days(position.get("open_time"), event.timestamp),
            "order_type": order_type,
            "fill_note": fill_note,
            "signal": signal.reason or signal.signal_type or "sell",
        }
    )
    remain = available - quantity
    if remain <= 0:
        positions.pop(event.symbol, None)
    else:
        reduce_position(position, quantity, payload.get("_session_index", 0))
    return cash


def _close_open_positions(
    cash: float,
    positions: PositionBook,
    trades: list[dict[str, Any]],
    events_by_symbol: dict[str, list[MarketEvent]],
    payload: dict[str, Any],
) -> float:
    for symbol in list(positions):
        events = events_by_symbol.get(symbol) or []
        if not events:
            continue
        final_event = events[-1]
        signal = StrategySignal(symbol=symbol, side="sell", quantity=0, reason="mark_to_close")
        cash = _close_long(
            cash,
            positions,
            trades,
            signal,
            final_event,
            payload,
            float(
                payload["commission_rate"] if payload.get("commission_rate") is not None else DEFAULT_COMMISSION_RATE
            ),
            float(payload.get("slippage_rate") or DEFAULT_SLIPPAGE_RATE),
        )
    return cash


def _sync_context(
    context: StrategyContext,
    cash: float,
    positions: PositionBook,
    latest_prices: dict[str, float],
    current_date: str,
    initial_cash: float,
) -> None:
    market_value = _market_value(positions, latest_prices)
    context.account = {
        "initial_cash": round(initial_cash, 2),
        "cash": round(cash, 2),
        "market_value": round(market_value, 2),
        "total_equity": round(cash + market_value, 2),
        "current_date": current_date,
        "positions": {
            symbol: {
                "quantity": item["quantity"],
                "avg_price": item["avg_price"],
                "last_price": latest_prices.get(symbol, item["avg_price"]),
            }
            for symbol, item in positions.items()
        },
    }


def _portfolio_value(cash: float, positions: PositionBook, latest_prices: dict[str, float]) -> float:
    return cash + _market_value(positions, latest_prices)


def _market_value(positions: PositionBook, latest_prices: dict[str, float]) -> float:
    return sum(
        float(item["quantity"]) * latest_prices.get(symbol, float(item["avg_price"]))
        for symbol, item in positions.items()
    )


def _holding_days(open_time: Any, close_time: Any) -> int:
    try:
        opened = datetime.fromisoformat(str(open_time).replace("Z", "+00:00"))
        closed = datetime.fromisoformat(str(close_time).replace("Z", "+00:00"))
        return max((closed.date() - opened.date()).days, 0)
    except (TypeError, ValueError):
        return 0


def _benchmark_value(
    initial_cash: float,
    events_by_symbol: dict[str, list[MarketEvent]],
    first_prices: dict[str, float],
    offset: int,
) -> float:
    returns = []
    for symbol, events in events_by_symbol.items():
        if not events or symbol not in first_prices:
            continue
        event = events[min(offset, len(events) - 1)]
        first_price = first_prices[symbol]
        if first_price > 0:
            returns.append(event.close / first_price - 1)
    return initial_cash * (1 + (sum(returns) / len(returns) if returns else 0.0))


def _dated_benchmark(initial_cash: float, first_prices: dict[str, float], latest_prices: dict[str, float]) -> float:
    # A symbol that has not started yet retains its equal-weight cash allocation.
    growth = [latest_prices.get(symbol, first) / first for symbol, first in first_prices.items() if first > 0]
    return initial_cash * sum(growth) / len(growth) if growth else initial_cash


def _first_prices(events_by_symbol: dict[str, list[MarketEvent]]) -> dict[str, float]:
    return {symbol: events[0].close for symbol, events in events_by_symbol.items() if events}


def _execution_price(
    signal: StrategySignal,
    event: MarketEvent,
    payload: dict[str, Any],
    *,
    buy: bool,
    slippage: float,
) -> tuple[float, str, str] | None:
    order_type = _normalize_order_type(payload.get("order_type"))
    if order_type == "open":
        base = event.open
        note = "按当日开盘价撮合"
    elif order_type == "limit":
        limit_price = float(signal.price or event.close)
        if limit_price < event.low or limit_price > event.high:
            return None
        base = limit_price
        note = "限价在当日高低区间内，按限价撮合"
    else:
        base = signal.price or event.close
        note = "市价按当日收盘价撮合"
    policy = policy_for(payload, {"slippage_rate": slippage})
    price = slipped_price(
        float(base), buy, policy, float(signal.price or event.close) if order_type == "limit" else None
    )
    return (price, order_type, note) if price is not None else None


def _metrics(
    initial_cash: float,
    equity: list[float],
    benchmark: list[float],
    drawdown: list[float],
    trades: list[dict[str, Any]],
    data_source: str,
    payload: dict[str, Any],
    curve: dict[str, Any] | None = None,
) -> dict[str, Any]:
    total_return = equity[-1] / initial_cash - 1 if initial_cash else 0.0
    periods = max(len(equity), 1)
    annual_return = (1 + total_return) ** (TRADING_DAYS_PER_YEAR / periods) - 1 if total_return > -1 else -1.0
    returns = [equity[index] / equity[index - 1] - 1 for index in range(1, len(equity)) if equity[index - 1]]
    downside = [item for item in returns if item < 0]
    sharpe = _annualized_ratio(returns)
    sortino = _annualized_ratio(returns, downside_only=downside)
    pnls = [float(item.get("pnl") or 0.0) for item in trades]
    wins = [item for item in pnls if item > 0]
    losses = [item for item in pnls if item < 0]
    profit_loss_ratio = (
        (sum(wins) / len(wins)) / abs(sum(losses) / len(losses)) if wins and losses else (1.0 if wins else 0.0)
    )
    max_drawdown = min(drawdown) if drawdown else 0.0
    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    profit_factor = gross_profit / gross_loss if gross_loss else (float("inf") if gross_profit else 0.0)
    average_win = sum(wins) / len(wins) if wins else 0.0
    average_loss = sum(losses) / len(losses) if losses else 0.0
    volatility = _annualized_volatility(returns)
    calmar = annual_return / abs(max_drawdown) if max_drawdown < 0 else 0.0
    daily_var_95 = _historical_var(returns)
    trade_count = len(pnls)
    expectancy = sum(pnls) / trade_count if trade_count else 0.0
    holding_days = [float(item.get("holding_days") or 0.0) for item in trades]
    commission = sum(float(item.get("commission") or 0.0) for item in trades)
    turnover_value = sum(
        float(item.get("open_value") or 0.0) + float(item.get("close_value") or 0.0) for item in trades
    )
    exposure = [float(item) for item in (curve or {}).get("exposure") or []]
    drawdown_details = _drawdown_details((curve or {}).get("dates") or [], equity, drawdown)
    benchmark_return = benchmark[-1] / initial_cash - 1 if benchmark and initial_cash else 0.0
    return {
        "total_return": round(total_return, 4),
        "annual_return": round(annual_return, 4),
        "max_drawdown": round(max_drawdown, 4),
        "annual_volatility": round(volatility, 4),
        "calmar": round(calmar, 4),
        "daily_var_95": round(daily_var_95, 4),
        "sharpe": round(sharpe, 4),
        "sortino": round(sortino, 4),
        "win_rate": round(len(wins) / trade_count, 4) if trade_count else 0.0,
        "win_count": len(wins),
        "loss_count": len(losses),
        "profit_loss_ratio": round(profit_loss_ratio, 4),
        "profit_factor": round(profit_factor, 4) if math.isfinite(profit_factor) else None,
        "average_win": round(average_win, 2),
        "average_loss": round(average_loss, 2),
        "expectancy": round(expectancy, 2),
        "best_trade": round(max(pnls), 2) if pnls else 0.0,
        "worst_trade": round(min(pnls), 2) if pnls else 0.0,
        "average_holding_days": round(sum(holding_days) / len(holding_days), 2) if holding_days else 0.0,
        "trade_count": trade_count,
        "excess_return": round(total_return - benchmark_return, 4),
        "commission_paid": round(commission, 2),
        "turnover_ratio": round(turnover_value / initial_cash, 4) if initial_cash else 0.0,
        "average_exposure": round(sum(exposure) / len(exposure), 4) if exposure else 0.0,
        "max_exposure": round(max(exposure), 4) if exposure else 0.0,
        "max_drawdown_duration_days": drawdown_details["max_duration_days"],
        "max_drawdown_recovery_days": drawdown_details["recovery_days"],
        "data_source": data_source,
        "benchmark_label": "标的池等权买入持有",
        "engine_mode": "event_kline",
        "order_type": _normalize_order_type(payload.get("order_type")),
        "price_adjustment": _normalize_price_adjustment(payload.get("price_adjustment")),
        "max_position_count": _max_position_count(payload),
        "max_position_weight": round(_max_position_weight(payload), 4),
        "lot_size": _lot_size(payload),
    }


def _annualized_volatility(returns: list[float]) -> float:
    if len(returns) < 2:
        return 0.0
    mean_return = sum(returns) / len(returns)
    variance = sum((item - mean_return) ** 2 for item in returns) / len(returns)
    return math.sqrt(variance) * math.sqrt(TRADING_DAYS_PER_YEAR)


def _tracking_error(equity: list[float], benchmark: list[float]) -> float:
    """Annualized standard deviation of strategy-minus-pool daily returns."""
    if len(equity) != len(benchmark) or len(equity) < 3:
        return 0.0
    active = []
    for index in range(1, len(equity)):
        if not equity[index - 1] or not benchmark[index - 1]:
            continue
        active.append((equity[index] / equity[index - 1] - 1) - (benchmark[index] / benchmark[index - 1] - 1))
    if len(active) < 2:
        return 0.0
    mean = sum(active) / len(active)
    variance = sum((item - mean) ** 2 for item in active) / len(active)
    return round(math.sqrt(variance) * math.sqrt(TRADING_DAYS_PER_YEAR), 4)


def _historical_var(returns: list[float], confidence: float = 0.95) -> float:
    if not returns:
        return 0.0
    ordered = sorted(returns)
    index = max(0, min(len(ordered) - 1, int((1 - confidence) * (len(ordered) - 1))))
    return ordered[index]


def _drawdown_details(dates: list[Any], equity: list[float], drawdown: list[float]) -> dict[str, int]:
    if not drawdown:
        return {"max_duration_days": 0, "recovery_days": 0}
    max_duration = 0
    duration_start: int | None = None
    for index, value in enumerate(drawdown):
        if value < 0 and duration_start is None:
            duration_start = index
        if value >= 0 and duration_start is not None:
            max_duration = max(max_duration, _date_span_days(dates, duration_start, index - 1))
            duration_start = None
    if duration_start is not None:
        max_duration = max(max_duration, _date_span_days(dates, duration_start, len(drawdown) - 1))
    trough_index = min(range(len(drawdown)), key=lambda index: drawdown[index])
    recovery_index = next((index for index in range(trough_index + 1, len(drawdown)) if drawdown[index] >= 0), None)
    peak_index = max(range(trough_index + 1), key=lambda index: equity[index]) if equity else trough_index
    recovery_days = _date_span_days(dates, peak_index, recovery_index) if recovery_index is not None else 0
    return {"max_duration_days": max_duration, "recovery_days": recovery_days}


def _date_span_days(dates: list[Any], start: int, end: int) -> int:
    if not dates or start >= len(dates) or end >= len(dates):
        return max(end - start, 0)
    try:
        start_date = date.fromisoformat(str(dates[start])[:10])
        end_date = date.fromisoformat(str(dates[end])[:10])
        return max((end_date - start_date).days, 0)
    except ValueError:
        return max(end - start, 0)


def _annualized_ratio(returns: list[float], downside_only: list[float] | None = None) -> float:
    samples = downside_only if downside_only is not None else returns
    if not returns or not samples:
        return 0.0
    mean_return = sum(returns) / len(returns)
    mean_sample = sum(samples) / len(samples)
    variance = sum((item - mean_sample) ** 2 for item in samples) / len(samples)
    std = math.sqrt(variance)
    if std <= 0:
        return 0.0
    return mean_return / std * math.sqrt(TRADING_DAYS_PER_YEAR)


def _buy_quantity(
    cash: float,
    signal: StrategySignal,
    price: float,
    commission_rate: float,
    payload: dict[str, Any],
) -> int:
    lot_size = _lot_size(payload)
    if signal.quantity > 0:
        requested = int(signal.quantity)
    else:
        initial_cash = _payload_float(payload, "initial_capital", _payload_float(payload, "initial_cash", cash))
        target_cash = max(initial_cash * _max_position_weight(payload), 0.0)
        requested = int(min(cash, target_cash) / (price * (1 + commission_rate))) if price > 0 else 0
    initial_cash = _payload_float(payload, "initial_capital", _payload_float(payload, "initial_cash", cash))
    weight_cap = (
        int(max(initial_cash * _max_position_weight(payload), 0) / (price * (1 + commission_rate))) if price > 0 else 0
    )
    requested = min(requested, weight_cap)
    max_quantity = int(cash / (price * (1 + commission_rate))) if price > 0 else 0
    return _round_lot(max(0, min(requested, max_quantity)), lot_size)


def _round_lot(quantity: int, lot_size: int) -> int:
    if lot_size <= 1:
        return max(quantity, 0)
    return max(quantity // lot_size * lot_size, 0)


def _normalize_order_type(value: Any) -> str:
    selected = str(value or DEFAULT_ORDER_TYPE).strip().lower()
    aliases = {
        "市价": "market",
        "收盘价": "market",
        "close": "market",
        "开盘价": "open",
        "open_price": "open",
        "限价": "limit",
    }
    normalized = aliases.get(selected, selected)
    return normalized if normalized in SUPPORTED_ORDER_TYPES else DEFAULT_ORDER_TYPE


def _normalize_price_adjustment(value: Any) -> str:
    selected = str(value or DEFAULT_PRICE_ADJUSTMENT).strip().lower()
    aliases = {
        "forward": "qfq",
        "pre": "qfq",
        "前复权": "qfq",
        "backward": "hfq",
        "post": "hfq",
        "后复权": "hfq",
        "raw": "none",
        "不复权": "none",
        "bfq": "none",
    }
    normalized = aliases.get(selected, selected)
    return normalized if normalized in SUPPORTED_PRICE_ADJUSTMENTS else DEFAULT_PRICE_ADJUSTMENT


def _max_position_count(payload: dict[str, Any]) -> int:
    return max(1, min(_payload_int(payload, "max_position_count", 999), 999))


def _max_position_weight(payload: dict[str, Any]) -> float:
    return max(0.01, min(_payload_float(payload, "max_position_weight", 1.0), 1.0))


def _lot_size(payload: dict[str, Any]) -> int:
    return max(1, min(_payload_int(payload, "lot_size", 1), 10000))


def _payload_float(payload: dict[str, Any], key: str, default: float) -> float:
    try:
        return float(payload.get(key, default))
    except (TypeError, ValueError):
        return default


def _payload_int(payload: dict[str, Any], key: str, default: int) -> int:
    try:
        return int(float(payload.get(key, default)))
    except (TypeError, ValueError):
        return default


def _parse_date(value: str) -> datetime | None:
    try:
        return datetime.strptime(value[:10], "%Y-%m-%d")
    except (TypeError, ValueError):
        return None
