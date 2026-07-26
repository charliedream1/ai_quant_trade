# -*- coding: utf-8 -*-
# @Author   : ai_quant_trade
# @File     : cninfo_demo.py
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
巨潮资讯网（CNINFO）官方披露数据接口示例
覆盖：公告查询、年报查询、定期报告查询
无需安装额外库，使用 requests 即可
注意：CNINFO 的 stock 参数需要 "代码,orgId" 格式，
      orgId 需通过搜索接口获取，本脚本已内置自动获取逻辑
"""

import requests
import pandas as pd
import time

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 120)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'http://www.cninfo.com.cn/new/commonUrl?url=disclosure/list/notice'
}


def get_org_id(stock_code='601318'):
    """
    通过搜索接口获取股票的 orgId
    CNINFO 的公告查询接口需要 "代码,orgId" 格式
    :param stock_code: 股票代码，如 601318
    :return: orgId 字符串
    """
    search_url = 'http://www.cninfo.com.cn/new/information/topSearch/query'
    r = requests.post(search_url, data={'keyWord': stock_code, 'maxNum': 10},
                      headers=HEADERS)
    results = r.json()
    if results and len(results) > 0:
        return results[0].get('orgId', '')
    return ''


def query_announcements(stock='601318', category='category_ndbg_szsh',
                        page=1, page_size=30):
    """
    查询公司历史公告
    :param stock: 股票代码，如 601318
    :param category: 公告类型
        category_ndbg_szsh: 年度报告
        category_bndbg_szsh: 半年度报告
        category_yjdbg_szsh: 一季报
        category_sjdbg_szsh: 三季报
        category_yjyg_szsh: 业绩预告
        category_yjkb_szsh: 业绩快报
    :param page: 页码
    :param page_size: 每页数量
    :return: DataFrame
    """
    # 自动获取 orgId
    org_id = get_org_id(stock)
    if not org_id:
        print(f"未找到股票 {stock} 的 orgId")
        return pd.DataFrame()

    # 判断市场：6/9开头为沪市(shj)，其余为深市(szse)
    is_sh = stock.startswith(('6', '9'))
    column = 'sse' if is_sh else 'szse'
    plate = 'sh' if is_sh else 'sz'

    url = 'http://www.cninfo.com.cn/new/hisAnnouncement/query'
    data = {
        'stock': f'{stock},{org_id}',
        'tabName': 'fulltext',
        'pageSize': page_size,
        'pageNum': page,
        'column': column,
        'category': category,
        'plate': plate,
        'searchkey': '',
        'secid': '',
        'sortName': '',
        'sortType': '',
        'isHLtitle': 'true'
    }
    r = requests.post(url, data=data, headers=HEADERS)
    result = r.json()
    announcements = result.get('announcements') or []
    if not announcements:
        print("未查询到公告")
        return pd.DataFrame()

    df = pd.DataFrame(announcements)
    # 提取关键字段
    cols = ['announcementTitle', 'announcementTime', 'adjunctUrl',
            'announcementTypeName']
    col_names = ['公告标题', '公告时间', '公告链接', '公告类型']
    available_cols = [c for c in cols if c in df.columns]
    df = df[available_cols]
    # 时间戳转日期
    if 'announcementTime' in df.columns:
        df['announcementTime'] = pd.to_datetime(
            df['announcementTime'], unit='ms'
        ).dt.strftime('%Y-%m-%d')
    df.columns = [col_names[cols.index(c)] for c in available_cols]
    return df


def get_announcement_url(adjunct_url):
    """
    获取公告 PDF 下载链接
    :param adjunct_url: 公告的 adjunctUrl 字段值
    :return: 完整下载URL
    """
    return f'http://static.cninfo.com.cn/{adjunct_url}'


def query_all_announcements(stock='601318', start_date='2023-01-01',
                            end_date='2023-12-31', page=1, page_size=30):
    """
    查询公司所有类型公告（按日期范围）
    :param stock: 股票代码
    :param start_date: 开始日期 YYYY-MM-DD
    :param end_date: 结束日期 YYYY-MM-DD
    :return: DataFrame
    """
    # 自动获取 orgId
    org_id = get_org_id(stock)
    if not org_id:
        print(f"未找到股票 {stock} 的 orgId")
        return pd.DataFrame()

    is_sh = stock.startswith(('6', '9'))
    column = 'sse' if is_sh else 'szse'
    plate = 'sh' if is_sh else 'sz'

    url = 'http://www.cninfo.com.cn/new/hisAnnouncement/query'
    data = {
        'stock': f'{stock},{org_id}',
        'tabName': 'fulltext',
        'pageSize': page_size,
        'pageNum': page,
        'column': column,
        'category': '',
        'plate': plate,
        'seDate': f'{start_date}~{end_date}',
        'searchkey': '',
        'secid': '',
        'sortName': '',
        'sortType': '',
        'isHLtitle': 'true'
    }
    r = requests.post(url, data=data, headers=HEADERS)
    result = r.json()
    announcements = result.get('announcements') or []
    if not announcements:
        print("未查询到公告")
        return pd.DataFrame()

    df = pd.DataFrame(announcements)
    cols = ['announcementTitle', 'announcementTime', 'adjunctUrl']
    col_names = ['公告标题', '公告时间', '公告链接']
    available_cols = [c for c in cols if c in df.columns]
    df = df[available_cols]
    if 'announcementTime' in df.columns:
        df['announcementTime'] = pd.to_datetime(
            df['announcementTime'], unit='ms'
        ).dt.strftime('%Y-%m-%d')
    df.columns = [col_names[cols.index(c)] for c in available_cols]
    return df


if __name__ == '__main__':
    # 1. 查询中国平安年度报告
    print("=" * 60)
    print("1. 中国平安(601318) 年度报告列表")
    print("=" * 60)
    df = query_announcements(stock='601318', category='category_ndbg_szsh')
    print(df)
    if not df.empty and '公告链接' in df.columns:
        print(f"\n最新年报下载链接: {get_announcement_url(df.iloc[0]['公告链接'])}")

    time.sleep(1)

    # 2. 查询2023年所有公告
    print("\n" + "=" * 60)
    print("2. 中国平安(601318) 2023年公告列表")
    print("=" * 60)
    df = query_all_announcements(stock='601318',
                                 start_date='2023-01-01',
                                 end_date='2023-12-31')
    print(df.head(10))
    print(f"\n共 {len(df)} 条公告")
