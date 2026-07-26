# -*- coding: utf-8 -*-
# @Author   : ai_quant_trade
# @File     : news_demo.py
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
财经新闻数据接口示例（基于 AKShare）
覆盖：个股新闻、财经快讯、新闻联播、微博舆情、新闻情绪指数
安装：pip install akshare --upgrade
"""

import akshare as ak
import pandas as pd
import threading
import functools

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 120)
pd.set_option('display.max_colwidth', 40)


class TimeoutError(Exception):
    pass


def with_timeout(seconds=30):
    """超时控制装饰器，使用线程实现，兼容 Windows/Linux/macOS"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            result = [None]
            exception = [None]

            def target():
                try:
                    result[0] = func(*args, **kwargs)
                except Exception as e:
                    exception[0] = e

            t = threading.Thread(target=target, daemon=True)
            t.start()
            t.join(seconds)
            if t.is_alive():
                raise TimeoutError(f"请求超时（{seconds}秒）")
            if exception[0]:
                raise exception[0]
            return result[0]
        return wrapper
    return decorator


def safe_call(func, name, timeout_sec=30):
    """安全调用接口，捕获异常避免中断"""
    try:
        wrapped = with_timeout(timeout_sec)(func)
        df = wrapped()
        if df is not None and not df.empty:
            print(df.head())
        else:
            print("未获取到数据")
        return df
    except Exception as e:
        print(f"获取失败: {str(e)[:100]}")
        return None


def demo_stock_news():
    """1. 个股新闻（东方财富）"""
    print("=" * 60)
    print("1. 中国平安(601318) 个股新闻")
    print("=" * 60)
    safe_call(lambda: ak.stock_news_em(symbol="601318"), "stock_news_em")
    # 字段：标题、内容、发布时间、文章来源、新闻链接


def demo_global_cls():
    """2. 财联社电报快讯"""
    print("\n" + "=" * 60)
    print("2. 财联社电报快讯")
    print("=" * 60)
    safe_call(lambda: ak.stock_info_global_cls(symbol="全部"), "stock_info_global_cls")
    # 字段：标题、内容、发布时间


def demo_global_em():
    """3. 东方财富全球财经快讯"""
    print("\n" + "=" * 60)
    print("3. 东方财富全球财经快讯")
    print("=" * 60)
    safe_call(lambda: ak.stock_info_global_em(), "stock_info_global_em")


def demo_global_sina():
    """4. 新浪财经全球快讯"""
    print("\n" + "=" * 60)
    print("4. 新浪财经全球快讯")
    print("=" * 60)
    safe_call(lambda: ak.stock_info_global_sina(), "stock_info_global_sina")


def demo_news_cctv():
    """5. 新闻联播文字稿"""
    print("\n" + "=" * 60)
    print("5. 新闻联播文字稿（2024-04-24）")
    print("=" * 60)
    safe_call(lambda: ak.news_cctv(date="20240424"), "news_cctv")
    # 字段：标题、内容


def demo_news_main_cx():
    """6. 财新网主要财经新闻"""
    print("\n" + "=" * 60)
    print("6. 财新网主要财经新闻")
    print("=" * 60)
    safe_call(lambda: ak.stock_news_main_cx(), "stock_news_main_cx")


def demo_weibo_report():
    """7. 微博舆情报告"""
    print("\n" + "=" * 60)
    print("7. 微博舆情报告（最近12小时）")
    print("=" * 60)
    safe_call(lambda: ak.stock_js_weibo_report(time_period="CNHOUR12"),
              "stock_js_weibo_report")
    # 字段：股票代码、股票名称、微博舆情指数、正负面情绪占比


def demo_news_sentiment():
    """8. 新闻情绪指数"""
    print("\n" + "=" * 60)
    print("8. 新闻情绪指数")
    print("=" * 60)
    safe_call(lambda: ak.index_news_sentiment_scope(), "index_news_sentiment_scope")
    # 字段：日期、新闻情绪指数


def demo_futures_news():
    """9. 期货新闻（上海期货交易所）"""
    print("\n" + "=" * 60)
    print("9. 上海期货交易所新闻")
    print("=" * 60)
    safe_call(lambda: ak.futures_news_shmet(symbol="全部"), "futures_news_shmet")


if __name__ == '__main__':
    demo_stock_news()
    demo_global_cls()
    demo_global_em()
    demo_global_sina()
    demo_news_cctv()
    demo_news_main_cx()
    demo_weibo_report()
    demo_news_sentiment()
    demo_futures_news()
