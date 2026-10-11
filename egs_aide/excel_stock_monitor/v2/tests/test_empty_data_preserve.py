# -*- coding: utf-8 -*-
"""空数据保持不变测试

验证核心需求：数据源未刷到（返回空 DataFrame）时，
不清除 Excel 中的旧数据，保持上一次成功刷新的内容不变。

覆盖：
    1. BaseSheet._write 对空 df 的保护（不清除、不写入）
    2. 各 Sheet refresh 空数据时不调用 clear_range
    3. 首次刷新成功 → 后续刷新失败 → 旧数据应保留
"""
import pandas as pd
from unittest.mock import MagicMock

from excel_monitor.config_loader import AppConfig
from excel_monitor.sheets.market_overview import MarketOverviewSheet
from excel_monitor.sheets.detailed_quotes import DetailedQuotesSheet
from excel_monitor.sheets.news_sheet import NewsSheet
from excel_monitor.sheets.custom_watch import CustomWatchSheet
from excel_monitor.sheets.sentiment_sheet import SentimentSheet


# =====================================================================
# 1. BaseSheet._write 空数据保护
# =====================================================================
def test_base_write_empty_df_does_not_clear():
    """_write 收到空 df 时不应调用 clear_range（保护旧数据）"""
    sheet = SentimentSheet("资金情绪", MagicMock(), MagicMock())
    sheet.sheet = MagicMock()
    empty_df = pd.DataFrame()

    sheet._write(empty_df, start_row=1, start_col=1)

    # 不应清除、不应写入
    sheet.excel_mgr.clear_range.assert_not_called()
    sheet.excel_mgr.write_df.assert_not_called()


def test_base_write_none_df_does_not_clear():
    """_write 收到 None 时不应调用 clear_range"""
    sheet = SentimentSheet("资金情绪", MagicMock(), MagicMock())
    sheet.sheet = MagicMock()

    sheet._write(None, start_row=1, start_col=1)

    sheet.excel_mgr.clear_range.assert_not_called()
    sheet.excel_mgr.write_df.assert_not_called()


def test_base_write_non_empty_df_clears_then_writes():
    """_write 收到非空 df 时应先清除后写入（正常流程）"""
    sheet = SentimentSheet("资金情绪", MagicMock(), MagicMock())
    sheet.sheet = MagicMock()
    df = pd.DataFrame({"A": [1, 2]})

    sheet._write(df, start_row=1, start_col=1)

    sheet.excel_mgr.clear_range.assert_called_once()
    sheet.excel_mgr.write_df.assert_called_once()


# =====================================================================
# 2. 各 Sheet 空数据时不清除
# =====================================================================
def test_market_overview_empty_data_no_clear():
    """大盘 Sheet：所有数据源返回空时，clear_range 不应被调用"""
    mock_excel = MagicMock()
    mock_data = MagicMock()
    mock_data.get_index_realtime.return_value = pd.DataFrame()
    mock_data.get_industry_boards.return_value = pd.DataFrame()
    mock_data.get_concept_boards.return_value = pd.DataFrame()
    mock_data.get_limit_up_pool.return_value = pd.DataFrame()

    sheet = MarketOverviewSheet("大盘", mock_excel, mock_data)
    sheet.sheet = MagicMock()
    sheet.refresh()

    mock_excel.clear_range.assert_not_called()
    mock_excel.write_df.assert_not_called()


def test_detailed_quotes_empty_data_no_clear():
    """详细行情 Sheet：数据源返回空时，clear_range 不应被调用"""
    mock_excel = MagicMock()
    mock_data = MagicMock()
    mock_excel.sheet_to_df.return_value = (
        pd.DataFrame({"代码": ["中国平安"], "名称": ["中国平安"]}), 2, 2,
    )
    mock_data.get_stock_realtime.return_value = pd.DataFrame()
    mock_data.get_billboard.return_value = pd.DataFrame()
    mock_data.get_realtime_change.return_value = pd.DataFrame()

    sheet = DetailedQuotesSheet("详细行情", mock_excel, mock_data)
    sheet.sheet = MagicMock()
    sheet.init()
    sheet.refresh()

    mock_excel.clear_range.assert_not_called()
    mock_excel.write_df.assert_not_called()


def test_news_sheet_empty_data_no_clear():
    """新闻 Sheet：数据源返回空时，clear_range 不应被调用"""
    mock_excel = MagicMock()
    mock_data = MagicMock()
    mock_data.get_news_cls.return_value = pd.DataFrame()
    mock_data.get_news_js.return_value = pd.DataFrame()

    sheet = NewsSheet("新闻", mock_excel, mock_data)
    sheet.sheet = MagicMock()
    sheet.refresh()

    mock_excel.clear_range.assert_not_called()
    mock_excel.write_df.assert_not_called()


def test_sentiment_sheet_empty_data_no_clear():
    """资金情绪 Sheet：所有数据源返回空时，clear_range 不应被调用"""
    mock_excel = MagicMock()
    mock_data = MagicMock()
    mock_data.get_north_money.return_value = pd.DataFrame()
    mock_data.get_weibo_sentiment.return_value = pd.DataFrame()
    mock_data.get_news_sentiment.return_value = pd.DataFrame()
    mock_data.get_guba_hot_posts.return_value = pd.DataFrame()

    sheet = SentimentSheet("资金情绪", mock_excel, mock_data)
    sheet.sheet = MagicMock()
    sheet.refresh()

    mock_excel.clear_range.assert_not_called()
    mock_excel.write_df.assert_not_called()


def test_custom_watch_empty_data_no_clear():
    """个性定制看盘 Sheet：行情返回空时，clear_range 不应被调用"""
    mock_excel = MagicMock()
    mock_data = MagicMock()
    mock_excel.sheet_to_df.return_value = (
        pd.DataFrame({"代码": ["中国平安"], "名称": ["中国平安"]}), 2, 2,
    )
    mock_data.get_stock_realtime.return_value = pd.DataFrame()

    cfg = AppConfig()
    cfg.alert_popup_enabled = False
    sheet = CustomWatchSheet("个性定制看盘", mock_excel, mock_data, cfg)
    sheet.sheet = MagicMock()
    sheet.init()
    sheet.refresh()

    mock_excel.clear_range.assert_not_called()
    mock_excel.write_df.assert_not_called()


# =====================================================================
# 3. 部分数据块空时，非空块正常写入、空块保留旧数据
# =====================================================================
def test_market_overview_partial_empty_preserves_others():
    """大盘 Sheet：指数空、行业有数据 → 行业正常写入，指数区域不清除"""
    mock_excel = MagicMock()
    mock_data = MagicMock()
    mock_data.get_index_realtime.return_value = pd.DataFrame()  # 指数空
    mock_data.get_industry_boards.return_value = pd.DataFrame({
        "名称": ["银行"], "涨幅": [1.2],
    })
    mock_data.get_concept_boards.return_value = pd.DataFrame()
    mock_data.get_limit_up_pool.return_value = pd.DataFrame()

    sheet = MarketOverviewSheet("大盘", mock_excel, mock_data)
    sheet.sheet = MagicMock()
    sheet.refresh()

    # 只有行业板块写入（1 次），指数/概念/涨停都不写入
    assert mock_excel.write_df.call_count == 1
    # clear_range 只因行业板块的 _write 被调用 1 次
    assert mock_excel.clear_range.call_count == 1


def test_sentiment_partial_empty_preserves_others():
    """资金情绪 Sheet：北向有数据、微博空 → 北向写入，微博区域不清除"""
    mock_excel = MagicMock()
    mock_data = MagicMock()
    mock_data.get_north_money.return_value = pd.DataFrame({
        "日期": ["2024-01-01"], "当日净流入": [100],
    })
    mock_data.get_weibo_sentiment.return_value = pd.DataFrame()  # 微博空
    mock_data.get_news_sentiment.return_value = pd.DataFrame()
    mock_data.get_guba_hot_posts.return_value = pd.DataFrame()

    sheet = SentimentSheet("资金情绪", mock_excel, mock_data)
    sheet.sheet = MagicMock()
    sheet.refresh()

    # 只有北向资金写入 1 次
    assert mock_excel.write_df.call_count == 1
    assert mock_excel.clear_range.call_count == 1


# =====================================================================
# 4. 连续刷新场景：第一次成功 → 第二次失败 → 旧数据保留
# =====================================================================
def test_consecutive_refresh_success_then_failure_preserves():
    """连续刷新：第1次成功写入，第2次数据源失败 → 不清除，旧数据保留"""
    mock_excel = MagicMock()
    mock_data = MagicMock()
    sheet = SentimentSheet("资金情绪", mock_excel, mock_data)
    sheet.sheet = MagicMock()

    # 第1次：北向资金有数据
    mock_data.get_north_money.return_value = pd.DataFrame({
        "日期": ["2024-01-01"], "当日净流入": [1000000],
    })
    mock_data.get_weibo_sentiment.return_value = pd.DataFrame()
    mock_data.get_news_sentiment.return_value = pd.DataFrame()
    mock_data.get_guba_hot_posts.return_value = pd.DataFrame()

    sheet.refresh()
    first_write_count = mock_excel.write_df.call_count
    assert first_write_count == 1

    # 第2次：所有数据源失败（返回空）
    mock_data.get_north_money.return_value = pd.DataFrame()
    sheet.refresh()

    # write_df 调用次数不变（第2次没写入新数据）
    assert mock_excel.write_df.call_count == first_write_count
    # 第2次没有新增 clear_range 调用
    assert mock_excel.clear_range.call_count == first_write_count
