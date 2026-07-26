# -*- coding: utf-8 -*-
# @Author   : ai_quant_trade
# @File     : eastmoney_news_guba.py
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
东方财富新闻与股吧舆情接口示例
覆盖：个股公告新闻、股吧帖子、股吧热度
无需安装额外库，使用 requests + pandas 即可
"""

import requests
import pandas as pd
import re
import json
import time

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 120)
pd.set_option('display.max_colwidth', 50)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'https://data.eastmoney.com/'
}


def get_stock_news(stock_code='601318', page=1, page_size=10):
    """
    获取东方财富个股公告新闻
    :param stock_code: 股票代码，如 601318
    :param page: 页码
    :param page_size: 每页数量
    :return: DataFrame
    """
    url = 'https://np-anotice-stock.eastmoney.com/api/security/ann'
    params = {
        'cb': 'jQuery',
        'sr': '-1',
        'page_size': page_size,
        'page_index': page,
        'ann_type': 'A',
        'client_source': 'web',
        'stock_list': stock_code,
        'f_node': '0',
        's_node': '0',
    }
    r = requests.get(url, params=params, headers=HEADERS)
    text = r.text
    # 去除 JSONP 回调包装
    if text.startswith('jQuery'):
        text = text[text.index('(') + 1: text.rindex(')')]
    import json
    data = json.loads(text)
    items = data.get('data', {}).get('list', [])
    if not items:
        print("未搜索到新闻")
        return pd.DataFrame()

    rows = []
    for item in items:
        codes = item.get('codes', [{}])
        rows.append({
            '标题': item.get('title', ''),
            '发布时间': item.get('notice_date', ''),
            '股票代码': codes[0].get('stock_code', '') if codes else '',
            '股票名称': codes[0].get('short_name', '') if codes else '',
            '公告类型': item.get('columns', [{}])[0].get('column_name', '') if item.get('columns') else '',
            '公告链接': f"https://np-anotice-stock.eastmoney.com/api/security/ann?art_code={item.get('art_code', '')}",
        })
    return pd.DataFrame(rows)


def get_guba_posts(code='601318', page=1, page_size=20):
    """
    获取东方财富股吧帖子（通过解析页面内嵌JSON数据）
    :param code: 股票代码
    :param page: 页码
    :param page_size: 每页数量
    :return: DataFrame
    """
    headers = {
        'User-Agent': HEADERS['User-Agent'],
        'Referer': f'https://guba.eastmoney.com/list,{code}.html'
    }
    url = f'https://guba.eastmoney.com/list,{code},f_{page}.html'
    r = requests.get(url, headers=headers, timeout=15)
    # 页面内嵌 article_list 变量包含帖子JSON数据
    match = re.search(r'var article_list=(\{.*?\});', r.text, re.DOTALL)
    if not match:
        print("未找到股吧帖子数据（页面结构可能已变更）")
        return pd.DataFrame()

    try:
        data = json.loads(match.group(1))
    except json.JSONDecodeError:
        print("股吧数据解析失败")
        return pd.DataFrame()

    posts = data.get('re', [])
    if not posts:
        print("未获取到股吧帖子")
        return pd.DataFrame()

    rows = []
    for p in posts[:page_size]:
        title = p.get('post_title', '') or (p.get('post_content', '') or '')[:50]
        rows.append({
            '标题': title,
            '发布时间': p.get('post_publish_time', ''),
            '阅读量': p.get('post_click_count', 0),
            '评论数': p.get('post_comment_count', 0),
            '点赞数': p.get('post_like_count', 0),
            '来源': p.get('post_from', ''),
        })
    return pd.DataFrame(rows)


def get_guba_hot_list(page=1, page_size=20):
    """
    获取股吧热门帖子列表（全局热门，通过东财热门股吧页面）
    :return: DataFrame
    """
    headers = {
        'User-Agent': HEADERS['User-Agent'],
        'Referer': 'https://guba.eastmoney.com/'
    }
    # 热门股吧 - 使用上证指数股吧作为热门入口
    url = f'https://guba.eastmoney.com/list,000001,f_{page}.html'
    r = requests.get(url, headers=headers, timeout=15)
    match = re.search(r'var article_list=(\{.*?\});', r.text, re.DOTALL)
    if not match:
        print("未找到热门帖子数据（页面结构可能已变更）")
        return pd.DataFrame()

    try:
        data = json.loads(match.group(1))
    except json.JSONDecodeError:
        print("热门数据解析失败")
        return pd.DataFrame()

    posts = data.get('re', [])
    if not posts:
        print("未获取到热门帖子")
        return pd.DataFrame()

    rows = []
    for p in posts[:page_size]:
        title = p.get('post_title', '') or (p.get('post_content', '') or '')[:50]
        rows.append({
            '标题': title,
            '发布时间': p.get('post_publish_time', ''),
            '阅读量': p.get('post_click_count', 0),
            '评论数': p.get('post_comment_count', 0),
            '点赞数': p.get('post_like_count', 0),
        })
    return pd.DataFrame(rows)


if __name__ == '__main__':
    # 1. 个股公告新闻
    print("=" * 60)
    print("1. 中国平安(601318) 公告新闻")
    print("=" * 60)
    df = get_stock_news(stock_code='601318', page=1, page_size=10)
    print(df)

    time.sleep(1)

    # 2. 股吧帖子
    print("\n" + "=" * 60)
    print("2. 中国平安(601318) 股吧帖子")
    print("=" * 60)
    df = get_guba_posts(code='601318', page=1, page_size=10)
    print(df)

    time.sleep(1)

    # 3. 股吧热门
    print("\n" + "=" * 60)
    print("3. 股吧热门帖子")
    print("=" * 60)
    df = get_guba_hot_list()
    print(df)
