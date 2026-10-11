# -*- coding: utf-8 -*-
"""AlertChecker 预警逻辑测试"""
from excel_monitor.core.alert_checker import (
    AlertCondition, AlertResult, AlertChecker
)


def test_no_alert_when_no_condition():
    """无预警条件时不触发"""
    cond = AlertCondition(code="000001", name="平安银行")
    results = AlertChecker.check(cond, latest_price=10.0, change_pct=5.0)
    assert len(results) == 0


def test_change_pct_exceeds_max():
    """涨跌幅超过上限触发"""
    cond = AlertCondition(code="000001", name="平安银行", change_pct_max=5.0)
    results = AlertChecker.check(cond, latest_price=10.0, change_pct=6.5)
    assert len(results) == 1
    assert results[0].indicator == "涨跌幅"
    assert results[0].direction == "超过上限"
    assert results[0].current_value == 6.5
    assert results[0].threshold == 5.0


def test_change_pct_below_min():
    """涨跌幅低于下限触发"""
    cond = AlertCondition(code="000001", name="平安银行", change_pct_min=-3.0)
    results = AlertChecker.check(cond, latest_price=10.0, change_pct=-5.0)
    assert len(results) == 1
    assert results[0].direction == "低于下限"
    assert results[0].current_value == -5.0


def test_price_exceeds_max():
    """价格超过上限触发"""
    cond = AlertCondition(code="600519", name="贵州茅台", price_max=1800.0)
    results = AlertChecker.check(cond, latest_price=1850.0, change_pct=1.0)
    assert len(results) == 1
    assert results[0].indicator == "价格"
    assert results[0].direction == "超过上限"


def test_price_below_min():
    """价格低于下限触发"""
    cond = AlertCondition(code="600519", name="贵州茅台", price_min=1700.0)
    results = AlertChecker.check(cond, latest_price=1650.0, change_pct=-2.0)
    assert len(results) == 1
    assert results[0].direction == "低于下限"


def test_multiple_alerts_triggered():
    """同时触发多个预警"""
    cond = AlertCondition(
        code="000001", name="平安银行",
        change_pct_max=3.0, price_max=10.0,
    )
    results = AlertChecker.check(cond, latest_price=11.0, change_pct=5.0)
    assert len(results) == 2
    indicators = [r.indicator for r in results]
    assert "涨跌幅" in indicators
    assert "价格" in indicators


def test_boundary_not_triggered():
    """等于阈值时不触发（严格大于/小于）"""
    cond = AlertCondition(code="000001", name="平安银行", change_pct_max=5.0)
    results = AlertChecker.check(cond, latest_price=10.0, change_pct=5.0)
    assert len(results) == 0


def test_batch_check():
    """批量检查多只股票"""
    conditions = [
        AlertCondition(code="000001", name="平安银行", change_pct_max=3.0),
        AlertCondition(code="600519", name="贵州茅台", price_max=1800.0),
    ]
    price_map = {"000001": 10.0, "600519": 1850.0}
    change_pct_map = {"000001": 5.0, "600519": 1.0}

    results = AlertChecker.check_batch(conditions, price_map, change_pct_map)
    assert len(results) == 2
    codes = [r.code for r in results]
    assert "000001" in codes
    assert "600519" in codes


def test_batch_check_missing_data_skipped():
    """缺少行情数据的股票跳过"""
    conditions = [
        AlertCondition(code="000001", name="平安银行", change_pct_max=3.0),
        AlertCondition(code="600519", name="贵州茅台", price_max=1800.0),
    ]
    price_map = {"000001": 10.0}  # 缺 600519
    change_pct_map = {"000001": 5.0}

    results = AlertChecker.check_batch(conditions, price_map, change_pct_map)
    assert len(results) == 1
    assert results[0].code == "000001"


def test_format_alert_message():
    """测试弹窗消息格式化"""
    results = [
        AlertResult("000001", "平安银行", "涨跌幅", 6.5, 5.0, "超过上限"),
        AlertResult("600519", "贵州茅台", "价格", 1850.0, 1800.0, "超过上限"),
    ]
    msg = AlertChecker.format_alert_message(results)
    assert "平安银行" in msg
    assert "贵州茅台" in msg
    assert "超过上限" in msg


def test_format_empty_message():
    """空结果返回空字符串"""
    msg = AlertChecker.format_alert_message([])
    assert msg == ""
