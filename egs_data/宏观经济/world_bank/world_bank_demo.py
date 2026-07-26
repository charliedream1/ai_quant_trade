# -*- coding: utf-8 -*-
# @Author   : ai_quant_trade
# @File     : world_bank_demo.py
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
World Bank 全球经济数据接口示例
覆盖：GDP、人口、CPI、失业率等全球指标
安装：pip install wbdata
无需 API Key
"""

import os
import tempfile

# 设置 wbdata 缓存到可写目录，避免沙箱限制写入 AppData
os.environ.setdefault('WBDATA_CACHE_PATH',
                      os.path.join(tempfile.gettempdir(), 'wbdata_cache'))

import pandas as pd
import datetime

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 120)


def demo_wbdata():
    """使用 wbdata 包获取数据"""
    import wbdata

    # 1. 查询国家列表
    print("=" * 60)
    print("1. 查询国家列表（前10个）")
    print("=" * 60)
    countries = wbdata.get_countries()
    for c in countries[:10]:
        print(f"  {c['id']}: {c['name']}")

    # 2. 获取中国GDP
    print("\n" + "=" * 60)
    print("2. 中国GDP（2010-2023）")
    print("=" * 60)
    result = wbdata.get_data('NY.GDP.MKTP.CD', country='CHN',
                            date=('2010', '2023'))
    # get_data 返回 Result 对象，可直接转为 DataFrame
    df = pd.DataFrame(result)
    if 'value' in df.columns:
        df['value'] = pd.to_numeric(df['value'], errors='coerce')
    print(df[['date', 'value']].sort_values('date') if 'date' in df.columns else df)

    # 3. 多国多指标对比
    print("\n" + "=" * 60)
    print("3. 中美日 GDP与人口对比")
    print("=" * 60)
    indicators = {
        'NY.GDP.MKTP.CD': 'GDP(美元)',
        'SP.POP.TOTL': '人口',
        'NY.GDP.PCAP.CD': '人均GDP(美元)'
    }
    # wbdata.get_dataframe 在某些版本中传入 country 列表会报
    # TypeError: unhashable type: dict，改为逐国获取后合并
    frames = []
    for country_code in ['CHN', 'USA', 'JPN']:
        df_c = wbdata.get_dataframe(indicators, country=country_code)
        df_c['country'] = country_code
        frames.append(df_c.reset_index())
    df = pd.concat(frames, ignore_index=True)
    df = df.sort_values(['country', 'date'], ascending=[True, False])
    print(df.head(20))


def demo_pandas_datareader():
    """使用 pandas_datareader 获取 World Bank 数据（备选方案）"""
    try:
        import pandas_datareader.data as web
    except Exception as e:
        print(f"pandas_datareader 不可用: {e}")
        print("请使用 demo_wbdata() 或 demo_requests() 替代")
        return

    print("\n" + "=" * 60)
    print("使用 pandas_datareader 获取 World Bank 数据")
    print("=" * 60)

    start = datetime.datetime(2010, 1, 1)
    end = datetime.datetime(2023, 12, 31)

    # 中国GDP
    gdp_chn = web.DataReader('NY.GDP.MKTP.CD', 'wb', start, end, country='CHN')
    print("中国GDP:")
    print(gdp_chn.tail())

    # 多国GDP
    gdp_multi = web.DataReader('NY.GDP.MKTP.CD', 'wb', start, end,
                               country=['CHN', 'USA', 'JPN', 'DEU'])
    print("\n多国GDP:")
    print(gdp_multi.tail())


def demo_requests():
    """直接使用 requests 调用 World Bank API（无需安装额外包）"""
    import requests

    print("\n" + "=" * 60)
    print("直接调用 World Bank API（requests）")
    print("=" * 60)

    # 1. 获取中国GDP
    url = 'https://api.worldbank.org/v2/country/CHN/indicator/NY.GDP.MKTP.CD'
    params = {'format': 'json', 'date': '2010:2023', 'per_page': 100}
    r = requests.get(url, params=params)
    data = r.json()
    if len(data) > 1:
        df = pd.DataFrame(data[1])
        df['value'] = pd.to_numeric(df['value'], errors='coerce')
        print("中国GDP:")
        print(df[['date', 'value']].sort_values('date'))

    # 2. 多国GDP对比
    print("\n多国GDP对比:")
    url = 'https://api.worldbank.org/v2/country/CHN;USA;JPN/indicator/NY.GDP.MKTP.CD'
    params = {'format': 'json', 'date': '2020:2023', 'per_page': 100}
    r = requests.get(url, params=params)
    data = r.json()
    if len(data) > 1:
        df = pd.DataFrame(data[1])
        df['value'] = pd.to_numeric(df['value'], errors='coerce')
        # 只取需要的列，避免 dict 列导致 drop_duplicates 失败
        df = df[['date', 'countryiso3code', 'value']].copy()
        df.columns = ['date', 'country', 'value']
        df = df.dropna(subset=['value']).drop_duplicates(
            subset=['date', 'country'])
        pivot = df.pivot(index='date', columns='country', values='value')
        print(pivot)


if __name__ == '__main__':
    demo_wbdata()
    demo_requests()
