"""报告生成器

将研报元数据 + 质量门禁结果 + LLM 分析结论，渲染为 Markdown 报告。
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from eastmoney_adapter import ReportMeta
from report_quality_gate import QualityResult

LOGGER = logging.getLogger(__name__)


def _fmt(v, suffix: str = "") -> str:
    if v is None:
        return "—"
    if isinstance(v, float):
        return f"{v:.2f}{suffix}"
    return f"{v}{suffix}"


def render_meta_table(reports: list[ReportMeta]) -> str:
    """渲染研报元数据表"""
    if not reports:
        return "_无可用研报_"
    headers = ["日期", "机构", "分析师", "评级(标准)", "评级(原始)", "变动", "当年EPS", "当年PE", "次年EPS"]
    rows = ["| " + " | ".join(headers) + " |",
            "|" + "|".join(["---"] * len(headers)) + "|"]
    for r in reports:
        rows.append("| " + " | ".join([
            r.publish_date,
            r.org_sname,
            r.researcher,
            r.em_rating or "—",
            r.org_rating or "—",
            r.rating_change or "—",
            _fmt(r.predict_this_year_eps),
            _fmt(r.predict_this_year_pe),
            _fmt(r.predict_next_year_eps),
        ]) + " |")
    return "\n".join(rows)


def render_consensus(reports: list[ReportMeta]) -> str:
    """渲染共识统计"""
    if not reports:
        return "_无数据_"
    ratings = [r.em_rating for r in reports if r.em_rating]
    eps_list = [r.predict_this_year_eps for r in reports if r.predict_this_year_eps]
    pe_list = [r.predict_this_year_pe for r in reports if r.predict_this_year_pe]

    from collections import Counter
    rating_dist = Counter(ratings)

    lines = [
        f"- **评级分布**：{dict(rating_dist) if rating_dist else '无'}",
        f"- **当年 EPS 预测**：均值 {_fmt(sum(eps_list)/len(eps_list)) if eps_list else '—'}，"
        f"区间 [{_fmt(min(eps_list))}, {_fmt(max(eps_list))}]" if eps_list else "- **当年 EPS 预测**：—",
        f"- **当年 PE 预测**：均值 {_fmt(sum(pe_list)/len(pe_list)) if pe_list else '—'}，"
        f"区间 [{_fmt(min(pe_list))}, {_fmt(max(pe_list))}]" if pe_list else "- **当年 PE 预测**：—",
        f"- **涉及机构数**：{len(set(r.org_sname for r in reports))}",
        f"- **涉及分析师数**：{len(set(r.researcher for r in reports if r.researcher))}",
    ]
    return "\n".join(lines)


def generate_report(
    subject: str,
    reports: list[ReportMeta],
    quality: QualityResult,
    llm_analysis: Optional[dict] = None,
) -> str:
    """生成完整的 Markdown 研报分析报告

    :param subject: 分析主题（股票名/行业名）
    :param reports: 通过质量门禁的研报列表
    :param quality: 质量门禁结果
    :param llm_analysis: LLM 多专家分析结论（可选，由 supervisor 产出）
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    llm_analysis = llm_analysis or {}

    sections = [
        f"# 券商研报分析报告：{subject}",
        "",
        f"> 生成时间：{now}  |  数据源：东方财富研报中心  |  仅作信息聚合，不构成投资建议",
        "",
        "## 一、研报概览",
        "",
        f"- **标的**：{subject}",
        f"- **时间窗口**：{reports[0].publish_date if reports else '—'} ~ "
        f"{reports[-1].publish_date if reports else '—'}",
        f"- **研报总数**：{quality.total}",
        f"- **通过质量门禁**：{quality.valid} 篇",
        f"- **机构数**：{len(set(r.org_sname for r in reports))}",
        "",
        "## 二、质量门禁结果",
        "",
        f"- 过期研报：{quality.expired}",
        f"- 非白名单机构：{quality.non_whitelist}",
        f"- 评级缺失：{quality.missing_rating}",
        f"- **利益冲突提示**：{quality.conflict_of_interest or '未发现明显异常'}",
        "",
        "## 三、机构共识统计",
        "",
        render_consensus(reports),
        "",
        "## 四、研报明细",
        "",
        render_meta_table(reports),
        "",
    ]

    if llm_analysis:
        sections += [
            "## 五、多专家分析结论",
            "",
        ]
        if llm_analysis.get("fundamental_view"):
            sections.append(f"### 基本面观点\n\n{llm_analysis['fundamental_view']}\n")
        if llm_analysis.get("rating_consensus"):
            sections.append(f"### 评级共识\n\n{llm_analysis['rating_consensus']}\n")
        if llm_analysis.get("divergence"):
            sections.append(f"### 机构分歧\n\n{llm_analysis['divergence']}\n")
        if llm_analysis.get("risk_warnings"):
            sections.append(f"### 风险提示\n\n{llm_analysis['risk_warnings']}\n")
        if llm_analysis.get("decision_hint"):
            sections.append(f"### 综合判断\n\n**决策提示**：{llm_analysis['decision_hint']}\n")
        # PDF 解析摘要（来自 MarkItDown/pdfplumber，供 LLM 后续深度分析使用）
        pdf_excerpts = llm_analysis.get("pdf_excerpts") or {}
        if pdf_excerpts:
            sections.append("### 研报 PDF 解析摘要（机器提取，待 LLM 深度分析）\n")
            for info_code, text in list(pdf_excerpts.items())[:3]:
                sections.append(f"#### {info_code}\n\n```\n{text[:1500]}\n```\n")

    sections += [
        "## 六、数据来源",
        "",
        "- 东方财富研报中心：https://data.eastmoney.com/report/",
        "- 原始 PDF 版权归各券商研究所所有",
        "- 本报告由 broker-research-analyst skill 自动生成",
        "",
        "---",
        "",
        "**免责声明**：本报告仅为公开研报信息的聚合与分析辅助，"
        "不构成任何投资建议。投资有风险，决策需谨慎。",
    ]

    return "\n".join(sections)


def save_report(content: str, output_path: str) -> str:
    """保存报告到文件"""
    from pathlib import Path
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    LOGGER.info("报告已保存: %s", path)
    return str(path)
