# -*- coding: utf-8 -*-
"""BackupSources 模块测试

测试备选数据源适配器的纯逻辑方法（无网络请求）。
所有需要 import akshare/efinance/requests 的方法都通过 mock 验证调用路径。
"""
import pandas as pd
from unittest.mock import MagicMock, patch

from excel_monitor.core.backup_sources import (
    BackupSources,
    _normalize_codes,
    _detect_market_prefix,
    _safe_int,
    _safe_float,
)


# =====================================================================
# 工具函数测试
# =====================================================================
def test_normalize_codes_removes_postfix():
    """测试代码归一化：去除 .SH/.SZ 后缀"""
    assert _normalize_codes(["000001.SZ"]) == ["000001"]
    assert _normalize_codes(["600000.SH"]) == ["600000"]
    assert _normalize_codes(["300001"]) == ["300001"]


def test_normalize_codes_removes_market_prefix():
    """测试代码归一化：去除 sh/sz/bj 前缀"""
    assert _normalize_codes(["sh600000"]) == ["600000"]
    assert _normalize_codes(["sz000001"]) == ["000001"]
    assert _normalize_codes(["bj430001"]) == ["430001"]


def test_normalize_codes_handles_empty():
    """测试代码归一化：过滤空值"""
    assert _normalize_codes([]) == []
    assert _normalize_codes(["", "  ", "600000"]) == ["600000"]


def test_detect_market_prefix_sh():
    """测试市场前缀识别：沪市"""
    assert _detect_market_prefix("600000") == "sh"
    assert _detect_market_prefix("688888") == "sh"  # 科创板
    assert _detect_market_prefix("sh600000") == "sh"


def test_detect_market_prefix_sz():
    """测试市场前缀识别：深市"""
    assert _detect_market_prefix("000001") == "sz"
    assert _detect_market_prefix("300001") == "sz"  # 创业板
    assert _detect_market_prefix("sz000001") == "sz"


def test_detect_market_prefix_bj():
    """测试市场前缀识别：北交所"""
    assert _detect_market_prefix("430001") == "bj"
    assert _detect_market_prefix("830001") == "bj"


def test_safe_int():
    """测试安全 int 转换"""
    assert _safe_int("100") == 100
    assert _safe_int(100.5) == 100
    assert _safe_int(None) == 0
    assert _safe_int("") == 0
    assert _safe_int("abc") == 0
    assert _safe_int("100", default=-1) == 100
    assert _safe_int(None, default=-1) == -1


def test_safe_float():
    """测试安全 float 转换"""
    assert _safe_float("10.5") == 10.5
    assert _safe_float(10) == 10.0
    assert _safe_float(None) is None
    assert _safe_float("") is None
    assert _safe_float("abc") is None


# =====================================================================
# BackupSources 类测试（mock 外部库）
# =====================================================================
def test_backup_sources_initialization():
    """测试 BackupSources 初始化"""
    bs = BackupSources()
    assert bs._akshare is None
    assert bs._efinance is None
    assert bs._requests is None


def test_backup_sources_lazy_loading_akshare():
    """测试 akshare 延迟加载"""
    import sys
    bs = BackupSources()
    mock_ak = MagicMock()
    sys.modules["akshare"] = mock_ak
    try:
        result = bs._get_akshare()
        assert result is mock_ak
        # 二次调用使用缓存，不重复 import
        result2 = bs._get_akshare()
        assert result2 is mock_ak
    finally:
        sys.modules.pop("akshare", None)


def test_akshare_stock_realtime_with_mock():
    """测试 AKShare 个股实时行情（mock akshare 库）"""
    bs = BackupSources()
    mock_ak = MagicMock()
    mock_ak.stock_zh_a_spot_em.return_value = pd.DataFrame({
        "代码": ["600000", "000001"],
        "名称": ["浦发银行", "平安银行"],
        "最新价": [10.5, 12.3],
        "涨跌幅": [1.2, -0.5],
        "涨跌额": [0.12, -0.06],
        "成交量": [100000, 200000],
        "成交额": [1050000, 2460000],
        "换手率": [0.5, 0.8],
        "最高": [10.6, 12.5],
        "最低": [10.3, 12.1],
        "今开": [10.4, 12.2],
        "昨收": [10.38, 12.36],
    })
    import sys
    sys.modules["akshare"] = mock_ak

    df = bs.akshare_stock_realtime(["600000", "000001"])
    assert not df.empty
    assert "代码" in df.columns
    assert "名称" in df.columns
    # 字段重命名后应为 "最新"
    assert "最新" in df.columns
    assert "涨幅" in df.columns
    assert len(df) == 2


def test_akshare_stock_realtime_empty_codes():
    """测试 AKShare 个股实时行情：空代码列表"""
    bs = BackupSources()
    df = bs.akshare_stock_realtime([])
    assert df.empty


def test_akshare_stock_realtime_failure():
    """测试 AKShare 个股实时行情：akshare 抛异常时返回空"""
    bs = BackupSources()
    mock_ak = MagicMock()
    mock_ak.stock_zh_a_spot_em.side_effect = Exception("network error")
    import sys
    sys.modules["akshare"] = mock_ak

    df = bs.akshare_stock_realtime(["600000"])
    assert df.empty  # 异常被捕获，返回空


def test_akshare_news_cls_with_mock():
    """测试 AKShare 财联社电报（mock）"""
    bs = BackupSources()
    mock_ak = MagicMock()
    mock_ak.stock_info_global_cls.return_value = pd.DataFrame({
        "标题": ["央行降息", "GDP数据公布"],
        "内容": ["详情1", "详情2"],
        "发布时间": ["2024-01-01 10:30", "2024-01-01 10:25"],
    })
    import sys
    sys.modules["akshare"] = mock_ak

    df = bs.akshare_news_cls()
    assert not df.empty
    assert "标题" in df.columns
    assert len(df) == 2


def test_eastmoney_secid():
    """测试 eastmoney secid 转换"""
    bs = BackupSources()
    # 沪市 → 1.代码
    assert bs._eastmoney_secid("600000") == "1.600000"
    assert bs._eastmoney_secid("688888") == "1.688888"
    # 深市 → 0.代码
    assert bs._eastmoney_secid("000001") == "0.000001"
    assert bs._eastmoney_secid("300001") == "0.300001"
    # 带后缀的输入
    assert bs._eastmoney_secid("600000.SH") == "1.600000"


def test_tencent_code():
    """测试腾讯代码转换"""
    bs = BackupSources()
    assert bs._tencent_code("600000") == "sh600000"
    assert bs._tencent_code("000001") == "sz000001"
    assert bs._tencent_code("600000.SH") == "sh600000"


def test_eastmoney_stock_realtime_with_mock():
    """测试东方财富个股实时行情（mock requests）"""
    bs = BackupSources()
    mock_requests = MagicMock()
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "data": {
            "diff": [
                {"f12": "600000", "f14": "浦发银行", "f2": 10.5,
                 "f3": 1.2, "f4": 0.12, "f5": 100000, "f6": 1050000,
                 "f8": 0.5, "f15": 10.6, "f16": 10.3,
                 "f17": 10.4, "f18": 10.38},
            ]
        }
    }
    mock_requests.get.return_value = mock_response
    import sys
    sys.modules["requests"] = mock_requests

    df = bs.eastmoney_stock_realtime(["600000"])
    assert not df.empty
    assert "代码" in df.columns
    assert df.iloc[0]["代码"] == "600000"
    assert df.iloc[0]["名称"] == "浦发银行"


def test_eastmoney_money_flow_with_mock():
    """测试东方财富个股资金流向（mock requests）"""
    bs = BackupSources()
    mock_requests = MagicMock()
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "data": {
            "klines": [
                "2024-01-01,1000000,500000,300000,200000,800000",
                "2024-01-02,2000000,600000,400000,300000,900000",
            ]
        }
    }
    mock_requests.get.return_value = mock_response
    import sys
    sys.modules["requests"] = mock_requests

    df = bs.eastmoney_money_flow("600000")
    assert not df.empty
    assert "日期" in df.columns
    assert "主力净流入" in df.columns
    assert len(df) == 2


def test_eastmoney_guba_hot_with_mock():
    """测试东方财富人气榜（mock akshare.stock_hot_rank_em）"""
    bs = BackupSources()
    mock_ak = MagicMock()
    mock_ak.stock_hot_rank_em.return_value = pd.DataFrame({
        "股票代码": ["600000", "000001"],
        "股票名称": ["浦发银行", "平安银行"],
        "排名": [1, 2],
        "排名较昨日变化": [0, 1],
    })
    import sys
    sys.modules["akshare"] = mock_ak

    df = bs.eastmoney_guba_hot(page_size=10)
    assert not df.empty
    assert "代码" in df.columns
    assert df.iloc[0]["代码"] == "600000"


def test_tencent_stock_realtime_with_mock():
    """测试腾讯个股实时行情（mock requests + gbk 解析）"""
    bs = BackupSources()
    mock_requests = MagicMock()
    mock_response = MagicMock()
    # 构造腾讯接口返回的字符串格式
    # v_sh600000="1~浦发银行~600000~10.5~10.38~10.4~100000~..."
    # 字段索引：3=最新 4=昨收 5=开盘 6=成交量 32=涨幅 33=最高 34=最低
    # 37=成交额 38=换手率（解析器要求 len(fields) >= 50）
    fields = ["1", "浦发银行", "600000", "10.5", "10.38", "10.4",
              "100000", "0", "0"] + ["0"] * 23 + ["1.2"] + ["10.6", "10.3"]
    fields += ["0"] * 2 + ["1050000"] + ["0.5"] + ["20"]
    fields += ["0"] * 10  # 补足到 55 个字段，满足 >=50 的校验
    mock_response.text = (
        f'v_sh600000="{"~".join(fields)}";\n'
    )
    mock_response.encoding = "gbk"
    mock_requests.get.return_value = mock_response
    import sys
    sys.modules["requests"] = mock_requests

    df = bs.tencent_stock_realtime(["600000"])
    assert not df.empty
    assert "代码" in df.columns
    assert df.iloc[0]["代码"] == "600000"


def test_netease_kline_with_mock():
    """测试网易历史 K 线（mock requests + CSV 解析）"""
    bs = BackupSources()
    mock_requests = MagicMock()
    mock_response = MagicMock()
    # 模拟网易 CSV 返回
    csv_content = (
        "日期,股票代码,名称,收盘价,最高价,最低价,开盘价,前收盘,涨跌额,"
        "涨跌幅,换手率,成交量,成交金额,总市值,流通市值\n"
        "2024-01-02,600000,浦发银行,10.5,10.6,10.3,10.4,10.38,0.12,1.15,"
        "0.5,100000,1050000,3000000000,2000000000\n"
        "2024-01-03,600000,浦发银行,10.6,10.7,10.4,10.5,10.5,0.10,0.95,"
        "0.4,80000,848000,3000000000,2000000000\n"
    )
    mock_response.text = csv_content
    mock_response.encoding = "gbk"
    mock_requests.get.return_value = mock_response
    import sys
    sys.modules["requests"] = mock_requests

    df = bs.netease_kline("600000", count=10)
    assert not df.empty
    assert "Open" in df.columns
    assert "Close" in df.columns
    assert "High" in df.columns
    assert "Low" in df.columns
    assert "Volume" in df.columns


def test_efinance_stock_realtime_with_mock():
    """测试 efinance 个股实时行情（mock）"""
    bs = BackupSources()
    mock_ef = MagicMock()
    mock_ef.stock.get_realtime_quotes.return_value = pd.DataFrame({
        "股票代码": ["600000", "000001"],
        "股票名称": ["浦发银行", "平安银行"],
        "最新价": [10.5, 12.3],
        "涨跌幅": [1.2, -0.5],
        "涨跌额": [0.12, -0.06],
        "成交量": [100000, 200000],
        "成交额": [1050000, 2460000],
        "换手率": [0.5, 0.8],
        "最高": [10.6, 12.5],
        "最低": [10.3, 12.1],
        "今开": [10.4, 12.2],
        "昨收": [10.38, 12.36],
    })
    import sys
    sys.modules["efinance"] = mock_ef

    df = bs.efinance_stock_realtime(["600000", "000001"])
    assert not df.empty
    assert "代码" in df.columns
    # 重命名后应为 "最新"
    assert "最新" in df.columns
    assert len(df) == 2


def test_backup_source_disabled_when_lib_missing():
    """测试：当 akshare 未安装时，方法应优雅返回空 DataFrame"""
    import sys
    bs = BackupSources()
    # 将 sys.modules["akshare"] 置为 None 会让 `import akshare` 抛 ImportError
    # （Python 内置行为），且不会影响 pandas 等其他库的正常导入
    with patch.dict(sys.modules, {"akshare": None}):
        df = bs.akshare_stock_realtime(["600000"])
        assert df.empty


def test_akshare_north_money_with_mock():
    """测试 AKShare 北向资金（mock）"""
    bs = BackupSources()
    mock_ak = MagicMock()
    mock_ak.stock_hsgt_hist_em.return_value = pd.DataFrame({
        "日期": ["2024-01-01", "2024-01-02"],
        "当日净流入": [10000000000, -5000000000],
        "当日余额": [500000000000, 495000000000],
    })
    import sys
    sys.modules["akshare"] = mock_ak

    df = bs.akshare_north_money()
    assert not df.empty
    assert "日期" in df.columns
    assert "当日净流入" in df.columns


def test_akshare_weibo_sentiment_with_mock():
    """测试 AKShare 微博舆情（mock）"""
    bs = BackupSources()
    mock_ak = MagicMock()
    mock_ak.stock_js_weibo_report.return_value = pd.DataFrame({
        "股票代码": ["600000"],
        "股票名称": ["浦发银行"],
        "微博舆情指数": [85.5],
    })
    import sys
    sys.modules["akshare"] = mock_ak

    df = bs.akshare_weibo_sentiment()
    assert not df.empty
    assert "股票代码" in df.columns


def test_akshare_news_sentiment_with_mock():
    """测试 AKShare 新闻情绪指数（mock）"""
    bs = BackupSources()
    mock_ak = MagicMock()
    mock_ak.index_news_sentiment_scope.return_value = pd.DataFrame({
        "日期": ["2024-01-01", "2024-01-02"],
        "新闻情绪指数": [60.5, 55.2],
    })
    import sys
    sys.modules["akshare"] = mock_ak

    df = bs.akshare_news_sentiment()
    assert not df.empty
    assert "新闻情绪指数" in df.columns
