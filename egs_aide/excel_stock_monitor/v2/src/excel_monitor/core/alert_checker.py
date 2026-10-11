# -*- coding: utf-8 -*-
"""预警检查器：检查股票是否达到用户设定的预警条件

用户可在 Excel 中为每只股票设置：
    - 涨跌幅上限 / 下限
    - 价格上限 / 下限

达到条件时返回 AlertResult，由 CustomWatchSheet 负责高亮和弹窗。
"""
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class AlertCondition:
    """单只股票的预警条件（None 表示不监控该指标）"""
    code: str
    name: str = ""
    change_pct_min: Optional[float] = None   # 涨跌幅下限（低于此值预警）
    change_pct_max: Optional[float] = None   # 涨跌幅上限（高于此值预警）
    price_min: Optional[float] = None        # 价格下限
    price_max: Optional[float] = None        # 价格上限


@dataclass
class AlertResult:
    """预警触发结果"""
    code: str
    name: str
    indicator: str       # 触发指标：涨跌幅 / 价格
    current_value: float  # 当前值
    threshold: float      # 阈值
    direction: str        # "超过上限" / "低于下限"


class AlertChecker:
    """预警条件检查器（纯逻辑，无副作用）"""

    @staticmethod
    def check(condition: AlertCondition,
              latest_price: float,
              change_pct: float) -> List[AlertResult]:
        """检查单只股票是否触发预警

        Args:
            condition: 预警条件
            latest_price: 最新价格
            change_pct: 涨跌幅（%）

        Returns:
            触发的预警结果列表（空列表表示未触发）
        """
        results: List[AlertResult] = []

        # 涨跌幅上限
        if condition.change_pct_max is not None \
                and change_pct > condition.change_pct_max:
            results.append(AlertResult(
                code=condition.code,
                name=condition.name,
                indicator="涨跌幅",
                current_value=change_pct,
                threshold=condition.change_pct_max,
                direction="超过上限",
            ))

        # 涨跌幅下限
        if condition.change_pct_min is not None \
                and change_pct < condition.change_pct_min:
            results.append(AlertResult(
                code=condition.code,
                name=condition.name,
                indicator="涨跌幅",
                current_value=change_pct,
                threshold=condition.change_pct_min,
                direction="低于下限",
            ))

        # 价格上限
        if condition.price_max is not None \
                and latest_price > condition.price_max:
            results.append(AlertResult(
                code=condition.code,
                name=condition.name,
                indicator="价格",
                current_value=latest_price,
                threshold=condition.price_max,
                direction="超过上限",
            ))

        # 价格下限
        if condition.price_min is not None \
                and latest_price < condition.price_min:
            results.append(AlertResult(
                code=condition.code,
                name=condition.name,
                indicator="价格",
                current_value=latest_price,
                threshold=condition.price_min,
                direction="低于下限",
            ))

        return results

    @staticmethod
    def check_batch(conditions: List[AlertCondition],
                    price_map: dict,
                    change_pct_map: dict) -> List[AlertResult]:
        """批量检查多只股票

        Args:
            conditions: 预警条件列表
            price_map: {股票代码: 最新价格}
            change_pct_map: {股票代码: 涨跌幅}

        Returns:
            所有触发的预警结果
        """
        all_results: List[AlertResult] = []
        for cond in conditions:
            price = price_map.get(cond.code)
            change = change_pct_map.get(cond.code)
            if price is None or change is None:
                continue
            results = AlertChecker.check(cond, price, change)
            all_results.extend(results)
        return all_results

    @staticmethod
    def format_alert_message(results: List[AlertResult]) -> str:
        """将预警结果格式化为弹窗消息"""
        if not results:
            return ""
        lines = ["⚠ 预警提醒 ⚠", ""]
        for r in results:
            lines.append(
                f"{r.name}({r.code}) {r.indicator} "
                f"当前 {r.current_value} {r.direction} {r.threshold}"
            )
        return "\n".join(lines)
