# -*- coding: utf-8 -*-
# @Author   : ai_quant_trade
# @File     : data_loader_base_demo.py
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
数据加载器框架示例
覆盖：Protocol 接口定义、注册表、回退链、缓存、重试机制

本示例展示如何构建一个统一的数据获取框架，使多个数据源
可以互换使用、自动降级回退。

参考来源：
  - Vibe-Trading:
    - backtest/loaders/base.py (DataLoaderProtocol, 重试, 缓存)
    - backtest/loaders/registry.py (注册表, 回退链)
  - daily_stock_analysis:
    - data_provider/base.py (策略模式, 自动切换)
"""

import time
import logging
from typing import Dict, List, Optional, Protocol, Type, TypeVar, runtime_checkable

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 120)


# ===========================================================================
# 第一部分：Protocol 接口定义（参考 Vibe-Trading DataLoaderProtocol）
# ===========================================================================

@runtime_checkable
class DataLoaderProtocol(Protocol):
    """数据加载器接口协议

    每个数据源加载器必须满足此接口，包括：
    - name: 数据源名称
    - markets: 支持的市场集合
    - requires_auth: 是否需要认证
    - is_available(): 检查是否可用
    - fetch(): 获取 OHLCV 数据
    """

    name: str
    markets: set
    requires_auth: bool

    def is_available(self) -> bool:
        """检查数据源是否可用（Token存在、网络正常等）"""
        ...

    def fetch(
        self,
        codes: List[str],
        start_date: str,
        end_date: str,
        *,
        interval: str = "1D",
        fields: Optional[List[str]] = None,
    ) -> Dict[str, pd.DataFrame]:
        """获取 OHLCV 数据

        Args:
            codes: 股票代码列表，如 ["600519.SH", "000001.SZ"]
            start_date: 起始日期 YYYY-MM-DD
            end_date: 结束日期 YYYY-MM-DD
            interval: K线周期，1D/1H/5m 等
            fields: 额外字段列表（可选）

        Returns:
            {symbol: DataFrame(trade_date, open, high, low, close, volume)}
        """
        ...


# ===========================================================================
# 第二部分：数据验证工具（参考 Vibe-Trading base.py）
# ===========================================================================

def validate_date_range(start_date: str, end_date: str) -> None:
    """验证日期范围"""
    try:
        start = pd.Timestamp(start_date)
        end = pd.Timestamp(end_date)
    except Exception as exc:
        raise ValueError(f"无效日期格式: start={start_date!r}, end={end_date!r}") from exc
    if start > end:
        raise ValueError(f"起始日期 ({start_date}) > 结束日期 ({end_date})")


def validate_ohlc(frame: pd.DataFrame, *, strategy: str = "drop") -> pd.DataFrame:
    """校验 OHLC 数据一致性

    检查 high >= low, high >= open/close, low <= open/close, 价格 > 0

    Args:
        frame: OHLCV DataFrame
        strategy: "drop"(删除无效行), "warn"(仅警告), "raise"(抛异常)

    Returns:
        校验后的 DataFrame
    """
    required = ("open", "high", "low", "close")
    if frame.empty or not all(col in frame.columns for col in required):
        return frame

    open_, high, low, close = (frame[c] for c in required)
    invalid = (
        (high < low)
        | (high < open_)
        | (high < close)
        | (low > open_)
        | (low > close)
        | (open_ <= 0)
        | (high <= 0)
        | (low <= 0)
        | (close <= 0)
    )
    n_invalid = int(invalid.sum())
    if n_invalid == 0:
        return frame

    if strategy == "raise":
        raise ValueError(f"{n_invalid} 条记录违反 OHLC 约束")
    if strategy == "warn":
        logger.warning("OHLC 校验: %d 条记录异常 (已保留)", n_invalid)
        return frame
    logger.warning("OHLC 校验: 删除 %d 条异常记录", n_invalid)
    return frame[~invalid]


# ===========================================================================
# 第三部分：重试机制（参考 Vibe-Trading base.py retry_with_budget）
# ===========================================================================

DEFAULT_BACKOFF = (0.5, 1.5, 4.0)
DEFAULT_MAX_RETRIES = 3


def retry_with_budget(
    fn,
    *,
    transient: type = Exception,
    max_retries: int = DEFAULT_MAX_RETRIES,
    backoff: tuple = DEFAULT_BACKOFF,
    budget_s: float = 60.0,
    label: str = "fetch",
) -> object:
    """带预算的有限重试

    在指定的瞬态异常上重试 fn()，最多重试 max_retries 次，
    总耗时不超过 budget_s 秒。

    Args:
        fn: 无参可调用对象
        transient: 视为可重试的异常类型
        max_retries: 最大重试次数
        backoff: 每次重试的等待秒数
        budget_s: 总时间预算（秒）
        label: 用于日志的标签

    Returns:
        fn() 的返回值
    """
    deadline = time.monotonic() + budget_s
    for attempt in range(max_retries + 1):
        try:
            return fn()
        except transient as exc:
            remaining = deadline - time.monotonic()
            if attempt == max_retries or remaining <= 0:
                raise TimeoutError(
                    f"{label} 在 {attempt + 1} 次尝试后失败: {exc}"
                ) from exc
            time.sleep(min(backoff[attempt], max(0.0, remaining)))
    raise AssertionError("unreachable")


# ===========================================================================
# 第四部分：注册表与回退链（参考 Vibe-Trading registry.py）
# ===========================================================================

LOADER_REGISTRY: Dict[str, Type] = {}


def register(cls: Type) -> Type:
    """类装饰器：将数据加载器注册到全局注册表"""
    LOADER_REGISTRY[cls.name] = cls
    return cls


# 回退链：市场类型 -> 优先级排序的数据源列表
FALLBACK_CHAINS: Dict[str, List[str]] = {
    "a_share":   ["akshare", "baostock", "tushare", "efinance"],
    "us_equity": ["yfinance", "stooq", "akshare"],
    "hk_equity": ["akshare", "yfinance"],
    "crypto":    ["ccxt", "yfinance"],
    "futures":   ["tushare", "akshare"],
    "fund":      ["tushare", "akshare"],
    "forex":     ["akshare", "yfinance"],
}


def resolve_loader(market: str):
    """按回退链获取第一个可用的数据加载器实例

    Args:
        market: 市场类型，如 "a_share", "us_equity"

    Returns:
        可用的数据加载器实例

    Raises:
        RuntimeError: 所有候选数据源均不可用
    """
    chain = FALLBACK_CHAINS.get(market, [])
    tried = []
    for name in chain:
        if name not in LOADER_REGISTRY:
            continue
        tried.append(name)
        try:
            loader = LOADER_REGISTRY[name]()
        except Exception as exc:
            logger.debug("加载器 %s 初始化失败: %s", name, exc)
            continue
        if loader.is_available():
            logger.info("为市场 %s 选择数据源: %s", market, name)
            return loader
    raise RuntimeError(
        f"市场 '{market}' 无可用数据源。尝试: {tried or chain}"
    )


# ===========================================================================
# 第五部分：具体数据源实现示例
# ===========================================================================

@register
class AkshareLoader:
    """AKShare 数据加载器（免费、无需认证）"""

    name = "akshare"
    markets = {"a_share", "us_equity", "hk_equity", "futures", "fund", "forex"}
    requires_auth = False

    def is_available(self) -> bool:
        try:
            import akshare  # noqa: F401
            return True
        except ImportError:
            return False

    def fetch(self, codes, start_date, end_date, *, interval="1D", fields=None):
        import akshare as ak
        validate_date_range(start_date, end_date)
        result = {}
        for code in codes:
            try:
                df = self._fetch_one(ak, code, start_date, end_date, interval)
                if df is not None and not df.empty:
                    result[code] = df
            except Exception as exc:
                logger.warning("akshare 获取 %s 失败: %s", code, exc)
        return result

    def _fetch_one(self, ak, code, start_date, end_date, interval):
        symbol = code.split(".")[0]
        sd = start_date.replace("-", "")
        ed = end_date.replace("-", "")
        period_map = {"1D": "daily", "1W": "weekly", "1M": "monthly"}
        period = period_map.get(interval, "daily")
        df = ak.stock_zh_a_hist(symbol=symbol, period=period,
                                start_date=sd, end_date=ed, adjust="qfq")
        if df is None or df.empty:
            return None
        # 标准化列名
        col_map = {"日期": "trade_date", "开盘": "open", "最高": "high",
                    "最低": "low", "收盘": "close", "成交量": "volume"}
        df = df.rename(columns=col_map)
        df["trade_date"] = pd.to_datetime(df["trade_date"])
        df = df.set_index("trade_date").sort_index()
        for col in ["open", "high", "low", "close", "volume"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        return df[["open", "high", "low", "close", "volume"]].dropna(
            subset=["open", "high", "low", "close"])


@register
class YfinanceLoader:
    """yfinance 数据加载器（免费、无需认证、支持美股/港股）"""

    name = "yfinance"
    markets = {"us_equity", "hk_equity", "crypto"}
    requires_auth = False

    def is_available(self) -> bool:
        try:
            import yfinance  # noqa: F401
            return True
        except ImportError:
            return False

    def fetch(self, codes, start_date, end_date, *, interval="1D", fields=None):
        import yfinance as yf
        validate_date_range(start_date, end_date)
        result = {}
        for code in codes:
            try:
                yf_code = self._convert_code(code)
                ticker = yf.Ticker(yf_code)
                hist = ticker.history(start=start_date, end=end_date, auto_adjust=True)
                if hist.empty:
                    continue
                df = hist.rename(columns={
                    "Open": "open", "High": "high", "Low": "low",
                    "Close": "close", "Volume": "volume",
                })
                df.index = pd.DatetimeIndex(df.index)
                df.index.name = "trade_date"
                for col in ["open", "high", "low", "close", "volume"]:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors="coerce")
                df = df[["open", "high", "low", "close", "volume"]]
                result[code] = df
            except Exception as exc:
                logger.warning("yfinance 获取 %s 失败: %s", code, exc)
        return result

    def _convert_code(self, code):
        """转换代码为 yfinance 格式"""
        upper = code.strip().upper()
        if upper.endswith(".US"):
            return upper[:-3]
        if upper.endswith(".SH"):
            return upper[:-3] + ".SS"
        if upper.endswith(".SZ"):
            return upper[:-3] + ".SZ"
        return upper


@register
class StooqLoader:
    """Stooq 数据加载器（免费、无需认证、美股兜底）"""

    name = "stooq"
    markets = {"us_equity"}
    requires_auth = False

    def is_available(self) -> bool:
        return True  # 纯 HTTP，无需额外依赖

    def fetch(self, codes, start_date, end_date, *, interval="1D", fields=None):
        from urllib.request import Request, urlopen
        validate_date_range(start_date, end_date)
        result = {}
        for code in codes:
            symbol = code.replace(".US", "").lower() + ".us"
            url = f"https://stooq.com/q/d/l/?s={symbol}&i=d"
            try:
                req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urlopen(req, timeout=15) as resp:
                    payload = resp.read().decode("utf-8", "ignore").strip()
                if not payload or payload.upper().startswith("NO DATA"):
                    continue
                from io import StringIO
                df = pd.read_csv(StringIO(payload))
                if df.empty:
                    continue
                col_map = {"Date": "trade_date", "Open": "open", "High": "high",
                            "Low": "low", "Close": "close", "Volume": "volume"}
                df = df.rename(columns=col_map)
                df["trade_date"] = pd.to_datetime(df["trade_date"])
                df = df.set_index("trade_date").sort_index()
                for col in ["open", "high", "low", "close", "volume"]:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors="coerce")
                result[code] = df[["open", "high", "low", "close", "volume"]]
            except Exception as exc:
                logger.warning("stooq 获取 %s 失败: %s", code, exc)
        return result


# ===========================================================================
# 第六部分：演示
# ===========================================================================

def demo_protocol_check():
    """1. 接口协议检查"""
    print("=" * 60)
    print("1. DataLoaderProtocol 接口检查")
    print("=" * 60)
    loader = AkshareLoader()
    print(f"  AkshareLoader 是否满足协议: {isinstance(loader, DataLoaderProtocol)}")
    print(f"  数据源名称: {loader.name}")
    print(f"  支持市场: {loader.markets}")
    print(f"  需要认证: {loader.requires_auth}")
    print(f"  当前可用: {loader.is_available()}")


def demo_registry():
    """2. 注册表与回退链"""
    print("\n" + "=" * 60)
    print("2. 数据加载器注册表")
    print("=" * 60)
    print(f"  已注册数据源: {list(LOADER_REGISTRY.keys())}")
    print(f"  A股回退链: {FALLBACK_CHAINS.get('a_share', [])}")
    print(f"  美股回退链: {FALLBACK_CHAINS.get('us_equity', [])}")


def demo_resolve_loader():
    """3. 自动选择数据源"""
    print("\n" + "=" * 60)
    print("3. 按回退链自动选择数据源")
    print("=" * 60)
    for market in ["a_share", "us_equity", "hk_equity", "crypto"]:
        try:
            loader = resolve_loader(market)
            print(f"  {market} -> {loader.name}")
        except RuntimeError as e:
            print(f"  {market} -> 无可用数据源: {e}")


def demo_data_validation():
    """4. OHLCV 数据校验"""
    print("\n" + "=" * 60)
    print("4. OHLCV 数据校验示例")
    print("=" * 60)
    # 构造含异常的数据
    data = {
        "open": [100, 105, 110, 0],      # 最后一行 open=0 违规
        "high": [102, 103, 112, 108],     # 第2行 high < low 违规
        "low":  [98,  106, 108, 107],
        "close":[101, 104, 111, 107],
    }
    df = pd.DataFrame(data, index=pd.date_range("2024-01-01", periods=4))
    print("  原始数据:")
    print(df)
    df_clean = validate_ohlc(df, strategy="drop")
    print(f"\n  校验后数据 (删除 {len(df) - len(df_clean)} 条异常):")
    print(df_clean)


def demo_retry():
    """5. 带预算的重试机制"""
    print("\n" + "=" * 60)
    print("5. 重试机制示例")
    print("=" * 60)
    attempt = 0

    def flaky_fetch():
        nonlocal attempt
        attempt += 1
        if attempt < 3:
            print(f"  第 {attempt} 次尝试: 模拟网络超时...")
            raise ConnectionError("模拟网络超时")
        print(f"  第 {attempt} 次尝试: 成功!")
        return pd.DataFrame({"close": [100, 101, 102]})

    try:
        result = retry_with_budget(
            flaky_fetch,
            transient=ConnectionError,
            max_retries=3,
            backoff=(0.1, 0.2, 0.5),
            budget_s=10.0,
            label="demo_fetch",
        )
        print(f"  重试成功，结果:\n{result}")
    except TimeoutError as e:
        print(f"  重试失败: {e}")


def demo_multi_source_fetch():
    """6. 多数据源获取对比"""
    print("\n" + "=" * 60)
    print("6. 多数据源获取同一标的数据（A股: 601318）")
    print("=" * 60)
    codes = ["601318"]
    start_date = "2024-01-02"
    end_date = "2024-01-10"

    for name, cls in LOADER_REGISTRY.items():
        try:
            loader = cls()
            if not loader.is_available():
                print(f"  {name}: 不可用（依赖未安装）")
                continue
            result = loader.fetch(codes, start_date, end_date)
            if result:
                key = list(result.keys())[0]
                df = result[key]
                print(f"  {name}: 获取 {len(df)} 条记录")
                print(f"    列: {list(df.columns)}")
                if not df.empty:
                    print(f"    最新收盘: {df['close'].iloc[-1]:.2f}")
            else:
                print(f"  {name}: 无数据返回")
        except Exception as e:
            print(f"  {name}: 失败 - {str(e)[:60]}")


if __name__ == '__main__':
    demo_protocol_check()
    demo_registry()
    demo_resolve_loader()
    demo_data_validation()
    demo_retry()
    demo_multi_source_fetch()
