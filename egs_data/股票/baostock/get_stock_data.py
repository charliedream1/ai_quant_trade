# -*- coding: utf-8 -*-
# @Author   : ai_quant_trade
# @File     : get_stock_data.py
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
Baostock (证券宝) 数据接口示例
覆盖：日线行情、上下文管理器、代码转换、ETF判断、股票列表、股票名称

安装：pip install baostock
特点：免费、无需 Token、数据稳定
局限：仅支持沪深A股，不支持港股/美股/北交所，数据更新 T+1

参考来源：
  - daily_stock_analysis: data_provider/baostock_fetcher.py
    (上下文管理器、代码转换、ETF判断、延迟加载)
"""

import logging
from contextlib import contextmanager
from typing import Optional, Generator

import pandas as pd

# 兼容 pandas 2.0+：pandas 2.0 移除了 DataFrame.append，baostock 库内部仍在使用
if not hasattr(pd.DataFrame, 'append'):
    pd.DataFrame.append = lambda self, other, **kwargs: pd.concat(
        [self, other], **kwargs)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 120)

# 标准化输出列
STANDARD_COLUMNS = ['date', 'open', 'high', 'low', 'close', 'volume', 'amount', 'pct_chg']


# ---------------------------------------------------------------------------
# 代码转换工具（参考 daily_stock_analysis BaostockFetcher）
# ---------------------------------------------------------------------------

# ETF 代码前缀规则
ETF_SH_PREFIXES = ('51', '52', '56', '58')   # 上交所 ETF
ETF_SZ_PREFIXES = ('15', '16', '18')         # 深交所 ETF
ETF_ALL_PREFIXES = ETF_SH_PREFIXES + ETF_SZ_PREFIXES


def is_etf_code(stock_code: str) -> bool:
    """判断是否为 ETF 基金代码

    ETF 代码规则：
    - 上交所 ETF: 51xxxx, 52xxxx, 56xxxx, 58xxxx
    - 深交所 ETF: 15xxxx, 16xxxx, 18xxxx
    """
    code = stock_code.strip().split('.')[0]
    return code.startswith(ETF_ALL_PREFIXES) and len(code) == 6


def convert_stock_code(stock_code: str) -> str:
    """转换股票代码为 Baostock 格式

    Baostock 要求的格式：
    - 沪市：sh.600519
    - 深市：sz.000001

    支持输入格式：
    - 纯数字: '600519', '000001'
    - 带后缀: '600519.SH', '000001.SZ'

    Args:
        stock_code: 原始代码

    Returns:
        Baostock 格式代码，如 'sh.600519'
    """
    code = stock_code.strip()

    # 已经包含前缀
    if code.startswith(('sh.', 'sz.')):
        return code.lower()

    # 去除可能的后缀
    code = code.replace('.SH', '').replace('.SZ', '').replace('.sh', '').replace('.sz', '')

    # ETF: 上交所 ETF -> sh, 深交所 ETF -> sz
    if len(code) == 6:
        if code.startswith(ETF_SH_PREFIXES):
            return f"sh.{code}"
        if code.startswith(ETF_SZ_PREFIXES):
            return f"sz.{code}"

    # A股：根据代码前缀判断市场
    if code.startswith(('600', '601', '603', '688')):
        return f"sh.{code}"
    elif code.startswith(('000', '002', '300')):
        return f"sz.{code}"
    else:
        logger.warning(f"无法确定股票 {code} 的市场，默认使用深市")
        return f"sz.{code}"


# ---------------------------------------------------------------------------
# 上下文管理器（参考 daily_stock_analysis BaostockFetcher）
# ---------------------------------------------------------------------------

@contextmanager
def baostock_session() -> Generator:
    """Baostock 连接上下文管理器

    确保：
    1. 进入上下文时自动登录
    2. 退出上下文时自动登出
    3. 异常时也能正确登出

    使用示例：
        with baostock_session() as bs:
            rs = bs.query_history_k_data_plus(...)
    """
    import baostock as bs
    login_result = None

    try:
        login_result = bs.login()
        if login_result.error_code != '0':
            raise ConnectionError(f"Baostock 登录失败: {login_result.error_msg}")
        logger.debug("Baostock 登录成功")
        yield bs
    finally:
        try:
            logout_result = bs.logout()
            if logout_result.error_code == '0':
                logger.debug("Baostock 登出成功")
            else:
                logger.warning(f"Baostock 登出异常: {logout_result.error_msg}")
        except Exception as e:
            logger.warning(f"Baostock 登出时发生错误: {e}")


# ---------------------------------------------------------------------------
# 标准化数据输出
# ---------------------------------------------------------------------------

def normalize_data(df: pd.DataFrame, stock_code: str) -> pd.DataFrame:
    """标准化 Baostock 数据

    Baostock 返回列名：date, open, high, low, close, volume, amount, pctChg
    映射到标准列名：date, open, high, low, close, volume, amount, pct_chg
    """
    df = df.copy()
    df = df.rename(columns={'pctChg': 'pct_chg'})

    # 数值类型转换（Baostock 返回的都是字符串）
    numeric_cols = ['open', 'high', 'low', 'close', 'volume', 'amount', 'pct_chg']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    df['code'] = stock_code
    keep_cols = ['code'] + STANDARD_COLUMNS
    existing_cols = [col for col in keep_cols if col in df.columns]
    return df[existing_cols]


# ---------------------------------------------------------------------------
# 演示函数
# ---------------------------------------------------------------------------

def demo_daily_kline():
    """1. 日K线数据（使用上下文管理器）"""
    print("=" * 60)
    print("1. 贵州茅台(600519) 日K线")
    print("=" * 60)
    try:
        with baostock_session() as bs:
            bs_code = convert_stock_code("600519")
            rs = bs.query_history_k_data_plus(
                code=bs_code,
                fields="date,open,high,low,close,volume,amount,pctChg",
                start_date="2024-01-01",
                end_date="2024-01-31",
                frequency="d",
                adjustflag="2"   # 前复权
            )
            if rs.error_code != '0':
                print(f"  查询失败: {rs.error_msg}")
                return
            data_list = []
            while rs.next():
                data_list.append(rs.get_row_data())
            if not data_list:
                print("  无数据")
                return
            df = pd.DataFrame(data_list, columns=rs.fields)
            print(df.head())
            # 字段: date, open, high, low, close, volume, amount, pctChg
    except Exception as e:
        print(f"  获取失败: {e}")


def demo_etf_kline():
    """2. ETF日K线数据"""
    print("\n" + "=" * 60)
    print("2. 沪深300ETF(510300) 日K线")
    print("=" * 60)
    code = "510300"
    print(f"  是ETF: {is_etf_code(code)}")
    print(f"  Baostock代码: {convert_stock_code(code)}")

    try:
        with baostock_session() as bs:
            bs_code = convert_stock_code(code)
            rs = bs.query_history_k_data_plus(
                code=bs_code,
                fields="date,open,high,low,close,volume,amount,pctChg",
                start_date="2024-01-01",
                end_date="2024-01-31",
                frequency="d",
                adjustflag="2"
            )
            if rs.error_code != '0':
                print(f"  查询失败: {rs.error_msg}")
                return
            data_list = []
            while rs.next():
                data_list.append(rs.get_row_data())
            if not data_list:
                print("  无数据")
                return
            df = pd.DataFrame(data_list, columns=rs.fields)
            print(df.head())
    except Exception as e:
        print(f"  获取失败: {e}")


def demo_standardized_output():
    """3. 标准化数据输出"""
    print("\n" + "=" * 60)
    print("3. 标准化数据输出（贵州茅台）")
    print("=" * 60)
    try:
        with baostock_session() as bs:
            bs_code = convert_stock_code("600519")
            rs = bs.query_history_k_data_plus(
                code=bs_code,
                fields="date,open,high,low,close,volume,amount,pctChg",
                start_date="2024-01-01",
                end_date="2024-01-31",
                frequency="d",
                adjustflag="2"
            )
            data_list = []
            while rs.next():
                data_list.append(rs.get_row_data())
            if not data_list:
                print("  无数据")
                return
            df = pd.DataFrame(data_list, columns=rs.fields)
            df_std = normalize_data(df, "600519")
            print(df_std.head())
    except Exception as e:
        print(f"  获取失败: {e}")


def demo_stock_name():
    """4. 获取股票名称"""
    print("\n" + "=" * 60)
    print("4. 获取股票名称")
    print("=" * 60)
    try:
        with baostock_session() as bs:
            for code in ["600519", "000001", "510300"]:
                bs_code = convert_stock_code(code)
                rs = bs.query_stock_basic(code=bs_code)
                if rs.error_code == '0':
                    data_list = []
                    while rs.next():
                        data_list.append(rs.get_row_data())
                    if data_list:
                        fields = rs.fields
                        name_idx = fields.index('code_name') if 'code_name' in fields else None
                        name = data_list[0][name_idx] if name_idx is not None else "未知"
                        print(f"  {code} -> {name}")
    except Exception as e:
        print(f"  获取失败: {e}")


def demo_stock_list():
    """5. 获取股票列表"""
    print("\n" + "=" * 60)
    print("5. 全部A股列表（前10行）")
    print("=" * 60)
    try:
        with baostock_session() as bs:
            rs = bs.query_stock_basic()
            if rs.error_code == '0':
                data_list = []
                while rs.next():
                    data_list.append(rs.get_row_data())
                if data_list:
                    df = pd.DataFrame(data_list, columns=rs.fields)
                    # 去除 sh./sz. 前缀
                    df['code'] = df['code'].apply(lambda x: x.split('.')[1] if '.' in x else x)
                    df = df.rename(columns={'code_name': 'name'})
                    print(df[['code', 'name']].head(10))
    except Exception as e:
        print(f"  获取失败: {e}")


def demo_code_convert():
    """6. 代码转换示例"""
    print("\n" + "=" * 60)
    print("6. 代码转换示例")
    print("=" * 60)
    test_codes = [
        "600519",          # 纯数字
        "600519.SH",       # 带后缀
        "000001",          # 深市
        "510300",          # 上交所ETF
        "159915",          # 深交所ETF
        "688981",          # 科创板
    ]
    for code in test_codes:
        bs_code = convert_stock_code(code)
        etf = is_etf_code(code)
        print(f"  {code:12s} -> {bs_code:12s}  ETF: {etf}")


if __name__ == '__main__':
    demo_daily_kline()
    demo_etf_kline()
    demo_standardized_output()
    demo_stock_name()
    demo_stock_list()
    demo_code_convert()
