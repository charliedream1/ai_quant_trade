# -*- coding: utf-8 -*-
# @Author   : ai_quant_trade
# @File     : pytdx_demo.py
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
Pytdx (通达信) 数据接口示例
覆盖：日K线、分钟K线、实时行情、股票列表、股票名称

安装：pip install pytdx
特点：免费、无需 Token、直连行情服务器、实时数据
局限：仅支持沪深A股，不支持港股/美股/北交所

参考来源：
  - daily_stock_analysis: data_provider/pytdx_fetcher.py
    (多服务器切换、上下文管理器、股票列表缓存)
"""

import logging
from contextlib import contextmanager
from typing import Optional, List, Tuple, Generator

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 120)


# ---------------------------------------------------------------------------
# 通达信服务器列表
# ---------------------------------------------------------------------------

DEFAULT_HOSTS = [
    ("119.147.212.81", 7709),   # 深圳
    ("112.74.214.43", 7727),    # 深圳
    ("221.231.141.60", 7709),   # 上海
    ("101.227.73.20", 7709),    # 上海
    ("101.227.77.254", 7709),   # 上海
    ("14.215.128.18", 7709),    # 广州
    ("59.173.18.140", 7709),    # 武汉
    ("180.153.39.51", 7709),    # 杭州
]


def get_market_code(stock_code: str) -> Tuple[int, str]:
    """根据股票代码判断市场

    Pytdx 市场代码：
    - 0: 深圳
    - 1: 上海

    Args:
        stock_code: 6位股票代码，如 '600519'

    Returns:
        (market, code) 元组
    """
    code = stock_code.strip()
    # 去除前缀后缀
    code = code.replace('.SH', '').replace('.SZ', '')
    code = code.replace('.sh', '').replace('.sz', '')
    code = code.replace('sh', '').replace('sz', '')

    # 上海：60xxxx, 68xxxx（科创板）
    # 深圳：00xxxx, 30xxxx（创业板）, 002xxx（中小板）
    if code.startswith(('60', '68')):
        return 1, code   # 上海
    else:
        return 0, code   # 深圳


@contextmanager
def pytdx_session(hosts: List[Tuple[str, int]] = None):
    """通达信连接上下文管理器

    确保：
    1. 进入上下文时自动连接
    2. 退出上下文时自动断开
    3. 异常时也能正确断开

    使用示例：
        with pytdx_session() as api:
            data = api.get_security_bars(...)
    """
    if hosts is None:
        hosts = DEFAULT_HOSTS

    try:
        from pytdx.hq import TdxHq_API
    except ImportError:
        print("[错误] pytdx 未安装，请运行: pip install pytdx")
        yield None
        return

    api = TdxHq_API()
    connected = False

    try:
        # 尝试连接服务器（自动选择最优）
        for host, port in hosts:
            try:
                if api.connect(host, port, time_out=5):
                    connected = True
                    logger.info(f"连接成功: {host}:{port}")
                    break
            except Exception as e:
                logger.debug(f"连接 {host}:{port} 失败: {e}")
                continue

        if not connected:
            raise ConnectionError("无法连接任何通达信服务器")

        yield api

    finally:
        try:
            api.disconnect()
            logger.debug("连接已断开")
        except Exception:
            pass


def demo_daily_kline():
    """1. 日K线数据"""
    print("=" * 60)
    print("1. 贵州茅台(600519) 日K线（最近30个交易日）")
    print("=" * 60)
    with pytdx_session() as api:
        if api is None:
            return
        market, code = get_market_code("600519")
        # category: 9=日线, 0=5分钟, 1=15分钟, 2=30分钟, 3=1小时
        data = api.get_security_bars(
            category=9, market=market, code=code, start=0, count=30
        )
        if data:
            df = api.to_df(data)
            print(df.tail(10))
            # 字段: datetime, open, high, low, close, vol, amount
        else:
            print("  无数据返回")


def demo_minute_kline():
    """2. 5分钟K线数据"""
    print("\n" + "=" * 60)
    print("2. 贵州茅台(600519) 5分钟K线（最近50条）")
    print("=" * 60)
    with pytdx_session() as api:
        if api is None:
            return
        market, code = get_market_code("600519")
        # category=0 表示5分钟线
        data = api.get_security_bars(
            category=0, market=market, code=code, start=0, count=50
        )
        if data:
            df = api.to_df(data)
            print(df.tail(10))
        else:
            print("  无数据返回")


def demo_realtime_quote():
    """3. 实时行情"""
    print("\n" + "=" * 60)
    print("3. 实时行情（贵州茅台 + 中国平安）")
    print("=" * 60)
    with pytdx_session() as api:
        if api is None:
            return
        # 批量获取实时行情
        # 格式: [(market, code), ...]
        quotes = api.get_security_quotes([
            (1, "600519"),   # 贵州茅台(上海)
            (0, "000001"),   # 平安银行(深圳)
        ])
        if quotes:
            for q in quotes:
                print(f"  {q.get('code', '')} {q.get('name', '')}")
                print(f"    最新价: {q.get('price', 0)}  开盘: {q.get('open', 0)}")
                print(f"    最高: {q.get('high', 0)}  最低: {q.get('low', 0)}")
                print(f"    成交量: {q.get('vol', 0)}  成交额: {q.get('amount', 0)}")
        else:
            print("  无数据返回")


def demo_stock_list():
    """4. 股票列表"""
    print("\n" + "=" * 60)
    print("4. 上海市场股票列表（前20条）")
    print("=" * 60)
    with pytdx_session() as api:
        if api is None:
            return
        # market=1 上海, market=0 深圳
        stocks = api.get_security_list(market=1, start=0)
        if stocks:
            for s in stocks[:20]:
                print(f"  {s.get('code', '')}  {s.get('name', '')}")
        else:
            print("  无数据返回")


def demo_stock_name():
    """5. 获取股票名称"""
    print("\n" + "=" * 60)
    print("5. 通过代码查询股票名称")
    print("=" * 60)
    with pytdx_session() as api:
        if api is None:
            return
        codes = ["600519", "000001", "300750", "688981"]
        for code in codes:
            market, _ = get_market_code(code)
            quotes = api.get_security_quotes([(market, code)])
            if quotes:
                name = quotes[0].get('name', '')
                print(f"  {code} -> {name}")


def demo_index_kline():
    """6. 指数K线数据"""
    print("\n" + "=" * 60)
    print("6. 上证指数 日K线（最近20个交易日）")
    print("=" * 60)
    with pytdx_session() as api:
        if api is None:
            return
        # 指数也使用 get_security_bars
        # 上证指数: market=1, code=000001
        data = api.get_security_bars(
            category=9, market=1, code="000001", start=0, count=20
        )
        if data:
            df = api.to_df(data)
            print(df.tail(10))
        else:
            print("  无数据返回")


# ---------------------------------------------------------------------------
# 标准化输出工具函数（参考 daily_stock_analysis）
# ---------------------------------------------------------------------------

STANDARD_COLUMNS = ['date', 'open', 'high', 'low', 'close', 'volume', 'amount', 'pct_chg']


def normalize_pytdx_data(df: pd.DataFrame, stock_code: str) -> pd.DataFrame:
    """标准化 Pytdx 数据

    Pytdx 返回的列名：datetime, open, high, low, close, vol, amount
    映射到标准列名：date, open, high, low, close, volume, amount, pct_chg
    """
    df = df.copy()
    df = df.rename(columns={'datetime': 'date', 'vol': 'volume'})

    # 计算涨跌幅（pytdx 不返回涨跌幅）
    if 'pct_chg' not in df.columns and 'close' in df.columns:
        df['pct_chg'] = df['close'].pct_change() * 100
        df['pct_chg'] = df['pct_chg'].fillna(0).round(2)

    df['code'] = stock_code
    keep_cols = ['code'] + STANDARD_COLUMNS
    existing_cols = [col for col in keep_cols if col in df.columns]
    return df[existing_cols]


def demo_normalized_output():
    """7. 标准化数据输出"""
    print("\n" + "=" * 60)
    print("7. 标准化数据输出（贵州茅台 日K线）")
    print("=" * 60)
    with pytdx_session() as api:
        if api is None:
            return
        market, code = get_market_code("600519")
        data = api.get_security_bars(
            category=9, market=market, code=code, start=0, count=30
        )
        if data:
            df = api.to_df(data)
            df_std = normalize_pytdx_data(df, "600519")
            print(df_std.tail(10))


if __name__ == '__main__':
    demo_daily_kline()
    demo_minute_kline()
    demo_realtime_quote()
    demo_stock_list()
    demo_stock_name()
    demo_index_kline()
    demo_normalized_output()
