# -*- coding: utf-8 -*-
"""资金情绪 Sheet Handler 测试（mock 数据源）

验证 SentimentSheet.refresh() 的完整流程：
    1. 北向资金（akshare）
    2. 微博舆情（akshare）
    3. 新闻情绪（akshare）
    4. 股吧热门帖子（eastmoney）

每个数据块独立，单个失败不影响其他写入。
"""
import pandas as pd
from unittest.mock import MagicMock

from excel_monitor.config_loader import AppConfig
from excel_monitor.sheets.sentiment_sheet import SentimentSheet


def _make_sheet(cfg=None, data_mock=None):
    """构造一个 SentimentSheet 实例（mock excel 和 data）"""
    cfg = cfg or AppConfig()
    mock_excel = MagicMock()
    mock_data = data_mock or MagicMock()
    sheet = SentimentSheet("资金情绪", mock_excel, mock_data, cfg)
    sheet.sheet = MagicMock()
    return sheet, mock_excel, mock_data


def test_sentiment_refresh_calls_all_four_sources():
    """测试 refresh 调用全部 4 个数据方法"""
    sheet, _, mock_data = _make_sheet()

    mock_data.get_north_money.return_value = pd.DataFrame({
        "日期": ["2024-01-01"], "当日净流入": [1000000], "当日余额": [5000000],
    })
    mock_data.get_weibo_sentiment.return_value = pd.DataFrame({
        "股票代码": ["000001"], "股票名称": ["平安银行"],
        "微博舆情指数": [0.8],
    })
    mock_data.get_news_sentiment.return_value = pd.DataFrame({
        "日期": ["2024-01-01"], "新闻情绪指数": [0.5],
    })
    mock_data.get_guba_hot_posts.return_value = pd.DataFrame({
        "标题": ["帖子1"], "发布时间": ["10:00"],
    })

    sheet.refresh()

    mock_data.get_north_money.assert_called_once()
    mock_data.get_weibo_sentiment.assert_called_once()
    mock_data.get_news_sentiment.assert_called_once()
    mock_data.get_guba_hot_posts.assert_called_once()


def test_sentiment_refresh_writes_all_blocks():
    """测试 4 个数据块都被写入 Excel（write_df 调用 4 次）"""
    sheet, mock_excel, mock_data = _make_sheet()

    mock_data.get_north_money.return_value = pd.DataFrame({
        "日期": ["2024-01-01"], "当日净流入": [1000000],
    })
    mock_data.get_weibo_sentiment.return_value = pd.DataFrame({
        "股票代码": ["000001"], "微博舆情指数": [0.8],
    })
    mock_data.get_news_sentiment.return_value = pd.DataFrame({
        "日期": ["2024-01-01"], "新闻情绪指数": [0.5],
    })
    mock_data.get_guba_hot_posts.return_value = pd.DataFrame({
        "标题": ["帖子1"],
    })

    sheet.refresh()

    assert mock_excel.write_df.call_count == 4


def test_sentiment_refresh_truncates_by_max_rows():
    """测试 sentiment_max_rows 限制每个数据块条数"""
    cfg = AppConfig()
    cfg.sentiment_max_rows = 2
    sheet, mock_excel, mock_data = _make_sheet(cfg)

    # 北向资金返回 5 条，应截断为 2 条
    mock_data.get_north_money.return_value = pd.DataFrame({
        "日期": [f"2024-01-0{i}" for i in range(1, 6)],
        "当日净流入": [i * 1000 for i in range(5)],
    })
    mock_data.get_weibo_sentiment.return_value = pd.DataFrame()
    mock_data.get_news_sentiment.return_value = pd.DataFrame()
    mock_data.get_guba_hot_posts.return_value = pd.DataFrame()

    sheet.refresh()

    # 第一次 write_df 是北向资金，应只有 2 条
    written_df = mock_excel.write_df.call_args_list[0][0][1]
    assert len(written_df) == 2


def test_sentiment_refresh_empty_blocks_skipped():
    """测试空数据块不写入（write_df 仅对非空数据调用）"""
    sheet, mock_excel, mock_data = _make_sheet()

    mock_data.get_north_money.return_value = pd.DataFrame()
    mock_data.get_weibo_sentiment.return_value = pd.DataFrame()
    mock_data.get_news_sentiment.return_value = pd.DataFrame()
    mock_data.get_guba_hot_posts.return_value = pd.DataFrame()

    sheet.refresh()

    # 全部为空，write_df 不应被调用
    mock_excel.write_df.assert_not_called()


def test_sentiment_refresh_partial_failure():
    """测试部分数据源失败不影响其他数据块写入"""
    sheet, mock_excel, mock_data = _make_sheet()

    # 北向资金有数据，微博舆情空，新闻情绪有数据，股吧空
    mock_data.get_north_money.return_value = pd.DataFrame({
        "日期": ["2024-01-01"], "当日净流入": [1000000],
    })
    mock_data.get_weibo_sentiment.return_value = pd.DataFrame()
    mock_data.get_news_sentiment.return_value = pd.DataFrame({
        "日期": ["2024-01-01"], "新闻情绪指数": [0.5],
    })
    mock_data.get_guba_hot_posts.return_value = pd.DataFrame()

    sheet.refresh()

    # 只有 2 个非空块被写入
    assert mock_excel.write_df.call_count == 2


def test_sentiment_refresh_guba_uses_config_max_rows():
    """测试股吧热门帖子使用 guba_hot_max_rows 配置"""
    cfg = AppConfig()
    cfg.guba_hot_max_rows = 15
    sheet, _, mock_data = _make_sheet(cfg)

    mock_data.get_north_money.return_value = pd.DataFrame()
    mock_data.get_weibo_sentiment.return_value = pd.DataFrame()
    mock_data.get_news_sentiment.return_value = pd.DataFrame()
    mock_data.get_guba_hot_posts.return_value = pd.DataFrame({
        "标题": ["t1"],
    })

    sheet.refresh()

    mock_data.get_guba_hot_posts.assert_called_once_with(page_size=15)


def test_sentiment_refresh_row_offset_increases():
    """测试数据块按行偏移依次写入（不重叠）"""
    sheet, mock_excel, mock_data = _make_sheet()

    mock_data.get_north_money.return_value = pd.DataFrame({
        "日期": ["2024-01-01", "2024-01-02"], "当日净流入": [1, 2],
    })
    mock_data.get_weibo_sentiment.return_value = pd.DataFrame({
        "股票代码": ["000001"], "微博舆情指数": [0.8],
    })
    mock_data.get_news_sentiment.return_value = pd.DataFrame()
    mock_data.get_guba_hot_posts.return_value = pd.DataFrame()

    sheet.refresh()

    # 北向 2 行，从 row=1 开始
    north_call = mock_excel.write_df.call_args_list[0]
    assert north_call[0][2] == 1  # start_row

    # 微博从 row = 2 + 3 = 5 开始（len(north)=2, offset += 2+3=5）
    weibo_call = mock_excel.write_df.call_args_list[1]
    assert weibo_call[0][2] == 5


def test_sentiment_init_logs_only():
    """测试 init 不触发数据获取"""
    sheet, _, mock_data = _make_sheet()

    sheet.init()

    mock_data.get_north_money.assert_not_called()
