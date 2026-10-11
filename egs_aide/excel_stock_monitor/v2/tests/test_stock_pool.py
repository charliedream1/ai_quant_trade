# -*- coding: utf-8 -*-
"""股票池管理器测试

覆盖：
    1. 工具函数：拼音首字母、市场判断
    2. 数据拉取：akshare 主源、efinance 备选、全失败兜底
    3. 缓存读写：保存、加载、过期判断、损坏文件处理
    4. 模糊搜索：代码前缀、名称包含、拼音首字母、空关键字、limit
"""
import json
import os
import time
import tempfile
from unittest.mock import MagicMock, patch

import pandas as pd

from excel_monitor.core.stock_pool import StockPool, _pinyin_first_letters


# =====================================================================
# 1. 工具函数
# =====================================================================
def test_pinyin_first_letters_basic():
    """测试拼音首字母提取（简化映射表，仅覆盖常见字）"""
    assert _pinyin_first_letters("平安银行") == "payh"
    assert _pinyin_first_letters("贵州茅台") == "gzmt"
    assert _pinyin_first_letters("000001") == "000001"
    # "比亚迪" 中 "亚" 不在常用映射表，返回 "bd"（比+迪）
    assert _pinyin_first_letters("比亚迪") == "bd"


def test_pinyin_first_letters_unknown_char():
    """测试未覆盖字符返回空"""
    # "齉" 是罕见字，不在映射表中
    result = _pinyin_first_letters("齉")
    assert result == ""


def test_detect_market():
    """测试市场判断"""
    assert StockPool._detect_market("600000") == "沪市"
    assert StockPool._detect_market("688981") == "沪市"  # 科创板
    assert StockPool._detect_market("000001") == "深圳"
    assert StockPool._detect_market("300750") == "深圳"  # 创业板
    assert StockPool._detect_market("830799") == "北交所"
    assert StockPool._detect_market("430047") == "北交所"


# =====================================================================
# 2. 数据拉取
# =====================================================================
def test_fetch_from_akshare_success():
    """测试 akshare 主源拉取成功"""
    pool = StockPool(cache_path="/tmp/nonexistent.json")
    mock_ak = MagicMock()
    mock_ak.stock_info_a_code_name.return_value = pd.DataFrame({
        "code": ["000001", "600000", "688981"],
        "name": ["平安银行", "浦发银行", "中芯国际"],
    })
    with patch.dict("sys.modules", {"akshare": mock_ak}):
        df = pool._fetch_from_akshare()
    assert len(df) == 3
    assert list(df.columns) == ["代码", "名称", "市场", "拼音"]
    assert df.iloc[0]["代码"] == "000001"
    assert df.iloc[0]["名称"] == "平安银行"
    assert df.iloc[0]["市场"] == "深圳"
    assert df.iloc[0]["拼音"] == "payh"


def test_fetch_from_akshare_failure():
    """测试 akshare 拉取失败返回空"""
    pool = StockPool(cache_path="/tmp/nonexistent.json")
    mock_ak = MagicMock()
    mock_ak.stock_info_a_code_name.side_effect = Exception("network error")
    with patch.dict("sys.modules", {"akshare": mock_ak}):
        df = pool._fetch_from_akshare()
    assert df.empty


def test_fetch_from_efinance_success():
    """测试 efinance 备选源拉取成功"""
    pool = StockPool(cache_path="/tmp/nonexistent.json")
    mock_ef = MagicMock()
    mock_ef.stock.get_realtime_quotes.return_value = pd.DataFrame({
        "股票代码": ["000001", "600000"],
        "股票名称": ["平安银行", "浦发银行"],
    })
    with patch.dict("sys.modules", {"efinance": mock_ef}):
        df = pool._fetch_from_efinance()
    assert len(df) == 2
    assert df.iloc[0]["代码"] == "000001"


def test_fetch_fallback_chain():
    """测试 fetch 主源失败自动切换备选"""
    pool = StockPool(cache_path="/tmp/nonexistent.json")
    mock_ak = MagicMock()
    mock_ak.stock_info_a_code_name.side_effect = Exception("fail")
    mock_ef = MagicMock()
    mock_ef.stock.get_realtime_quotes.return_value = pd.DataFrame({
        "股票代码": ["000001"], "股票名称": ["平安银行"],
    })
    with patch.dict("sys.modules", {"akshare": mock_ak, "efinance": mock_ef}):
        df = pool.fetch()
    assert len(df) == 1
    assert df.iloc[0]["名称"] == "平安银行"


def test_fetch_all_fail():
    """测试所有数据源失败返回空"""
    pool = StockPool(cache_path="/tmp/nonexistent.json")
    mock_ak = MagicMock()
    mock_ak.stock_info_a_code_name.side_effect = Exception("fail")
    mock_ef = MagicMock()
    mock_ef.stock.get_realtime_quotes.side_effect = Exception("fail")
    with patch.dict("sys.modules", {"akshare": mock_ak, "efinance": mock_ef}):
        df = pool.fetch()
    assert df.empty


# =====================================================================
# 3. 缓存读写
# =====================================================================
def test_save_and_load_cache_fresh():
    """测试缓存保存和加载（未过期）"""
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "pool.json")
        pool = StockPool(cache_path=path, cache_days=7)
        pool.df = pd.DataFrame({
            "代码": ["000001", "600000"],
            "名称": ["平安银行", "浦发银行"],
            "市场": ["深圳", "沪市"],
            "拼音": ["payh", "pfyh"],
        })
        pool.save_cache()
        assert os.path.exists(path)

        # 新实例加载
        pool2 = StockPool(cache_path=path, cache_days=7)
        fresh = pool2.load_cache()
        assert fresh is True
        assert len(pool2.df) == 2
        assert pool2.df.iloc[0]["代码"] == "000001"


def test_load_cache_expired():
    """测试缓存过期：返回 False（需要刷新）但数据仍加载"""
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "pool.json")
        # 写入一个过期的缓存（时间戳为 10 天前）
        data = {
            "timestamp": time.time() - 10 * 86400,
            "records": [
                {"代码": "000001", "名称": "平安银行", "市场": "深圳", "拼音": "payh"},
            ],
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)

        pool = StockPool(cache_path=path, cache_days=1)
        fresh = pool.load_cache()
        assert fresh is False  # 过期
        assert len(pool.df) == 1  # 但数据仍加载


def test_load_cache_not_exist():
    """测试缓存不存在返回 False"""
    pool = StockPool(cache_path="/tmp/nonexistent_pool.json")
    assert pool.load_cache() is False
    assert pool.df.empty


def test_load_cache_corrupted():
    """测试缓存文件损坏"""
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "pool.json")
        with open(path, "w") as f:
            f.write("not a valid json {{{")
        pool = StockPool(cache_path=path)
        assert pool.load_cache() is False


def test_load_or_fetch_uses_cache():
    """测试 load_or_fetch 优先用缓存"""
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "pool.json")
        # 先保存一个新鲜缓存
        pool = StockPool(cache_path=path, cache_days=7)
        pool.df = pd.DataFrame({
            "代码": ["000001"], "名称": ["平安银行"],
            "市场": ["深圳"], "拼音": ["payh"],
        })
        pool.save_cache()

        # 新实例：有新鲜缓存，不应调用 fetch
        pool2 = StockPool(cache_path=path, cache_days=7)
        pool2.fetch = MagicMock(return_value=pd.DataFrame())
        result = pool2.load_or_fetch()
        pool2.fetch.assert_not_called()
        assert len(result) == 1


def test_load_or_fetch_refreshes_when_expired():
    """测试缓存过期时重新拉取"""
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "pool.json")
        # 过期缓存
        data = {
            "timestamp": time.time() - 10 * 86400,
            "records": [{"代码": "000001", "名称": "平安银行",
                         "市场": "深圳", "拼音": "payh"}],
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)

        pool = StockPool(cache_path=path, cache_days=1)
        new_df = pd.DataFrame({
            "代码": ["600000"], "名称": ["浦发银行"],
            "市场": ["沪市"], "拼音": ["pfyh"],
        })
        pool.fetch = MagicMock(return_value=new_df)
        result = pool.load_or_fetch()
        pool.fetch.assert_called_once()
        assert len(result) == 1
        assert result.iloc[0]["代码"] == "600000"  # 用新数据


def test_load_or_fetch_falls_back_to_expired_cache():
    """测试拉取失败时使用过期缓存保底"""
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "pool.json")
        # 过期缓存
        data = {
            "timestamp": time.time() - 10 * 86400,
            "records": [{"代码": "000001", "名称": "平安银行",
                         "市场": "深圳", "拼音": "payh"}],
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)

        pool = StockPool(cache_path=path, cache_days=1)
        pool.fetch = MagicMock(return_value=pd.DataFrame())  # 拉取失败
        result = pool.load_or_fetch()
        pool.fetch.assert_called_once()
        assert len(result) == 1  # 用过期缓存
        assert result.iloc[0]["代码"] == "000001"


# =====================================================================
# 4. 模糊搜索
# =====================================================================
def _make_pool_with_data():
    """构造带测试数据的 StockPool"""
    pool = StockPool(cache_path="/tmp/nonexistent.json")
    pool.df = pd.DataFrame({
        "代码": ["000001", "600000", "600519", "000333", "300750"],
        "名称": ["平安银行", "浦发银行", "贵州茅台", "美的集团", "宁德时代"],
        "市场": ["深圳", "沪市", "沪市", "深圳", "深圳"],
        "拼音": ["payh", "pfyh", "gzmt", "mdjt", "ndsd"],
    })
    return pool


def test_search_by_code_prefix():
    """测试按代码前缀搜索"""
    pool = _make_pool_with_data()
    result = pool.search("600")
    assert len(result) == 2  # 600000, 600519
    assert "600000" in result["代码"].tolist()
    assert "600519" in result["代码"].tolist()


def test_search_by_name_contains():
    """测试按名称包含搜索"""
    pool = _make_pool_with_data()
    result = pool.search("平安")
    assert len(result) == 1
    assert result.iloc[0]["名称"] == "平安银行"


def test_search_by_pinyin():
    """测试按拼音首字母搜索"""
    pool = _make_pool_with_data()
    result = pool.search("pa")
    assert len(result) == 1
    assert result.iloc[0]["名称"] == "平安银行"


def test_search_empty_keyword_returns_head():
    """测试空关键字返回前 N 条"""
    pool = _make_pool_with_data()
    result = pool.search("")
    assert len(result) == 5  # 全部


def test_search_no_match():
    """测试无匹配返回空"""
    pool = _make_pool_with_data()
    result = pool.search("xyz不存在的股票")
    assert result.empty


def test_search_limit():
    """测试 limit 限制返回条数"""
    pool = _make_pool_with_data()
    result = pool.search("0", limit=2)  # 0 开头的代码
    assert len(result) == 2


def test_search_case_insensitive():
    """测试大小写不敏感"""
    pool = _make_pool_with_data()
    result = pool.search("PA")
    assert len(result) == 1
    assert result.iloc[0]["名称"] == "平安银行"


def test_get_codes():
    """测试获取全部代码列表"""
    pool = _make_pool_with_data()
    codes = pool.get_codes()
    assert len(codes) == 5
    assert "000001" in codes


def test_get_codes_empty():
    """测试空股票池返回空列表"""
    pool = StockPool(cache_path="/tmp/nonexistent.json")
    assert pool.get_codes() == []
