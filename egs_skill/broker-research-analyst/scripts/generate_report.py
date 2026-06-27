"""报告生成器

将研报元数据 + 质量门禁结果 + LLM 分析结论，渲染为 Markdown 报告。
报告结构：
  索引
  一、研报概览
  二、质量门禁结果
  三、机构共识统计
  四、研报明细
  五、多专家分析结论（含 PDF 摘要、图表提取）
  六、数据来源
  七、质量评估与幻觉检查
  八、引用文章
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


def render_index(reports: list[ReportMeta], has_llm: bool, has_images: bool) -> str:
    """渲染报告索引（目录）"""
    lines = [
        "| 章节 | 内容 |",
        "|---|---|",
        f"| 一、研报概览 | 标的、时间窗口、研报总数、机构数 |",
        f"| 二、质量门禁结果 | 过期/白名单/评级缺失/利益冲突 |",
        f"| 三、机构共识统计 | 评级分布、EPS/PE 共识、机构与分析师数 |",
        f"| 四、研报明细 | {len(reports)} 篇研报的元数据表 |",
    ]
    if has_llm:
        lines.append("| 五、多专家分析结论 | 基本面/评级/分歧/风险/决策/PDF 摘要/图表 |")
    lines.append("| 六、数据来源 | 东方财富研报中心 |")
    lines.append("| 七、质量评估与幻觉检查 | 结构/一致性校验、幻觉发现、置信度 |")
    lines.append("| 八、引用文章 | 引用的原始研报列表（含 PDF 链接） |")
    return "\n".join(lines)


def render_references(reports: list[ReportMeta]) -> str:
    """渲染引用文章列表（含 PDF 链接）"""
    if not reports:
        return "_无引用研报_"
    lines = []
    for i, r in enumerate(reports, 1):
        # 引用格式：[序号] 标题. 机构, 日期. 分析师. [PDF链接]
        researcher = f" {r.researcher}." if r.researcher else ""
        rating = f" 评级：{r.org_rating}。" if r.org_rating else ""
        pdf_link = r.pdf_url or "（无 PDF 链接）"
        lines.append(f"{i}. **{r.title}**. {r.org_sname}, {r.publish_date}.{researcher}{rating}")
        lines.append(f"   - PDF: {pdf_link}")
        lines.append(f"   - info_code: `{r.info_code}`")
    return "\n".join(lines)


def render_quality_assessment(assessment) -> str:
    """渲染质量评估与幻觉检查章节"""
    lines = [
        f"### 综合评分：**{assessment.overall_score:.0f} / 100**  |  置信度：**{assessment.confidence}**",
        "",
        f"- 报告字符数：{assessment.char_count}",
        f"- 二级章节数：{assessment.section_count}",
        f"- 表格数：{assessment.table_count}",
        f"- 图片引用数：{assessment.image_ref_count}",
        f"- 引用文章数：{assessment.citation_count}",
        f"- 幻觉发现数：{assessment.hallucination_count}（HIGH: {assessment.high_severity_count}）",
        "",
        "### 结构校验",
        "",
        "| 校验项 | 结果 | 详情 |",
        "|---|---|---|",
    ]
    for c in assessment.structure_checks:
        status = "✅" if c.passed else "❌"
        lines.append(f"| {c.name} | {status} | {c.detail} |")

    lines += ["", "### 数据一致性校验", "",
              "| 校验项 | 结果 | 详情 |",
              "|---|---|---|"]
    for c in assessment.consistency_checks:
        status = "✅" if c.passed else "❌"
        lines.append(f"| {c.name} | {status} | {c.detail} |")

    if assessment.hallucination_findings:
        lines += ["", "### 幻觉检查发现", "",
                  "| 严重度 | 类别 | 描述 |",
                  "|---|---|---|"]
        for h in assessment.hallucination_findings:
            lines.append(f"| {h.severity} | {h.category} | {h.description} |")
    else:
        lines += ["", "### 幻觉检查发现", "", "_未发现明显幻觉_"]

    return "\n".join(lines)


def generate_report(
    subject: str,
    reports: list[ReportMeta],
    quality: QualityResult,
    llm_analysis: Optional[dict] = None,
    quality_assessment=None,
) -> str:
    """生成完整的 Markdown 研报分析报告

    :param subject: 分析主题（股票名/行业名）
    :param reports: 通过质量门禁的研报列表
    :param quality: 质量门禁结果
    :param llm_analysis: LLM 多专家分析结论（可选，由 supervisor 产出）
    :param quality_assessment: QualityAssessment 对象（可选，由 report_validator 产出）
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    llm_analysis = llm_analysis or {}
    pdf_excerpts = llm_analysis.get("pdf_excerpts") or {}
    pdf_images = llm_analysis.get("pdf_images") or {}
    has_llm = bool(llm_analysis)
    has_images = bool(pdf_images)

    sections = [
        f"# 券商研报分析报告：{subject}",
        "",
        f"> 生成时间：{now}  |  数据源：东方财富研报中心  |  仅作信息聚合，不构成投资建议",
        "",
        "## 索引",
        "",
        render_index(reports, has_llm, has_images),
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

    if has_llm:
        sections += ["## 五、多专家分析结论", ""]
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
        if pdf_excerpts:
            sections.append("### 研报 PDF 解析摘要（机器提取，待 LLM 深度分析）\n")
            for info_code, text in list(pdf_excerpts.items())[:3]:
                sections.append(f"#### {info_code}\n\n```\n{text[:1500]}\n```\n")
        # PDF 图片清单（来自 PyMuPDF，可用于 LLM 多模态分析）
        total_images = llm_analysis.get("total_images", 0)
        if pdf_images:
            sections.append(f"### 研报图表提取（共 {total_images} 张，可用于多模态分析）\n")
            sections.append("> 研报中的图表（营收走势、毛利率趋势、批发价走势等）已提取为图片文件，"
                            "支持 LLM 视觉模型读取以辅助分析图表趋势与异常。\n")
            for info_code, paths in list(pdf_images.items())[:3]:
                sections.append(f"**{info_code}**（{len(paths)} 张）：")
                for p in paths[:5]:
                    sections.append(f"- `{p}`")
                if len(paths) > 5:
                    sections.append(f"- ... 等 {len(paths)} 张")
                sections.append("")

    sections += [
        "## 六、数据来源",
        "",
        "- 东方财富研报中心：https://data.eastmoney.com/report/",
        "- 原始 PDF 版权归各券商研究所所有",
        "- 本报告由 broker-research-analyst skill 自动生成",
        "",
    ]

    # 质量评估与幻觉检查章节
    if quality_assessment is not None:
        sections += [
            "## 七、质量评估与幻觉检查",
            "",
            render_quality_assessment(quality_assessment),
            "",
        ]

    # 引用文章章节
    sections += [
        "## 八、引用文章",
        "",
        "> 本报告引用的原始券商研报列表（按时间倒序）",
        "",
        render_references(reports),
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
