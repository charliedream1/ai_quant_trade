# -*- coding: utf-8 -*-
# @Author   : ai_quant_trade
# @File     : gdelt_demo.py
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
GDELT Project 全球新闻事件+情绪数据接口示例
覆盖：最新15分钟切片下载、事件查询、情绪分析
完全免费，无需 API Key
安装：pip install gdeltdoc（可选）或直接 requests
"""

import requests
import pandas as pd
from io import StringIO, BytesIO
import zipfile

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 120)


def get_latest_updates():
    """
    获取最新的 GDELT 更新文件列表
    GDELT 每15分钟更新一次，返回最新的文件URL列表
    :return: list of URLs
    """
    url = 'http://data.gdeltproject.org/gdeltv2/lastupdate.txt'
    r = requests.get(url)
    lines = r.text.strip().split('\n')
    urls = []
    for line in lines:
        parts = line.split()
        if len(parts) >= 2:
            urls.append(parts[2])  # 文件URL
    return urls


def download_events(url):
    """
    下载并解析 GDELT 事件文件（CSV格式）
    GDELT 2.0 Events 表共 61 列，这里使用完整列名定义
    :param url: 事件文件URL
    :return: DataFrame
    """
    # GDELT 2.0 Events 表完整字段（共61列）
    all_columns = [
        'GLOBALEVENTID', 'SQLDATE', 'MonthYear', 'Year', 'FractionDate',
        'Actor1Code', 'Actor1Name', 'Actor1CountryCode', 'Actor1KnownGroupCode',
        'Actor1EthnicCode', 'Actor1Religion1Code', 'Actor1Religion2Code',
        'Actor1Type1Code', 'Actor1Type2Code', 'Actor1Type3Code',
        'Actor2Code', 'Actor2Name', 'Actor2CountryCode', 'Actor2KnownGroupCode',
        'Actor2EthnicCode', 'Actor2Religion1Code', 'Actor2Religion2Code',
        'Actor2Type1Code', 'Actor2Type2Code', 'Actor2Type3Code',
        'IsRootEvent', 'EventCode', 'EventBaseCode', 'EventRootCode',
        'QuadClass', 'GoldsteinScale', 'NumMentions', 'NumSources',
        'NumArticles', 'AvgTone',
        'Actor1Geo_Type', 'Actor1Geo_FullName', 'Actor1Geo_CountryCode',
        'Actor1Geo_ADM1Code', 'Actor1Geo_ADM2Code', 'Actor1Geo_Lat',
        'Actor1Geo_Long', 'Actor1Geo_FeatureID',
        'Actor2Geo_Type', 'Actor2Geo_FullName', 'Actor2Geo_CountryCode',
        'Actor2Geo_ADM1Code', 'Actor2Geo_ADM2Code', 'Actor2Geo_Lat',
        'Actor2Geo_Long', 'Actor2Geo_FeatureID',
        'ActionGeo_Type', 'ActionGeo_FullName', 'ActionGeo_CountryCode',
        'ActionGeo_ADM1Code', 'ActionGeo_ADM2Code', 'ActionGeo_Lat',
        'ActionGeo_Long', 'ActionGeo_FeatureID', 'DATEADDED', 'SOURCEURL',
    ]

    r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
    r.raise_for_status()
    # GDELT 2.0 文件是 zip 压缩的，需先解压
    with zipfile.ZipFile(BytesIO(r.content)) as zf:
        csv_name = zf.namelist()[0]
        with zf.open(csv_name) as f:
            df = pd.read_csv(f, sep='\t', header=None,
                            low_memory=False, on_bad_lines='skip',
                            names=all_columns)
    # 转换日期
    df['SQLDATE'] = pd.to_datetime(df['SQLDATE'], format='%Y%m%d',
                                  errors='coerce')
    # 数值转换
    for col in ['GoldsteinScale', 'AvgTone', 'NumMentions', 'NumArticles']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    return df


def analyze_tone(df):
    """
    分析新闻情绪
    :param df: 事件 DataFrame
    :return: 统计结果
    """
    print("=" * 60)
    print("新闻情绪分析")
    print("=" * 60)
    print(f"总事件数: {len(df)}")
    print(f"平均情绪分数: {df['AvgTone'].mean():.2f}")
    print(f"正面事件占比: {(df['AvgTone'] > 0).mean() * 100:.1f}%")
    print(f"负面事件占比: {(df['AvgTone'] < 0).mean() * 100:.1f}%")

    # 按国家统计
    print("\n按事件发生国家统计（前10）:")
    country_stats = df.groupby('ActionGeo_CountryCode').agg({
        'AvgTone': 'mean',
        'GLOBALEVENTID': 'count'
    }).round(2)
    country_stats.columns = ['平均情绪', '事件数']
    country_stats = country_stats.sort_values('事件数', ascending=False)
    print(country_stats.head(10))


def demo_gdeltdoc():
    """使用 gdeltdoc 库查询（需安装 gdeltdoc）"""
    try:
        from gdeltdoc import GdeltDoc, Filters
    except ImportError:
        try:
            from gdeltdoc import GdeltDoc
            Filters = None
        except ImportError:
            print("gdeltdoc 未安装，请运行: pip install gdeltdoc")
            print("使用直接下载方式替代")
            return

    print("=" * 60)
    print("使用 gdeltdoc 库查询 GDELT DOC API")
    print("=" * 60)

    f = GdeltDoc()

    # gdeltdoc 不同版本 API 不同，尝试多种调用方式
    try:
        if Filters is not None:
            # 新版 API：使用 Filters 对象
            filters = Filters(
                keyword='China',
                start_date='2024-04-01',
                end_date='2024-04-02'
            )
            articles = f.article_search(filters)
        else:
            # 旧版 API：使用字典列表
            filters = [
                {'keyword': 'China', 'start_date': '2024-04-01',
                 'end_date': '2024-04-02'}
            ]
            articles = f.article_search(filters)
        print(f"查询到 {len(articles)} 篇文章")
        if not articles.empty:
            print(articles[['title', 'url', 'domain']].head())
    except Exception as e:
        print(f"gdeltdoc 库调用失败: {e}")
        print("建议使用上方的直接下载方式获取 GDELT 数据")


if __name__ == '__main__':
    # 1. 获取最新更新文件列表
    print("=" * 60)
    print("1. GDELT 最新更新文件列表")
    print("=" * 60)
    urls = get_latest_updates()
    print(f"共 {len(urls)} 个文件")
    for u in urls[:3]:
        print(f"  {u}")

    # 2. 下载并解析最新事件文件
    if urls:
        print("\n" + "=" * 60)
        print("2. 下载并解析最新事件文件")
        print("=" * 60)
        # GDELT 2.0 文件列表顺序：
        # [0] export.CSV.zip（事件数据）
        # [1] mentions.CSV.zip（提及数据）
        # [2] gkg.csv.zip（全球知识图谱）
        # 注意：GDELT 每15分钟更新，URL可能很快过期，需重新获取
        df = pd.DataFrame()
        for attempt in range(3):
            urls = get_latest_updates()
            events_url = urls[0]  # 使用 export 文件（事件数据）
            print(f"下载（尝试 {attempt + 1}）: {events_url}")
            try:
                df = download_events(events_url)
                break
            except Exception as e:
                print(f"下载失败: {e}，重新获取最新URL...")
                import time
                time.sleep(2)

        if df.empty:
            print("无法下载事件数据，请稍后重试")
        else:
            print(f"共 {len(df)} 条事件")
            # 只显示关键字段
            display_cols = ['SQLDATE', 'Actor1Name', 'Actor1CountryCode',
                            'Actor2Name', 'Actor2CountryCode', 'EventCode',
                            'GoldsteinScale', 'AvgTone', 'ActionGeo_CountryCode']
            available_display = [c for c in display_cols if c in df.columns]
            print(df[available_display].head())

        # 3. 情绪分析
        if not df.empty:
            analyze_tone(df)

    # 4. gdeltdoc 库查询（可选）
    print("\n" + "=" * 60)
    print("4. gdeltdoc 库查询（可选）")
    print("=" * 60)
    demo_gdeltdoc()
