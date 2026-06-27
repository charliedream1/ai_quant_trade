"""报告校验与质量评估模块

对最终生成的 Markdown 报告进行：
1. 结构完整性校验（章节齐全、表格格式正确）
2. 数据一致性校验（统计数字与明细对得上）
3. 内容质量评估（覆盖率、置信度评分）
4. 幻觉检查（关键数据是否能在源 PDF 中找到依据）

评估结果以 QualityAssessment 数据类返回，并记录到错误日志。
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field, asdict
from typing import Optional

from eastmoney_adapter import ReportMeta
from report_quality_gate import QualityResult
from error_logger import ErrorLog

LOGGER = logging.getLogger(__name__)


@dataclass
class CheckItem:
    """单项校验结果"""
    name: str
    passed: bool
    detail: str = ""


@dataclass
class HallucinationFinding:
    """幻觉检查发现"""
    severity: str           # HIGH / MEDIUM / LOW
    category: str           # unsupported_number / inconsistent_rating / fabricated_entity / unverifiable_claim
    description: str
    evidence: str = ""      # 源 PDF 中的依据（若有）


@dataclass
class QualityAssessment:
    """报告质量评估结果"""
    # 结构校验
    structure_checks: list[CheckItem] = field(default_factory=list)
    # 数据一致性校验
    consistency_checks: list[CheckItem] = field(default_factory=list)
    # 幻觉检查
    hallucination_findings: list[HallucinationFinding] = field(default_factory=list)
    # 综合评分
    overall_score: float = 0.0       # 0-100
    confidence: str = "LOW"          # LOW / MEDIUM / HIGH
    # 元信息
    char_count: int = 0
    section_count: int = 0
    table_count: int = 0
    image_ref_count: int = 0
    citation_count: int = 0

    @property
    def all_checks_passed(self) -> bool:
        return all(c.passed for c in self.structure_checks + self.consistency_checks)

    @property
    def hallucination_count(self) -> int:
        return len(self.hallucination_findings)

    @property
    def high_severity_count(self) -> int:
        return sum(1 for h in self.hallucination_findings if h.severity == "HIGH")

    def to_dict(self) -> dict:
        return {
            "overall_score": self.overall_score,
            "confidence": self.confidence,
            "char_count": self.char_count,
            "section_count": self.section_count,
            "table_count": self.table_count,
            "image_ref_count": self.image_ref_count,
            "citation_count": self.citation_count,
            "structure_checks": [asdict(c) for c in self.structure_checks],
            "consistency_checks": [asdict(c) for c in self.consistency_checks],
            "hallucination_findings": [asdict(h) for h in self.hallucination_findings],
            "all_checks_passed": self.all_checks_passed,
            "hallucination_count": self.hallucination_count,
            "high_severity_count": self.high_severity_count,
        }


# 必须包含的章节关键词（用于结构校验）
REQUIRED_SECTIONS = [
    ("overview", ["研报概览", "一、"]),
    ("quality_gate", ["质量门禁", "二、"]),
    ("consensus", ["共识统计", "三、"]),
    ("detail", ["研报明细", "四、"]),
    ("data_source", ["数据来源"]),
    ("disclaimer", ["免责声明"]),
    ("index", ["索引"]),
    ("references", ["引用", "参考文献"]),
]


def _count_tables(md: str) -> int:
    """统计 Markdown 表格数（按 |---| 分隔符）"""
    return len(re.findall(r"\|\s*-{3,}\s*\|", md))


def _count_sections(md: str) -> int:
    """统计 ## 二级标题数"""
    return len(re.findall(r"^##\s+", md, re.MULTILINE))


def _count_image_refs(md: str) -> int:
    """统计图片引用数（本地路径或 markdown 图片语法）"""
    # 匹配 `xxx/p1_img1.jpeg` 这类代码块引用，以及 ![alt](path)
    code_refs = len(re.findall(r"`[^`]+\.(?:png|jpeg|jpg)`", md))
    md_refs = len(re.findall(r"!\[[^\]]*\]\([^)]+\)", md))
    return code_refs + md_refs


def _count_citations(md: str) -> int:
    """统计引用条目数（## 引用 章节下的列表项）"""
    # 找到引用章节（标题可能含"八、"等序号前缀）
    ref_match = re.search(r"##\s+(?:[一二三四五六七八九十]+、)?(?:引用|参考文献|引用文章)(.*?)(?=\n##\s|\Z)", md, re.DOTALL)
    if not ref_match:
        return 0
    ref_section = ref_match.group(1)
    # 统计有序列表项（1. **标题**）和无序列表项
    ordered = len(re.findall(r"^\s*\d+\.\s+\*\*", ref_section, re.MULTILINE))
    unordered = len(re.findall(r"^\s*-\s+\[", ref_section, re.MULTILINE))
    return ordered + unordered


def check_structure(md: str, error_log: ErrorLog) -> list[CheckItem]:
    """结构完整性校验"""
    checks: list[CheckItem] = []

    # 1. 必须章节齐全
    for key, keywords in REQUIRED_SECTIONS:
        found = any(kw in md for kw in keywords)
        checks.append(CheckItem(
            name=f"section_{key}",
            passed=found,
            detail="; ".join(keywords),
        ))
        if not found:
            error_log.add_warning("validate", f"缺失章节: {key}（应包含 {keywords}）")

    # 2. 表格格式校验（每张表应有表头分隔符）
    table_count = _count_tables(md)
    checks.append(CheckItem(
        name="table_format",
        passed=table_count > 0,
        detail=f"识别到 {table_count} 个表格分隔符",
    ))

    # 3. 报告非空且足够长
    char_count = len(md)
    checks.append(CheckItem(
        name="report_length",
        passed=char_count >= 1000,
        detail=f"字符数 {char_count}（阈值 1000）",
    ))
    if char_count < 1000:
        error_log.add_warning("validate", f"报告过短: {char_count} 字符")

    # 4. 含免责声明
    has_disclaimer = "免责声明" in md and "不构成" in md
    checks.append(CheckItem(
        name="disclaimer",
        passed=has_disclaimer,
        detail="合规免责声明",
    ))

    return checks


def check_consistency(
    md: str,
    reports: list[ReportMeta],
    quality: QualityResult,
    error_log: ErrorLog,
) -> list[CheckItem]:
    """数据一致性校验"""
    checks: list[CheckItem] = []

    # 1. 研报总数一致（格式：**研报总数**：26 或 研报总数：26）
    total_in_md = re.search(r"研报总数\*?\*?[：:]\s*(\d+)", md)
    total_expected = quality.total
    total_actual = int(total_in_md.group(1)) if total_in_md else -1
    checks.append(CheckItem(
        name="total_count",
        passed=total_actual == total_expected,
        detail=f"报告中 {total_actual} vs 实际 {total_expected}",
    ))
    if total_actual != total_expected:
        error_log.add_error("validate", "研报总数不一致",
                            reported=total_actual, actual=total_expected)

    # 2. 通过门禁数一致
    valid_in_md = re.search(r"通过质量门禁\*?\*?[：:]\s*(\d+)\s*篇", md)
    valid_expected = quality.valid
    valid_actual = int(valid_in_md.group(1)) if valid_in_md else -1
    checks.append(CheckItem(
        name="valid_count",
        passed=valid_actual == valid_expected,
        detail=f"报告中 {valid_actual} vs 实际 {valid_expected}",
    ))

    # 3. 明细表行数 = 通过门禁研报数
    # 统计明细表中数据行（含日期格式的行）
    detail_rows = len(re.findall(r"\|\s*\d{4}-\d{2}-\d{2}\s*\|", md))
    checks.append(CheckItem(
        name="detail_rows",
        passed=detail_rows == len(reports),
        detail=f"明细行 {detail_rows} vs 研报数 {len(reports)}",
    ))
    if detail_rows != len(reports):
        error_log.add_warning("validate", "明细表行数与研报数不一致",
                              detail_rows=detail_rows, report_count=len(reports))

    # 4. 评级分布一致性（报告中评级分布与实际 reports 计算）
    from collections import Counter
    actual_ratings = Counter(r.em_rating for r in reports if r.em_rating)
    # 报告中的评级分布
    rating_match = re.search(r"评级分布[：:]\s*(\{[^}]+\})", md)
    if rating_match and actual_ratings:
        try:
            md_ratings_str = rating_match.group(1).replace("'", '"')
            md_ratings = json.loads(md_ratings_str)
            checks.append(CheckItem(
                name="rating_distribution",
                passed=dict(md_ratings) == dict(actual_ratings),
                detail=f"报告 {md_ratings} vs 实际 {dict(actual_ratings)}",
            ))
        except (json.JSONDecodeError, Exception):
            checks.append(CheckItem(
                name="rating_distribution",
                passed=False,
                detail="评级分布解析失败",
            ))

    return checks


def check_hallucination(
    md: str,
    reports: list[ReportMeta],
    pdf_excerpts: dict,
    error_log: ErrorLog,
) -> list[HallucinationFinding]:
    """幻觉检查

    检查报告中的关键数据/陈述是否有源依据：
    1. 数字幻觉：报告中提到的具体数字（EPS、PE、目标价）是否在源 PDF 或元数据中出现
    2. 评级幻觉：报告引用的评级是否与原始研报评级一致
    3. 实体幻觉：提到的机构/分析师是否在原始研报列表中
    4. 不可验证陈述：关键结论是否标注了来源
    """
    findings: list[HallucinationFinding] = []

    # 收集所有源文本（PDF 摘要 + 元数据）
    source_texts = list(pdf_excerpts.values())
    source_concat = "\n".join(source_texts).lower()
    # 元数据中的实体
    actual_orgs = {r.org_sname for r in reports if r.org_sname}
    actual_researchers = set()
    for r in reports:
        if r.researcher:
            # 分析师可能是多个，按逗号/空格分割
            for name in re.split(r"[,，、\s]+", r.researcher):
                if len(name) >= 2:
                    actual_researchers.add(name)
    actual_ratings = {r.em_rating for r in reports if r.em_rating}
    actual_eps_values = [r.predict_this_year_eps for r in reports if r.predict_this_year_eps]
    actual_pe_values = [r.predict_this_year_pe for r in reports if r.predict_this_year_pe]

    # 1. 实体幻觉：检查报告中提到的机构是否都在源数据中
    # 报告中明细表里的机构名
    md_orgs = set(re.findall(r"\|\s*([\u4e00-\u9fa5]{2,8}(?:证券|资本|投资))\s*\|", md))
    for org in md_orgs:
        if org not in actual_orgs:
            findings.append(HallucinationFinding(
                severity="MEDIUM",
                category="fabricated_entity",
                description=f"报告中出现的机构 '{org}' 不在原始研报列表中",
                evidence=f"实际机构: {actual_orgs}",
            ))
            error_log.add_warning("hallucination", f"疑似实体幻觉: 机构 {org}",
                                  category="fabricated_entity")

    # 2. 评级幻觉：报告中出现的评级是否都在实际评级集合中
    # 已知合法评级
    known_ratings = {"买入", "增持", "中性", "减持", "卖出", "推荐", "谨慎推荐",
                     "优于大市", "跑赢大市", "同步大市", "落后大市", "—"}
    md_ratings = set(re.findall(r"(买入|增持|中性|减持|卖出|推荐|谨慎推荐|优于大市|跑赢大市|同步大市|落后大市)", md))
    for rating in md_ratings:
        if rating not in actual_ratings and rating not in known_ratings:
            findings.append(HallucinationFinding(
                severity="HIGH",
                category="inconsistent_rating",
                description=f"报告中出现的评级 '{rating}' 不在任何源研报中",
                evidence=f"实际评级: {actual_ratings}",
            ))
            error_log.add_error("hallucination", f"疑似评级幻觉: {rating}",
                                category="inconsistent_rating")

    # 3. 数字幻觉：检查 EPS/PE 等关键数字
    # 报告中"当年 EPS 预测"区间
    eps_match = re.search(r"当年\s*EPS\s*预测[：:][^[]*\[([\d.]+),\s*([\d.]+)\]", md)
    if eps_match and actual_eps_values:
        md_min, md_max = float(eps_match.group(1)), float(eps_match.group(2))
        actual_min, actual_max = min(actual_eps_values), max(actual_eps_values)
        # 允许 0.01 的浮点误差
        if abs(md_min - actual_min) > 0.01 or abs(md_max - actual_max) > 0.01:
            findings.append(HallucinationFinding(
                severity="HIGH",
                category="unsupported_number",
                description=f"EPS 区间 [{md_min}, {md_max}] 与实际 [{actual_min:.2f}, {actual_max:.2f}] 不符",
                evidence=f"源数据 EPS: {actual_eps_values}",
            ))
            error_log.add_error("hallucination", "EPS 区间与源数据不符",
                                reported=[md_min, md_max], actual=[actual_min, actual_max])

    # 4. 不可验证陈述：检查关键结论段落是否有源引用
    # 找到"综合判断"/"决策提示"段落
    decision_match = re.search(r"(?:综合判断|决策提示)[：:](.*?)(?=\n##|\n###|\Z)", md, re.DOTALL)
    if decision_match:
        decision_text = decision_match.group(1)
        # 如果结论段落较长（>50字）但未引用任何源
        if len(decision_text.strip()) > 50:
            has_source_ref = any(
                kw in decision_text for kw in ["源", "依据", "根据", "参见", "见", "PDF"]
            )
            if not has_source_ref:
                findings.append(HallucinationFinding(
                    severity="LOW",
                    category="unverifiable_claim",
                    description="综合判断段落较长但未标注信息来源，建议补充引用",
                    evidence=decision_text[:100],
                ))
                error_log.add_warning("hallucination", "综合判断未标注来源",
                                      category="unverifiable_claim")

    # 5. 目标价幻觉：如果报告提到具体目标价，检查是否在源中
    target_prices = re.findall(r"目标价[为约]?\s*([\d.]+)\s*元", md)
    if target_prices:
        for price_str in target_prices:
            price = float(price_str)
            # 目标价通常出现在 PDF 全文中，检查源文本是否含该数字
            if source_concat and str(int(price)) not in source_concat and price_str not in source_concat:
                findings.append(HallucinationFinding(
                    severity="MEDIUM",
                    category="unsupported_number",
                    description=f"目标价 {price} 元未在源 PDF 中找到依据",
                    evidence="源 PDF 摘要中未出现该数字",
                ))
                error_log.add_warning("hallucination", f"目标价 {price} 无源依据",
                                      category="unsupported_number")

    return findings


def compute_score(
    structure_checks: list[CheckItem],
    consistency_checks: list[CheckItem],
    hallucination_findings: list[HallucinationFinding],
) -> tuple[float, str]:
    """计算综合质量评分与置信度

    评分规则：
    - 结构校验：每项通过 +5 分，最高 40 分
    - 一致性校验：每项通过 +10 分，最高 40 分
    - 幻觉检查：基础 20 分，每个 HIGH -10，每个 MEDIUM -5，每个 LOW -2（不低于 0）
    """
    structure_score = sum(5 for c in structure_checks if c.passed)
    structure_score = min(structure_score, 40)

    consistency_score = sum(10 for c in consistency_checks if c.passed)
    consistency_score = min(consistency_score, 40)

    hallucination_score = 20
    for h in hallucination_findings:
        if h.severity == "HIGH":
            hallucination_score -= 10
        elif h.severity == "MEDIUM":
            hallucination_score -= 5
        elif h.severity == "LOW":
            hallucination_score -= 2
    hallucination_score = max(hallucination_score, 0)

    total = structure_score + consistency_score + hallucination_score

    # 置信度
    if total >= 85 and not any(h.severity == "HIGH" for h in hallucination_findings):
        confidence = "HIGH"
    elif total >= 60:
        confidence = "MEDIUM"
    else:
        confidence = "LOW"

    return total, confidence


def assess_report(
    md: str,
    reports: list[ReportMeta],
    quality: QualityResult,
    pdf_excerpts: dict,
    error_log: ErrorLog,
) -> QualityAssessment:
    """对报告进行全面质量评估

    :param md: 报告 Markdown 内容
    :param reports: 通过门禁的研报列表
    :param quality: 质量门禁结果
    :param pdf_excerpts: PDF 解析摘要（用于幻觉检查的源依据）
    :param error_log: 错误日志（评估过程中的发现会记录其中）
    :return: QualityAssessment
    """
    error_log.add_info("validate", "开始报告质量评估",
                       char_count=len(md), report_count=len(reports))

    structure_checks = check_structure(md, error_log)
    consistency_checks = check_consistency(md, reports, quality, error_log)
    hallucination_findings = check_hallucination(md, reports, pdf_excerpts, error_log)

    score, confidence = compute_score(structure_checks, consistency_checks, hallucination_findings)

    assessment = QualityAssessment(
        structure_checks=structure_checks,
        consistency_checks=consistency_checks,
        hallucination_findings=hallucination_findings,
        overall_score=score,
        confidence=confidence,
        char_count=len(md),
        section_count=_count_sections(md),
        table_count=_count_tables(md),
        image_ref_count=_count_image_refs(md),
        citation_count=_count_citations(md),
    )

    error_log.add_info("validate", "质量评估完成",
                       score=score, confidence=confidence,
                       hallucinations=len(hallucination_findings),
                       high_severity=assessment.high_severity_count)

    return assessment
