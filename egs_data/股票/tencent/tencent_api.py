# -*- coding: utf-8 -*-
# @Author   : ai_quant_trade
# @File     : tencent_api.py
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
腾讯财经 Web API 示例
覆盖：实时行情、历史日K线、分钟K线
无需安装额外库，使用 requests 即可
"""

import requests
import pandas as pd

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 120)


def get_realtime(code='sh601318'):
    """
    获取实时行情
    :param code: 股票代码，如 sh601318, sz000001, hk00700
    :return: dict
    """
    url = f'http://qt.gtimg.cn/q={code}'
    r = requests.get(url)
    r.encoding = 'gbk'
    text = r.text.strip()
    # 格式: v_sh601318="1~中国平安~601318~49.50~49.30~..."
    content = text.split('=')[1].strip('"')
    fields = content.split('~')
    result = {
        '代码': fields[2],
        '名称': fields[1],
        '最新价': fields[3],
        '昨收': fields[4],
        '今开': fields[5],
        '成交量(手)': fields[6],
        '外盘': fields[7],
        '内盘': fields[8],
        '买一价': fields[9],
        '卖一价': fields[19],
        '最高': fields[33],
        '最低': fields[34],
        '成交额(万)': fields[37],
        '换手率': fields[38],
        '市盈率': fields[39],
        '总市值(亿)': fields[45],
        '流通市值(亿)': fields[44],
        '涨跌幅': fields[32],
    }
    return result


def get_daily(code='sh601318', count=320, fqt='qfq'):
    """
    获取历史日K线
    :param code: 股票代码
    :param count: 获取K线数量，最大640
    :param fqt: 复权类型 qfq前复权/hfq后复权/空不复权
    :return: DataFrame
    """
    url = 'http://web.ifzq.gtimg.cn/appstock/app/fqkline/get'
    params = {'param': f'{code},day,,,{count},{fqt}'}
    r = requests.get(url, params=params)
    data = r.json().get('data', {}).get(code, {})
    # 日K线在 day 或 qfqday/hfqday 字段下
    day_data = data.get('day') or data.get('qfqday') or data.get('hfqday') or []
    # 部分行可能含第7列（分红信息dict），只取前6列
    rows = [row[:6] for row in day_data]
    df = pd.DataFrame(rows, columns=['日期', '开盘', '收盘', '最高',
                                     '最低', '成交量'])
    for col in ['开盘', '收盘', '最高', '最低', '成交量']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    return df


def get_minute(code='sh601318', mtype=5):
    """
    获取分钟K线
    :param code: 股票代码
    :param mtype: 分钟类型 1/5/15/30/60
    :return: DataFrame
    """
    url = 'http://ifzq.gtimg.cn/appstock/app/kline/mkline'
    params = {'param': f'{code},m{mtype},,320'}
    r = requests.get(url, params=params)
    data = r.json().get('data', {}).get(code, {})
    key = f'm{mtype}'
    minute_data = data.get(key, [])
    # 部分行可能含额外列（均价等），只取前6列
    rows = [row[:6] for row in minute_data]
    df = pd.DataFrame(rows, columns=['时间', '开盘', '收盘',
                                     '最高', '最低', '成交量'])
    for col in ['开盘', '收盘', '最高', '最低', '成交量']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    return df


if __name__ == '__main__':
    # 1. 实时行情
    print("=" * 60)
    print("1. 中国平安(sh601318) 实时行情")
    print("=" * 60)
    info = get_realtime('sh601318')
    for k, v in info.items():
        print(f"  {k}: {v}")

    # 2. 历史日K线
    print("\n" + "=" * 60)
    print("2. 中国平安(sh601318) 历史日K线（前复权）")
    print("=" * 60)
    df = get_daily('sh601318', count=100, fqt='qfq')
    print(df.tail())

    # 3. 5分钟K线
    print("\n" + "=" * 60)
    print("3. 中国平安(sh601318) 5分钟K线")
    print("=" * 60)
    df = get_minute('sh601318', mtype=5)
    print(df.tail())
