# -*- coding: utf-8 -*-
# @Author   : ai_quant_trade
# @File     : finnhub_demo.py
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
Finnhub 国际财经新闻+情绪数据接口示例
覆盖：市场新闻、公司新闻、新闻情绪分析
安装：pip install finnhub-python
注意：需免费注册获取 API Key
"""

import pandas as pd
from datetime import datetime, timedelta

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 120)
pd.set_option('display.max_colwidth', 50)


# ============================================================
# 方式一：使用 finnhub-python SDK
# ============================================================
def demo_finnhub_sdk():
    """使用 finnhub-python SDK 获取数据"""
    import finnhub

    # 替换为你的 API Key
    # 注册地址：https://finnhub.io/
    API_KEY = 'YOUR_FINNHUB_API_KEY'

    client = finnhub.Client(api_key=API_KEY)

    # 1. 市场新闻（通用财经新闻）
    print("=" * 60)
    print("1. 市场新闻（前10条）")
    print("=" * 60)
    news = client.general_news('general', min_id=0)
    df = pd.DataFrame(news[:10])
    if not df.empty:
        cols = ['headline', 'summary', 'source', 'datetime', 'url']
        available = [c for c in cols if c in df.columns]
        df = df[available]
        if 'datetime' in df.columns:
            df['datetime'] = pd.to_datetime(df['datetime'], unit='s')
        print(df)

    # 2. 公司新闻（按股票代码）
    print("\n" + "=" * 60)
    print("2. 苹果(AAPL) 公司新闻")
    print("=" * 60)
    today = datetime.now().strftime('%Y-%m-%d')
    week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    company_news = client.company_news('AAPL', _from=week_ago, to=today)
    df = pd.DataFrame(company_news[:10])
    if not df.empty:
        cols = ['headline', 'summary', 'source', 'datetime', 'url']
        available = [c for c in cols if c in df.columns]
        df = df[available]
        if 'datetime' in df.columns:
            df['datetime'] = pd.to_datetime(df['datetime'], unit='s')
        print(df)

    # 3. 新闻情绪分析
    print("\n" + "=" * 60)
    print("3. 新闻情绪分析")
    print("=" * 60)
    sentiment = client.news_sentiment('AAPL')
    print(f"  看涨情绪占比: {sentiment.get('bullishPercent', 0) * 100:.1f}%")
    print(f"  看跌情绪占比: {sentiment.get('bearishPercent', 0) * 100:.1f}%")
    buzz = sentiment.get('buzz', {})
    print(f"  新闻热度: {buzz.get('buzz', 0)}")
    print(f"  周文章数: {buzz.get('weeklyArticles', 0)}")


# ============================================================
# 方式二：直接使用 requests 调用 REST API
# ============================================================
def demo_requests():
    """直接使用 requests 调用 Finnhub API"""
    import requests

    # 替换为你的 API Key
    API_KEY = 'YOUR_FINNHUB_API_KEY'
    base_url = 'https://finnhub.io/api/v1'

    # 1. 市场新闻
    print("=" * 60)
    print("使用 requests 调用 Finnhub API - 市场新闻")
    print("=" * 60)

    r = requests.get(f'{base_url}/news', params={
        'category': 'general',
        'token': API_KEY
    })
    if r.status_code == 200:
        news = r.json()
        print(f"获取到 {len(news)} 条新闻")
        for n in news[:5]:
            print(f"  [{n.get('source', '')}] {n.get('headline', '')[:60]}")
    else:
        print(f"请求失败: HTTP {r.status_code}")

    # 2. 公司新闻
    print("\n" + "=" * 60)
    print("使用 requests 调用 Finnhub API - 公司新闻")
    print("=" * 60)

    today = datetime.now().strftime('%Y-%m-%d')
    week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    r = requests.get(f'{base_url}/company-news', params={
        'symbol': 'AAPL',
        'from': week_ago,
        'to': today,
        'token': API_KEY
    })
    if r.status_code == 200:
        news = r.json()
        print(f"获取到 {len(news)} 条公司新闻")
        for n in news[:5]:
            print(f"  [{n.get('source', '')}] {n.get('headline', '')[:60]}")
    else:
        print(f"请求失败: HTTP {r.status_code}")


if __name__ == '__main__':
    # 方式一：使用 finnhub-python SDK（需 API Key）
    # demo_finnhub_sdk()

    # 方式二：使用 requests（需 API Key）
    # demo_requests()

    print("请替换 YOUR_FINNHUB_API_KEY 后取消注释运行")
    print("API Key 注册地址: https://finnhub.io/")
