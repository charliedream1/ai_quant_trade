# -*- coding: utf-8 -*-
# @Author   : ai_quant_trade
# @File     : newsapi_demo.py
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
NewsAPI.org 国际财经新闻接口示例
覆盖：头条新闻、新闻搜索、新闻源列表
安装：pip install newsapi-python
注意：需免费注册获取 API Key
"""

import pandas as pd
from datetime import datetime, timedelta

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 120)
pd.set_option('display.max_colwidth', 50)


# ============================================================
# 方式一：使用 newsapi-python SDK
# ============================================================
def demo_newsapi_sdk():
    """使用 newsapi-python SDK 获取数据"""
    from newsapi import NewsApiClient

    # 替换为你的 API Key
    # 注册地址：https://newsapi.org/
    API_KEY = 'YOUR_NEWSAPI_KEY'

    newsapi = NewsApiClient(api_key=API_KEY)

    # 1. 财经头条新闻（美国）
    print("=" * 60)
    print("1. 美国财经头条新闻")
    print("=" * 60)
    top_headlines = newsapi.get_top_headlines(
        category='business',
        country='us',
        page_size=10,
        page=1
    )
    articles = top_headlines.get('articles', [])
    df = pd.DataFrame(articles)
    if not df.empty:
        cols = ['title', 'description', 'source', 'author',
                'publishedAt', 'url']
        available = [c for c in cols if c in df.columns]
        # source 是 dict，提取 name
        if 'source' in df.columns:
            df['source'] = df['source'].apply(
                lambda x: x.get('name', '') if isinstance(x, dict) else ''
            )
        print(df[available])

    # 2. 搜索财经新闻
    print("\n" + "=" * 60)
    print("2. 搜索财经新闻（stock market）")
    print("=" * 60)
    today = datetime.now().strftime('%Y-%m-%d')
    week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    all_news = newsapi.get_everything(
        q='stock market OR finance OR economy',
        from_param=week_ago,
        to=today,
        language='en',
        sort_by='relevancy',
        page_size=10,
        page=1
    )
    articles = all_news.get('articles', [])
    df = pd.DataFrame(articles)
    if not df.empty:
        cols = ['title', 'description', 'source', 'publishedAt', 'url']
        available = [c for c in cols if c in df.columns]
        if 'source' in df.columns:
            df['source'] = df['source'].apply(
                lambda x: x.get('name', '') if isinstance(x, dict) else ''
            )
        print(df[available])

    # 3. 财经新闻源列表
    print("\n" + "=" * 60)
    print("3. 财经新闻源列表")
    print("=" * 60)
    sources = newsapi.get_sources(
        category='business',
        language='en',
        country='us'
    )
    src_list = sources.get('sources', [])
    df = pd.DataFrame(src_list)
    if not df.empty:
        cols = ['name', 'description', 'url', 'category']
        available = [c for c in cols if c in df.columns]
        print(df[available].head(10))


# ============================================================
# 方式二：直接使用 requests 调用 REST API
# ============================================================
def demo_requests():
    """直接使用 requests 调用 NewsAPI"""
    import requests

    API_KEY = 'YOUR_NEWSAPI_KEY'
    base_url = 'https://newsapi.org/v2'

    # 1. 财经头条新闻
    print("=" * 60)
    print("使用 requests 调用 NewsAPI - 财经头条")
    print("=" * 60)

    r = requests.get(f'{base_url}/top-headlines', params={
        'category': 'business',
        'country': 'us',
        'pageSize': 10,
        'apiKey': API_KEY
    })
    if r.status_code == 200:
        data = r.json()
        articles = data.get('articles', [])
        print(f"获取到 {len(articles)} 条新闻")
        for a in articles[:5]:
            src = a.get('source', {}).get('name', '')
            print(f"  [{src}] {a.get('title', '')[:60]}")
    else:
        print(f"请求失败: HTTP {r.status_code} - {r.text[:100]}")

    # 2. 搜索新闻
    print("\n" + "=" * 60)
    print("使用 requests 调用 NewsAPI - 搜索新闻")
    print("=" * 60)

    today = datetime.now().strftime('%Y-%m-%d')
    week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    r = requests.get(f'{base_url}/everything', params={
        'q': 'stock market',
        'from': week_ago,
        'to': today,
        'language': 'en',
        'sortBy': 'relevancy',
        'pageSize': 10,
        'apiKey': API_KEY
    })
    if r.status_code == 200:
        data = r.json()
        articles = data.get('articles', [])
        print(f"获取到 {len(articles)} 条新闻")
        for a in articles[:5]:
            src = a.get('source', {}).get('name', '')
            print(f"  [{src}] {a.get('title', '')[:60]}")
    else:
        print(f"请求失败: HTTP {r.status_code}")


if __name__ == '__main__':
    # 需替换 YOUR_NEWSAPI_KEY 后取消注释运行
    # demo_newsapi_sdk()
    # demo_requests()

    print("请替换 YOUR_NEWSAPI_KEY 后取消注释运行")
    print("API Key 注册地址: https://newsapi.org/")
