# -*- coding: utf-8 -*-
# @Author   : ai_quant_trade
# @File     : yfinance_data.py
# @Project  : ai_quant_trade
# Copyright (c) Personal
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
yfinance 数据接口示例
覆盖：美股/港股/A股行情、代码转换、指数行情、多股批量获取

安装：pip install yfinance
特点：免费、支持多市场、分钟级数据
局限：A股数据可能有延迟，某些股票可能无数据

参考来源：
  - Vibe-Trading: backtest/loaders/yfinance_loader.py
    (代码转换、批量下载、OHLCV标准化)
  - daily_stock_analysis: data_provider/yfinance_fetcher.py
    (A股代码转换、指数行情、Stooq兜底)
"""

import os
import tempfile
import logging
from collections import defaultdict
from typing import Dict, List, Optional

import pandas as pd
import yfinance as yf

# 设置缓存目录到可写位置，避免 peewee 数据库路径错误
cache_dir = os.path.join(tempfile.gettempdir(), 'yfinance_cache')
os.makedirs(cache_dir, exist_ok=True)
yf.set_tz_cache_location(cache_dir)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 120)


# ---------------------------------------------------------------------------
# 代码转换工具（参考 Vibe-Trading yfinance_loader + daily_stock_analysis）
# ---------------------------------------------------------------------------

def convert_to_yfinance_code(stock_code: str) -> str:
    """转换股票代码为 Yahoo Finance 格式

    Yahoo Finance 代码格式：
    - A股沪市：600519.SS (Shanghai Stock Exchange)
    - A股深市：000001.SZ (Shenzhen Stock Exchange)
    - 港股：0700.HK (Hong Kong Stock Exchange)
    - 美股：AAPL, TSLA (无需后缀)
    - 加密货币：BTC-USD

    支持输入格式：
    - '600519'      -> '600519.SS'
    - '600519.SH'   -> '600519.SS'
    - 'hk00700'     -> '0700.HK'
    - 'AAPL.US'     -> 'AAPL'
    - 'BTC-USDT'    -> 'BTC-USD'
    """
    code = stock_code.strip().upper()

    # 美股：去除 .US 后缀
    if code.endswith(".US"):
        return code[:-3]

    # 加密货币：USDT/USDC -> USD
    if code.endswith("-USDT"):
        return code[:-5] + "-USD"
    if code.endswith("-USDC"):
        return code[:-5] + "-USD"

    # 港股：hk前缀 -> .HK后缀
    if code.startswith('HK'):
        hk_code = code[2:].lstrip('0') or '0'
        hk_code = hk_code.zfill(4)  # 补齐到4位
        return f"{hk_code}.HK"

    # 已有后缀
    if '.SS' in code or '.SZ' in code or '.HK' in code:
        return code

    # 去除 .SH 后缀
    code = code.replace('.SH', '')

    # 纯数字：判断市场
    if code.isdigit() and len(code) == 6:
        # ETF: 上交所 ETF -> .SS, 深交所 ETF -> .SZ
        if code.startswith(('51', '52', '56', '58')):
            return f"{code}.SS"
        if code.startswith(('15', '16', '18')):
            return f"{code}.SZ"
        # A股：沪市 -> .SS, 深市 -> .SZ
        if code.startswith(('600', '601', '603', '688')):
            return f"{code}.SS"
        if code.startswith(('000', '002', '300')):
            return f"{code}.SZ"

    return code


# ---------------------------------------------------------------------------
# 演示函数
# ---------------------------------------------------------------------------

def demo_us_stock():
    """1. 美股行情"""
    print("=" * 60)
    print("1. 美股行情（AAPL, GOOG, AMZN）")
    print("=" * 60)
    tickers_list = ["AAPL", "GOOG", "AMZN"]
    for ticker in tickers_list:
        try:
            ticker_object = yf.Ticker(ticker)
            hist = ticker_object.history(period="5d")
            if hist.empty:
                print(f"  {ticker}: 未获取到数据")
                continue
            print(f"  {ticker}: 获取 {len(hist)} 条数据, "
                  f"最新收盘价 {hist['Close'].iloc[-1]:.2f}")
        except Exception as e:
            print(f"  {ticker}: 获取失败 - {str(e)[:80]}")


def demo_a_stock():
    """2. A股行情（参考 daily_stock_analysis YfinanceFetcher 代码转换）"""
    print("\n" + "=" * 60)
    print("2. A股行情（贵州茅台, 中国平安）")
    print("=" * 60)
    a_codes = ["600519", "000001"]
    for code in a_codes:
        yf_code = convert_to_yfinance_code(code)
        print(f"  {code} -> {yf_code}")
        try:
            ticker = yf.Ticker(yf_code)
            hist = ticker.history(period="5d", auto_adjust=True)
            if hist.empty:
                print(f"    无数据")
                continue
            # 处理 MultiIndex 列名（新版 yfinance）
            if isinstance(hist.columns, pd.MultiIndex):
                hist.columns = hist.columns.get_level_values(0)
            print(f"    最新收盘: {hist['Close'].iloc[-1]:.2f}")
        except Exception as e:
            print(f"    获取失败: {str(e)[:60]}")


def demo_hk_stock():
    """3. 港股行情"""
    print("\n" + "=" * 60)
    print("3. 港股行情（腾讯控股）")
    print("=" * 60)
    # 支持 hk00700 / 00700.HK / 700.HK 等格式
    test_codes = ["hk00700", "0700.HK"]
    for code in test_codes:
        yf_code = convert_to_yfinance_code(code)
        print(f"  {code} -> {yf_code}")
        try:
            ticker = yf.Ticker(yf_code)
            hist = ticker.history(period="5d", auto_adjust=True)
            if not hist.empty:
                print(f"    最新收盘: {hist['Close'].iloc[-1]:.2f}")
            else:
                print(f"    无数据")
        except Exception as e:
            print(f"    获取失败: {str(e)[:60]}")


def demo_cn_indices():
    """4. A股指数行情（参考 daily_stock_analysis get_main_indices）"""
    print("\n" + "=" * 60)
    print("4. A股主要指数行情")
    print("=" * 60)
    # A股指数：akshare 代码 -> (yfinance 代码, 显示名称)
    index_mapping = {
        'sh000001': ('000001.SS', '上证指数'),
        'sz399001': ('399001.SZ', '深证成指'),
        'sz399006': ('399006.SZ', '创业板指'),
        'sh000688': ('000688.SS', '科创50'),
        'sh000300': ('000300.SS', '沪深300'),
    }
    for ak_code, (yf_code, name) in index_mapping.items():
        try:
            ticker = yf.Ticker(yf_code)
            hist = ticker.history(period='2d')
            if hist.empty:
                print(f"  {name}({yf_code}): 无数据")
                continue
            today = hist.iloc[-1]
            prev = hist.iloc[-2] if len(hist) > 1 else today
            price = float(today['Close'])
            prev_close = float(prev['Close'])
            change_pct = ((price - prev_close) / prev_close) * 100 if prev_close else 0
            print(f"  {name}({yf_code}): {price:.2f}  涨跌: {change_pct:+.2f}%")
        except Exception as e:
            print(f"  {name}({yf_code}): 获取失败 - {str(e)[:40]}")


def demo_us_indices():
    """5. 美股指数行情"""
    print("\n" + "=" * 60)
    print("5. 美股主要指数行情")
    print("=" * 60)
    us_indices = {
        'S&P 500': '^GSPC',
        '道琼斯': '^DJI',
        '纳斯达克': '^IXIC',
        'VIX恐慌指数': '^VIX',
    }
    for name, symbol in us_indices.items():
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period='2d')
            if hist.empty:
                print(f"  {name}: 无数据")
                continue
            price = float(hist['Close'].iloc[-1])
            print(f"  {name}: {price:.2f}")
        except Exception as e:
            print(f"  {name}: 获取失败 - {str(e)[:40]}")


def demo_batch_download():
    """6. 批量下载多股数据（参考 Vibe-Trading yfinance_loader）"""
    print("\n" + "=" * 60)
    print("6. 批量下载多股数据")
    print("=" * 60)
    codes = ["AAPL", "GOOG", "MSFT"]
    try:
        # yfinance 支持批量下载
        data = yf.download(codes, period="5d", auto_adjust=True, progress=False)
        if not data.empty:
            for code in codes:
                if isinstance(data.columns, pd.MultiIndex):
                    if code in data.columns.get_level_values(1):
                        close = data['Close'][code].dropna()
                        if not close.empty:
                            print(f"  {code}: 最新收盘 {close.iloc[-1]:.2f}")
                else:
                    close = data['Close'].dropna()
                    if not close.empty:
                        print(f"  最新收盘 {close.iloc[-1]:.2f}")
        else:
            print("  无数据")
    except Exception as e:
        print(f"  批量下载失败: {str(e)[:60]}")


def demo_code_conversion():
    """7. 代码转换示例"""
    print("\n" + "=" * 60)
    print("7. 代码转换示例")
    print("=" * 60)
    test_codes = [
        "600519",          # A股沪市
        "000001",          # A股深市
        "600519.SH",       # 带后缀
        "510300",          # 上交所ETF
        "159915",          # 深交所ETF
        "688981",          # 科创板
        "hk00700",         # 港股
        "0700.HK",         # 港股
        "AAPL.US",         # 美股
        "BTC-USDT",        # 加密货币
    ]
    for code in test_codes:
        yf_code = convert_to_yfinance_code(code)
        print(f"  {code:12s} -> {yf_code}")


# ---------------------------------------------------------------------------
# 标准化 OHLCV 输出（参考 Vibe-Trading yfinance_loader）
# ---------------------------------------------------------------------------

OHLCV_COLUMNS = ["open", "high", "low", "close", "volume"]
COLUMN_RENAMES = {
    "Open": "open", "High": "high", "Low": "low",
    "Close": "close", "Volume": "volume",
}


def fetch_ohlcv_standardized(code: str, start_date: str, end_date: str,
                              interval: str = "1D") -> pd.DataFrame:
    """获取标准化 OHLCV 数据

    将 yfinance 返回的数据统一为 (trade_date, open, high, low, close, volume) 格式

    Args:
        code: 原始代码，如 "600519", "AAPL.US"
        start_date: YYYY-MM-DD
        end_date: YYYY-MM-DD
        interval: yfinance 周期 (1d, 1h, 5m 等)

    Returns:
        标准化 OHLCV DataFrame
    """
    yf_code = convert_to_yfinance_code(code)
    # yfinance end_date 是排除的，加一天
    yf_end = (pd.Timestamp(end_date) + pd.Timedelta(days=1)).strftime("%Y-%m-%d")

    interval_map = {"1D": "1d", "1H": "1h", "4H": "1h"}
    yf_interval = interval_map.get(interval, interval.lower())

    try:
        df = yf.download(yf_code, start=start_date, end=yf_end,
                          interval=yf_interval, auto_adjust=True, progress=False)
    except Exception as e:
        logger.warning(f"yfinance 下载失败: {e}")
        return pd.DataFrame(columns=OHLCV_COLUMNS)

    if df.empty:
        return pd.DataFrame(columns=OHLCV_COLUMNS)

    # 处理 MultiIndex 列名
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df = df.rename(columns=COLUMN_RENAMES)
    for col in OHLCV_COLUMNS:
        if col not in df.columns:
            df[col] = 0.0 if col == "volume" else pd.NA

    df = df.loc[:, OHLCV_COLUMNS].apply(pd.to_numeric, errors="coerce")
    df.index = pd.DatetimeIndex(pd.to_datetime(df.index))
    if getattr(df.index, 'tz', None) is not None:
        df.index = df.index.tz_localize(None)
    df.index.name = "trade_date"
    df["volume"] = df["volume"].fillna(0.0)
    df = df.dropna(subset=["open", "high", "low", "close"])
    return df.sort_index()


def demo_standardized_ohlcv():
    """8. 标准化 OHLCV 数据输出"""
    print("\n" + "=" * 60)
    print("8. 标准化 OHLCV 数据（贵州茅台）")
    print("=" * 60)
    df = fetch_ohlcv_standardized("600519", "2024-01-01", "2024-01-10")
    if not df.empty:
        print(df)
    else:
        print("  无数据")


if __name__ == '__main__':
    demo_us_stock()
    demo_a_stock()
    demo_hk_stock()
    demo_cn_indices()
    demo_us_indices()
    demo_batch_download()
    demo_code_conversion()
    demo_standardized_ohlcv()
