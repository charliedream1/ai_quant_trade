"""Legacy SVG trade charts without forcing a Windows-specific interactive backend."""

from importlib import import_module
from pathlib import Path

import yaml

from src.core.config import PROJECT_ROOT


def _settings():
    return yaml.safe_load((PROJECT_ROOT / "egs/config/platform/legacy_utilities.yaml").read_text(encoding="utf-8"))[
        "chart"
    ]


def _annotations(axis, trades, column):
    cfg = _settings()
    for index, (_, trade) in enumerate(trades.iterrows()):
        axis.annotate(
            str(trade["trade_type"]),
            (trade["time_index"], trade[column]),
            xytext=(0, cfg["annotation_points"] * (1 if index % 2 else -1)),
            textcoords="offset points",
            arrowprops={"arrowstyle": "->"},
        )


def _save(figure, destination):
    if destination:
        path = Path(destination)
        path.parent.mkdir(parents=True, exist_ok=True)
        figure.savefig(path, format="svg", transparent=True)


def plot_trades_on_capital(stock_id, capital_list, df_trade, save_plt_path):
    pyplot = import_module("matplotlib.pyplot")
    figure, axis = pyplot.subplots()
    axis.set_title(str(stock_id) + " Trading Details with Capital Changing")
    axis.plot(range(len(capital_list)), capital_list)
    _annotations(axis, df_trade, "capital")
    axis.grid(True)
    _save(figure, save_plt_path)
    return figure


def plot_trades_on_k_line(stock_id, df_stock, df_trade, save_plt_path):
    pyplot = import_module("matplotlib.pyplot")
    cfg = _settings()
    figure, (price, volume) = pyplot.subplots(2, 1)
    x = list(range(len(df_stock)))
    colors = [
        cfg["up_color"] if close >= opened else cfg["down_color"]
        for opened, close in zip(df_stock["open"], df_stock["close"], strict=True)
    ]
    price.vlines(x, df_stock["low"], df_stock["high"], colors=colors)
    price.bar(x, df_stock["close"] - df_stock["open"], bottom=df_stock["open"], color=colors, width=cfg["candle_width"])
    volume.bar(x, df_stock["vol"], color=colors)
    for column in ("ma_short", "ma_long"):
        if column in df_stock:
            price.plot(x, df_stock[column], label=column)
    if any(column in df_stock for column in ("ma_short", "ma_long")):
        price.legend()
    _annotations(price, df_trade, "close")
    price.set_title(str(stock_id) + " K Line")
    volume.set_title("Volume")
    price.grid(True)
    volume.grid(True)
    figure.tight_layout()
    _save(figure, save_plt_path)
    return figure


def show_plt():
    import_module("matplotlib.pyplot").show(block=True)
