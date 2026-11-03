"""Model market report generator."""

import json
from typing import Any

from src.core.repository import Repository
from src.core.timeutil import utc_now_iso


class MarketReportGenerator:
    def __init__(self, repo: Repository | None = None) -> None:
        self.repo = repo or Repository()

    def create(self, payload: dict[str, Any]) -> dict[str, Any]:
        now = utc_now_iso()
        report_type = payload.get("report_type", "daily")
        topic = payload.get("topic") or "市场日报"
        content = f"# {topic}\n\n- 科技成长方向活跃。\n- 成交额维持高位。\n- 风险提示：本内容为系统模拟报告，不构成投资建议。\n"
        row = self.repo.insert(
            "model_reports",
            {
                "title": f"{topic}-{now[:10]}",
                "report_type": report_type,
                "status": "finished",
                "content": content,
                "topic": topic,
                "model_name": "mock-llm" if payload.get("use_llm", True) else "rule-based",
                "generated_at": now,
                "file_path": "",
            },
        )
        return {
            "task_id": row["id"],
            "report_id": row["id"],
            "report_type": report_type,
            "status": "finished",
            "created_at": now,
        }

    def list(
        self,
        page: int,
        page_size: int,
        report_type: str | None = None,
        status: str | None = None,
    ) -> dict[str, Any]:
        where: list[str] = []
        params: list[Any] = []
        if report_type:
            where.append("report_type = ?")
            params.append(report_type)
        if status:
            where.append("status = ?")
            params.append(status)
        return self.repo.page(
            "model_reports", page, page_size, " AND ".join(where), params, order_by="generated_at DESC"
        )

    def detail(self, report_id: int) -> dict[str, Any]:
        row = self.repo.get("model_reports", report_id)
        return {
            "report_id": row["id"],
            "title": row["title"],
            "report_type": row["report_type"],
            "generated_at": row["generated_at"],
            "market_summary": row["content"],
            "hot_sectors": ["半导体", "机器人", "证券"],
            "key_events": ["政策支持扩大内需", "海外市场等待通胀数据"],
            "risk_notice": "市场有风险，投资需谨慎。",
            "sources": json.loads("[]"),
        }
