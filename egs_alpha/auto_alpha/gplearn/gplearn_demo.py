"""
gplearn 遗传规划因子挖掘 demo
使用 akshare 获取 A 股数据，用 gplearn 自动搜索 Alpha 因子表达式

注意：需要先安装依赖
    pip install gplearn akshare pandas numpy scikit-learn
"""

import pandas as pd
import numpy as np


def generate_mock_data(symbol="000001", days=480):
    """生成模拟 OHLCV 数据（akshare 不可用时的后备）"""
    np.random.seed(hash(symbol) % 2**32)
    dates = pd.bdate_range("2022-01-01", periods=days)
    base_price = 10 + np.random.rand() * 40
    returns = np.random.randn(days) * 0.02
    close = base_price * np.cumprod(1 + returns)
    open_ = close * (1 + np.random.randn(days) * 0.01)
    high = np.maximum(open_, close) * (1 + np.abs(np.random.randn(days)) * 0.01)
    low = np.minimum(open_, close) * (1 - np.abs(np.random.randn(days)) * 0.01)
    volume = np.random.randint(5000000, 50000000, size=days).astype(float)
    df = pd.DataFrame({
        "date": dates, "开盘": open_, "收盘": close,
        "最高": high, "最低": low, "成交量": volume,
    }).set_index("date")
    return df


def get_stock_data(symbol, start_date="20220101", end_date="20231231"):
    """获取股票数据，akshare 失败时使用模拟数据"""
    try:
        import akshare as ak
        df = ak.stock_zh_a_hist(symbol=symbol, period="daily",
                                start_date=start_date, end_date=end_date)
        print(f"  [akshare] 获取 {symbol} 成功，{len(df)} 条数据")
        return df
    except Exception as e:
        print(f"  [模拟数据] akshare 不可用({type(e).__name__})，使用模拟数据: {symbol}")
        return generate_mock_data(symbol)


# ============================================================
# 量化专用算子定义
# ============================================================
def _ts_sum(data):
    """时序求和（窗口=10）"""
    window = 10
    if data.ndim == 1:
        return pd.Series(data).rolling(window).sum().fillna(0).values
    return pd.DataFrame(data).rolling(window).sum().fillna(0).values


def _ts_mean(data):
    """时序均值（窗口=10）"""
    window = 10
    if data.ndim == 1:
        return pd.Series(data).rolling(window).mean().fillna(0).values
    return pd.DataFrame(data).rolling(window).mean().fillna(0).values


def _ts_std(data):
    """时序标准差（窗口=10）"""
    window = 10
    if data.ndim == 1:
        return pd.Series(data).rolling(window).std().fillna(0).values
    return pd.DataFrame(data).rolling(window).std().fillna(0).values


def _ts_max(data):
    """时序最大值（窗口=10）"""
    window = 10
    if data.ndim == 1:
        return pd.Series(data).rolling(window).max().fillna(0).values
    return pd.DataFrame(data).rolling(window).max().fillna(0).values


def _ts_min(data):
    """时序最小值（窗口=10）"""
    window = 10
    if data.ndim == 1:
        return pd.Series(data).rolling(window).min().fillna(0).values
    return pd.DataFrame(data).rolling(window).min().fillna(0).values


def _delta(data):
    """差分"""
    if data.ndim == 1:
        return np.append(0, np.diff(data))
    return np.vstack([np.zeros(data.shape[1]), np.diff(data, axis=0)])


def _delay(data):
    """滞后1期"""
    if data.ndim == 1:
        return np.append(0, data[:-1])
    return np.vstack([np.zeros(data.shape[1]), data[:-1]])


def _rank(data):
    """截面排名"""
    if data.ndim == 1:
        return pd.Series(data).rank(pct=True).fillna(0.5).values
    return pd.DataFrame(data).rank(pct=True).fillna(0.5).values


def _corr(x, y):
    """滚动相关系数（窗口=10）"""
    if x.ndim == 1 and y.ndim == 1:
        return pd.Series(x).rolling(10).corr(pd.Series(y)).fillna(0).values
    return np.zeros_like(x)


# 注册自定义算子（需要 gplearn）
try:
    from gplearn.functions import make_function
    from gplearn.genetic import SymbolicTransformer

    ts_sum = make_function(function=_ts_sum, name="ts_sum", arity=1)
    ts_mean = make_function(function=_ts_mean, name="ts_mean", arity=1)
    ts_std = make_function(function=_ts_std, name="ts_std", arity=1)
    ts_max = make_function(function=_ts_max, name="ts_max", arity=1)
    ts_min = make_function(function=_ts_min, name="ts_min", arity=1)
    delta = make_function(function=_delta, name="delta", arity=1)
    delay = make_function(function=_delay, name="delay", arity=1)
    rank = make_function(function=_rank, name="rank", arity=1)
    corr = make_function(function=_corr, name="corr", arity=2)
    _GPLEARN_AVAILABLE = True
except ImportError:
    _GPLEARN_AVAILABLE = False


def demo_gplearn_factor_mining():
    """使用 gplearn 自动挖掘因子"""
    if not _GPLEARN_AVAILABLE:
        print("跳过：gplearn 未安装，请运行 pip install gplearn")
        return
    print("=== 获取数据 ===")
    # 获取平安银行数据
    df = get_stock_data("000001")
    df = df.rename(columns={
        "日期": "date", "开盘": "open", "收盘": "close",
        "最高": "high", "最低": "low", "成交量": "volume",
    })
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date")
    df = df.sort_index()

    # 构造特征
    features = pd.DataFrame(index=df.index)
    features["open"] = df["open"]
    features["close"] = df["close"]
    features["high"] = df["high"]
    features["low"] = df["low"]
    features["volume"] = df["volume"].astype(float)
    features["vwap"] = (df["high"] + df["low"] + df["close"]) / 3

    # 标签：5日前向收益
    features["label"] = df["close"].pct_change(5).shift(-5)
    features = features.dropna()

    X = features[["open", "close", "high", "low", "volume", "vwap"]].values
    y = features["label"].values

    # 划分训练集和测试集
    split = int(len(X) * 0.8)
    X_train, X_test = X[:split], X[split:]
    y_train, y_test = y[:split], y[split:]

    print(f"训练集: {len(X_train)} 样本, 测试集: {len(X_test)} 样本")

    # 定义函数集（基础+量化专用）
    function_set = (
        "add", "sub", "mul", "div",
        "sqrt", "log", "abs", "neg",
        ts_sum, ts_mean, ts_std, ts_max, ts_min,
        delta, delay, rank,
    )

    # 使用 SymbolicTransformer 自动挖掘多个因子
    print("\n=== 开始遗传规划因子挖掘 ===")
    st = SymbolicTransformer(
        population_size=500,
        generations=10,
        tournament_size=20,
        hall_of_fame=5,  # 保留最好的5个因子
        n_components=5,  # 输出5个因子
        function_set=function_set,
        metric="pearson",  # 用皮尔逊相关系数作为适应度
        parsimony_coefficient=0.001,
        max_samples=0.9,
        verbose=1,
        random_state=42,
        n_jobs=-1,
    )

    st.fit(X_train, y_train)

    # 输出挖掘到的因子表达式
    print("\n=== 挖掘到的因子表达式 ===")
    for i, formula in enumerate(st._best_programs):
        print(f"因子 {i+1}: {formula}")

    # 用测试集评估
    X_transformed = st.transform(X_test)
    print(f"\n生成的因子矩阵形状: {X_transformed.shape}")

    # 计算各因子与标签的 IC
    print("\n=== 因子 IC 评估 ===")
    for i in range(X_transformed.shape[1]):
        ic = np.corrcoef(X_transformed[:, i], y_test)[0, 1]
        print(f"因子 {i+1} IC: {ic:.4f}")


if __name__ == "__main__":
    demo_gplearn_factor_mining()
