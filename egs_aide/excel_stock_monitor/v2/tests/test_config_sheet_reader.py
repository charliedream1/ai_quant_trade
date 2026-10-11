# -*- coding: utf-8 -*-
"""ConfigSheetReader 测试：从 Excel 配置 Sheet 读取配置"""
import pandas as pd
from unittest.mock import MagicMock

from excel_monitor.config_loader import AppConfig
from excel_monitor.core.config_sheet_reader import ConfigSheetReader


def test_read_scalars_from_excel():
    """测试从 Excel 读取标量配置"""
    mock_excel = MagicMock()
    reader = ConfigSheetReader(mock_excel)

    # mock 配置 Sheet 数据
    mock_excel.get_sheet_by_name.return_value = MagicMock()
    mock_excel.sheet_to_df.return_value = (
        pd.DataFrame({
            "配置项": ["刷新间隔(秒)", "预警弹窗", "新闻条数", "配置重载间隔"],
            "值": [10, "false", 100, 3],
        }),
        6, 2,
    )

    defaults = AppConfig()
    cfg = reader.read_config("配置", defaults)

    assert cfg.refresh_interval == 10
    assert cfg.alert_popup_enabled is False
    assert cfg.news_max_rows == 100
    assert cfg.config_reload_interval == 3


def test_read_lists_from_excel():
    """测试从 Excel 读取列表配置（自选股、指数）"""
    mock_excel = MagicMock()
    reader = ConfigSheetReader(mock_excel)

    mock_excel.get_sheet_by_name.return_value = MagicMock()
    mock_excel.sheet_to_df.return_value = (
        pd.DataFrame({
            "配置项": ["刷新间隔(秒)", None, None, None, None, None, None],
            "值": [3, None, None, None, None, None, None],
            "自选股": ["中国平安", "贵州茅台", "宁德时代", None, None, None, None],
            "指数": ["上证指数", "深证成指", "创业板指", None, None, None, None],
        }),
        10, 4,
    )

    defaults = AppConfig()
    cfg = reader.read_config("配置", defaults)

    assert cfg.watch_stocks == ["中国平安", "贵州茅台", "宁德时代"]
    assert cfg.market_indices == ["上证指数", "深证成指", "创业板指"]


def test_missing_config_sheet_returns_defaults():
    """测试配置 Sheet 不存在时返回默认配置"""
    mock_excel = MagicMock()
    mock_excel.get_sheet_by_name.return_value = None
    reader = ConfigSheetReader(mock_excel)

    defaults = AppConfig()
    cfg = reader.read_config("配置", defaults)

    assert cfg.refresh_interval == defaults.refresh_interval
    assert cfg.watch_stocks == defaults.watch_stocks


def test_partial_config_keeps_defaults():
    """测试部分配置时未覆盖项保持默认值"""
    mock_excel = MagicMock()
    reader = ConfigSheetReader(mock_excel)

    mock_excel.get_sheet_by_name.return_value = MagicMock()
    mock_excel.sheet_to_df.return_value = (
        pd.DataFrame({
            "配置项": ["刷新间隔(秒)"],
            "值": [15],
        }),
        2, 2,
    )

    defaults = AppConfig()
    cfg = reader.read_config("配置", defaults)

    # 覆盖的项
    assert cfg.refresh_interval == 15
    # 未覆盖的项保持默认
    assert cfg.alert_popup_enabled == defaults.alert_popup_enabled
    assert cfg.news_max_rows == defaults.news_max_rows
