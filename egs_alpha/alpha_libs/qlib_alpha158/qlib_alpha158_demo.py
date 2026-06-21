"""
Qlib Alpha158 因子计算 demo
使用 akshare 获取 A 股数据，用 qlib 的 Alpha158 handler 计算因子

注意：
1. 需要先安装依赖：pip install pyqlib akshare pandas
2. 首次运行需要下载 qlib 数据：python -c "from qlib.data.data import GetData; GetData().qlib_data(target_dir='~/.qlib/qlib_data/cn_data', region='cn')"
"""

import akshare as ak
import pandas as pd
import qlib
from qlib.data import D
from qlib.contrib.data.handler import Alpha158


def demo_alpha158_via_qlib_data():
    """方式一：使用 qlib 内置数据源计算 Alpha158 因子"""
    # 初始化 qlib（需提前下载好数据）
    qlib.init(provider_uri="~/.qlib/qlib_data/cn_data", region="cn")

    # 初始化 Alpha158 数据处理器
    handler = Alpha158(
        instruments="csi300",
        start_time="2020-01-01",
        end_time="2023-12-31",
        freq="day",
    )

    # 获取特征和标签
    data = handler.fetch()
    features = data.get("feature")
    labels = data.get("label")

    print("=== Alpha158 因子 ===")
    print(f"因子数量: {features.shape[1]}")
    print(f"样本数量: {features.shape[0]}")
    print(f"因子名称（前10个）:\n{list(features.columns)[:10]}")
    print(f"\n前5行数据:\n{features.head()}")
    print(f"\n标签:\n{labels.head()}")


def demo_alpha158_manual():
    """方式二：使用 akshare 获取数据，手动计算部分 Alpha158 风格因子"""
    # 用 akshare 获取平安银行日行情
    df = ak.stock_zh_a_hist(symbol="000001", period="daily", start_date="20230101", end_date="20231231")
    df = df.rename(columns={
        "日期": "date", "开盘": "open", "收盘": "close",
        "最高": "high", "最低": "low", "成交量": "volume",
    })
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date").sort_index()

    close = df["close"]
    volume = df["volume"]
    high = df["high"]
    low = df["low"]

    # 手动计算几个 Alpha158 中的典型因子
    factors = pd.DataFrame(index=df.index)

    # 1. KBAR: (high-low)/open 风格因子
    factors["KBAR"] = (high - low) / df["open"]

    # 2. ROC10: 10日价格变化率
    factors["ROC10"] = close.pct_change(10)

    # 3. RSI6: 6日相对强弱指数
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(6).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(6).mean()
    rs = gain / loss
    factors["RSI6"] = 100 - (100 / (1 + rs))

    # 4. BIAS10: 10日乖离率
    factors["BIAS10"] = (close - close.rolling(10).mean()) / close.rolling(10).mean()

    # 5. VSTD20: 20日成交量标准差
    factors["VSTD20"] = volume.rolling(20).std()

    # 6. MA5-MA20: 短长期均线差
    factors["MA5_MA20"] = close.rolling(5).mean() - close.rolling(20).mean()

    print("=== 手动计算 Alpha158 风格因子（平安银行 000001）===")
    print(f"数据区间: {df.index[0].date()} ~ {df.index[-1].date()}")
    print(f"计算因子数: {factors.shape[1]}")
    print(f"\n因子值（最近5天）:\n{factors.tail()}")

    return factors


if __name__ == "__main__":
    print("=" * 60)
    print("Demo 1: 手动计算 Alpha158 风格因子（使用 akshare 数据）")
    print("=" * 60)
    demo_alpha158_manual()

    print("\n" + "=" * 60)
    print("Demo 2: 使用 qlib 内置 Alpha158（需提前下载 qlib 数据）")
    print("=" * 60)
    try:
        demo_alpha158_via_qlib_data()
    except Exception as e:
        print(f"跳过（需先下载 qlib 数据）: {e}")
        print("下载命令: python -c \"from qlib.data.data import GetData; GetData().qlib_data(target_dir='~/.qlib/qlib_data/cn_data', region='cn')\"")
