# -*- coding: utf-8 -*-
# @Author   : ai_quant_trade
# @File     : akshare_demo.py
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
AKShare 免费金融数据接口示例
覆盖：股票行情、指数、期货、宏观经济、北向资金、财务报表、ETF、港股、美股、外汇
安装：pip install akshare --upgrade
"""

import akshare as ak
import pandas as pd

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 120)


def demo_stock_realtime():
    """1. A股实时行情（东方财富）"""
    print("=" * 60)
    print("1. A股实时行情（前5行）")
    print("=" * 60)
    try:
        df = ak.stock_zh_a_spot_em()
        print(df.head())
        # 字段：代码、名称、最新价、涨跌幅、涨跌额、成交量、成交额、振幅、最高、最低、今开、昨收、量比、换手率、市盈率-动态、市净率、总市值、流通市值
    except Exception as e:
        print(f"  获取失败: {e}")


def demo_stock_hist():
    """2. 股票历史K线（前复权，日频）"""
    print("\n" + "=" * 60)
    print("2. 中国平安(601318) 历史日K线（前复权）")
    print("=" * 60)
    try:
        df = ak.stock_zh_a_hist(
            symbol="601318",
            period="daily",        # daily/weekly/monthly
            start_date="20230101",
            end_date="20231231",
            adjust="qfq"           # qfq前复权/hfq后复权/空不复权
        )
        print(df.head())
        # 字段：日期、股票代码、开盘、收盘、最高、最低、成交量、成交额、振幅、涨跌幅、涨跌额、换手率
    except Exception as e:
        print(f"  获取失败: {e}")


def demo_index_daily():
    """3. 指数历史行情（上证指数）"""
    print("\n" + "=" * 60)
    print("3. 上证指数(sh000001) 历史行情")
    print("=" * 60)
    try:
        df = ak.stock_zh_index_daily(symbol="sh000001")
        print(df.tail())
    except Exception as e:
        print(f"  获取失败: {e}")


def demo_futures():
    """4. 期货日K线数据"""
    print("\n" + "=" * 60)
    print("4. 期货日K线（PVC主力）")
    print("=" * 60)
    try:
        df = ak.futures_main_sina(symbol="V0")
        print(df.tail())
        # 字段：日期、开盘价、最高价、最低价、收盘价、成交量、持仓量、动态结算价
    except Exception as e:
        print(f"  获取失败: {e}")


def demo_macro_gdp():
    """5. 宏观经济 - 中国GDP"""
    print("\n" + "=" * 60)
    print("5. 中国GDP季度数据")
    print("=" * 60)
    try:
        df = ak.macro_china_gdp()
        print(df.tail())
        # 字段：季度、国内生产总值-绝对值、国内生产总值-同比增长、第一产业-绝对值、...
    except Exception as e:
        print(f"  获取失败: {e}")


def demo_north_money():
    """6. 北向资金每日净流入"""
    print("\n" + "=" * 60)
    print("6. 北向资金每日净流入")
    print("=" * 60)
    try:
        df = ak.stock_hsgt_hist_em(symbol="北向资金")
        print(df.tail())
        # 字段：日期、当日净流入、当日余额
    except Exception as e:
        print(f"  获取失败: {e}")


def demo_financial_report():
    """7. 财务报表 - 资产负债表"""
    print("\n" + "=" * 60)
    print("7. 中国平安(601318) 资产负债表")
    print("=" * 60)
    try:
        df = ak.stock_financial_report_sina(stock="601318", symbol="资产负债表")
        print(df.head())
        # 返回最新报告期的资产负债表数据
    except Exception as e:
        print(f"  获取失败: {e}")


def demo_fund_etf():
    """8. ETF历史行情"""
    print("\n" + "=" * 60)
    print("8. 沪深300ETF(510300) 历史行情")
    print("=" * 60)
    try:
        df = ak.fund_etf_hist_em(symbol="510300", period="daily",
                                 start_date="20230101", end_date="20231231",
                                 adjust="qfq")
        print(df.head())
    except Exception as e:
        print(f"  获取失败: {e}")


# ---------------------------------------------------------------------------
# 以下示例参考 Vibe-Trading 和 daily_stock_analysis 的多市场采集模式
# ---------------------------------------------------------------------------

def demo_etf_sina():
    """9. ETF历史行情（新浪接口，参考 Vibe-Trading _fetch_etf）"""
    print("\n" + "=" * 60)
    print("9. 黄金ETF(518880) 历史行情（新浪接口）")
    print("=" * 60)
    try:
        # fund_etf_hist_sina 返回全量历史，需手动裁剪
        df = ak.fund_etf_hist_sina(symbol="sh518880")
        if df is not None and not df.empty:
            # 裁剪到指定窗口
            df = df.rename(columns={"date": "trade_date"})
            df["trade_date"] = pd.to_datetime(df["trade_date"])
            df = df.set_index("trade_date").sort_index()
            # 取最近30天
            recent = df.last("30D")
            print(recent.head())
        else:
            print("  无数据")
    except Exception as e:
        print(f"  获取失败: {e}")


def demo_hk_stock():
    """10. 港股历史行情（参考 Vibe-Trading _fetch_hk）"""
    print("\n" + "=" * 60)
    print("10. 腾讯控股(00700) 港股历史行情")
    print("=" * 60)
    try:
        # akshare 港股代码为5位数字
        df = ak.stock_hk_hist(
            symbol="00700",
            period="daily",
            start_date="20240101",
            end_date="20240131",
            adjust="qfq"
        )
        if df is not None and not df.empty:
            print(df.head())
            # 字段：日期、开盘、收盘、最高、最低、成交量、成交额、振幅、涨跌幅、涨跌额、换手率
        else:
            print("  无数据")
    except Exception as e:
        print(f"  获取失败: {e}")


def demo_us_stock():
    """11. 美股历史行情（参考 Vibe-Trading _fetch_us）"""
    print("\n" + "=" * 60)
    print("11. 苹果(AAPL) 美股历史行情")
    print("=" * 60)
    try:
        # akshare 美股接口需要带前缀（105=纳斯达克）
        df = ak.stock_us_hist(
            symbol="105.AAPL",
            period="daily",
            start_date="20240101",
            end_date="20240131",
            adjust="qfq"
        )
        if df is not None and not df.empty:
            print(df.head())
        else:
            print("  无数据（尝试不带前缀...）")
            try:
                df = ak.stock_us_hist(
                    symbol="AAPL",
                    period="daily",
                    start_date="20240101",
                    end_date="20240131",
                    adjust="qfq"
                )
                if df is not None and not df.empty:
                    print(df.head())
            except Exception:
                print("  仍失败")
    except Exception as e:
        print(f"  获取失败: {e}")


def demo_forex():
    """12. 外汇历史行情（参考 Vibe-Trading _fetch_forex）"""
    print("\n" + "=" * 60)
    print("12. EURUSD 外汇历史行情")
    print("=" * 60)
    try:
        df = ak.forex_hist_em(symbol="EURUSD")
        if df is not None and not df.empty:
            # 标准化列名
            df = df.rename(columns={
                "日期": "trade_date", "今开": "open", "最新价": "close",
                "最高": "high", "最低": "low",
            })
            df["trade_date"] = pd.to_datetime(df["trade_date"])
            df = df.set_index("trade_date").sort_index()
            # 外汇无成交量，补零
            df["volume"] = 0.0
            for col in ("open", "high", "low", "close"):
                df[col] = pd.to_numeric(df[col], errors="coerce")
            print(df[["open", "high", "low", "close", "volume"]].tail(10))
        else:
            print("  无数据")
    except Exception as e:
        print(f"  获取失败: {e}")


def demo_standardized_ohlcv():
    """13. 标准化 OHLCV 输出（参考 Vibe-Trading DataLoader 统一接口）

    将不同市场的数据统一为 (trade_date, open, high, low, close, volume) 格式
    """
    print("\n" + "=" * 60)
    print("13. 标准化 OHLCV 数据获取")
    print("=" * 60)

    def _normalize(df, date_col="日期"):
        """通用标准化函数"""
        cn_map = {"开盘": "open", "最高": "high", "最低": "low",
                  "收盘": "close", "成交量": "volume"}
        en_map = {"date": "trade_date", "open": "open", "high": "high",
                  "low": "low", "close": "close", "volume": "volume"}
        if date_col in df.columns:
            df = df.rename(columns={date_col: "trade_date"})
        elif "date" in df.columns:
            df = df.rename(columns={"date": "trade_date"})
        if "开盘" in df.columns:
            df = df.rename(columns=cn_map)
        else:
            df = df.rename(columns=en_map)
        df["trade_date"] = pd.to_datetime(df["trade_date"])
        df = df.set_index("trade_date").sort_index()
        for col in ["open", "high", "low", "close", "volume"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        ohlcv = [c for c in ["open", "high", "low", "close", "volume"] if c in df.columns]
        subset = [c for c in ["open", "high", "low", "close"] if c in df.columns]
        if subset:
            df = df.dropna(subset=subset)
        if "volume" not in df.columns:
            df["volume"] = 0.0
        return df[ohlcv]

    # A股
    try:
        df_a = ak.stock_zh_a_hist(symbol="601318", period="daily",
                                   start_date="20240101", end_date="20240110", adjust="qfq")
        df_a_std = _normalize(df_a)
        print("  A股(601318) 标准化数据:")
        print(f"    列: {list(df_a_std.columns)}")
        print(f"    行数: {len(df_a_std)}")
    except Exception as e:
        print(f"  A股获取失败: {e}")

    # 港股
    try:
        df_hk = ak.stock_hk_hist(symbol="00700", period="daily",
                                  start_date="20240101", end_date="20240110", adjust="qfq")
        df_hk_std = _normalize(df_hk)
        print(f"  港股(00700) 标准化数据: {len(df_hk_std)} 行")
    except Exception as e:
        print(f"  港股: {e}")


def demo_realtime_enhanced():
    """14. 增强实时行情（参考 daily_stock_analysis AkshareFetcher）

    包含量比、换手率、市盈率、市净率、市值等增强指标
    """
    print("\n" + "=" * 60)
    print("14. 增强实时行情（前5行）")
    print("=" * 60)
    try:
        df = ak.stock_zh_a_spot_em()
        if df is not None and not df.empty:
            # 增强字段示例：选取贵州茅台
            maotai = df[df["代码"] == "600519"]
            if not maotai.empty:
                row = maotai.iloc[0]
                print(f"  贵州茅台(600519) 增强行情:")
                for col in df.columns:
                    val = row.get(col, "")
                    print(f"    {col}: {val}")
        else:
            print("  无数据")
    except Exception as e:
        print(f"  获取失败: {e}")


if __name__ == '__main__':
    demo_stock_realtime()
    demo_stock_hist()
    demo_index_daily()
    demo_futures()
    demo_macro_gdp()
    demo_north_money()
    demo_financial_report()
    demo_fund_etf()
    demo_etf_sina()
    demo_hk_stock()
    demo_us_stock()
    demo_forex()
    demo_standardized_ohlcv()
    demo_realtime_enhanced()
