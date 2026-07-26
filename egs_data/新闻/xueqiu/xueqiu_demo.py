# -*- coding: utf-8 -*-
# @Author   : ai_quant_trade
# @File     : xueqiu_demo.py
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
雪球网舆情数据接口示例
覆盖：股票讨论帖、用户动态、热门话题
安装：pip install pysnowball（可选）或直接 requests
注意：需登录获取 Cookie（xq_a_token）
"""

import requests
import pandas as pd
import time

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 120)
pd.set_option('display.max_colwidth', 50)


# ============================================================
# 方式一：直接使用 requests 调用雪球 API
# ============================================================
class XueqiuAPI:
    """雪球 API 封装（需 Cookie）"""

    def __init__(self, xq_a_token=''):
        """
        :param xq_a_token: 从浏览器 Cookie 获取的 xq_a_token
        """
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                          'AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://xueqiu.com/',
            'Origin': 'https://xueqiu.com',
        })
        if xq_a_token:
            self.session.cookies.set('xq_a_token', xq_a_token)

    def _init_cookie(self):
        """未提供 token 时，先访问首页获取基础 Cookie"""
        if not self.session.cookies.get('xq_a_token'):
            try:
                self.session.get('https://xueqiu.com/', timeout=10)
            except Exception:
                pass

    def get_stock_quote(self, symbol='SH601318'):
        """
        获取股票实时行情（无需登录 Cookie，访问首页后即可使用）
        :param symbol: 股票代码，格式 SH601318
        :return: dict
        """
        self._init_cookie()
        url = 'https://stock.xueqiu.com/v5/stock/quote.json'
        params = {'symbol': symbol, 'extend': 'detail'}
        r = self.session.get(url, params=params, timeout=10)
        try:
            data = r.json()
            quote = data.get('data', {}).get('quote', {})
            if quote:
                print(f"  股票代码: {quote.get('symbol', '')}")
                print(f"  股票名称: {quote.get('name', '')}")
                print(f"  当前价: {quote.get('current', 0)}")
                print(f"  涨跌幅: {quote.get('percent', 0)}%")
                print(f"  成交量: {quote.get('volume', 0)}")
                return quote
        except Exception:
            pass

        # 雪球接口需要登录，回退到新浪实时行情
        print("  [雪球行情接口需登录，回退到新浪实时行情]")
        try:
            sina_code = symbol.lower()
            r2 = self.session.get(
                f'https://hq.sinajs.cn/list={sina_code}',
                headers={'Referer': 'https://finance.sina.com.cn/'},
                timeout=10)
            if r2.status_code == 200 and r2.text.strip():
                parts = r2.text.split('"')[1].split(',')
                if len(parts) > 3:
                    name = parts[0]
                    open_p = float(parts[1])
                    current = float(parts[3])
                    change_pct = ((current - float(parts[2])) /
                                  float(parts[2]) * 100) if parts[2] != '0' else 0
                    print(f"  股票名称: {name}")
                    print(f"  今开: {open_p}")
                    print(f"  当前价: {current}")
                    print(f"  涨跌幅: {change_pct:.2f}%")
                    return {'name': name, 'current': current}
        except Exception as e:
            print(f"  新浪行情也失败: {e}")
        return {}

    def get_stock_posts(self, symbol='SH601318', page=1, size=10):
        """
        获取股票讨论帖
        :param symbol: 股票代码，格式 市场代码（如 SH601318, SZ000001）
        :param page: 页码
        :param size: 每页数量
        :return: DataFrame
        """
        self._init_cookie()
        url = 'https://xueqiu.com/query/v1/symbol/search/status'
        params = {
            'count': size,
            'comment': '0',
            'symbol': symbol,
            'hl': '0',
            'source': 'all',
            'sort': 'time',
            'page': page,
            'q_type': '',
            'type': '11,12',
            'session_token': None,
            'access_token': None
        }
        r = self.session.get(url, params=params)
        try:
            data = r.json()
        except Exception:
            print(f"雪球接口返回非JSON，状态码: {r.status_code}")
            print("可能需要登录获取Cookie（xq_a_token）")
            return pd.DataFrame()
        posts = data.get('list', [])
        if not posts:
            print("未获取到帖子")
            return pd.DataFrame()

        rows = []
        for p in posts:
            rows.append({
                '标题': p.get('title', '') or p.get('description', '')[:50],
                '作者': p.get('user', {}).get('screen_name', ''),
                '发布时间': pd.to_datetime(
                    p.get('created_at', 0), unit='ms'
                ).strftime('%Y-%m-%d %H:%M') if p.get('created_at') else '',
                '阅读量': p.get('reply_count', 0),
                '评论数': p.get('reply_count', 0),
                '转发数': p.get('retweet_count', 0),
                '点赞数': p.get('like_count', 0),
            })
        return pd.DataFrame(rows)

    def get_hot_topics(self, page=1, size=10):
        """
        获取热门话题
        :return: DataFrame
        """
        self._init_cookie()
        url = 'https://xueqiu.com/query/v1/symbol/search/status'
        params = {
            'count': size,
            'comment': '0',
            'symbol': 'SH000001',
            'hl': '0',
            'source': 'all',
            'sort': 'hot',
            'page': page,
            'q_type': '',
            'type': '11,12',
        }
        r = self.session.get(url, params=params)
        try:
            data = r.json()
        except Exception:
            print(f"雪球接口返回非JSON，状态码: {r.status_code}")
            print("可能需要登录获取Cookie（xq_a_token）")
            return pd.DataFrame()
        posts = data.get('list', [])
        if not posts:
            print("未获取到热门帖子")
            return pd.DataFrame()

        rows = []
        for p in posts:
            rows.append({
                '标题': p.get('title', '') or p.get('description', '')[:50],
                '作者': p.get('user', {}).get('screen_name', ''),
                '发布时间': pd.to_datetime(
                    p.get('created_at', 0), unit='ms'
                ).strftime('%Y-%m-%d %H:%M') if p.get('created_at') else '',
                '阅读量': p.get('reply_count', 0),
                '点赞数': p.get('like_count', 0),
            })
        return pd.DataFrame(rows)


# ============================================================
# 方式二：使用 pysnowball 库
# ============================================================
def demo_pysnowball():
    """使用 pysnowball 库获取数据"""
    try:
        import pysnowball
    except ImportError:
        print("pysnowball 未安装，请运行: pip install pysnowball")
        return

    # 设置 token（从浏览器 Cookie 获取）
    # pysnowball.set_token('your_xq_a_token_here')

    print("=" * 60)
    print("使用 pysnowball 获取雪球数据")
    print("=" * 60)

    # 获取股票详情
    # detail = pysnowball.quotec('SH601318')
    # print(detail)

    print("请设置 token 后取消注释运行")


if __name__ == '__main__':
    # 方式一：直接 requests（未提供 token 也能获取部分数据，但可能被限流）
    api = XueqiuAPI(xq_a_token='')  # 替换为你的 token

    # 1. 股票实时行情（无需登录）
    print("=" * 60)
    print("1. 中国平安(SH601318) 实时行情")
    print("=" * 60)
    api.get_stock_quote(symbol='SH601318')

    import time
    time.sleep(1)

    # 2. 股票讨论帖
    print("\n" + "=" * 60)
    print("2. 中国平安(SH601318) 雪球讨论帖")
    print("=" * 60)
    df = api.get_stock_posts(symbol='SH601318', page=1, size=10)
    print(df)

    time.sleep(2)

    # 3. 热门帖子
    print("\n" + "=" * 60)
    print("3. 雪球热门帖子")
    print("=" * 60)
    df = api.get_hot_topics(page=1, size=10)
    print(df)

    # 方式二：pysnowball（需 token）
    # demo_pysnowball()
