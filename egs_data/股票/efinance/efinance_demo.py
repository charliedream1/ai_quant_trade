# -*- coding: utf-8 -*-
# @Author   : ai_quant_trade
# @File     : efinance_demo.py
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
efinance 免费金融数据接口示例
覆盖：股票行情、实时行情、基金数据、可转债、基本信息
安装：pip install efinance

注意：efinance 底层调用东方财富 push2his.eastmoney.com 接口，
若该接口被封锁（返回 ConnectionError），会自动回退到 akshare 库。
"""

import efinance as ef
import pandas as pd

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 120)


def _fallback_akshare(name, func, *args, **kwargs):
    """efinance 失败时回退到 akshare"""
    try:
        import akshare as ak
        print(f"  [efinance 失败，回退到 akshare]")
        return func(*args, **kwargs)
    except Exception as e:
        print(f"  [akshare 也失败: {e}]")
        return pd.DataFrame()


def demo_stock_history():
    """1. 股票历史行情"""
    print("=" * 60)
    print("1. 中国平安(601318) 历史日K线")
    print("=" * 60)
    try:
        df = ef.stock.get_quote_history('601318')
        if df is None or df.empty:
            raise Exception("efinance 返回空数据")
        print(df.head())
    except Exception as e:
        print(f"  efinance 错误: {str(e)[:80]}")
        # akshare 的 stock_zh_a_hist 也用 push2his.eastmoney.com，同样会被拒
        # 改用 baostock（不同数据源）
        try:
            import baostock as bs
            lg = bs.login()
            rs = bs.query_history_k_data_plus(
                'sh.601318',
                'date,code,open,high,low,close,volume,amount,pctChg',
                start_date='2024-01-01', end_date='2024-03-01',
                frequency='d', adjustflag='2')
            df = rs.get_data()
            bs.logout()
            print("  [回退到 baostock 成功]")
            print(df.head())
        except Exception as e2:
            print(f"  baostock 也失败: {str(e2)[:80]}")


def demo_stock_realtime():
    """2. 股票实时行情"""
    print("\n" + "=" * 60)
    print("2. A股实时行情（前5行）")
    print("=" * 60)
    try:
        df = ef.stock.get_realtime_quotes()
        if df is None or df.empty:
            raise Exception("efinance 返回空数据")
        print(df.head())
    except Exception as e:
        print(f"  efinance 错误: {str(e)[:80]}")
        # 用新浪实时行情接口
        try:
            import requests
            r = requests.get(
                'https://hq.sinajs.cn/list=sh601318',
                headers={'Referer': 'https://finance.sina.com.cn/'},
                timeout=10)
            print("  [回退到新浪实时行情]")
            print(f"  {r.text[:100]}")
        except Exception as e2:
            print(f"  新浪也失败: {str(e2)[:80]}")


def demo_stock_info():
    """3. 个股基本信息"""
    print("\n" + "=" * 60)
    print("3. 中国平安(601318) 基本信息")
    print("=" * 60)
    try:
        df = ef.stock.get_base_info('601318')
        print(df)
    except Exception as e:
        print(f"  efinance 错误: {str(e)[:80]}")


def demo_fund_history():
    """4. 基金历史净值"""
    print("\n" + "=" * 60)
    print("4. 招商中证白酒基金(161725) 历史净值")
    print("=" * 60)
    try:
        df = ef.fund.get_quote_history('161725')
        if df is None or df.empty:
            raise Exception("efinance 返回空数据")
        print(df.head())
    except Exception as e:
        print(f"  efinance 错误: {str(e)[:80]}")
        # 用天天基金网直接请求
        try:
            import requests
            url = 'https://api.fund.eastmoney.com/f10/lsjz'
            params = {
                'fundCode': '161725', 'pageIndex': 1, 'pageSize': 5,
                'startDate': '', 'endDate': ''
            }
            r = requests.get(url, params=params,
                             headers={'Referer': 'https://fundf10.eastmoney.com/'},
                             timeout=10)
            data = r.json()
            print("  [回退到天天基金网]")
            for item in data.get('Data', {}).get('LSJZList', []):
                print(f"  {item.get('FSRQ', '')}  净值: {item.get('DWJZ', '')}")
        except Exception as e2:
            print(f"  天天基金也失败: {str(e2)[:80]}")


def demo_bond_history():
    """5. 可转债历史行情"""
    print("\n" + "=" * 60)
    print("5. 中行转债(113001) 历史行情")
    print("=" * 60)
    try:
        df = ef.stock.get_quote_history('113001', klt=101)  # klt=101 日K
        if df is None or df.empty:
            raise Exception("efinance 返回空数据")
        print(df.head())
    except Exception as e:
        print(f"  efinance 错误: {str(e)[:80]}")


def demo_belong_board():
    """6. 个股所属板块"""
    print("\n" + "=" * 60)
    print("6. 中国平安(601318) 所属板块")
    print("=" * 60)
    try:
        df = ef.stock.get_belong_board('601318')
        print(df)
    except Exception as e:
        print(f"  efinance 错误: {str(e)[:80]}")


if __name__ == '__main__':
    demo_stock_history()
    demo_stock_realtime()
    demo_stock_info()
    demo_fund_history()
    demo_bond_history()
    demo_belong_board()
