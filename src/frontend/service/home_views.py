"""Compact, data-driven summaries for the homepage."""

from __future__ import annotations

from html import escape
from typing import Any

from .home_config import home_config, label, limit
from .home_data import HomeAccount, number


def metric(label_text: str, value: str, hint: str, tone: str = "neutral") -> str:
    return (
        f"<article class='home-metric {tone}'><span>{escape(label_text)}</span>"
        f"<strong>{escape(value)}</strong><small>{escape(hint)}</small></article>"
    )


def money(value: float | None, *, signed: bool = False) -> str:
    if value is None:
        return "—"
    return f"{value:+,.2f}" if signed else f"{value:,.2f}"


def tone(value: float | None) -> str:
    return "gain" if value is not None and value > 0 else "loss" if value is not None and value < 0 else "neutral"


def account_kpis(snapshot: HomeAccount) -> str:
    history_date = str(snapshot.history[-1].get("nav_date") or "") if snapshot.history else "无快照"
    pnl = snapshot.total_pnl
    items = [
        metric(
            "账户总资产",
            money(snapshot.total_asset),
            "元 · 当前可用行情估值" if snapshot.mode == "paper" else "待 broker 回传",
        ),
        metric(
            "今日盈亏",
            money(snapshot.daily_pnl, signed=True),
            "元 · 当天与前次快照之差" if snapshot.daily_pnl is not None else label("missing_daily"),
            tone(snapshot.daily_pnl),
        ),
        metric(
            "累计盈亏",
            money(pnl, signed=True),
            "元 · 相对初始资金" if snapshot.mode == "paper" else "未提供真实盈亏",
            tone(pnl),
        ),
        metric(
            "仓位暴露", f"{snapshot.exposure:.1%}" if snapshot.exposure is not None else "—", "持仓市值 / 当前总资产"
        ),
        metric(
            "快照回撤",
            f"{snapshot.drawdown:.2%}" if snapshot.drawdown is not None else "—",
            f"截至 {history_date} · 相对历史峰值",
        ),
        metric(
            "持仓数量", str(snapshot.position_count) if snapshot.position_count is not None else "—", "当前持仓标的数"
        ),
        metric(
            "盈利持仓", str(snapshot.profit_count) if snapshot.profit_count is not None else "—", "浮动盈亏 > 0", "gain"
        ),
        metric(
            "亏损持仓", str(snapshot.loss_count) if snapshot.loss_count is not None else "—", "浮动盈亏 < 0", "loss"
        ),
    ]
    return "<div class='home-kpi-grid'>" + "".join(items) + "</div>"


def risk_summary(snapshot: HomeAccount) -> str:
    references = home_config()["risk_reference"]
    meters = []
    for title, value, key in (
        ("仓位暴露", snapshot.exposure, "exposure"),
        ("单票集中度", snapshot.concentration, "concentration"),
    ):
        threshold = float(references[key])
        width = min(max(value or 0, 0), 1) * 100
        status = "超参考线" if value is not None and value > threshold else "可观察" if value is not None else "未提供"
        display = f"{value:.1%}" if value is not None else "—"
        meters.append(
            f"<div class='home-risk-meter'><span>{title}<b>{display}</b></span>"
            f"<div role='meter' aria-label='{title}' aria-valuemin='0' aria-valuemax='100' "
            f"aria-valuenow='{width:.1f}'><i class='{'breach' if status == '超参考线' else ''}' style='width:{width:.1f}%'></i>"
            f"<em style='left:{threshold * 100:.1f}%'></em></div><small>{status} · 参考 {threshold:.0%}</small></div>"
        )
    return (
        "<div class='home-risk-grid'>"
        + "".join(meters)
        + f"</div><p class='home-muted'>{escape(str(references['label']))}</p>"
    )


def risk_alerts(snapshot: HomeAccount) -> str:
    rows: list[tuple[str, str, str]] = []
    references = home_config()["risk_reference"]
    if snapshot.exposure is not None and snapshot.exposure > float(references["exposure"]):
        rows.append(("高", "仓位暴露超过观察线", f"当前 {snapshot.exposure:.1%}"))
    if snapshot.concentration is not None and snapshot.concentration > float(references["concentration"]):
        rows.append(("高", "单票集中度超过观察线", f"当前 {snapshot.concentration:.1%}"))
    if snapshot.loss_count and snapshot.position_count and snapshot.loss_count / snapshot.position_count >= 0.5:
        rows.append(("中", "亏损持仓占比较高", f"{snapshot.loss_count}/{snapshot.position_count}"))
    rows.extend(("中", "数据提醒", warning) for warning in snapshot.warnings[:2])
    if not rows:
        return "<div class='home-alert calm'><span>● 暂无高优先级风险预警</span><small>参考线仅用于观察，不触发自动交易</small></div>"
    return (
        "<div class='home-alert risk-alerts'>"
        + "".join(
            f"<article><b>{escape(level)}</b><span>{escape(title)}</span><small>{escape(detail)}</small></article>"
            for level, title, detail in rows[: limit("alerts")]
        )
        + "</div>"
    )


def theme_summary(news_items: list[dict[str, Any]]) -> str:
    counts: dict[str, int] = {}
    for item in news_items:
        values = item.get("keywords") or []
        if not isinstance(values, list):
            values = [values]
        for keyword in values:
            text = str(keyword).strip()
            if text:
                counts[text] = counts.get(text, 0) + 1
    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:10]
    if not ranked:
        return "<section class='home-themes'><strong>热词与主题</strong><span>暂无新闻关键词</span></section>"
    chips = "".join(f"<b>{escape(word)} <em>{count}</em></b>" for word, count in ranked)
    return f"<section class='home-themes'><strong>热词与主题</strong><div>{chips}</div><small>来自当前新闻样本，不代表投资建议</small></section>"


def module_link(module: str, text: str) -> str:
    return f"<a href='/app/{escape(module)}/' data-home-module='{escape(module)}'>{escape(text)} ↗</a>"


def action_summary(rows: list[dict[str, Any]], *, alerts: bool = False) -> str:
    ranking = {"高": 0, "中": 1, "低": 2, "正常": 3}
    ordered = sorted(rows, key=lambda row: ranking.get(str(row.get("priority")), 3))
    if alerts:
        ordered = [row for row in ordered if row.get("priority") == "高"]
        if not ordered:
            return "<div class='home-alert calm'><span>● 未发现高优先级事项</span><small>仍需核查数据来源与估值时间</small></div>"
    items = []
    for row in ordered[: limit("actions")]:
        module = (
            "live"
            if row.get("category") == "实盘"
            else "simulation"
            if row.get("category") in {"账户", "交易", "回测", "风险"}
            else "admin"
        )
        items.append(
            f"<article><span class='home-priority'>{escape(str(row.get('priority') or '提示'))}</span>"
            f"<div><strong>{escape(str(row.get('item') or ''))}</strong><small>{escape(str(row.get('next_step') or ''))}</small></div>"
            f"{module_link(module, '查看')}</article>"
        )
    return f"<div class='{'home-alert' if alerts else 'home-action-list'}'>" + "".join(items) + "</div>"


def market_summary(indices: list[dict[str, Any]], sectors: list[dict[str, Any]]) -> str:
    cards = [
        metric(
            str(row.get("name") or row.get("code")),
            f"{number(row.get('change_pct')):+.2f}%" if number(row.get("change_pct")) is not None else "—",
            f"{row.get('price', '—')} · {row.get('data_source') or '来源未提供'}",
            tone(number(row.get("change_pct"))),
        )
        for row in indices
    ]
    return (
        "<div class='home-index-grid'>"
        + "".join(cards)
        + f"</div><p class='home-muted'>板块样本 {len(sectors)} 个；不代表全市场广度。红涨绿跌，悬停查看数值。</p>"
    )


def operation_summary(counts: list[dict[str, Any]]) -> str:
    items = [
        f"<div><span>{escape(str(row['module']))}</span><b>{int(row['count'])}</b>"
        f"<small>{escape(str(row['status']))}</small></div>"
        for row in counts
    ]
    return "<div class='home-operations'>" + "".join(items) + "</div>" + module_link("ai", "进入 AI 工作台")
