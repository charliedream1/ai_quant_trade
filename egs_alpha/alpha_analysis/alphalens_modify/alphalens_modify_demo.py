"""
alphalens-modify 因子分析 demo
使用 akshare 获取 A 股数据，用 alphalens-modify 生成因子分析报告

注意：需要先安装依赖
    pip install alphalens-modify akshare pandas numpy
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


def demo_alphalens_modify():
    """使用 alphalens-modify 做因子分析"""
    print("=== 获取数据 ===")
    symbols = ["000001", "000002", "000063", "000333",
               "000338", "000425", "000538", "000568",
               "000625", "000651", "000708", "000725"]
    prices = get_multi_stock_data(symbols)
    print(f"获取到 {prices.shape[1]} 只股票，{len(prices)} 个交易日")

    # 计算因子：20日动量
    print("\n=== 计算因子（20日动量）===")
    factor = prices.pct_change(20)
    factor_stack = factor.stack()
    factor_stack.index.names = ["date", "asset"]
    factor_df = pd.DataFrame({"factor": factor_stack})

    print("\n=== alphalens-modify 因子分析 ===")
    try:
        import alphalens_modify as al

        # 数据清洗与对齐
        factor_data = al.utils.get_clean_factor_and_forward_returns(
            factor_df,
            prices,
            quantiles=5,
            periods=[1, 5, 10],
            max_loss=0.5,
        )

        print(f"清洗后数据形状: {factor_data.shape}")

        # 生成摘要报告
        print("\n=== 生成摘要 Tear Sheet ===")
        al.tears.create_summary_tear_sheet(factor_data)

        # 生成收益分析
        print("\n=== 生成收益分析 ===")
        al.tears.create_returns_tear_sheet(factor_data)

        # 生成 IC 分析
        print("\n=== 生成 IC 分析 ===")
        al.tears.create_information_tear_sheet(factor_data)

        # 生成换手率分析
        print("\n=== 生成换手率分析 ===")
        al.tears.create_turnover_tear_sheet(factor_data)

        print("\n分析完成！图表已生成。")

    except ImportError:
        print("请先安装: pip install alphalens-modify")
    except Exception as e:
        print(f"分析出错: {e}")


def demo_market_cap_factor():
    """使用市值因子做分析（alphalens-modify 的典型用例）"""
    print("=== 市值因子分析 ===")
    symbols = ["000001", "000002", "000063", "000333",
               "000338", "000425", "000538", "000568"]

    prices = get_multi_stock_data(symbols)

    # 获取总市值作为因子
    factor_data_dict = {}
    for sym in symbols:
        try:
            df = ak.stock_individual_info_em(symbol=sym)
            # 简化：用价格作为市值代理（实际应获取真实市值）
            factor_data_dict[sym] = prices[sym].iloc[0]  # 用首日价格作为因子
        except:
            pass

    # 构造因子序列（简化版：用每日收盘价作为市值代理）
    factor = prices.copy()
    factor_stack = factor.stack()
    factor_stack.index.names = ["date", "asset"]
    factor_df = pd.DataFrame({"factor": factor_stack})

    print(f"因子数据形状: {factor_df.shape}")

    try:
        import alphalens_modify as al
        clean_data = al.utils.get_clean_factor_and_forward_returns(
            factor_df, prices, quantiles=5, periods=[1, 5, 10], max_loss=0.5
        )
        al.tears.create_summary_tear_sheet(clean_data)
        print("市值因子分析完成！")
    except ImportError:
        print("请先安装: pip install alphalens-modify")
    except Exception as e:
        print(f"分析出错: {e}")


if __name__ == "__main__":
    print("=" * 60)
    print("Demo 1: alphalens-modify 动量因子分析")
    print("=" * 60)
    demo_alphalens_modify()

    print("\n" + "=" * 60)
    print("Demo 2: 市值因子分析")
    print("=" * 60)
    demo_market_cap_factor()
