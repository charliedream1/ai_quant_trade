# -*- coding: utf-8 -*-
# @Author   : ai_quant_trade
# @File     : tushare_demo.py
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
Tushare Pro 数据接口示例
覆盖：日线行情、分钟行情、基本面数据、交易日历

安装：pip install tushare
使用前需在 https://tushare.pro 注册获取 Token，并设置环境变量：
  export TUSHARE_TOKEN=your_token_here

免费用户配额：每分钟最多80次请求，每天最多500次请求

参考来源：
  - Vibe-Trading: backtest/loaders/tushare.py (日线+分钟+基本面)
  - daily_stock_analysis: data_provider/tushare_fetcher.py (流控+HTTP客户端)
"""

import os
import time
import logging
from typing import Optional

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 120)


# ---------------------------------------------------------------------------
# 方式1: 使用 Tushare SDK
# ---------------------------------------------------------------------------

def get_tushare_api():
    """初始化 Tushare Pro API（需设置 TUSHARE_TOKEN 环境变量）"""
    token = os.getenv("TUSHARE_TOKEN", "").strip()
    if not token:
        print("[警告] TUSHARE_TOKEN 未设置，部分示例将跳过")
        print("  请在 https://tushare.pro 注册获取 Token 后设置环境变量")
        return None
    try:
        import tushare as ts
        return ts.pro_api(token)
    except ImportError:
        print("[警告] tushare 未安装，请运行: pip install tushare")
        return None


def demo_daily_ohlcv(api):
    """1. 日线 OHLCV 数据（前复权）"""
    print("=" * 60)
    print("1. 贵州茅台(600519.SH) 日线行情")
    print("=" * 60)
    if api is None:
        print("  [跳过] API 未初始化")
        return
    df = api.daily(ts_code="600519.SH", start_date="20240101", end_date="20240301")
    if df is None or df.empty:
        print("  无数据返回")
        return
    df = df.sort_values("trade_date")
    print(df.head())
    # 字段: ts_code, trade_date, open, high, low, close, pre_close, change, pct_chg, vol, amount


def demo_minute_ohlcv(api):
    """2. 分钟级行情（需 Tushare 积分 >= 2000）"""
    print("\n" + "=" * 60)
    print("2. 贵州茅台(600519.SH) 5分钟K线")
    print("=" * 60)
    if api is None:
        print("  [跳过] API 未初始化")
        return
    try:
        df = api.stk_mins(ts_code="600519.SH", freq="5min",
                          start_date="2024-01-02 09:00:00",
                          end_date="2024-01-02 15:00:00")
        if df is not None and not df.empty:
            print(df.head())
        else:
            print("  无数据（可能积分不足，需 >= 2000）")
    except Exception as e:
        print(f"  获取失败: {e}")


def demo_daily_basic(api):
    """3. 每日基本面指标（市盈率、市净率、换手率等）"""
    print("\n" + "=" * 60)
    print("3. 每日基本面指标")
    print("=" * 60)
    if api is None:
        print("  [跳过] API 未初始化")
        return
    df = api.daily_basic(ts_code="600519.SH", trade_date="20240102",
                         fields="ts_code,trade_date,pe,pb,turnover_rate,volume,amount,total_mv,circ_mv")
    if df is not None and not df.empty:
        print(df)
    # 字段: pe(市盈率), pb(市净率), turnover_rate(换手率), total_mv(总市值), circ_mv(流通市值)


def demo_trade_cal(api):
    """4. 交易日历"""
    print("\n" + "=" * 60)
    print("4. 交易日历 (2024年1月)")
    print("=" * 60)
    if api is None:
        print("  [跳过] API 未初始化")
        return
    df = api.trade_cal(exchange="SSE", start_date="20240101", end_date="20240131")
    if df is not None and not df.empty:
        # 只显示交易日
        trading_days = df[df["is_open"] == 1]
        print(trading_days[["cal_date", "is_open"]])


def demo_stock_basic(api):
    """5. 股票列表"""
    print("\n" + "=" * 60)
    print("5. 沪深A股列表（前10行）")
    print("=" * 60)
    if api is None:
        print("  [跳过] API 未初始化")
        return
    df = api.stock_basic(exchange="", list_status="L",
                         fields="ts_code,symbol,name,area,industry,market,list_date")
    if df is not None and not df.empty:
        print(df.head(10))


# ---------------------------------------------------------------------------
# 方式2: 轻量级 HTTP 客户端（无需 Tushare SDK）
# 参考 daily_stock_analysis 的 _TushareHttpClient
# ---------------------------------------------------------------------------

class TushareHttpClient:
    """轻量级 Tushare Pro HTTP 客户端，不依赖 tushare SDK

    优势：
    - 避免运行时强依赖 tushare SDK
    - 减少 Docker / PyInstaller / 多虚拟环境场景下的兼容性问题
    - 内置超时控制，防止无限挂起
    """

    API_URL = "http://api.tushare.pro"

    def __init__(self, token: str, timeout: int = 30):
        self._token = token
        self._timeout = timeout
        self._call_count = 0
        self._minute_start: Optional[float] = None

    def _check_rate_limit(self, limit_per_minute: int = 80):
        """每分钟调用计数器，防止超出免费配额"""
        now = time.time()
        if self._minute_start is None or (now - self._minute_start) >= 60:
            self._call_count = 0
            self._minute_start = now

        self._call_count += 1
        if self._call_count > limit_per_minute:
            sleep_time = 60 - (now - self._minute_start)
            if sleep_time > 0:
                logger.warning(f"达到每分钟配额({limit_per_minute}次)，休眠 {sleep_time:.0f}s")
                time.sleep(sleep_time)
                self._call_count = 0
                self._minute_start = time.time()

    def query(self, api_name: str, fields: str = "", **kwargs) -> pd.DataFrame:
        """直接调用 Tushare Pro HTTP 接口"""
        import requests

        self._check_rate_limit()

        req_params = {
            "api_name": api_name,
            "token": self._token,
            "params": kwargs,
            "fields": fields,
        }
        res = requests.post(self.API_URL, json=req_params, timeout=self._timeout)
        if res.status_code != 200:
            raise Exception(f"Tushare API HTTP {res.status_code}")

        result = res.json()
        if result.get("code") != 0:
            raise Exception(result.get("msg") or f"Tushare API error code {result.get('code')}")

        data = result.get("data") or {}
        columns = data.get("fields") or []
        items = data.get("items") or []
        return pd.DataFrame(items, columns=columns)


def demo_http_client():
    """6. 轻量级 HTTP 客户端示例"""
    print("\n" + "=" * 60)
    print("6. 轻量级 HTTP 客户端（无需 tushare SDK）")
    print("=" * 60)
    token = os.getenv("TUSHARE_TOKEN", "").strip()
    if not token:
        print("  [跳过] TUSHARE_TOKEN 未设置")
        return
    try:
        client = TushareHttpClient(token=token)
        # 调用方式与 tushare SDK 的 pro_api 完全一致
        df = client.query("daily", ts_code="600519.SH",
                          start_date="20240101", end_date="20240110")
        print(df)
    except Exception as e:
        print(f"  获取失败: {e}")


# ---------------------------------------------------------------------------
# 方式3: OHLCV 标准化输出（参考 Vibe-Trading 的统一接口）
# ---------------------------------------------------------------------------

def fetch_ohlcv_standardized(api, code: str, start_date: str, end_date: str,
                             interval: str = "1D") -> pd.DataFrame:
    """获取标准化 OHLCV 数据

    将 Tushare 原始字段映射为统一的 (trade_date, open, high, low, close, volume) 格式

    Args:
        api: tushare pro_api 实例或 TushareHttpClient 实例
        code: 股票代码，如 "600519.SH"
        start_date: 起始日期 YYYYMMDD
        end_date: 结束日期 YYYYMMDD
        interval: 周期，1D=日线, 1m/5m/15m/30m/1H=分钟线

    Returns:
        标准化 OHLCV DataFrame，索引为 trade_date
    """
    if api is None:
        return pd.DataFrame()

    if interval != "1D":
        # 分钟级数据
        freq_map = {"1m": "1min", "5m": "5min", "15m": "15min",
                     "30m": "30min", "1H": "60min"}
        freq = freq_map.get(interval)
        if not freq:
            print(f"不支持的周期: {interval}")
            return pd.DataFrame()
        try:
            df = api.stk_mins(ts_code=code, freq=freq,
                              start_date=start_date, end_date=end_date)
        except Exception as e:
            print(f"分钟数据获取失败: {e}")
            return pd.DataFrame()
        if df is None or df.empty:
            return pd.DataFrame()
        df = df.sort_values("trade_time")
        df["trade_date"] = pd.to_datetime(df["trade_time"])
        df = df.set_index("trade_date")
        df = df.rename(columns={"vol": "volume"})
    else:
        # 日线数据
        sd = start_date.replace("-", "")
        ed = end_date.replace("-", "")
        if hasattr(api, 'query'):
            # TushareHttpClient
            df = api.query("daily", ts_code=code, start_date=sd, end_date=ed)
        else:
            # tushare SDK pro_api
            df = api.daily(ts_code=code, start_date=sd, end_date=ed)
        if df is None or df.empty:
            return pd.DataFrame()
        df = df.sort_values("trade_date")
        df["trade_date"] = pd.to_datetime(df["trade_date"])
        df = df.set_index("trade_date")
        df = df.rename(columns={"vol": "volume"})

    # 保留 OHLCV 列并转换数值类型
    for col in ["open", "high", "low", "close", "volume"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    ohlcv_cols = [c for c in ["open", "high", "low", "close", "volume"] if c in df.columns]
    df = df[ohlcv_cols].dropna(subset=["open", "high", "low", "close"])
    return df


def demo_standardized_ohlcv():
    """7. 标准化 OHLCV 输出示例"""
    print("\n" + "=" * 60)
    print("7. 标准化 OHLCV 数据（贵州茅台 2024年1月）")
    print("=" * 60)
    api = get_tushare_api()
    if api is None:
        print("  [跳过] API 未初始化")
        return
    df = fetch_ohlcv_standardized(api, "600519.SH", "20240101", "20240131")
    if not df.empty:
        print(df.head())
    else:
        print("  无数据")


if __name__ == '__main__':
    api = get_tushare_api()
    demo_daily_ohlcv(api)
    demo_minute_ohlcv(api)
    demo_daily_basic(api)
    demo_trade_cal(api)
    demo_stock_basic(api)
    demo_http_client()
    demo_standardized_ohlcv()
