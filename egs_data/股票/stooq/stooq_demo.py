# -*- coding: utf-8 -*-
# @Author   : ai_quant_trade
# @File     : stooq_demo.py
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
Stooq 免费金融数据接口示例
覆盖：美股行情、全球指数、CSV历史数据下载

特点：免费、无需 API Key、支持 CSV 直接下载
局限：数据延迟约15分钟、不支持实时分时

参考来源：
  - Vibe-Trading: backtest/loaders/stooq_loader.py (标准 OHLCV 加载器)
  - daily_stock_analysis: data_provider/yfinance_fetcher.py
    (Stooq 作为 yfinance 限流时的免密钥兜底)
"""

import csv
import logging
from datetime import datetime
from io import StringIO
from typing import Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 120)

# Stooq 基础 URL
STOOQ_BASE_URL = "https://stooq.com"


def _stooq_request(url: str, timeout: int = 15) -> Optional[str]:
    """发送 Stooq HTTP 请求，返回响应文本

    注意：Stooq 网站对非浏览器请求返回 JavaScript 验证页面，
    若返回内容包含 HTML 标签，则视为验证页面，返回 None。
    """
    request = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/csv,text/plain,text/html,*/*",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            content = response.read().decode("utf-8", "ignore").strip()
            # 检测是否被重定向到 JavaScript 验证页面
            if "<!DOCTYPE html>" in content or "<html" in content.lower():
                logger.warning("Stooq 返回了 JavaScript 验证页面，请使用浏览器访问或稍后重试")
                return None
            return content
    except (HTTPError, URLError, TimeoutError) as exc:
        logger.warning(f"Stooq 请求失败: {exc}")
        return None


def demo_us_stock_quote():
    """1. 美股最新行情（CSV格式）"""
    print("=" * 60)
    print("1. AAPL 美股最新行情")
    print("=" * 60)
    url = f"{STOOQ_BASE_URL}/q/l/?s=aapl.us"
    payload = _stooq_request(url)
    if not payload or payload.upper().startswith("NO DATA"):
        print("  无数据")
        return
    print(f"  原始CSV:\n{payload}")
    # 解析CSV
    reader = csv.reader(StringIO(payload))
    rows = list(reader)
    if len(rows) >= 2:
        header = rows[0]
        data = rows[1] if len(rows) > 1 else rows[0]
        print(f"\n  解析结果:")
        for h, d in zip(header, data):
            print(f"    {h}: {d}")


def demo_us_stock_history():
    """2. 美股历史日线数据"""
    print("\n" + "=" * 60)
    print("2. AAPL 日线历史数据（最近30天）")
    print("=" * 60)
    url = f"{STOOQ_BASE_URL}/q/d/l/?s=aapl.us&i=d"
    payload = _stooq_request(url)
    if not payload or payload.upper().startswith("NO DATA"):
        print("  无数据")
        return
    try:
        df = pd.read_csv(StringIO(payload))
        print(df.tail(10))
        # 字段: Date, Open, High, Low, Close, Volume
    except Exception as e:
        print(f"  解析失败: {e}")


def demo_global_index():
    """3. 全球指数行情"""
    print("\n" + "=" * 60)
    print("3. 全球主要指数行情")
    print("=" * 60)
    # Stooq 指数代码
    indices = {
        "^spx": "S&P 500",
        "^dji": "道琼斯工业",
        "^ndq": "纳斯达克100",
        "^dax": "德国DAX",
        "^nkx": "日经225",
    }
    for symbol, name in indices.items():
        url = f"{STOOQ_BASE_URL}/q/l/?s={symbol}"
        payload = _stooq_request(url)
        if payload and not payload.upper().startswith("NO DATA"):
            try:
                reader = csv.reader(StringIO(payload))
                rows = list(reader)
                if len(rows) >= 2:
                    # 最后一列通常是收盘价
                    price = rows[-1][-2] if len(rows[-1]) >= 2 else "N/A"
                    print(f"  {name}({symbol}): {price}")
            except Exception:
                print(f"  {name}({symbol}): 解析失败")
        else:
            print(f"  {name}({symbol}): 无数据")


def demo_etf_history():
    """4. ETF 历史数据"""
    print("\n" + "=" * 60)
    print("4. SPY ETF 日线历史数据")
    print("=" * 60)
    url = f"{STOOQ_BASE_URL}/q/d/l/?s=spy.us&i=d"
    payload = _stooq_request(url)
    if not payload or payload.upper().startswith("NO DATA"):
        print("  无数据")
        return
    try:
        df = pd.read_csv(StringIO(payload))
        print(df.tail(10))
    except Exception as e:
        print(f"  解析失败: {e}")


# ---------------------------------------------------------------------------
# 标准化 OHLCV 输出（参考 Vibe-Trading 的 DataLoader 接口）
# ---------------------------------------------------------------------------

def fetch_ohlcv_from_stooq(symbol: str, start_date: str = "", end_date: str = "",
                           interval: str = "d") -> pd.DataFrame:
    """从 Stooq 获取标准化 OHLCV 数据

    Args:
        symbol: Stooq 代码，如 "aapl.us", "spy.us"
        start_date: 起始日期 YYYYMMDD（可选）
        end_date: 结束日期 YYYYMMDD（可选）
        interval: d=日线, w=周线, m=月线

    Returns:
        标准化 OHLCV DataFrame，索引为 trade_date
    """
    url = f"{STOOQ_BASE_URL}/q/d/l/?s={symbol}&i={interval}"
    if start_date:
        url += f"&d1={start_date}"
    if end_date:
        url += f"&d2={end_date}"

    payload = _stooq_request(url)
    if not payload or payload.upper().startswith("NO DATA"):
        return pd.DataFrame()

    try:
        df = pd.read_csv(StringIO(payload))
    except Exception:
        return pd.DataFrame()

    if df.empty:
        return pd.DataFrame()

    # 标准化列名
    col_map = {
        "Date": "trade_date", "Open": "open", "High": "high",
        "Low": "low", "Close": "close", "Volume": "volume",
    }
    df = df.rename(columns=col_map)

    if "trade_date" in df.columns:
        df["trade_date"] = pd.to_datetime(df["trade_date"])
        df = df.set_index("trade_date").sort_index()

    for col in ["open", "high", "low", "close", "volume"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    ohlcv_cols = [c for c in ["open", "high", "low", "close", "volume"] if c in df.columns]
    if not ohlcv_cols:
        return pd.DataFrame()
    subset = [c for c in ["open", "high", "low", "close"] if c in df.columns]
    if subset:
        df = df.dropna(subset=subset)
    return df[ohlcv_cols]


def demo_standardized_ohlcv():
    """5. 标准化 OHLCV 数据输出"""
    print("\n" + "=" * 60)
    print("5. 标准化 OHLCV 数据（AAPL 最近30天）")
    print("=" * 60)
    df = fetch_ohlcv_from_stooq("aapl.us")
    if not df.empty:
        print(df.tail(10))
    else:
        print("  无数据")


def demo_as_fallback():
    """6. 作为 yfinance 限流时的兜底数据源

    参考 daily_stock_analysis 的 _get_us_stock_quote_from_stooq 方法：
    当 yfinance 被限流时，Stooq 提供免密钥的兜底行情
    """
    print("\n" + "=" * 60)
    print("6. Stooq 作为 yfinance 限流兜底")
    print("=" * 60)
    symbol = "aapl.us"
    url = f"{STOOQ_BASE_URL}/q/l/?s={symbol}"
    payload = _stooq_request(url)

    if not payload or payload.upper().startswith("NO DATA"):
        print("  Stooq 也无法获取数据")
        return

    try:
        reader = csv.reader(StringIO(payload))
        first_row = next(reader, None)
        if first_row is None:
            return
        # 判断是否包含 header
        header_tokens = {cell.strip().lower() for cell in first_row if cell}
        has_header = 'open' in header_tokens and 'close' in header_tokens
        row = next(reader, None) if has_header else first_row
        if row and len(row) >= 7:
            normalized = [cell.strip() for cell in row]
            print(f"  AAPL 兜底行情:")
            print(f"    开盘: {normalized[2] if len(normalized) > 2 else 'N/A'}")
            print(f"    最高: {normalized[3] if len(normalized) > 3 else 'N/A'}")
            print(f"    最低: {normalized[4] if len(normalized) > 4 else 'N/A'}")
            print(f"    收盘: {normalized[5] if len(normalized) > 5 else 'N/A'}")
            print(f"    成交量: {normalized[6] if len(normalized) > 6 else 'N/A'}")
    except Exception as e:
        print(f"  解析失败: {e}")


if __name__ == '__main__':
    demo_us_stock_quote()
    demo_us_stock_history()
    demo_global_index()
    demo_etf_history()
    demo_standardized_ohlcv()
    demo_as_fallback()
