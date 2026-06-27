"""研报质量门禁

在分析前对研报集合做合规性与时效性校验：
1. 时效性：发布日期是否在有效期窗口内
2. 来源权威性：机构是否在白名单
3. 字段完整性：评级/EPS预测是否缺失
4. 利益冲突提示：卖方研报普遍偏多，统计评级分布
"""
from __future__ import annotations

import logging
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

from eastmoney_adapter import ReportMeta

LOGGER = logging.getLogger(__name__)

# 主流券商白名单（按研究实力排序，非穷举）
ORG_WHITELIST = {
    "中信证券", "中金公司", "中信建投", "华泰证券", "国泰君安",
    "海通证券", "招商证券", "广发证券", "兴业证券", "国信证券",
    "申万宏源", "长江证券", "东方证券", "东吴证券", "光大证券",
    "安信证券", "方正证券", "民生证券", "国元证券", "浙商证券",
    "西部证券", "开源证券", "天风证券", "财通证券", "中泰证券",
}


@dataclass
class QualityResult:
    """质量门禁结果"""
    total: int = 0
    valid: int = 0
    expired: int = 0
    non_whitelist: int = 0
    missing_rating: int = 0
    rating_distribution: dict = field(default_factory=dict)
    conflict_of_interest: str = ""
    passed_reports: list = field(default_factory=list)
    rejected_reports: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "total": self.total,
            "valid": self.valid,
            "expired": self.expired,
            "non_whitelist": self.non_whitelist,
            "missing_rating": self.missing_rating,
            "rating_distribution": self.rating_distribution,
            "conflict_of_interest": self.conflict_of_interest,
            "passed_count": len(self.passed_reports),
            "rejected_count": len(self.rejected_reports),
        }


def check_freshness(meta: ReportMeta, expire_days: int = 90) -> bool:
    """校验研报时效性"""
    if not meta.publish_date:
        return False
    try:
        pub_date = datetime.strptime(meta.publish_date, "%Y-%m-%d")
    except ValueError:
        return False
    return (datetime.now() - pub_date).days <= expire_days


def is_org_whitelisted(meta: ReportMeta, require_whitelist: bool = True) -> bool:
    """校验机构是否在白名单"""
    if not require_whitelist:
        return True
    if not meta.org_sname:
        return False
    # 模糊匹配：白名单中任一机构名是 org_sname 的子串
    return any(org in meta.org_sname for org in ORG_WHITELIST)


def detect_conflict_of_interest(reports: list[ReportMeta]) -> str:
    """检测卖方利益冲突：评级分布是否过度乐观"""
    if not reports:
        return ""
    ratings = [r.em_rating for r in reports if r.em_rating]
    if not ratings:
        return ""
    dist = Counter(ratings)
    total = len(ratings)
    # 买入/增持 占比
    bullish = dist.get("买入", 0) + dist.get("增持", 0) + dist.get("推荐", 0) + dist.get("强烈推荐", 0)
    bearish = dist.get("减持", 0) + dist.get("卖出", 0)
    if bullish / total > 0.8 and bearish == 0:
        return (f"卖方研报普遍偏多：买入/增持占比 {bullish}/{total} "
                f"({bullish/total:.0%})，无减持/卖出评级，注意卖方利益冲突与乐观倾向")
    return ""


def run_quality_gate(
    reports: list[ReportMeta],
    expire_days: int = 90,
    require_whitelist: bool = True,
    min_count: int = 3,
) -> QualityResult:
    """执行质量门禁

    :param reports: 待校验研报列表
    :param expire_days: 时效性阈值（天）
    :param require_whitelist: 是否要求机构在白名单
    :param min_count: 最少有效研报数
    :return: QualityResult
    """
    result = QualityResult(total=len(reports))
    rating_counter: Counter = Counter()

    for meta in reports:
        reasons = []
        if not check_freshness(meta, expire_days):
            result.expired += 1
            reasons.append("时效性不足")
        if not is_org_whitelisted(meta, require_whitelist):
            result.non_whitelist += 1
            reasons.append("机构非主流白名单")
        if not meta.em_rating and not meta.org_rating:
            result.missing_rating += 1
            reasons.append("评级缺失")

        if reasons:
            result.rejected_reports.append({"info_code": meta.info_code, "reasons": reasons})
        else:
            result.passed_reports.append(meta)
            if meta.em_rating:
                rating_counter[meta.em_rating] += 1

    result.valid = len(result.passed_reports)
    result.rating_distribution = dict(rating_counter)
    result.conflict_of_interest = detect_conflict_of_interest(result.passed_reports)

    LOGGER.info(
        "质量门禁: 总计 %d, 通过 %d, 拒绝 %d (过期 %d, 非白名单 %d, 缺评级 %d)",
        result.total, result.valid, len(result.rejected_reports),
        result.expired, result.non_whitelist, result.missing_rating,
    )

    if result.valid < min_count:
        LOGGER.warning("有效研报数 %d 不足最低要求 %d，结论置信度将受限", result.valid, min_count)

    return result
