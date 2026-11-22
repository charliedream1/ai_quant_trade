"""Explain indicators from the same dated bars shown in the chart."""

import pandas as pd

from src.engine.economics.config import economics_config


def indicator_rows(bars, benchmark=()):
    cfg = economics_config()["technical_indicators"]
    ordered = sorted((row for row in bars if row.get("close") is not None), key=lambda row: row["date"])
    if not ordered:
        return []
    close = pd.Series([float(row["close"]) for row in ordered])
    rows = []

    def add(name, value, reading):
        rows.append({"指标": name, "数值": round(float(value), 4) if value is not None else None, "解读": reading})

    for window in cfg["moving_averages"]:
        mean = close.tail(window).mean() if len(close) >= window else None
        reading = "样本不足"
        if mean is not None:
            reading = "收盘价高于均线，趋势偏强" if close.iloc[-1] > mean else "收盘价未高于均线，趋势偏弱或持平"
        add(f"MA{window}", mean, reading)

    length = cfg["rsi_window"]
    if len(close) > length:
        changes = close.diff().dropna()
        up, down = changes.clip(lower=0), -changes.clip(upper=0)

        def smooth(series):
            seed = pd.Series([series.iloc[:length].mean()])
            return pd.concat([seed, series.iloc[length:]]).ewm(alpha=1 / length, adjust=False).mean().iloc[-1]

        gain, loss = smooth(up), smooth(down)
        value = 100 * gain / (gain + loss) if gain + loss else 50
        reading = (
            "动量强，留意超买与回撤"
            if value >= cfg["rsi_high"]
            else "动量弱，留意超卖"
            if value <= cfg["rsi_low"]
            else "处于常用阈值之间"
        )
        add(f"RSI{length}", value, reading)
    else:
        add(f"RSI{length}", None, "样本不足")

    fast, slow, signal = cfg["macd_spans"]
    if len(close) >= slow + signal:
        diff = close.ewm(span=fast, adjust=False).mean() - close.ewm(span=slow, adjust=False).mean()
        value = (diff - diff.ewm(span=signal, adjust=False).mean()).iloc[-1]
        add("MACD", value, "快线在信号线上方，动量偏强" if value > 0 else "快线未高于信号线，动量偏弱或持平")
    else:
        add("MACD", None, "样本不足")

    window = cfg["volume_window"]
    volume = pd.to_numeric(pd.Series([row.get("volume") for row in ordered]), errors="coerce")
    if len(volume) > window and volume.tail(window + 1).notna().all():
        average = volume.iloc[-window - 1 : -1].mean()
        if average > 0:
            value = volume.iloc[-1] / average
            add(
                "量能比",
                value,
                "量能放大，结合价格方向判断" if value >= cfg["unusual_volume"] else "量能未达到放大阈值",
            )

    reference = {row["date"]: float(row["close"]) for row in benchmark if row.get("close")}
    for window in cfg["return_windows"]:
        if len(ordered) <= window or not close.iloc[-window - 1]:
            continue
        begin, end = ordered[-window - 1]["date"], ordered[-1]["date"]
        change = 100 * (close.iloc[-1] / close.iloc[-window - 1] - 1)
        add(
            f"{window} 根 K 线涨跌幅（%）",
            change,
            "收盘价较窗口起点上涨" if change > 0 else "收盘价较窗口起点下跌或持平",
        )
        if begin in reference and end in reference:
            value = change - 100 * (reference[end] / reference[begin] - 1)
            add(f"{window} 根 K 线相对上证综合（百分点）", value, "跑赢基准" if value > 0 else "跑输或持平基准")
    return rows
