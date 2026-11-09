"""Read-only report catalog with explicit origins and shared preview contracts."""

from datetime import datetime, timezone
from html import escape

import gradio as gr

from src.agent_strategies.service import AgentStrategyService
from src.alpha_mining.config import digest
from src.alpha_mining.service import AlphaService
from src.engine.insights.service import InsightReportService
from src.engine.market.report_generator import MarketReportGenerator

from ..common.navigation import navigation_config
from .foundation import require_id, to_frame
from .insights import _view


class ReportLibraryMixin:
    def report_library_list(self, selected=None, source="all", status="all", keyword=""):
        rows = []
        agents = AgentStrategyService()
        for item in agents.store.history():
            if agents.store.artifact(item["id"], "report.html").is_file():
                rows.append(
                    {
                        "key": f"agent_strategy:{item['id']}",
                        "来源": "Agent策略",
                        "标题": item["config"]["definition"]["name"],
                        "状态": item["status"],
                        "时间": item["updated_at"],
                    }
                )
        alpha = AlphaService()
        for item in alpha.store.list("alpha_studies"):
            if alpha.store.artifact(item["id"], "report.html").is_file():
                rows.append(
                    {
                        "key": f"alpha:{item['id']}",
                        "来源": "Alpha研究",
                        "标题": item["name"],
                        "状态": item["status"],
                        "时间": item["updated_at"],
                    }
                )
        for item in MarketReportGenerator().list(page=1, page_size=navigation_config()["reports_history_limit"])[
            "items"
        ]:
            rows.append(
                {
                    "key": f"model:{item['id']}",
                    "来源": "旧版模板报告",
                    "标题": item["title"],
                    "状态": item["status"],
                    "时间": item["generated_at"],
                }
            )
        service = InsightReportService()
        for item in service.store.history(service.config["defaults"]["history_limit"]):
            rows.append(
                {
                    "key": f"skill:{item['run_id']}",
                    "来源": "Skill报告",
                    "标题": item.get("title") or item["request"]["kind"],
                    "状态": item["status"],
                    "时间": item["created_at"],
                }
            )
        rows = [
            row
            for row in rows
            if (source == "all" or row["key"].startswith(source + ":"))
            and (status == "all" or row["状态"] == status)
            and str(keyword or "").casefold() in (row["标题"] + row["key"]).casefold()
        ]

        def timestamp(row):
            try:
                value = datetime.fromisoformat(row["时间"].replace("Z", "+00:00"))
                return value.replace(tzinfo=timezone.utc).timestamp() if value.tzinfo is None else value.timestamp()
            except (ValueError, TypeError):
                return float("-inf")

        rows.sort(key=timestamp, reverse=True)
        return to_frame(rows, ["key", "来源", "标题", "状态", "时间"]), gr.update(
            choices=[(f"{row['来源']} · {row['标题']} · {row['状态']} · {row['key']}", row["key"]) for row in rows],
            value=selected if selected in {row["key"] for row in rows} else None,
        )

    def report_library_open(self, key):
        source, separator, identifier = str(key or "").partition(":")
        if not separator or source not in {"model", "skill", "alpha", "agent_strategy"}:
            raise ValueError("请先选择报告")
        if source == "agent_strategy":
            agents = AgentStrategyService()
            run = agents.store.get(require_id(identifier, "运行ID"))
            process = "\n\n".join(str(event["payload"]) for event in agents.all_events(run["id"]))
            return (
                f"Agent策略 · {run['status']} · 流程完成与有效性分开评价",
                process,
                f'<iframe title="Agent策略报告" sandbox="allow-same-origin" style="width:100%;height:850px;border:0" src="/api/v1/agent-strategies/runs/{run["id"]}/files/report.html?v={digest(run["result"])}"></iframe>',
                str(agents.store.artifact(run["id"], "report.html")),
            )
        if source == "alpha":
            service = AlphaService()
            study_id = require_id(identifier, "研究ID")
            study = service.detail(study_id)
            path = service.store.artifact(study_id, "report.html")
            return (
                f"Alpha研究 · {study['status']} · 历史回放与前向证据需分别核对",
                "真实试验事件见策略构建 → Alpha研究；未触发新任务",
                f'<iframe title="Alpha研究报告" sandbox="allow-same-origin" style="width:100%;height:850px;border:0" src="/api/v1/alpha/studies/{study_id}/files/report.html?v={digest(study["result"])}"></iframe>',
                str(path),
            )
        if source == "skill":
            insight_service = InsightReportService()
            status, process, html, download, *_ = _view(
                insight_service, insight_service.detail(identifier), insight_service.store.events(identifier)
            )
            return status, process, html, download
        row = MarketReportGenerator().detail(require_id(identifier, "报告ID"))
        content = str(row.get("market_summary") or "")
        return (
            "旧版模板报告；不表示真实LLM生成或完整事实核查",
            "历史内容只读，未触发新任务",
            f"<article><h3>{escape(row['title'])}</h3><pre style='white-space:pre-wrap'>{escape(content)}</pre></article>",
            None,
        )
