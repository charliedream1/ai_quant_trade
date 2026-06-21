"""
jqfactor_analyzer 单因子分析 demo
使用 akshare 获取 A 股数据，用 jqfactor_analyzer 做因子分析

注意：需要先安装依赖
    pip install jqfactor_analyzer akshare pandas numpy
"""

import pandas as pd
import numpy as np


def generate_mock_stock_data(symbols, days=240):
    """生成模拟 OHLCV 数据（akshare 不可用时的后备）"""
    dates = pd.bdate_range("2023-01-01", periods=days)
    all_data = {}
    for sym in symbols:
        np.random.seed(hash(sym) % 2**32)
        base_price = 10 + np.random.rand() * 40
        returns = np.random.randn(days) * 0.02
        close = base_price * np.cumprod(1 + returns)
        open_ = close * (1 + np.random.randn(days) * 0.01)
        high = np.maximum(open_, close) * (1 + np.abs(np.random.randn(days)) * 0.01)
        low = np.minimum(open_, close) * (1 - np.abs(np.random.randn(days)) * 0.01)
        volume = np.random.randint(5000000, 50000000, size=days).astype(float)
        df = pd.DataFrame({
            "开盘": open_, "收盘": close,
            "最高": high, "最低": low, "成交量": volume,
        }, index=dates)
        all_data[sym] = df
    return all_data


def get_multi_stock_data(symbols, start_date="20230101", end_date="20231231"):
    """用 akshare 获取多只股票的 OHLCV 数据，失败时使用模拟数据"""
    all_data = {}
    for sym in symbols:
        try:
            import akshare as ak
            df = ak.stock_zh_a_hist(symbol=sym, period="daily",
                                     start_date=start_date, end_date=end_date)
            df["日期"] = pd.to_datetime(df["日期"])
            df = df.set_index("日期").sort_index()
            all_data[sym] = df
        except Exception:
            pass
    if not all_data:
        print("  [模拟数据] akshare 不可用，使用模拟数据")
        all_data = generate_mock_stock_data(symbols)
    return all_data


def prepare_factor_data(symbols):
    """
    准备因子数据
    返回: factor (Series), prices (DataFrame)
    """
    all_data = get_multi_stock_data(symbols)

    # 收集收盘价
    prices = pd.DataFrame()
    for sym, df in all_data.items():
        prices[sym] = df["收盘"]

    # 计算因子：20日动量
    factor = prices.pct_change(20)

    # 转换为 jqfactor_analyzer 需要的格式
    # factor: DataFrame, index=日期, columns=股票代码
    factor = factor.dropna(how="all")

    return factor, prices


def demo_jqfactor_analyzer():
    """使用 jqfactor_analyzer 做因子分析"""
    print("=== 获取数据 ===")
    symbols = ["000001", "000002", "000063", "000333",
               "000338", "000425", "000538", "000568",
               "000625", "000651", "000708", "000725"]

    factor, prices = prepare_factor_data(symbols)
    print(f"获取到 {prices.shape[1]} 只股票，{len(prices)} 个交易日")
    print(f"因子数据形状: {factor.shape}")

    print("\n=== jqfactor_analyzer 因子分析 ===")
    try:
        import jqfactor_analyzer as ja

        # 创建分析器
        # factor: 因子值 DataFrame (index=日期, columns=股票代码)
        # prices: 价格 DataFrame (index=日期, columns=股票代码)
        analyzer = ja.analyze_factor(
            factor_df=factor,  # 因子值
            prices=prices,     # 价格数据
            quantiles=5,        # 分5组
            periods=(1, 5, 10), # 分析1日、5日、10日前向收益
        )

        # 生成完整分析报告
        print("\n=== 生成因子分析报告 ===")
        analyzer.create_full_tear_sheet()

        # 也可以单独调用各分析模块
        # analyzer.create_returns_tear_sheet()    # 收益分析
        # analyzer.create_information_tear_sheet() # IC 分析
        # analyzer.create_turnover_tear_sheet()    # 换手率分析

        print("\n因子分析完成！")

    except ImportError:
        print("请先安装: pip install jqfactor_analyzer")
    except Exception as e:
        print(f"分析出错: {e}")
        print("提示：jqfactor_analyzer 对数据格式有特定要求，请参考官方文档")


def demo_manual_factor_analysis():
    """手动因子分析（不依赖 jqfactor_analyzer，演示原理）"""
    print("=== 手动因子分析（演示原理）===")
    symbols = ["000001", "000002", "000063", "000333",
               "000338", "000425", "000538", "000568",
               "000625", "000651", "000708", "000725"]

    all_data = get_multi_stock_data(symbols)
    prices = pd.DataFrame()
    for sym, df in all_data.items():
        prices[sym] = df["收盘"]

    # 计算因子：20日动量
    factor = prices.pct_change(20)

    # 计算前向收益
    forward_5d = prices.pct_change(5).shift(-5)

    # 分5组分析
    print("\n=== 分组收益分析 ===")
    group_returns = {i: [] for i in range(1, 6)}

    for date in factor.index:
        if date not in forward_5d.index:
            continue
        f = factor.loc[date].dropna()
        r = forward_5d.loc[date]
        common = f.index.intersection(r.dropna().index)

        if len(common) >= 10:
            # 按因子值分5组
            ranked = f[common].rank()
            n = len(common)
            for i in range(5):
                start_idx = int(n * i / 5)
                end_idx = int(n * (i + 1) / 5)
                group_syms = ranked[(ranked > start_idx) & (ranked <= end_idx + 1)].index
                if len(group_syms) > 0:
                    group_ret = r[group_syms].mean()
                    group_returns[i + 1].append(group_ret)

    print("分组平均收益:")
    for group, rets in group_returns.items():
        if rets:
            avg_ret = np.nanmean(rets)
            print(f"  第{group}组: {avg_ret:.4f}")

    # 多空收益
    if group_returns[1] and group_returns[5]:
        long_short = np.array(group_returns[5]) - np.array(group_returns[1])
        print(f"\n多空组合平均收益: {np.nanmean(long_short):.4f}")

    # IC 分析
    print("\n=== IC 分析 ===")
    ic_list = []
    for date in factor.index:
        if date in forward_5d.index:
            f = factor.loc[date].dropna()
            r = forward_5d.loc[date].dropna()
            common = f.index.intersection(r.index)
            if len(common) >= 5:
                ic = f[common].corr(r[common])
                if not np.isnan(ic):
                    ic_list.append(ic)

    ic_array = np.array(ic_list)
    print(f"  IC 均值: {ic_array.mean():.4f}")
    print(f"  IC 标准差: {ic_array.std():.4f}")
    print(f"  ICIR: {ic_array.mean() / ic_array.std():.4f}")
    print(f"  IC > 0 占比: {(ic_array > 0).mean():.2%}")


if __name__ == "__main__":
    print("=" * 60)
    print("Demo 1: 手动因子分析（演示原理，无需安装额外库）")
    print("=" * 60)
    demo_manual_factor_analysis()

    print("\n" + "=" * 60)
    print("Demo 2: jqfactor_analyzer 完整因子分析")
    print("=" * 60)
    demo_jqfactor_analyzer()
