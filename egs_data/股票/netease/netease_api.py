# -*- coding: utf-8 -*-
# @Author   : ai_quant_trade
# @File     : netease_api.py
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
网易财经 Web API 示例
覆盖：历史日K线（CSV下载）、实时行情
无需安装额外库，使用 requests + pandas 即可
"""

import requests
import pandas as pd
from io import StringIO

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 120)


def get_history(code='600000', start='20230101', end='20231231'):
    """
    获取股票历史日K线数据（CSV下载方式）
    :param code: 6位股票代码，如 600000(浦发银行) 601318(中国平安)
    :param start: 开始日期 YYYYMMDD
    :param end: 结束日期 YYYYMMDD
    :return: DataFrame
    """
    # 判断市场前缀：沪市0，深市1
    prefix = '0' if code.startswith(('6', '9')) else '1'

    url = 'http://quotes.money.163.com/service/chddata.html'
    params = {
        'code': f'{prefix}{code}',
        'start': start,
        'end': end,
        'fields': 'TCLOSE;HIGH;LOW;TOPEN;LCLOSE;CHG;PCHG;TURNOVER;'
                  'VOTURNOVER;VATURNOVER;TCAP;MCAP'
    }
    r = requests.get(url, params=params)
    r.encoding = 'gbk'
    df = pd.read_csv(StringIO(r.text))
    # 列名中文化
    col_map = {
        '日期': '日期', '股票代码': '股票代码', '名称': '名称',
        '收盘价': '收盘价', '最高价': '最高价', '最低价': '最低价',
        '开盘价': '开盘价', '前收盘': '前收盘', '涨跌额': '涨跌额',
        '涨跌幅': '涨跌幅', '换手率': '换手率', '成交量': '成交量',
        '成交金额': '成交额', '总市值': '总市值', '流通市值': '流通市值'
    }
    df.rename(columns=col_map, inplace=True)
    return df


def get_realtime(codes=None):
    """
    获取实时行情（网易接口）
    :param codes: 股票代码列表，如 ['600000','601318']
    :return: DataFrame
    """
    if codes is None:
        codes = ['600000', '601318']

    # 网易实时行情接口
    # 沪市前缀0，深市前缀1
    code_list = []
    for code in codes:
        prefix = '0' if code.startswith(('6', '9')) else '1'
        code_list.append(f'{prefix}{code}')

    url = 'http://api.money.126.net/data/feed/'
    full_url = url + ','.join(code_list) + ',?callback=a'
    r = requests.get(full_url)
    text = r.text
    # 去除 JSONP 回调包装
    text = text.strip('a(').rstrip(')')
    import json
    data = json.loads(text)
    rows = []
    for k, v in data.items():
        rows.append({
            '代码': v.get('symbol'),
            '名称': v.get('name'),
            '最新价': v.get('price'),
            '涨跌幅': v.get('percent'),
            '涨跌额': v.get('updown'),
            '开盘价': v.get('open'),
            '最高价': v.get('high'),
            '最低价': v.get('low'),
            '成交量': v.get('volume'),
            '成交额': v.get('amount'),
            '昨收': v.get('yestclose'),
        })
    return pd.DataFrame(rows)


if __name__ == '__main__':
    # 1. 历史日K线
    print("=" * 60)
    print("1. 浦发银行(600000) 历史日K线")
    print("=" * 60)
    df = get_history(code='600000', start='20230101', end='20231231')
    print(df.head())

    # 2. 实时行情
    print("\n" + "=" * 60)
    print("2. 实时行情")
    print("=" * 60)
    df = get_realtime(['600000', '601318'])
    print(df)
