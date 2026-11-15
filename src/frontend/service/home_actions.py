"""Local task and account readiness actions without quote acquisition."""

from __future__ import annotations

from typing import Any

from src.core.repository import Repository


def _percent(value):
    return f"{value * 100:.2f}%"


def action_rows(
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
