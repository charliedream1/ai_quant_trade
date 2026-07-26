# -*- coding: utf-8 -*-
# @Author   : ai_quant_trade
# @File     : eastmoney_api.py
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
东方财富 Web API 示例
覆盖：历史K线、实时行情、资金流向
无需安装额外库，使用 requests + pandas 即可
"""

import requests
import pandas as pd
import time

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 120)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'https://quote.eastmoney.com/'
}


def get_kline(secid='1.601318', klt=101, fqt=1, beg='20230101', end='20231231'):
    """
    获取股票历史K线数据
    :param secid: 证券ID，格式 市场.代码，如 1.601318(沪市平安) 0.000001(深市平安银行)
    :param klt: K线类型 5/15/30/60分钟, 101日, 102周, 103月
    :param fqt: 复权 0不复权/1前复权/2后复权
    :param beg: 开始日期 YYYYMMDD
    :param end: 结束日期 YYYYMMDD
    :return: DataFrame
    """
    url = 'http://push2his.eastmoney.com/api/qt/stock/kline/get'
    params = {
        'secid': secid,
        'klt': klt,
        'fqt': fqt,
        'beg': beg,
        'end': end,
        'fields1': 'f1,f2,f3,f4,f5,f6',
        'fields2': 'f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61',
        'ut': 'fa5fd1943c7b386f172d6893dbbd1',
        '_': str(int(time.time() * 1000))
    }
    r = requests.get(url, params=params, headers=HEADERS)
    data = r.json().get('data', {})
    klines = data.get('klines', [])
    if not klines:
        print("未获取到数据")
        return pd.DataFrame()

    # 解析数据：格式 "日期,开盘,收盘,最高,最低,成交量,成交额,振幅,涨跌幅,涨跌额,换手率"
    rows = [k.split(',') for k in klines]
    df = pd.DataFrame(rows, columns=['日期', '开盘', '收盘', '最高', '最低',
                                     '成交量', '成交额', '振幅', '涨跌幅',
                                     '涨跌额', '换手率'])
    # 转换数值类型
    for col in ['开盘', '收盘', '最高', '最低', '成交量', '成交额',
                '振幅', '涨跌幅', '涨跌额', '换手率']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    return df


def get_realtime(secid='1.601318'):
    """
    获取股票实时行情
    :param secid: 证券ID
    :return: dict
    """
    url = 'http://push2.eastmoney.com/api/qt/stock/get'
    params = {
        'secid': secid,
        'fields': 'f43,f44,f45,f46,f47,f48,f50,f51,f52,f55,f57,f58,f60,f116,f117,f162,f167,f170,f171',
        'ut': 'fa5fd1943c7b386f172d6893dbbd1'
    }
    r = requests.get(url, params=params, headers=HEADERS)
    data = r.json().get('data', {})
    # 字段映射
    field_map = {
        'f43': '最新价', 'f44': '最高', 'f45': '最低', 'f46': '今开',
        'f47': '成交量', 'f48': '成交额', 'f50': '量比', 'f51': '涨停',
        'f52': '跌停', 'f55': '涨速', 'f57': '代码', 'f58': '名称',
        'f60': '昨收', 'f116': '总市值', 'f117': '流通市值',
        'f162': '市盈率(动)', 'f167': '市净率', 'f170': '涨跌幅', 'f171': '涨跌额'
    }
    result = {field_map.get(k, k): v for k, v in data.items()}
    return result


def get_money_flow(secid='1.601318', klt=101):
    """
    获取股票资金流向（日级）
    :param secid: 证券ID
    :param klt: K线类型
    :return: DataFrame
    """
    url = 'http://push2his.eastmoney.com/api/qt/stock/fflow/daykline/get'
    params = {
        'secid': secid,
        'klt': klt,
        'fields1': 'f1,f2,f3,f7',
        'fields2': 'f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63,f64,f65',
        'ut': 'b2884a393a59ad64002292a3e90d46a5'
    }
    r = requests.get(url, params=params, headers=HEADERS)
    data = r.json().get('data', {})
    klines = data.get('klines', [])
    if not klines:
        print("未获取到数据")
        return pd.DataFrame()

    rows = [k.split(',') for k in klines]
    df = pd.DataFrame(rows, columns=['日期', '主力净流入', '小单净流入',
                                     '中单净流入', '大单净流入', '超大单净流入'])
    for col in df.columns[1:]:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    return df


if __name__ == '__main__':
    # 1. 历史K线
    print("=" * 60)
    print("1. 中国平安(601318) 历史日K线")
    print("=" * 60)
    df = get_kline(secid='1.601318', klt=101, fqt=1,
                  beg='20230101', end='20231231')
    print(df.head())

    # 2. 实时行情
    print("\n" + "=" * 60)
    print("2. 中国平安(601318) 实时行情")
    print("=" * 60)
    info = get_realtime(secid='1.601318')
    for k, v in info.items():
        print(f"  {k}: {v}")

    # 3. 资金流向
    print("\n" + "=" * 60)
    print("3. 中国平安(601318) 资金流向")
    print("=" * 60)
    df = get_money_flow(secid='1.601318', klt=101)
    print(df.tail())
