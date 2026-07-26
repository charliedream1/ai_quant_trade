# -*- coding: utf-8 -*-
# @Author   : ai_quant_trade
# @File     : futures_demo.py
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
期货数据接口示例
覆盖：主力连续日K线、单合约历史K线、主力合约列表
数据源：AKShare（新浪财经）
安装：pip install akshare
无需 API Key

期货代码说明（新浪格式）：
- V0  : PVC 主力连续
- RB0 : 螺纹钢主力连续
- CU0 : 沪铜主力连续
- V2409: PVC 2024年9月合约
"""

import pandas as pd
import signal
import functools

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 120)
pd.set_option('display.max_colwidth', 30)


class TimeoutError(Exception):
    pass


def _timeout_handler(signum, frame):
    raise TimeoutError("请求超时")


def with_timeout(seconds=30):
    """超时控制装饰器"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if not hasattr(signal, 'SIGALRM'):
                return func(*args, **kwargs)
            old_handler = signal.signal(signal.SIGALRM, _timeout_handler)
            signal.alarm(seconds)
            try:
                return func(*args, **kwargs)
            finally:
                signal.alarm(0)
                signal.signal(signal.SIGALRM, old_handler)
        return wrapper
    return decorator


def safe_call(func, name, timeout_sec=30):
    """安全调用，捕获异常并打印结果"""
    print("=" * 60)
    print(name)
    print("=" * 60)
    try:
        wrapped = with_timeout(timeout_sec)(func)
        df = wrapped()
        if df is not None and not df.empty:
            print(df.tail(10))
            print(f"\n共 {len(df)} 条记录")
        else:
            print("未获取到数据")
        return df
    except Exception as e:
        print(f"获取失败: {str(e)[:120]}")
        return None


def demo_futures_main():
    """1. 期货主力连续日K线（PVC）"""
    import akshare as ak
    df = ak.futures_main_sina(symbol='V0')
    return df


def demo_futures_contract():
    """2. 单合约历史日K线（PVC 2409合约）"""
    import akshare as ak
    df = ak.futures_zh_daily_sina(symbol='V2409')
    return df


def demo_futures_list():
    """3. 全市场主力合约列表"""
    import akshare as ak
    df = ak.futures_display_main_sina()
    return df


if __name__ == '__main__':
    # 1. 主力连续日K线
    safe_call(demo_futures_main, "1. PVC主力连续 日K线")

    # 2. 单合约历史K线
    safe_call(demo_futures_contract, "2. PVC 2409合约 历史日K线")

    # 3. 主力合约列表
    safe_call(demo_futures_list, "3. 全市场主力合约列表")
