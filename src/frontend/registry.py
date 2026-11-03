"""Stable registry for independently mounted Gradio modules."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GradioModule:
    key: str
    title: str
    slug: str
    description: str
    order: int
    views: tuple[tuple[str, str], ...]

    @property
    def mount_path(self) -> str:
        return f"/app/{self.slug}"

    @property
    def href(self) -> str:
        return f"{self.mount_path}/"


MODULES: tuple[GradioModule, ...] = (
    GradioModule(
        "dashboard",
        "投研看板",
        "dashboard",
        "账户、市场与任务总览",
        10,
        (("overview", "总览"), ("custom", "自定义仪表盘")),
    ),
    GradioModule(
        "market",
        "市场研究",
        "market",
        "行情、因子、个股与推荐",
        20,
        (
            ("quotes", "行情看盘"),
            ("news", "新闻中心"),
            ("stock", "个股分析"),
            ("relations", "关系图谱"),
            ("resources", "资源池"),
            ("recommendations", "股票推荐"),
        ),
    ),
    GradioModule(
        "strategy",
        "策略构建",
        "strategy",
        "策略生命周期、版本与构建",
        40,
        (
            ("workshop", "图形策略工坊"),
            ("management", "策略管理"),
            ("factors", "因子研究与监控"),
            ("alpha", "Alpha研究"),
            ("etf", "ETF研究"),
            ("qlib", "Qlib实验"),
        ),
    ),
    GradioModule(
        "simulation",
        "策略仿真",
        "simulation",
        "回测、模拟交易与归因",
        50,
        (("backtest", "回测与模拟"), ("attribution", "运行归因")),
    ),
    GradioModule(
        "live", "实盘", "live", "发布、风控、运行与归因", 60, (("deployment", "发布策略"), ("attribution", "归因分析"))
    ),
    GradioModule(
        "ai",
        "AI工作台",
        "ai",
        "智能洞察、专家与闭环工作流",
        70,
        (("main", "主界面"), ("insights", "智能洞察"), ("workflow", "工作流中心")),
    ),
    GradioModule(
        "knowledge",
        "知识与资料",
        "knowledge",
        "带引用的AI问答、资料与远程知识源",
        80,
        (
            ("qa", "知识库问答"),
            ("library", "知识库入库"),
            ("research", "研报与论文"),
            ("reports", "报告库"),
            ("learning", "系统资料"),
        ),
    ),
    GradioModule(
        "learning", "学习空间", "learning", "按章节学习量化基础、回测和风控", 85, (("course", "量化基础课程"),)
    ),
    GradioModule(
        "admin",
        "系统管理",
        "admin",
        "任务、设置、模型、MCP 与 Skill",
        90,
        (("help", "帮助文档"), ("jobs", "定时任务"), ("settings", "系统配置")),
    ),
)

LEGACY_MODULES = (
    GradioModule(
        "research",
        "研报论文",
        "research",
        "兼容旧研报地址",
        30,
        (("reports", "研报与模型分析"), ("papers", "论文检索")),
    ),
)

MODULE_BY_KEY = {module.key: module for module in (*MODULES, *LEGACY_MODULES)}


def get_module(key: str) -> GradioModule:
    try:
        return MODULE_BY_KEY[key]
    except KeyError as exc:
        raise ValueError(f"unknown Gradio module: {key}") from exc
