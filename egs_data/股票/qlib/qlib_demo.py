# -*- coding: utf-8 -*-
# @Author   : ai_quant_trade
# @File     : qlib_demo.py
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
Qlib 数据接口示例
覆盖：数据初始化、单股/多股数据获取、表达式计算
安装：pip install pyqlib
首次使用需下载数据（在非项目目录下运行）：
    cd ~ && python -c "from qlib.tests.data import GetData; GetData.qlib_data(target_dir='~/.qlib/qlib_data/cn_data', region='cn')"
"""

import sys
import os

# 避免工作区本地 qlib 目录覆盖 pip 安装的 pyqlib 包
# 移除工作区根目录从 sys.path
_workspace_root = os.path.normpath(os.path.join(
    os.path.dirname(__file__), '..', '..', '..'))
sys.path = [p for p in sys.path
            if os.path.normpath(p) != _workspace_root]
# 确保site-packages在前
_site_packages = os.path.join(
    os.path.dirname(sys.executable), 'Lib', 'site-packages')
if _site_packages not in sys.path:
    sys.path.insert(0, _site_packages)

import qlib
from qlib.data import D
import pandas as pd

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 120)

QLIB_DATA_DIR = os.path.expanduser('~/.qlib/qlib_data/cn_data')


def ensure_data():
    """检查 Qlib 数据是否存在，不存在则自动下载"""
    if os.path.exists(QLIB_DATA_DIR) and os.listdir(QLIB_DATA_DIR):
        return True
    print("Qlib 中国区数据未下载，正在自动下载（约1GB，需几分钟）...")
    print(f"目标目录: {QLIB_DATA_DIR}")
    try:
        import requests
        import tarfile
        import tempfile

        # 使用 chenditc/investment_data 仓库的预处理数据
        url = ('https://github.com/chenditc/investment_data/'
               'releases/latest/download/qlib_bin.tar.gz')
        print(f"下载: {url}")
        r = requests.get(url, stream=True, timeout=300)
        r.raise_for_status()

        # 下载到临时文件
        tmp_tar = os.path.join(tempfile.gettempdir(), 'qlib_bin.tar.gz')
        total = int(r.headers.get('content-length', 0))
        downloaded = 0
        with open(tmp_tar, 'wb') as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                f.write(chunk)
                downloaded += len(chunk)
                if total > 0:
                    pct = downloaded * 100 // total
                    print(f"\r  下载进度: {pct}% ({downloaded // 1024 // 1024}MB)",
                          end='', flush=True)
        print("\n下载完成，正在解压...")

        # 创建目标目录并解压
        os.makedirs(QLIB_DATA_DIR, exist_ok=True)
        with tarfile.open(tmp_tar, 'r:gz') as tar:
            tar.extractall(path=QLIB_DATA_DIR)
        os.remove(tmp_tar)
        print("解压完成")
        return True
    except Exception as e:
        print(f"\n自动下载失败: {e}")
        print(f"请手动下载并解压:")
        print(f"  1. 下载: {url}")
        print(f"  2. 解压到: {QLIB_DATA_DIR}")
        return False


def init_qlib():
    """1. 初始化 Qlib 中国区数据"""
    print("=" * 60)
    print("1. 初始化 Qlib（中国区数据）")
    print("=" * 60)
    if not ensure_data():
        return False
    qlib.init(provider_uri=QLIB_DATA_DIR, region='cn')
    print("初始化完成")
    return True


def demo_single_stock():
    """2. 获取单只股票数据"""
    print("\n" + "=" * 60)
    print("2. 中国平安(SH601318) 日K线数据")
    print("=" * 60)
    df = D.features(
        ['SH601318'],
        ['$open', '$close', '$high', '$low', '$volume'],
        start_time='2023-01-01',
        end_time='2023-12-31'
    )
    print(df.head(10))
    # 索引为 (instrument, datetime)，列为各字段


def demo_multi_stock():
    """3. 获取多只股票数据"""
    print("\n" + "=" * 60)
    print("3. 多只股票收盘价")
    print("=" * 60)
    df = D.features(
        ['SH600000', 'SH601318', 'SZ000001'],
        ['$close'],
        start_time='2023-06-01',
        end_time='2023-06-30'
    )
    print(df.head(10))


def demo_expression():
    """4. 使用表达式计算技术指标"""
    print("\n" + "=" * 60)
    print("4. 中国平安 - 5日均线 + 涨跌幅")
    print("=" * 60)
    df = D.features(
        ['SH601318'],
        ['$close', 'Mean($close, 5)', '($close / Ref($close, 1) - 1)'],
        start_time='2023-01-01',
        end_time='2023-01-31'
    )
    print(df.head(10))
    # Mean($close, 5): 5日均线
    # Ref($close, 1): 前一日收盘价


def demo_stock_list():
    """5. 获取股票池（如沪深300成分股）"""
    print("\n" + "=" * 60)
    print("5. 沪深300成分股（前10只）")
    print("=" * 60)
    instruments = D.instruments(market='csi300')
    stock_list = D.list_instruments(instruments=instruments,
                                   start_time='2023-01-01',
                                   end_time='2023-12-31',
                                   as_list=True)
    print(stock_list[:10])


if __name__ == '__main__':
    if not init_qlib():
        sys.exit(1)
    demo_single_stock()
    demo_multi_stock()
    demo_expression()
    demo_stock_list()
