# -*- coding: utf-8 -*-
"""DataProvider 测试：纯逻辑方法 + fallback 机制 + 新数据方法"""
import pandas as pd
from unittest.mock import MagicMock, patch

from excel_monitor.config_loader import AppConfig
from excel_monitor.core.data_provider import DataProvider


# =====================================================================
# 纯逻辑方法测试
# =====================================================================
def test_clean_stock_code_removes_postfix():
    """测试去除代码后缀 (.SZ / .SH)"""
    dp = DataProvider()
    assert dp.clean_code("000001.SZ") == "000001"
    assert dp.clean_code("600000.SH") == "600000"
    assert dp.clean_code("300001") == "300001"


def test_filter_columns():
    """测试按指定列过滤 DataFrame"""
    dp = DataProvider()
    df = pd.DataFrame({
        "代码": ["000001"], "名称": ["平安银行"],
        "最新": [10.5], "涨幅": [2.3], "多余列": [0],
    })
    result = dp.filter_columns(df, ["代码", "名称", "最新", "涨幅"])
    assert list(result.columns) == ["代码", "名称", "最新", "涨幅"]
    assert "多余列" not in result.columns


def test_rename_columns():
    """测试列名重命名映射"""
    dp = DataProvider()
    df = pd.DataFrame({"最新": [10.5], "涨幅": [2.3]})
    result = dp.rename_columns(df, {"最新": "最新价", "涨幅": "涨跌幅"})
    assert "最新价" in result.columns
    assert "涨跌幅" in result.columns


# =====================================================================
# Fallback 机制测试
# =====================================================================
def test_try_with_fallback_primary_success():
    """测试 fallback: 主源成功时不调用备选源"""
    dp = DataProvider()
    primary = MagicMock(return_value=pd.DataFrame({"a": [1]}))
    backup1 = MagicMock(return_value=pd.DataFrame({"b": [2]}))
    backup2 = MagicMock(return_value=pd.DataFrame({"c": [3]}))

    df = dp._try_with_fallback(
        primary_func=primary,
        fallback_chain=[("akshare", backup1), ("tencent", backup2)],
        args=("600000",),
        name="test",
    )

    assert not df.empty
    assert "a" in df.columns
    primary.assert_called_once_with("600000")
    backup1.assert_not_called()
    backup2.assert_not_called()


def test_try_with_fallback_primary_empty_uses_backup():
    """测试 fallback: 主源返回空时尝试备选源"""
    dp = DataProvider()
    primary = MagicMock(return_value=pd.DataFrame())
    backup1 = MagicMock(return_value=pd.DataFrame({"a": [1]}))
    backup2 = MagicMock(return_value=pd.DataFrame({"b": [2]}))

    df = dp._try_with_fallback(
        primary_func=primary,
        fallback_chain=[("akshare", backup1), ("tencent", backup2)],
        args=("600000",),
        name="test",
    )

    assert not df.empty
    assert "a" in df.columns  # 用第一个备选源的结果
    primary.assert_called_once()
    backup1.assert_called_once()
    backup2.assert_not_called()


def test_try_with_fallback_primary_exception_uses_backup():
    """测试 fallback: 主源抛异常时尝试备选源"""
    dp = DataProvider()
    primary = MagicMock(side_effect=Exception("network error"))
    backup1 = MagicMock(return_value=pd.DataFrame())
    backup2 = MagicMock(return_value=pd.DataFrame({"a": [1]}))

    df = dp._try_with_fallback(
        primary_func=primary,
        fallback_chain=[("akshare", backup1), ("tencent", backup2)],
        args=("600000",),
        name="test",
    )

    assert not df.empty
    assert "a" in df.columns  # 用第二个备选源（第一个返回空）
    primary.assert_called_once()
    backup1.assert_called_once()
    backup2.assert_called_once()


def test_try_with_fallback_all_fail():
    """测试 fallback: 所有源都失败时返回空 DataFrame"""
    dp = DataProvider()
    primary = MagicMock(side_effect=Exception("error"))
    backup1 = MagicMock(side_effect=Exception("error"))
    backup2 = MagicMock(return_value=pd.DataFrame())

    df = dp._try_with_fallback(
        primary_func=primary,
        fallback_chain=[("akshare", backup1), ("tencent", backup2)],
        args=("600000",),
        name="test",
    )

    assert df.empty


def test_try_with_fallback_respects_enabled_sources():
    """测试 fallback: 未启用的源不会被调用"""
    dp = DataProvider()
    # 只启用 akshare
    dp.enabled_sources = ["akshare"]
    primary = MagicMock(return_value=pd.DataFrame())
    backup_akshare = MagicMock(return_value=pd.DataFrame({"a": [1]}))
    backup_tencent = MagicMock(return_value=pd.DataFrame({"b": [2]}))

    df = dp._try_with_fallback(
        primary_func=primary,
        fallback_chain=[("tencent", backup_tencent), ("akshare", backup_akshare)],
        args=("600000",),
        name="test",
    )

    # tencent 未启用，应被跳过；akshare 启用，应被调用
    assert not df.empty
    assert "a" in df.columns
    backup_tencent.assert_not_called()
    backup_akshare.assert_called_once()


# =====================================================================
# 数据方法测试（mock qstock + 备选源）
# =====================================================================
def test_get_stock_realtime_uses_qstock_first():
    """测试 get_stock_realtime 优先使用 qstock"""
    dp = DataProvider()
    fake_df = pd.DataFrame({
        "代码": ["600000"], "名称": ["浦发银行"],
        "最新": [10.5], "涨幅": [1.2],
    })

    with patch("excel_monitor.core.data_provider._get_qstock") as mock_qs:
        mock_qs.return_value.realtime_data.return_value = fake_df
        # mock 备选源（不应被调用）
        dp.backup.akshare_stock_realtime = MagicMock()
        dp.backup.tencent_stock_realtime = MagicMock()

        df = dp.get_stock_realtime(["600000"])

        assert not df.empty
        assert "代码" in df.columns
        dp.backup.akshare_stock_realtime.assert_not_called()


def test_get_stock_realtime_fallback_to_akshare():
    """测试 get_stock_realtime: qstock 失败时 fallback 到 akshare"""
    dp = DataProvider()
    fake_df = pd.DataFrame({
        "代码": ["600000"], "名称": ["浦发银行"],
        "最新": [10.5], "涨幅": [1.2],
    })

    with patch("excel_monitor.core.data_provider._get_qstock") as mock_qs:
        # qstock 抛异常
        mock_qs.return_value.realtime_data.side_effect = Exception("qstock error")
        # akshare 备选源返回数据
        dp.backup.akshare_stock_realtime = MagicMock(return_value=fake_df)
        dp.backup.tencent_stock_realtime = MagicMock()

        df = dp.get_stock_realtime(["600000"])

        assert not df.empty
        dp.backup.akshare_stock_realtime.assert_called_once()
        dp.backup.tencent_stock_realtime.assert_not_called()  # akshare 成功，不调 tencent


def test_get_stock_realtime_fallback_chain_exhausted():
    """测试 get_stock_realtime: 所有源都失败时返回空"""
    dp = DataProvider()
    with patch("excel_monitor.core.data_provider._get_qstock") as mock_qs:
        mock_qs.return_value.realtime_data.side_effect = Exception("error")
        dp.backup.akshare_stock_realtime = MagicMock(return_value=pd.DataFrame())
        dp.backup.tencent_stock_realtime = MagicMock(side_effect=Exception("err"))
        dp.backup.eastmoney_stock_realtime = MagicMock(return_value=pd.DataFrame())
        dp.backup.efinance_stock_realtime = MagicMock(return_value=pd.DataFrame())

        df = dp.get_stock_realtime(["600000"])
        assert df.empty


def test_get_news_cls_uses_qstock_first():
    """测试 get_news_cls: 优先用 qstock"""
    dp = DataProvider()
    fake_df = pd.DataFrame({
        "标题": ["央行降息"], "发布时间": ["2024-01-01 10:30"],
        "发布日期": ["2024-01-01"],
    })
    with patch("excel_monitor.core.data_provider._get_qstock") as mock_qs:
        mock_qs.return_value.news_data.return_value = fake_df
        dp.backup.akshare_news_cls = MagicMock()

        df = dp.get_news_cls()
        assert not df.empty
        dp.backup.akshare_news_cls.assert_not_called()


def test_get_kline_data_fallback_to_tencent():
    """测试 get_kline_data: qstock 失败时 fallback 到 tencent"""
    dp = DataProvider()
    fake_df = pd.DataFrame({
        "Open": [10.0], "High": [10.5], "Low": [9.8],
        "Close": [10.2], "Volume": [100000],
    }, index=pd.date_range("2024-01-01", periods=1))

    with patch("excel_monitor.core.data_provider._get_qstock") as mock_qs:
        mock_qs.return_value.get_data.side_effect = Exception("qstock error")
        dp.backup.tencent_kline = MagicMock(return_value=fake_df)
        dp.backup.eastmoney_kline = MagicMock()
        dp.backup.akshare_kline = MagicMock()

        df = dp.get_kline_data("600000", count=10)

        assert not df.empty
        assert "Open" in df.columns
        dp.backup.tencent_kline.assert_called_once()
        dp.backup.eastmoney_kline.assert_not_called()


# =====================================================================
# 新增数据方法测试
# =====================================================================
def test_get_north_money_calls_akshare():
    """测试 get_north_money 调用 akshare"""
    dp = DataProvider()
    fake_df = pd.DataFrame({
        "日期": ["2024-01-01"], "当日净流入": [10000000000],
    })
    dp.backup.akshare_north_money = MagicMock(return_value=fake_df)

    df = dp.get_north_money()
    assert not df.empty
    dp.backup.akshare_north_money.assert_called_once()


def test_get_north_money_returns_empty_when_akshare_disabled():
    """测试 get_north_money: akshare 未启用时返回空"""
    cfg = AppConfig()
    cfg.enabled_backup_sources = ["tencent"]  # 不含 akshare
    dp = DataProvider(cfg)
    dp.backup.akshare_north_money = MagicMock()

    df = dp.get_north_money()
    assert df.empty
    dp.backup.akshare_north_money.assert_not_called()


def test_get_stock_money_flow_calls_eastmoney():
    """测试 get_stock_money_flow 调用 eastmoney"""
    dp = DataProvider()
    fake_df = pd.DataFrame({"日期": ["2024-01-01"], "主力净流入": [1000000]})
    dp.backup.eastmoney_money_flow = MagicMock(return_value=fake_df)

    df = dp.get_stock_money_flow("600000")
    assert not df.empty
    dp.backup.eastmoney_money_flow.assert_called_once_with("600000")


def test_get_weibo_sentiment_calls_akshare():
    """测试 get_weibo_sentiment 调用 akshare"""
    dp = DataProvider()
    fake_df = pd.DataFrame({"股票代码": ["600000"], "微博舆情指数": [85.5]})
    dp.backup.akshare_weibo_sentiment = MagicMock(return_value=fake_df)

    df = dp.get_weibo_sentiment()
    assert not df.empty
    dp.backup.akshare_weibo_sentiment.assert_called_once()


def test_get_news_sentiment_calls_akshare():
    """测试 get_news_sentiment 调用 akshare"""
    dp = DataProvider()
    fake_df = pd.DataFrame({"日期": ["2024-01-01"], "新闻情绪指数": [60.5]})
    dp.backup.akshare_news_sentiment = MagicMock(return_value=fake_df)

    df = dp.get_news_sentiment()
    assert not df.empty
    dp.backup.akshare_news_sentiment.assert_called_once()


def test_get_guba_hot_posts_calls_eastmoney():
    """测试 get_guba_hot_posts 调用 eastmoney"""
    dp = DataProvider()
    fake_df = pd.DataFrame({"标题": ["帖子1"], "阅读量": [100]})
    dp.backup.eastmoney_guba_hot = MagicMock(return_value=fake_df)

    df = dp.get_guba_hot_posts(page_size=10)
    assert not df.empty
    dp.backup.eastmoney_guba_hot.assert_called_once_with(10)


def test_get_guba_posts_calls_eastmoney():
    """测试 get_guba_posts 调用 eastmoney"""
    dp = DataProvider()
    fake_df = pd.DataFrame({"标题": ["帖子1"]})
    dp.backup.eastmoney_guba_posts = MagicMock(return_value=fake_df)

    df = dp.get_guba_posts("600000", page_size=15)
    assert not df.empty
    dp.backup.eastmoney_guba_posts.assert_called_once_with("600000", 15)


def test_get_global_sina_news_calls_akshare():
    """测试 get_global_sina_news 调用 akshare"""
    dp = DataProvider()
    fake_df = pd.DataFrame({"标题": ["快讯1"]})
    dp.backup.akshare_news_sina = MagicMock(return_value=fake_df)

    df = dp.get_global_sina_news()
    assert not df.empty


def test_get_caixin_news_calls_akshare():
    """测试 get_caixin_news 调用 akshare"""
    dp = DataProvider()
    fake_df = pd.DataFrame({"标题": ["财新1"]})
    dp.backup.akshare_news_caixin = MagicMock(return_value=fake_df)

    df = dp.get_caixin_news()
    assert not df.empty


def test_get_cctv_news_calls_akshare():
    """测试 get_cctv_news 调用 akshare"""
    dp = DataProvider()
    fake_df = pd.DataFrame({"标题": ["新闻联播1"]})
    dp.backup.akshare_news_cctv = MagicMock(return_value=fake_df)

    df = dp.get_cctv_news("20240101")
    assert not df.empty
    dp.backup.akshare_news_cctv.assert_called_once_with("20240101")


# =====================================================================
# 配置集成测试
# =====================================================================
def test_data_provider_reads_enabled_sources_from_config():
    """测试 DataProvider 从 AppConfig 读取 enabled_backup_sources"""
    cfg = AppConfig()
    cfg.enabled_backup_sources = ["akshare", "tencent"]
    dp = DataProvider(cfg)
    assert dp.enabled_sources == ["akshare", "tencent"]


def test_data_provider_default_enabled_sources():
    """测试 DataProvider 默认启用所有备选源"""
    dp = DataProvider()
    assert "akshare" in dp.enabled_sources
    assert "eastmoney" in dp.enabled_sources
    assert "tencent" in dp.enabled_sources
    assert "netease" in dp.enabled_sources
    assert "efinance" in dp.enabled_sources
