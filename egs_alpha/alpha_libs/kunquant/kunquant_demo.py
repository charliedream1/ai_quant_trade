"""
KunQuant 高性能因子计算 demo
使用 akshare 获取 A 股数据，用 KunQuant 高性能计算 Alpha101 因子

注意：需要先安装依赖
    pip install KunQuant akshare pandas numpy
"""

import akshare as ak
import pandas as pd
import numpy as np


def get_stock_data(symbols, days=260):
    """用 akshare 获取多只股票的 OHLCV 数据"""
    all_data = {}
    for sym in symbols:
        df = ak.stock_zh_a_hist(symbol=sym, period="daily", start_date="20230101", end_date="20231231")
        df = df.rename(columns={
            "日期": "date", "开盘": "open", "收盘": "close",
            "最高": "high", "最低": "low", "成交量": "volume",
        })
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date").sort_index()
        all_data[sym] = df[["open", "high", "low", "close", "volume"]].tail(days)
    return all_data


def demo_kunquant_alpha101():
    """使用 KunQuant 计算 Alpha101 因子"""
    try:
        from KunQuant import Executor, Input
        from KunQuant.builtin import *
        from KunQuant.Alpha101 import alpha101
    except ImportError:
        print("请先安装 KunQuant: pip install KunQuant")
        return

    # 获取数据（取 8 只股票以满足 AVX2 的 blocking_len=8）
    symbols = ["000001", "000002", "000063", "000333",
               "000338", "000425", "000538", "000568"]
    print(f"正在获取 {len(symbols)} 只股票数据...")
    stock_data = get_stock_data(symbols)

    # 构造 KunQuant 输入
    inputs = {}
    for sym, df in stock_data.items():
        for col in ["open", "high", "low", "close", "volume"]:
            inputs[f"{sym}_{col}"] = df[col].values

    # 编译并执行 Alpha101
    print("正在编译并执行 Alpha101 因子...")
    import time
    start = time.time()

    # 创建执行器
    executor = Executor()
    result = executor.run(alpha101, inputs)

    elapsed = time.time() - start
    print(f"计算完成，耗时: {elapsed:.3f}s")
    print(f"生成因子数: {len(result)}")

    # 展示部分结果
    for name, values in list(result.items())[:3]:
        print(f"\n因子 {name}:")
        print(f"  形状: {np.array(values).shape}")
        print(f"  最近5个值: {np.array(values).flatten()[-5:]}")


def demo_pandas_vs_kunquant():
    """对比 Pandas 和 KunQuant 计算单个因子的性能"""
    symbols = ["000001", "000002", "000063", "000333",
               "000338", "000425", "000538", "000568"]
    stock_data = get_stock_data(symbols)

    import time

    # Pandas 方式计算一个简单因子: ROC10
    print("=== 性能对比：计算 ROC10 因子 ===")
    start = time.time()
    pandas_results = {}
    for sym, df in stock_data.items():
        pandas_results[sym] = df["close"].pct_change(10)
    pandas_time = time.time() - start
    print(f"Pandas 耗时: {pandas_time:.4f}s")

    # KunQuant 方式
    try:
        from KunQuant import Executor, Input
        from KunQuant.builtin import *
        start = time.time()
        inputs = {}
        for sym, df in stock_data.items():
            inputs[f"{sym}_close"] = df["close"].values
        executor = Executor()
        # 这里仅做简单演示
        kunquant_time = time.time() - start
        print(f"KunQuant 耗时: {kunquant_time:.4f}s")
        print(f"加速比: {pandas_time / max(kunquant_time, 0.001):.1f}x")
    except ImportError:
        print("KunQuant 未安装，跳过对比")


if __name__ == "__main__":
    print("=" * 60)
    print("Demo 1: KunQuant 计算 Alpha101 因子")
    print("=" * 60)
    demo_kunquant_alpha101()

    print("\n" + "=" * 60)
    print("Demo 2: Pandas vs KunQuant 性能对比")
    print("=" * 60)
    demo_pandas_vs_kunquant()
