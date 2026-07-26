# -*- coding: utf-8 -*-
# @Author   : ai_quant_trade
# @File     : fund_demo.py
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
基金数据接口示例
覆盖：开放式基金净值、基金排行、基金持仓、ETF行情
数据源：AKShare（东方财富）+ efinance
安装：pip install akshare efinance
无需 API Key
"""

import pandas as pd
import signal
import functools

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 120)
pd.set_option('display.max_colwidth', 30)


class TimeoutError(Exception):
    pass


def _timeout_handler(signum, frame):
    raise TimeoutError("请求超时")


def with_timeout(seconds=30):
    """超时控制装饰器，避免被阻断的接口卡住整个脚本"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if not hasattr(signal, 'SIGALRM'):
                return func(*args, **kwargs)
            old_handler = signal.signal(signal.SIGALRM, _timeout_handler)
            signal.alarm(seconds)
            try:
                return func(*args, **kwargs)
            finally:
                signal.alarm(0)
                signal.signal(signal.SIGALRM, old_handler)
        return wrapper
    return decorator


def safe_call(func, name, timeout_sec=30):
    """安全调用，捕获异常并打印结果"""
    print("=" * 60)
    print(name)
    print("=" * 60)
    try:
        wrapped = with_timeout(timeout_sec)(func)
        df = wrapped()
        if df is not None and not df.empty:
            print(df.head(10))
            print(f"\n共 {len(df)} 条记录")
        else:
            print("未获取到数据")
        return df
    except Exception as e:
        print(f"获取失败: {str(e)[:120]}")
        return None


def demo_fund_nav():
    """1. 开放式基金净值走势（招商中证白酒 161725）"""
    import akshare as ak
    df = ak.fund_open_fund_info_em(symbol='161725', indicator='累计净值走势')
    return df


def demo_fund_rank():
    """2. 开放式基金业绩排行（全部）"""
    import akshare as ak
    df = ak.fund_open_fund_rank_em(symbol='全部')
    return df


def demo_fund_holdings():
    """3. 基金股票持仓（招商中证白酒 161725）"""
    import akshare as ak
    df = ak.fund_portfolio_hold_em(symbol='161725', date='2024')
    return df


def demo_etf_hist():
    """4. ETF历史行情（沪深300ETF 510300）"""
    import akshare as ak
    df = ak.fund_etf_hist_em(
        symbol='510300', period='daily',
        start_date='20240101', end_date='20240601', adjust='qfq'
    )
    return df


def demo_fund_nav_efinance():
    """5. 基金净值（efinance 备选方案）"""
    import efinance as ef
    df = ef.fund.get_quote_history('161725')
    return df


if __name__ == '__main__':
    # 1. 基金净值走势
    safe_call(demo_fund_nav, "1. 招商中证白酒(161725) 累计净值走势")

    # 2. 基金排行
    safe_call(demo_fund_rank, "2. 开放式基金业绩排行（全部）")

    # 3. 基金持仓
    safe_call(demo_fund_holdings, "3. 招商中证白酒(161725) 股票持仓")

    # 4. ETF行情（需东财可访问，部分网络环境可能被阻断）
    safe_call(demo_etf_hist, "4. 沪深300ETF(510300) 历史行情", timeout_sec=30)

    # 5. 基金净值（efinance 备选）
    safe_call(demo_fund_nav_efinance, "5. 基金净值（efinance 备选方案）")
