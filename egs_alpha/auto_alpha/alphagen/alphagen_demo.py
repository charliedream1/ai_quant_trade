"""
AlphaGen 强化学习因子挖掘 demo
演示如何使用 RL 自动生成 Alpha 因子表达式

注意：
1. AlphaGen 需要配合 Qlib 数据使用
2. 完整 RL 训练需要 GPU，本 demo 演示基本流程和表达式生成
3. 安装：pip install torch qlib akshare
"""

import akshare as ak
import pandas as pd
import numpy as np


# ============================================================
# Alpha 因子表达式的基本算子定义
# ============================================================
class AlphaOperators:
    """Alpha 因子常用算子（与 AlphaGen/WorldQuant 风格一致）"""

    @staticmethod
    def ts_rank(data, window=10):
        """时序排名"""
        return data.rolling(window).apply(lambda x: x.rank().iloc[-1] / len(x))

    @staticmethod
    def ts_sum(data, window=10):
        """时序求和"""
        return data.rolling(window).sum()

    @staticmethod
    def ts_mean(data, window=10):
        """时序均值"""
        return data.rolling(window).mean()

    @staticmethod
    def ts_std(data, window=10):
        """时序标准差"""
        return data.rolling(window).std()

    @staticmethod
    def ts_max(data, window=10):
        """时序最大值"""
        return data.rolling(window).max()

    @staticmethod
    def ts_min(data, window=10):
        """时序最小值"""
        return data.rolling(window).min()

    @staticmethod
    def delay(data, period=1):
        """滞后"""
        return data.shift(period)

    @staticmethod
    def delta(data, period=1):
        """差分"""
        return data.diff(period)

    @staticmethod
    def correlation(x, y, window=10):
        """滚动相关系数"""
        return x.rolling(window).corr(y)

    @staticmethod
    def covariance(x, y, window=10):
        """滚动协方差"""
        return x.rolling(window).cov(y)

    @staticmethod
    def rank(data):
        """截面排名"""
        return data.rank(pct=True)


# ============================================================
# 模拟 AlphaGen 的因子表达式生成
# ============================================================
def generate_alpha_expressions():
    """
    模拟 AlphaGen RL 智能体生成的因子表达式
    真实场景中这些表达式由 RL 智能体搜索得到
    """
    expressions = [
        # 表达式1: 量价背离因子
        {
            "name": "alpha_vp_divergence",
            "expr": "-1 * correlation(open, volume, 10)",
            "desc": "开盘价与成交量的10日负相关，刻画量价背离"
        },
        # 表达式2: 动量反转因子
        {
            "name": "alpha_momentum_reversal",
            "expr": "rank(ts_mean(close, 5) / ts_mean(close, 20))",
            "desc": "短期均线与长期均线比值排名，捕捉动量反转"
        },
        # 表达式3: 波动率因子
        {
            "name": "alpha_volatility",
            "expr": "ts_std(delta(close, 1), 10)",
            "desc": "日收益率10日标准差，度量波动率"
        },
        # 表达式4: 量能因子
        {
            "name": "alpha_volume_surge",
            "expr": "rank(volume / ts_mean(volume, 20))",
            "desc": "当日成交量与20日均量比值排名，识别放量"
        },
        # 表达式5: 振幅因子
        {
            "name": "alpha_amplitude",
            "expr": "rank((high - low) / close)",
            "desc": "当日振幅排名"
        },
    ]
    return expressions


def evaluate_alpha(factor, forward_return, periods=[1, 5, 10]):
    """
    评估因子有效性（IC 分析）
    模拟 AlphaGen 中的因子评估环节
    """
    results = {}
    for p in periods:
        fwd_ret = forward_return.shift(-p)
        aligned = pd.DataFrame({"factor": factor, "return": fwd_ret}).dropna()
        if len(aligned) > 10:
            ic = aligned["factor"].corr(aligned["return"])
            results[f"IC_{p}d"] = ic
    return results


def demo_alphagen_flow():
    """演示 AlphaGen 因子挖掘流程"""
    print("=== 获取数据 ===")
    # 获取多只股票数据
    symbols = ["000001", "000002", "000063", "000333"]
    all_factors = {}

    for sym in symbols:
        df = ak.stock_zh_a_hist(symbol=sym, period="daily",
                                 start_date="20230101", end_date="20231231")
        df = df.rename(columns={
            "日期": "date", "开盘": "open", "收盘": "close",
            "最高": "high", "最低": "low", "成交量": "volume",
        })
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date").sort_index()

        ops = AlphaOperators()
        close = df["close"]
        open_ = df["open"]
        volume = df["volume"]
        high = df["high"]
        low = df["low"]

        # 前向收益（标签）
        forward_return = close.pct_change(5)

        # 生成因子
        expressions = generate_alpha_expressions()
        print(f"\n=== 股票 {sym} 的因子评估 ===")

        for expr_info in expressions:
            name = expr_info["name"]
            # 计算因子值
            if name == "alpha_vp_divergence":
                factor = -1 * ops.correlation(open_, volume, 10)
            elif name == "alpha_momentum_reversal":
                factor = ops.rank(ops.ts_mean(close, 5) / ops.ts_mean(close, 20))
            elif name == "alpha_volatility":
                factor = ops.ts_std(ops.delta(close, 1), 10)
            elif name == "alpha_volume_surge":
                factor = ops.rank(volume / ops.ts_mean(volume, 20))
            elif name == "alpha_amplitude":
                factor = ops.rank((high - low) / close)

            # 评估因子
            ic_results = evaluate_alpha(factor, forward_return)
            print(f"  {name}: {expr_info['expr']}")
            print(f"    IC: {ic_results}")

    print("\n=== RL 生成的因子表达式 ===")
    for expr in generate_alpha_expressions():
        print(f"  {expr['name']}: {expr['expr']}")
        print(f"    说明: {expr['desc']}")


if __name__ == "__main__":
    demo_alphagen_flow()
