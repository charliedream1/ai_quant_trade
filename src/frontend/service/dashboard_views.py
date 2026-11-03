"""Shared frontend dashboard views."""

from __future__ import annotations

from .foundation import (
    Any,
    Sequence,
    _display_now,
    escape,
    re,
)
from .visuals import (
    _format_display_time,
    _money,
    _pct_points,
    _percent,
    _safe_float,
    _signed_money,
)


def _dashboard_kpis_html(
    cards: Sequence[dict[str, Any]],
    priority_cards: Sequence[dict[str, Any]] | None = None,
) -> str:
    items = []
    for card in cards:
        tone = escape(str(card.get("tone") or "neutral"))
        label = escape(str(card.get("label") or "-"))
        value = escape(str(card.get("value") or "-"))
        hint = escape(str(card.get("hint") or ""))
        items.append(
            "<div class='dashboard-card "
            + tone
            + "'><div class='dashboard-label'>"
            + label
            + "</div><div class='dashboard-value'>"
            + value
            + "</div><div class='dashboard-hint'>"
            + hint
            + "</div></div>"
        )
    return (
        "<div class='dashboard-control-deck'>"
        + _dashboard_priority_html(priority_cards or [])
        + "<div class='dashboard-kpis'>"
        + "".join(items)
        + "</div>"
        + "</div>"
    )


def _dashboard_priority_html(cards: Sequence[dict[str, Any]]) -> str:
    if not cards:
        return ""
    items = []
    for card in cards[:4]:
        tone = escape(str(card.get("tone") or "neutral"))
        label = escape(str(card.get("label") or "-"))
        value = escape(str(card.get("value") or "-"))
        hint = escape(str(card.get("hint") or ""))
        items.append(
            "<article class='dashboard-priority-card "
            + tone
            + "'><small>"
            + label
            + "</small><strong>"
            + value
            + "</strong><span>"
            + hint
            + "</span></article>"
        )
    return (
        "<section class='dashboard-priority-strip'>"
        "<div class='dashboard-priority-head'><span>今日必须看</span>"
        "<strong>账户风险、今日盈亏、大盘温度、AI 待办</strong></div>"
        "<div class='dashboard-priority-grid'>" + "".join(items) + "</div></section>"
    )


def _dashboard_signal_html(cards: Sequence[dict[str, Any]]) -> str:
    insight_items = []
    for index, card in enumerate(cards[:4], start=1):
        tone = escape(str(card.get("tone") or "neutral"))
        label = escape(str(card.get("label") or "-"))
        value = escape(str(card.get("value") or "-"))
        hint = escape(str(card.get("hint") or ""))
        width = _dashboard_meter_width(str(card.get("value") or ""), str(card.get("tone") or "neutral"))
        insight_items.append(
            "<article class='dashboard-signal-card "
            + tone
            + "'><div class='dashboard-signal-index'>"
            + f"{index:02d}"
            + "</div><div class='dashboard-signal-copy'><strong>"
            + label
            + "</strong><span>"
            + value
            + "</span><small>"
            + hint
            + "</small></div><div class='dashboard-signal-meter'><i style='width:"
            + f"{width:.0f}%"
            + "'></i></div></article>"
        )
    if not insight_items:
        return ""
    return (
        "<section class='dashboard-signal-board'>"
        "<div class='dashboard-signal-head'><span>市场驾驶舱</span><strong>先看结论，再看明细</strong></div>"
        "<div class='dashboard-signal-grid'>" + "".join(insight_items) + "</div></section>"
    )


def _dashboard_meter_width(value: str, tone: str) -> float:
    if value.strip() in {"", "-"}:
        return 18.0
    percent_match = re.search(r"[-+]?\d+(?:\.\d+)?(?=%)", value)
    if percent_match:
        return max(8.0, min(abs(float(percent_match.group(0))), 100.0))
    number_match = re.search(r"[-+]?\d+(?:\.\d+)?", value.replace(",", ""))
    if number_match:
        number = abs(float(number_match.group(0)))
        if "亿" in value:
            return max(28.0, min(number * 12.0, 96.0))
        if "万" in value:
            return max(24.0, min(number / 2.0, 92.0))
        return max(16.0, min(number * 12.0 if number <= 10 else number, 92.0))
    return {"positive": 78.0, "warning": 54.0, "negative": 68.0}.get(tone, 46.0)


def _top_by_change(rows: Sequence[dict[str, Any]], reverse: bool = True) -> dict[str, Any] | None:
    candidates = [row for row in rows if row.get("change_pct") not in (None, "")]
    if not candidates:
        return None
    return sorted(candidates, key=lambda row: _safe_float(row.get("change_pct")), reverse=reverse)[0]


def _dashboard_focus_html(
    account_label: str,
    account_name: str,
    overview: dict[str, Any],
    positions: Sequence[dict[str, Any]],
    pending_orders: int,
    account_mode: str,
) -> str:
    total_asset = _safe_float(overview.get("total_asset"))
    market_value = _safe_float(overview.get("market_value"))
    cash = _safe_float(overview.get("cash"))
    daily_pnl = _safe_float(overview.get("daily_pnl"))
    total_pnl = _safe_float(overview.get("total_pnl"))
    position_count = int(_safe_float(overview.get("position_count"), len(positions)))
    exposure = market_value / total_asset if total_asset > 0 else 0.0
    cards = [
        ("账户资产", _money(total_asset), f"{account_label} · {account_name or '未创建'}", "neutral"),
        ("今日盈亏", _signed_money(daily_pnl), "按账户快照估算", "positive" if daily_pnl >= 0 else "negative"),
        ("累计盈亏", _signed_money(total_pnl), "相对初始资金", "positive" if total_pnl >= 0 else "negative"),
        (
            "持仓数量",
            str(position_count),
            f"持仓市值 {_money(market_value)}",
            "warning" if position_count == 0 else "neutral",
        ),
        ("仓位暴露", _percent(exposure), f"现金 {_money(cash)}", "warning" if exposure > 0.85 else "neutral"),
        ("未完成委托", str(pending_orders), "需要先处理再复盘", "warning" if pending_orders else "positive"),
    ]
    card_html = []
    for label, value, hint, tone in cards:
        card_html.append(
            "<article class='dashboard-focus-card "
            + tone
            + "'><small>"
            + escape(label)
            + "</small><strong>"
            + escape(value)
            + "</strong><span>"
            + escape(hint)
            + "</span></article>"
        )
    mode_hint = "paper trading 视角" if account_mode == "paper" else "实盘配置视角"
    return (
        "<section class='dashboard-focus-panel'><div class='dashboard-panel-head'>"
        "<span>账户驾驶舱</span><strong>资产、盈亏、持仓先行</strong><em>"
        + escape(mode_hint)
        + "</em></div><div class='dashboard-focus-grid'>"
        + "".join(card_html)
        + "</div></section>"
    )


def _dashboard_market_brief_html(
    indices: Sequence[dict[str, Any]],
    sectors: Sequence[dict[str, Any]],
    watchlist: Sequence[dict[str, Any]],
) -> str:
    index_changes = [_safe_float(item.get("change_pct")) for item in indices]
    average_index = sum(index_changes) / len(index_changes) if index_changes else 0.0
    positive_indices = sum(1 for value in index_changes if value > 0)
    positive_sectors = sum(1 for item in sectors if _safe_float(item.get("change_pct")) > 0)
    leader_index = _top_by_change(indices) or {}
    leader_sector = _top_by_change(sectors) or {}
    weak_sector = _top_by_change(sectors, reverse=False) or {}
    leader_watch = _top_by_change(watchlist) or {}
    breadth = positive_sectors / max(len(sectors), 1)
    if average_index >= 0.6 and breadth >= 0.55:
        mood = "偏热扩散"
        tone = "positive"
    elif average_index <= -0.6 and breadth <= 0.35:
        mood = "偏冷收缩"
        tone = "negative"
    else:
        mood = "震荡分化"
        tone = "warning"
    cards = [
        ("大盘温度", mood, f"指数均值 {_pct_points(average_index)}", tone),
        ("指数红盘", f"{positive_indices}/{len(indices)}", str(leader_index.get("name") or "主要指数"), "neutral"),
        (
            "板块红盘",
            f"{positive_sectors}/{len(sectors)}",
            f"广度 {_percent(breadth)}",
            "positive" if breadth >= 0.55 else "warning",
        ),
        (
            "领涨方向",
            str(leader_sector.get("name") or "-"),
            _pct_points(leader_sector.get("change_pct")),
            "positive",
        ),
        (
            "回撤方向",
            str(weak_sector.get("name") or "-"),
            _pct_points(weak_sector.get("change_pct")),
            "negative",
        ),
        (
            "自选最强",
            str(leader_watch.get("name") or "待配置"),
            _pct_points(leader_watch.get("change_pct")) if leader_watch else "添加自选后监控",
            "neutral",
        ),
    ]
    items = []
    for label, value, hint, card_tone in cards:
        items.append(
            "<article class='dashboard-market-chip "
            + card_tone
            + "'><small>"
            + escape(label)
            + "</small><strong>"
            + escape(value)
            + "</strong><span>"
            + escape(hint)
            + "</span></article>"
        )
    return (
        "<section class='dashboard-market-panel'><div class='dashboard-panel-head'>"
        "<span>大盘概览</span><strong>指数、广度、板块强弱</strong><em>红涨绿跌</em></div>"
        "<div class='dashboard-market-grid'>" + "".join(items) + "</div></section>"
    )


def _dashboard_news_html(items: Sequence[dict[str, Any]]) -> str:
    cards = []
    for item in list(items)[:5]:
        title = escape(str(item.get("title") or "-"))
        url = str(item.get("url") or "").strip()
        source = escape(str(item.get("source") or "-"))
        published = escape(_format_display_time(item.get("published_at")))
        summary = escape(str(item.get("summary") or "")[:160])
        keywords = item.get("keywords") or []
        keyword_text = (
            " · ".join(str(keyword) for keyword in keywords[:4]) if isinstance(keywords, list) else str(keywords)
        )
        title_html = f"<a href='{escape(url)}'>{title}</a>" if url else title
        cards.append(
            "<article class='dashboard-news-card'><div><small>"
            + source
            + " · "
            + published
            + "</small><strong>"
            + title_html
            + "</strong></div><p>"
            + summary
            + "</p><span>"
            + escape(keyword_text or "要点新闻")
            + "</span></article>"
        )
    if not cards:
        return "<section class='dashboard-news-panel'><div class='ai-empty-state'>暂无新闻快照。</div></section>"
    return (
        "<section class='dashboard-news-panel'><div class='dashboard-panel-head'>"
        "<span>要点新闻</span><strong>先看会影响情绪的事件</strong><em>点击标题打开来源</em></div>"
        "<div class='dashboard-news-grid'>" + "".join(cards) + "</div></section>"
    )


def _dashboard_monitor_tables(
    indices: Sequence[dict[str, Any]],
    sectors: Sequence[dict[str, Any]],
    watchlist: Sequence[dict[str, Any]],
    action_rows: Sequence[dict[str, Any]],
    exposure: float,
    concentration: float,
    pending_orders: int,
    running_live: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    index_changes = [_safe_float(item.get("change_pct")) for item in indices]
    average_index = sum(index_changes) / len(index_changes) if index_changes else 0.0
    positive_indices = sum(1 for value in index_changes if value > 0)
    positive_sectors = sum(1 for item in sectors if _safe_float(item.get("change_pct")) > 0)
    sector_ratio = positive_sectors / max(len(sectors), 1)
    leader_sector = _top_by_change(sectors)
    weak_sector = _top_by_change(sectors, reverse=False)
    leader_watch = _top_by_change(watchlist)
    weak_watch = _top_by_change(watchlist, reverse=False)
    latest_time = (
        str(indices[0].get("updated_at") or "")
        if indices
        else str((sectors[0].get("updated_at") if sectors else "") or _display_now())
    )

    if average_index >= 0.6 and sector_ratio >= 0.55:
        emotion_status = "偏热"
    elif average_index <= -0.6 and sector_ratio <= 0.35:
        emotion_status = "偏冷"
    else:
        emotion_status = "中性震荡"
    risk_status = "高约束" if exposure > 0.9 or concentration > 0.35 else "可观察"

    monitor_rows = [
        {
            "module": "情绪节点",
            "signal": f"指数 {positive_indices}/{len(indices)} 红盘",
            "status": emotion_status,
            "evidence": f"指数均值 {_pct_points(average_index)}，板块红盘 {positive_sectors}/{len(sectors)}",
            "updated_at": latest_time,
        },
        {
            "module": "市场风格",
            "signal": str((leader_sector or {}).get("name") or "-"),
            "status": "主线扩散" if sector_ratio >= 0.6 else "局部分化",
            "evidence": f"领涨板块 {_pct_points((leader_sector or {}).get('change_pct'))}",
            "updated_at": latest_time,
        },
        {
            "module": "自选/持仓",
            "signal": str((leader_watch or {}).get("name") or "暂无自选强势标的"),
            "status": "有强弱对照" if leader_watch and weak_watch else "待配置",
            "evidence": (
                f"强势 {_pct_points((leader_watch or {}).get('change_pct'))} / "
                f"弱势 {_pct_points((weak_watch or {}).get('change_pct'))}"
                if leader_watch and weak_watch
                else "添加自选后可监控内部强弱"
            ),
            "updated_at": latest_time,
        },
        {
            "module": "风险约束",
            "signal": f"仓位 {_percent(exposure)} / 集中度 {_percent(concentration)}",
            "status": risk_status,
            "evidence": f"未完成委托 {pending_orders} 笔，待处理 {len([item for item in action_rows if item['priority'] != '正常'])} 项",
            "updated_at": latest_time,
        },
        {
            "module": "策略闭环",
            "signal": f"运行策略 {running_live} 个",
            "status": "监控中" if running_live else "未运行",
            "evidence": "结合回测、模拟交易和任务中心验证信号，不做自动买卖判断",
            "updated_at": latest_time,
        },
    ]

    style_rows = [
        {
            "dimension": "指数环境",
            "leader": str((_top_by_change(indices) or {}).get("name") or "-"),
            "score": _pct_points(average_index),
            "evidence": f"主要指数红盘 {positive_indices}/{len(indices)}",
            "monitor_point": "看指数环境是否支持题材扩散",
        },
        {
            "dimension": "领涨方向",
            "leader": str((leader_sector or {}).get("name") or "-"),
            "score": _pct_points((leader_sector or {}).get("change_pct")),
            "evidence": f"成交额 {_money((leader_sector or {}).get('amount'))}",
            "monitor_point": "看领涨方向是否保持成交和涨幅优势",
        },
        {
            "dimension": "分歧方向",
            "leader": str((weak_sector or {}).get("name") or "-"),
            "score": _pct_points((weak_sector or {}).get("change_pct")),
            "evidence": "弱势方向用于判断市场是否轮动或退潮",
            "monitor_point": "若弱势扩散到主线，需要降低解释置信度",
        },
        {
            "dimension": "自选强度",
            "leader": str((leader_watch or {}).get("name") or "-"),
            "score": _pct_points((leader_watch or {}).get("change_pct")),
            "evidence": f"自选数量 {len(watchlist)}",
            "monitor_point": "看自选池是否跑赢大盘和领涨板块",
        },
    ]

    chain_rows = [
        {
            "chain_level": "1 市场环境",
            "name": str((_top_by_change(indices) or {}).get("name") or "主要指数"),
            "link_type": "指数情绪",
            "evidence": f"指数均值 {_pct_points(average_index)}",
            "monitor_point": "确认市场是否支持短线题材扩散",
        },
        {
            "chain_level": "2 主线方向",
            "name": str((leader_sector or {}).get("name") or "暂无领涨板块"),
            "link_type": "板块风格",
            "evidence": f"板块涨幅 {_pct_points((leader_sector or {}).get('change_pct'))}",
            "monitor_point": "确认主线是否连续强于其他方向",
        },
        {
            "chain_level": "3 候选标的",
            "name": str((leader_watch or {}).get("name") or "自选池待补充"),
            "link_type": "自选/持仓映射",
            "evidence": (
                f"自选最强 {_pct_points((leader_watch or {}).get('change_pct'))}" if leader_watch else "暂无自选标的"
            ),
            "monitor_point": "只做强弱验证，不输出买入指令",
        },
        {
            "chain_level": "4 风险验证",
            "name": str(action_rows[0].get("item") if action_rows else "无优先事项"),
            "link_type": "风控与任务",
            "evidence": str(action_rows[0].get("next_step") if action_rows else "继续监控"),
            "monitor_point": "先处理高优先级风险，再解释行情信号",
        },
    ]

    paths_rows = [
        {
            "path": "强势延续",
            "condition": "指数均值为正，领涨板块继续高于市场均值，自选强势标的同步走强",
            "validation": f"当前：指数 {_pct_points(average_index)}，领涨 {_pct_points((leader_sector or {}).get('change_pct'))}",
            "risk_control": "若成交不足或高优先级风险出现，不提高信号置信度",
        },
        {
            "path": "震荡分歧",
            "condition": "指数中性但板块分化，自选强弱差扩大",
            "validation": f"当前：板块红盘 {positive_sectors}/{len(sectors)}，自选数量 {len(watchlist)}",
            "risk_control": "以验证为主，等待主线重新聚合",
        },
        {
            "path": "走弱回撤",
            "condition": "指数和板块同步转弱，弱势方向扩散到自选/持仓",
            "validation": f"当前：风险状态 {risk_status}，待处理 {len([item for item in action_rows if item['priority'] != '正常'])} 项",
            "risk_control": "优先检查仓位、集中度、未完成委托和策略运行状态",
        },
    ]
    return monitor_rows, style_rows, chain_rows, paths_rows
