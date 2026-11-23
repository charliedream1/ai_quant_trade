"""On-demand company profile, source coverage and historical risk."""

from html import escape

import pandas as pd

from src.data import DataSourceManager, current_market
from src.engine.market.model_graph.store import GraphStore

from .foundation import NEWS_COLUMNS, resolve_stock_symbol, to_frame
from .home_data import number


class StockResearchMixin:
    def stock_profile(self, symbol):
        code = resolve_stock_symbol(symbol, "股票代码/名称")
        quote = DataSourceManager().stock_quote(code)
        fields = {
            "证券代码": code,
            "公司名称": quote.get("name"),
            "市场": current_market(),
            "行业": quote.get("industry"),
            "市盈率": quote.get("pe"),
            "市净率": quote.get("pb"),
            "总市值（报价币种）": quote.get("market_cap"),
            "报价时间": quote.get("updated_at") or quote.get("timestamp"),
            "来源": quote.get("data_source"),
        }
        return to_frame([{"指标": key, "数值": value} for key, value in fields.items()])

    def stock_disclosures(self, symbol):
        code = resolve_stock_symbol(symbol, "股票代码/名称")
        data = DataSourceManager()
        detail = data.stock_detail(code)
        rows = detail.get("news") or []
        reports = detail.get("reports") or []
        status = f"**{escape(code)}** · {len(rows)} 条资讯 / {len(reports)} 份研报"
        if not rows and not reports:
            status += " · 当前来源无覆盖记录"
        return status, to_frame(rows, NEWS_COLUMNS), to_frame(reports)

    def stock_relationships(self, symbol):
        code = resolve_stock_symbol(symbol, "股票代码/名称")
        rows = []
        for scope, label in (("rule_graph_runs", "规则"), ("relation_graph_runs", "模型")):
            for run in GraphStore(scope).history():
                request = run["request"]
                if run["status"] not in {"completed", "partial"} or request.get("market") != current_market():
                    continue
                if str(request.get("symbol", "")).upper() not in {code.upper(), code.upper().split(".")[0]}:
                    continue
                rows.append(
                    {"构建方式": label, "时间": run["created_at"], "状态": run["status"], "编号": run["run_id"]}
                )
        return to_frame(sorted(rows, key=lambda row: row["时间"], reverse=True))

    def stock_risk(self, symbol):
        code = resolve_stock_symbol(symbol, "股票代码/名称")
        data = DataSourceManager()
        snapshot = getattr(data, "strategy_snapshot", data.stock_detail)(code)
        bars = sorted(snapshot.get("kline") or [], key=lambda row: row["date"])
        closes = pd.Series([number(row.get("close")) for row in bars], dtype=float).where(lambda values: values > 0)
        volatility = closes.pct_change(fill_method=None).std()
        drawdown = (closes / closes.cummax() - 1).min()
        quote = snapshot.get("quote") or {}
        rows = [
            {"指标": "日收益波动率（%）", "数值": number(volatility * 100), "依据": f"{closes.count()} 个有效日收盘价"},
            {"指标": "区间最大回撤（%）", "数值": number(drawdown * 100), "依据": "相对区间内历史高点"},
            {"指标": "最新换手率（%）", "数值": quote.get("turnover_rate"), "依据": quote.get("data_source")},
        ]
        return to_frame(rows)

    def stock_events(self, symbol):
        if current_market() != "CN":
            return "当前市场未配置财报公告日期来源。", to_frame([])
        from src.engine.economics.service import EconomicAnalysis

        code = resolve_stock_symbol(symbol, "股票代码/名称")
        snapshot = EconomicAnalysis().fundamentals(code)
        rows = []
        for period in reversed(snapshot["periods"]):
            dates = {
                (item["statement"], item["announcement_date"])
                for item in period["origins"].values()
                if item.get("announcement_date")
            }
            for statement, announced in sorted(dates, key=lambda entry: entry[1], reverse=True):
                source = snapshot["sources"].get(statement, {})
                rows.append(
                    {
                        "报告期": period["report_period"],
                        "公告日期": announced,
                        "类型": statement,
                        "来源": source.get("source"),
                        "来源链接": source.get("url"),
                    }
                )
        return "以下为来源提供的历史公告日期。" if rows else "当前来源未提供公告日期。", to_frame(rows)
