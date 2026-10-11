# -*- coding: utf-8 -*-
"""Sheet Handler 逻辑测试（mock 数据源）"""
import pandas as pd
from unittest.mock import MagicMock

from excel_monitor.config_loader import AppConfig
from excel_monitor.core.data_provider import DataProvider
from excel_monitor.sheets.market_overview import MarketOverviewSheet
from excel_monitor.sheets.detailed_quotes import DetailedQuotesSheet
from excel_monitor.sheets.news_sheet import NewsSheet
from excel_monitor.sheets.custom_watch import CustomWatchSheet


def test_market_overview_refresh_with_mock():
    """测试大盘 Sheet 刷新逻辑（mock 数据源）"""
    mock_excel = MagicMock()
    mock_data = MagicMock()

    mock_data.get_index_realtime.return_value = pd.DataFrame({
        "名称": ["上证指数", "深证成指"],
        "最新": [3200.0, 10500.0],
        "涨幅": [0.5, -0.3],
    })
    mock_data.get_industry_boards.return_value = pd.DataFrame({
        "名称": ["银行", "证券"], "涨幅": [1.2, -0.5],
    })
    mock_data.get_concept_boards.return_value = pd.DataFrame()
    mock_data.get_limit_up_pool.return_value = pd.DataFrame()

    sheet = MarketOverviewSheet("大盘", mock_excel, mock_data)
    sheet.sheet = MagicMock()

    sheet.refresh()

    mock_data.get_index_realtime.assert_called_once()
    mock_data.get_industry_boards.assert_called_once()


def test_detailed_quotes_refresh_with_mock():
    """测试详细行情 Sheet 刷新逻辑"""
    mock_excel = MagicMock()
    mock_data = MagicMock()

    mock_excel.sheet_to_df.return_value = (
        pd.DataFrame({
            "代码": ["000001", "600000"],
            "名称": ["平安银行", "浦发银行"],
        }),
        3, 2,
    )
    mock_data.get_stock_realtime.return_value = pd.DataFrame({
        "代码": ["000001", "600000"],
        "名称": ["平安银行", "浦发银行"],
        "最新": [10.5, 8.3],
        "涨幅": [2.1, -0.5],
        "时间": ["10:30:00", "10:30:00"],
    })
    mock_data.get_billboard.return_value = pd.DataFrame()
    mock_data.get_realtime_change.return_value = pd.DataFrame()

    sheet = DetailedQuotesSheet("详细行情", mock_excel, mock_data)
    sheet.sheet = MagicMock()

    sheet.init()
    sheet.refresh()

    mock_data.get_stock_realtime.assert_called_once()


def test_news_sheet_refresh_with_mock():
    """测试新闻 Sheet 刷新逻辑"""
    mock_excel = MagicMock()
    mock_data = MagicMock()

    mock_data.get_news_cls.return_value = pd.DataFrame({
        "发布时间": ["10:30", "10:25"],
        "标题": ["央行降息", "GDP增长5%"],
    })
    mock_data.get_news_js.return_value = pd.DataFrame({
        "时间": ["10:28"],
        "内容": ["美国CPI数据公布"],
    })

    sheet = NewsSheet("新闻", mock_excel, mock_data)
    sheet.sheet = MagicMock()

    sheet.refresh()

    mock_data.get_news_cls.assert_called_once()
    mock_data.get_news_js.assert_called_once()


def test_custom_watch_refresh_with_mock():
    """测试个性定制看盘 Sheet 刷新逻辑（无预警条件）"""
    mock_excel = MagicMock()
    real_dp = DataProvider()
    mock_data = MagicMock(wraps=real_dp)

    mock_excel.sheet_to_df.return_value = (
        pd.DataFrame({
            "代码": ["中国平安", "贵州茅台"],
            "名称": ["中国平安", "贵州茅台"],
        }),
        3, 2,
    )
    mock_data.get_stock_realtime.return_value = pd.DataFrame({
        "代码": ["中国平安", "贵州茅台"],
        "名称": ["中国平安", "贵州茅台"],
        "最新": [45.0, 1800.0],
        "涨幅": [1.5, 0.8],
        "时间": ["10:30:00", "10:30:00"],
    })

    config = AppConfig()
    sheet = CustomWatchSheet("个性定制看盘", mock_excel, mock_data, config)
    sheet.sheet = MagicMock()

    sheet.init()
    sheet.refresh()

    mock_data.get_stock_realtime.assert_called_once()
    # 无预警条件，不应高亮
    mock_excel.highlight_row.assert_not_called()


def test_custom_watch_alert_triggered():
    """测试预警触发：涨跌幅超限 → 高亮 + 弹窗"""
    mock_excel = MagicMock()
    real_dp = DataProvider()
    mock_data = MagicMock(wraps=real_dp)

    # Excel 中有预警条件：中国平安 涨跌幅上限 3%
    mock_excel.sheet_to_df.return_value = (
        pd.DataFrame({
            "代码": ["中国平安", "贵州茅台"],
            "名称": ["中国平安", "贵州茅台"],
            "涨跌幅下限": [None, None],
            "涨跌幅上限": [3.0, None],
            "价格下限": [None, None],
            "价格上限": [None, None],
        }),
        3, 6,
    )
    # 实时行情：中国平安涨 5%（超限），贵州茅台涨 0.8%（正常）
    mock_data.get_stock_realtime.return_value = pd.DataFrame({
        "代码": ["中国平安", "贵州茅台"],
        "名称": ["中国平安", "贵州茅台"],
        "最新": [45.0, 1800.0],
        "涨幅": [5.0, 0.8],
        "时间": ["10:30:00", "10:30:00"],
    })

    config = AppConfig()
    config.alert_popup_enabled = False  # 测试中禁用弹窗
    sheet = CustomWatchSheet("个性定制看盘", mock_excel, mock_data, config)
    sheet.sheet = MagicMock()

    sheet.init()
    sheet.refresh()

    # 验证预警条件被加载
    assert len(sheet._alert_conditions) == 1
    assert sheet._alert_conditions[0].code == "中国平安"

    # 验证高亮被调用（至少 1 次：中国平安）
    assert mock_excel.highlight_row.call_count >= 1

    # 验证清除高亮也被调用（每次刷新前清除旧高亮）
    mock_excel.clear_highlight.assert_called_once()


def test_custom_watch_alert_price_triggered():
    """测试价格预警触发"""
    mock_excel = MagicMock()
    real_dp = DataProvider()
    mock_data = MagicMock(wraps=real_dp)

    mock_excel.sheet_to_df.return_value = (
        pd.DataFrame({
            "代码": ["贵州茅台"],
            "名称": ["贵州茅台"],
            "涨跌幅下限": [None],
            "涨跌幅上限": [None],
            "价格下限": [None],
            "价格上限": [2000.0],
        }),
        2, 6,
    )
    # 茅台价格 2100，超过 2000 上限
    mock_data.get_stock_realtime.return_value = pd.DataFrame({
        "代码": ["贵州茅台"],
        "名称": ["贵州茅台"],
        "最新": [2100.0],
        "涨幅": [1.0],
        "时间": ["10:30:00"],
    })

    config = AppConfig()
    config.alert_popup_enabled = False
    sheet = CustomWatchSheet("个性定制看盘", mock_excel, mock_data, config)
    sheet.sheet = MagicMock()

    sheet.init()
    sheet.refresh()

    assert len(sheet._alert_conditions) == 1
    assert mock_excel.highlight_row.call_count == 1


def test_custom_watch_no_alert_when_within_range():
    """测试未触发预警：行情在条件范围内"""
    mock_excel = MagicMock()
    real_dp = DataProvider()
    mock_data = MagicMock(wraps=real_dp)

    mock_excel.sheet_to_df.return_value = (
        pd.DataFrame({
            "代码": ["中国平安"],
            "名称": ["中国平安"],
            "涨跌幅下限": [-3.0],
            "涨跌幅上限": [5.0],
            "价格下限": [40.0],
            "价格上限": [50.0],
        }),
        2, 6,
    )
    # 涨跌幅 1%，价格 45 → 都在范围内
    mock_data.get_stock_realtime.return_value = pd.DataFrame({
        "代码": ["中国平安"],
        "名称": ["中国平安"],
        "最新": [45.0],
        "涨幅": [1.0],
        "时间": ["10:30:00"],
    })

    config = AppConfig()
    config.alert_popup_enabled = False
    sheet = CustomWatchSheet("个性定制看盘", mock_excel, mock_data, config)
    sheet.sheet = MagicMock()

    sheet.init()
    sheet.refresh()

    # 有预警条件但未触发
    assert len(sheet._alert_conditions) == 1
    mock_excel.highlight_row.assert_not_called()


def test_custom_watch_reload_after_n_refreshes():
    """测试每 N 次刷新后重新读取 Excel 配置"""
    mock_excel = MagicMock()
    real_dp = DataProvider()
    mock_data = MagicMock(wraps=real_dp)

    # 初始：2 只股票
    initial_df = pd.DataFrame({
        "代码": ["中国平安", "贵州茅台"],
        "名称": ["中国平安", "贵州茅台"],
    })
    # 刷新后：用户修改为 3 只股票（模拟实时修改）
    updated_df = pd.DataFrame({
        "代码": ["中国平安", "贵州茅台", "宁德时代"],
        "名称": ["中国平安", "贵州茅台", "宁德时代"],
    })

    # sheet_to_df 在 init 时调用一次，refresh 2 重载时再调用一次
    # refresh 1 不重载所以不调用 sheet_to_df
    mock_excel.sheet_to_df.side_effect = [
        (initial_df, 3, 2),  # init
        (updated_df, 4, 2),  # refresh 2 (重载，config_reload_interval=2)
    ]

    mock_data.get_stock_realtime.return_value = pd.DataFrame({
        "代码": ["中国平安", "贵州茅台"],
        "名称": ["中国平安", "贵州茅台"],
        "最新": [45.0, 1800.0],
        "涨幅": [1.5, 0.8],
        "时间": ["10:30:00", "10:30:00"],
    })

    config = AppConfig()
    config.alert_popup_enabled = False
    config.config_reload_interval = 2  # 每 2 次刷新重载
    sheet = CustomWatchSheet("个性定制看盘", mock_excel, mock_data, config)
    sheet.sheet = MagicMock()

    # init: 读取初始 2 只股票
    sheet.init()
    assert len(sheet._stock_codes) == 2

    # refresh 1: 不重载（count=1, 1%2!=0）
    sheet.refresh()
    assert len(sheet._stock_codes) == 2

    # refresh 2: 重载（count=2, 2%2==0），应读到 3 只股票
    sheet.refresh()
    assert len(sheet._stock_codes) == 3
    assert "宁德时代" in sheet._stock_codes


def test_custom_watch_kline_button_added():
    """测试 init 时画K线按钮被添加"""
    mock_excel = MagicMock()
    real_dp = DataProvider()
    mock_data = MagicMock(wraps=real_dp)

    mock_excel.sheet_to_df.return_value = (
        pd.DataFrame({
            "代码": ["中国平安"],
            "名称": ["中国平安"],
        }),
        2, 2,
    )

    config = AppConfig()
    sheet = CustomWatchSheet("个性定制看盘", mock_excel, mock_data, config)
    sheet.sheet = MagicMock()

    sheet.init()

    # 验证 add_button 被调用
    mock_excel.add_button.assert_called_once()
    call_kwargs = mock_excel.add_button.call_args
    assert call_kwargs[1]["text"] == "画K线"
    assert call_kwargs[1]["macro"] == "DrawKLineMacro"


def test_custom_watch_kline_trigger_via_polling():
    """测试轮询模式：D21 含 DRAW 时触发画K线"""
    mock_excel = MagicMock()
    real_dp = DataProvider()
    mock_data = MagicMock(wraps=real_dp)

    mock_excel.sheet_to_df.return_value = (
        pd.DataFrame({
            "代码": ["中国平安", "贵州茅台"],
            "名称": ["中国平安", "贵州茅台"],
        }),
        3, 2,
    )
    mock_data.get_stock_realtime.return_value = pd.DataFrame({
        "代码": ["中国平安", "贵州茅台"],
        "名称": ["中国平安", "贵州茅台"],
        "最新": [45.0, 1800.0],
        "涨幅": [1.5, 0.8],
        "时间": ["10:30:00", "10:30:00"],
    })

    # 模拟 K 线数据
    kline_df = pd.DataFrame({
        "Open": [44.0, 44.5, 45.0],
        "High": [45.0, 45.5, 46.0],
        "Low": [43.5, 44.0, 44.5],
        "Close": [44.5, 45.0, 45.5],
        "Volume": [100000, 120000, 90000],
    }, index=pd.date_range("2024-01-01", periods=3))
    mock_data.get_kline_data.return_value = kline_df

    # mock KLineChart.draw 返回图片路径
    config = AppConfig()
    config.alert_popup_enabled = False
    sheet = CustomWatchSheet("个性定制看盘", mock_excel, mock_data, config)
    sheet.sheet = MagicMock()
    sheet._kline_chart = MagicMock()
    sheet._kline_chart.draw.return_value = "/tmp/kline_test.png"

    # init
    sheet.init()

    # 模拟用户在 B21 输入行号 2，D21 输入 DRAW
    # get_cell_value: 第一次调用(21,4)=trigger, 第二次(21,2)=row_num,
    # 第三次(row_num,1)=code, 第四次(row_num,2)=name
    mock_excel.get_cell_value.side_effect = [
        "DRAW",     # D21 trigger
        2,          # B21 row number
        "中国平安",  # A2 code
        "中国平安",  # B2 name
    ]

    # refresh 应检测到 trigger 并画K线
    sheet.refresh()

    # 验证 K 线数据被获取
    mock_data.get_kline_data.assert_called_once()
    # 验证图片被插入
    mock_excel.insert_image.assert_called_once()
    # 验证 draw 被调用
    sheet._kline_chart.draw.assert_called_once()


def test_custom_watch_kline_invalid_row():
    """测试画K线时行号无效的情况"""
    mock_excel = MagicMock()
    real_dp = DataProvider()
    mock_data = MagicMock(wraps=real_dp)

    mock_excel.sheet_to_df.return_value = (
        pd.DataFrame({
            "代码": ["中国平安"],
            "名称": ["中国平安"],
        }),
        2, 2,
    )
    mock_data.get_stock_realtime.return_value = pd.DataFrame({
        "代码": ["中国平安"],
        "名称": ["中国平安"],
        "最新": [45.0],
        "涨幅": [1.5],
        "时间": ["10:30:00"],
    })

    config = AppConfig()
    config.alert_popup_enabled = False
    sheet = CustomWatchSheet("个性定制看盘", mock_excel, mock_data, config)
    sheet.sheet = MagicMock()

    sheet.init()

    # B21 = "abc"（无效行号）
    mock_excel.get_cell_value.side_effect = [
        "DRAW",   # D21 trigger
        "abc",    # B21 invalid row
    ]

    # 不应抛异常，只是 warning
    sheet.refresh()

    # K 线数据不应被获取
    mock_data.get_kline_data.assert_not_called()
    # 图片不应被插入
    mock_excel.insert_image.assert_not_called()


def test_custom_watch_kline_no_trigger():
    """测试无触发信号时不画K线"""
    mock_excel = MagicMock()
    real_dp = DataProvider()
    mock_data = MagicMock(wraps=real_dp)

    mock_excel.sheet_to_df.return_value = (
        pd.DataFrame({
            "代码": ["中国平安"],
            "名称": ["中国平安"],
        }),
        2, 2,
    )
    mock_data.get_stock_realtime.return_value = pd.DataFrame({
        "代码": ["中国平安"],
        "名称": ["中国平安"],
        "最新": [45.0],
        "涨幅": [1.5],
        "时间": ["10:30:00"],
    })

    config = AppConfig()
    config.alert_popup_enabled = False
    sheet = CustomWatchSheet("个性定制看盘", mock_excel, mock_data, config)
    sheet.sheet = MagicMock()

    sheet.init()

    # D21 = None（无触发）
    mock_excel.get_cell_value.return_value = None

    sheet.refresh()

    # K 线数据不应被获取
    mock_data.get_kline_data.assert_not_called()
    mock_excel.insert_image.assert_not_called()
