"""
Alphalens 因子分析 demo
使用 akshare 获取 A 股数据，计算因子后用 alphalens 生成 tear sheet

注意：需要先安装依赖
    pip install alphalens-reloaded akshare pandas numpy
"""

import pandas as pd
import numpy as np


def generate_mock_prices(symbols, days=240):
    """生成模拟收盘价数据（akshare 不可用时的后备）"""
    dates = pd.bdate_range("2023-01-01", periods=days)
    prices = pd.DataFrame(index=dates)
    for sym in symbols:
        np.random.seed(hash(sym) % 2**32)
        base_price = 10 + np.random.rand() * 40
        returns = np.random.randn(days) * 0.02
        prices[sym] = base_price * np.cumprod(1 + returns)
    return prices


def get_multi_stock_data(symbols, start_date="20230101", end_date="20231231"):
    """用 akshare 获取多只股票的收盘价数据，失败时使用模拟数据"""
    prices = pd.DataFrame()
    for sym in symbols:
        try:
            import akshare as ak
            df = ak.stock_zh_a_hist(symbol=sym, period="daily",
                                     start_date=start_date, end_date=end_date)
            df["日期"] = pd.to_datetime(df["日期"])
            df = df.set_index("日期").sort_index()
            prices[sym] = df["收盘"]
        except Exception:
            pass
    if prices.empty:
        print("  [模拟数据] akshare 不可用，使用模拟数据")
        prices = generate_mock_prices(symbols)
    return prices


def compute_factor(prices):
    """
    计算一个简单的动量因子：过去20日收益率
    """
    factor = prices.pct_change(20)
    # 转换为 alphalens 需要的 MultiIndex 格式 (date, asset)
    factor_stack = factor.stack()
    factor_stack.index.names = ["date", "asset"]
    return factor_stack


def demo_alphalens_analysis():
    """使用 alphalens 做因子分析"""
    print("=== 获取数据 ===")
    symbols = ["000001", "000002", "000063", "000333",
               "000338", "000425", "000538", "000568",
               "000625", "000651", "000708", "000725"]
    prices = get_multi_stock_data(symbols)
    print(f"获取到 {len(symbols)} 只股票，{len(prices)} 个交易日")

    print("\n=== 计算因子（20日动量）===")
    factor = compute_factor(prices)
    print(f"因子数据形状: {factor.shape}")
    print(f"因子值示例:\n{factor.head()}")

    # 转换为 alphalens 格式
    factor_df = pd.DataFrame({"factor": factor})

    print("\n=== Alphalens 因子分析 ===")
    try:
        import alphalens

        # 准备数据
        factor_data = alphalens.utils.get_clean_factor_and_forward_returns(
            factor_df,
            prices,
            quantiles=5,
            periods=[1, 5, 10],
            max_loss=0.5,
        )

        print(f"清洗后数据形状: {factor_data.shape}")
        print(f"\n数据预览:\n{factor_data.head()}")

        # 生成完整 tear sheet
        print("\n=== 生成 Tear Sheet ===")
        alphalens.tears.create_full_tear_sheet(factor_data)

        # 也可以分别生成
        # alphalens.tears.create_returns_tear_sheet(factor_data)
        # alphalens.tears.create_information_tear_sheet(factor_data)
        # alphalens.tears.create_turnover_tear_sheet(factor_data)

    except ImportError:
        print("请先安装 alphalens: pip install alphalens-reloaded")
    except Exception as e:
        print(f"分析出错: {e}")
        print("提示：alphalens 对数据量有要求，建议使用更多股票和更长的时间区间")


def demo_manual_ic_analysis():
    """手动计算 IC（不依赖 alphalens，演示原理）"""
    print("=== 手动 IC 分析（演示原理）===")
    symbols = ["000001", "000002", "000063", "000333",
               "000338", "000425", "000538", "000568"]
    prices = get_multi_stock_data(symbols)

    # 计算因子：20日动量
    factor = prices.pct_change(20)

    # 计算前向收益
    forward_returns = prices.pct_change(5).shift(-5)

    # 逐日计算截面 IC
    ic_series = []
    for date in factor.index:
        if date in forward_returns.index:
            f = factor.loc[date].dropna()
            r = forward_returns.loc[date].dropna()
            common = f.index.intersection(r.index)
            if len(common) >= 5:
                ic = f[common].corr(r[common])
                ic_series.append({"date": date, "ic": ic})

    ic_df = pd.DataFrame(ic_series).set_index("date").dropna()

    print(f"IC 统计:")
    print(f"  IC 均值: {ic_df['ic'].mean():.4f}")
    print(f"  IC 标准差: {ic_df['ic'].std():.4f}")
    print(f"  ICIR: {ic_df['ic'].mean() / ic_df['ic'].std():.4f}")
    print(f"  IC > 0 占比: {(ic_df['ic'] > 0).mean():.2%}")
    print(f"\nIC 时间序列（最近10天）:\n{ic_df.tail(10)}")


if __name__ == "__main__":
    print("=" * 60)
    print("Demo 1: 手动 IC 分析（演示原理，无需 alphalens）")
    print("=" * 60)
    demo_manual_ic_analysis()

    print("\n" + "=" * 60)
    print("Demo 2: Alphalens 完整因子分析")
    print("=" * 60)
    demo_alphalens_analysis()
