# -*- coding: utf-8 -*-
# @Author   : ai_quant_trade
# @File     : ccxt_demo.py
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
CCXT 加密货币数据接口示例
覆盖：行情获取、历史K线、订单簿、交易对列表
安装：pip install ccxt
公开行情接口无需 API Key
"""

import ccxt
import pandas as pd
import time

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 120)


def demo_ticker():
    """1. 获取最新行情"""
    print("=" * 60)
    print("1. Binance BTC/USDT 最新行情")
    print("=" * 60)
    exchange = ccxt.binance()
    ticker = exchange.fetch_ticker('BTC/USDT')
    print(f"  最新价: {ticker['last']}")
    print(f"  24h最高: {ticker['high']}")
    print(f"  24h最低: {ticker['low']}")
    print(f"  24h成交量: {ticker['baseVolume']}")
    print(f"  24h涨跌幅: {((ticker['last'] / ticker['open']) - 1) * 100:.2f}%")


def demo_ohlcv():
    """2. 获取历史K线数据"""
    print("\n" + "=" * 60)
    print("2. Binance BTC/USDT 日K线（最近100天）")
    print("=" * 60)
    exchange = ccxt.binance()
    ohlcv = exchange.fetch_ohlcv('BTC/USDT', timeframe='1d', limit=100)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high',
                                      'low', 'close', 'volume'])
    df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('datetime', inplace=True)
    df.drop('timestamp', axis=1, inplace=True)
    print(df.tail(10))


def demo_orderbook():
    """3. 获取订单簿"""
    print("\n" + "=" * 60)
    print("3. Binance BTC/USDT 订单簿（前5档）")
    print("=" * 60)
    exchange = ccxt.binance()
    orderbook = exchange.fetch_order_book('BTC/USDT')
    print("  买单（买5）:")
    for bid in orderbook['bids'][:5]:
        print(f"    价格: {bid[0]}, 数量: {bid[1]}")
    print("  卖单（卖5）:")
    for ask in orderbook['asks'][:5]:
        print(f"    价格: {ask[0]}, 数量: {ask[1]}")


def demo_markets():
    """4. 获取支持的交易对"""
    print("\n" + "=" * 60)
    print("4. Binance 支持的USDT交易对（前10个）")
    print("=" * 60)
    exchange = ccxt.binance()
    markets = exchange.load_markets()
    usdt_pairs = [s for s in markets.keys() if s.endswith('/USDT')]
    print(f"  共 {len(usdt_pairs)} 个USDT交易对")
    for s in usdt_pairs[:10]:
        print(f"    {s}")


def demo_multi_exchange():
    """5. 对比多个交易所行情"""
    print("\n" + "=" * 60)
    print("5. 多交易所 BTC/USDT 最新价对比")
    print("=" * 60)
    exchanges = {
        'Binance': ccxt.binance(),
        'OKX': ccxt.okx(),
        'Gate': ccxt.gate(),
    }
    for name, ex in exchanges.items():
        try:
            ticker = ex.fetch_ticker('BTC/USDT')
            print(f"  {name}: {ticker['last']}")
        except Exception as e:
            print(f"  {name}: 获取失败 - {e}")
        time.sleep(0.5)


if __name__ == '__main__':
    demo_ticker()
    demo_ohlcv()
    demo_orderbook()
    demo_markets()
    demo_multi_exchange()
