# -*- coding: utf-8 -*-
# @Author   : ai_quant_trade
# @File     : fred_demo.py
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
FRED 宏观经济数据接口示例
覆盖：GDP、CPI、失业率、利率、国债收益率、美元指数
安装：pip install fredapi
注意：需免费注册获取 API Key
"""

import pandas as pd
import requests
from io import StringIO

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 120)


# ============================================================
# 方式一：使用 fredapi 包（需 API Key）
# ============================================================
def demo_fredapi():
    """使用 fredapi 包获取数据"""
    from fredapi import Fred

    # 替换为你的 API Key
    # 注册地址：https://fred.stlouisfed.org/
    FRED_API_KEY = 'YOUR_FRED_API_KEY'

    fred = Fred(api_key=FRED_API_KEY)

    # 1. GDP（季度）
    print("=" * 60)
    print("1. 美国GDP（最近5个季度）")
    print("=" * 60)
    gdp = fred.get_series('GDP')
    print(gdp.tail())

    # 2. CPI（月度）
    print("\n" + "=" * 60)
    print("2. 美国CPI消费者物价指数（最近6个月）")
    print("=" * 60)
    cpi = fred.get_series('CPIAUCSL')
    print(cpi.tail(6))

    # 3. 失业率（月度）
    print("\n" + "=" * 60)
    print("3. 美国失业率（最近6个月）")
    print("=" * 60)
    unemployment = fred.get_series('UNRATE')
    print(unemployment.tail(6))

    # 4. 联邦基金利率（月度）
    print("\n" + "=" * 60)
    print("4. 美国联邦基金利率（最近6个月）")
    print("=" * 60)
    fed_funds = fred.get_series('FEDFUNDS')
    print(fed_funds.tail(6))

    # 5. 10年期国债收益率（日频）
    print("\n" + "=" * 60)
    print("5. 美国10年期国债收益率（最近5天）")
    print("=" * 60)
    ten_year = fred.get_series('GS10')
    print(ten_year.tail())

    # 6. 美元指数
    print("\n" + "=" * 60)
    print("6. 美元指数（最近5天）")
    print("=" * 60)
    dxy = fred.get_series('DTWEXBGS')
    print(dxy.tail())


# ============================================================
# 方式二：直接 CSV 下载（无需 API Key 和额外包）
# ============================================================
def demo_csv_download():
    """直接从 FRED 网站下载 CSV 数据（无需 API Key）"""
    print("=" * 60)
    print("直接从 FRED 下载 CSV 数据（无需 API Key）")
    print("=" * 60)

    indicators = {
        'GDP': '美国GDP（季度）',
        'CPIAUCSL': 'CPI消费者物价指数（月度）',
        'UNRATE': '失业率（月度）',
        'FEDFUNDS': '联邦基金利率（月度）',
        'GS10': '10年期国债收益率（月度）',
    }

    for series_id, desc in indicators.items():
        url = f'https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}'
        r = requests.get(url)
        if r.status_code == 200:
            df = pd.read_csv(StringIO(r.text))
            # 列名通常为 'date' 和 series_id
            print(f"\n{desc} ({series_id}):")
            print(df.tail(5))
        else:
            print(f"\n{desc} ({series_id}): 下载失败 HTTP {r.status_code}")


# ============================================================
# 方式三：使用 pandas_datareader（备选方案）
# ============================================================
def demo_pandas_datareader():
    """使用 pandas_datareader 获取 FRED 数据"""
    try:
        import pandas_datareader.data as web
        import datetime
    except Exception as e:
        print(f"pandas_datareader 不可用: {e}")
        print("请使用 demo_fredapi() 或 demo_csv_download() 替代")
        return

    print("=" * 60)
    print("使用 pandas_datareader 获取 FRED 数据")
    print("=" * 60)

    start = datetime.datetime(2020, 1, 1)
    end = datetime.datetime(2023, 12, 31)

    # 获取GDP
    gdp = web.DataReader('GDP', 'fred', start, end)
    print("GDP:")
    print(gdp.tail())

    # 获取多个指标
    df = web.DataReader(['GDP', 'UNRATE', 'CPIAUCSL'], 'fred', start, end)
    print("\n多指标:")
    print(df.tail())


if __name__ == '__main__':
    # 方式一需要 API Key
    # demo_fredapi()

    # 方式二无需 API Key，直接下载 CSV
    demo_csv_download()

    # 方式三为备选方案（部分 Python 版本可能不兼容）
    # demo_pandas_datareader()
