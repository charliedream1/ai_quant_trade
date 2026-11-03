"""Finite, causal operator trees; generated Python is an auditable adapter, never executed text."""

from pprint import pformat
from typing import Any

import numpy as np
import pandas as pd

from .config import config, digest, invalid


def validate_expression(expression: dict[str, Any]) -> set[str]:
    cfg, fields, count = config(), set(), 0

    def visit(node: Any, depth: int) -> None:
        nonlocal count
        count += 1
        if not isinstance(node, dict) or depth > cfg["limits"]["max_depth"] or count > cfg["limits"]["max_nodes"]:
            raise invalid("因子树深度、数量或节点类型不合法")
        if set(node) == {"field"}:
            if node["field"] not in cfg["fields"]:
                raise invalid("假设使用未登记字段")
            fields.add(node["field"])
            return
        if set(node) == {"constant"}:
            value = node["constant"]
            if not isinstance(value, (float, int)) or isinstance(value, bool) or not np.isfinite(value):
                raise invalid("因子常数必须有限")
            return
        if set(node) - {"op", "args", "window"} or "op" not in node:
            raise invalid("只支持登记的因子树，不执行Python表达式")
        op, args = node["op"], node.get("args")
        if op not in sum(cfg["operators"].values(), []) or not isinstance(args, list):
            raise invalid("因子算子或输入不合法")
        if len(args) != (2 if op in cfg["operators"]["binary"] else 1):
            raise invalid("因子算子输入数量不合法")
        if op in cfg["operators"]["rolling"] or op == "corr":
            window = node.get("window")
            if type(window) is not int or not 1 <= window <= cfg["limits"]["max_window"]:
                raise invalid("因子窗口必须为受限的正整数，禁止未来位移")
            if op in {"std", "corr"} and window < 2:
                raise invalid("波动率或相关性至少需要两个观察")
        elif "window" in node:
            raise invalid("非窗口算子不能带window")
        for child in args:
            visit(child, depth + 1)

    visit(expression, 0)
    if not fields:
        raise invalid("常数本身不能作为Alpha")
    return fields


def market_panel(history: dict[str, list[dict]]) -> dict[str, pd.DataFrame]:
    return {
        field: pd.DataFrame(
            {
                symbol: pd.Series({row["date"]: row.get(field, np.nan) for row in rows})
                for symbol, rows in sorted(history.items())
            }
        )
        .sort_index()
        .astype(float)
        for field in config()["fields"]
    }


def evaluate_expression(expression: dict[str, Any], panel: dict[str, pd.DataFrame]) -> pd.DataFrame:
    fields = validate_expression(expression)
    if fields - set(panel):
        raise invalid("数据缺少因子所需字段")
    reference = panel[next(iter(sorted(fields)))]

    def evaluate(node):
        if "field" in node:
            return panel[node["field"]].reindex(index=reference.index, columns=reference.columns)
        if "constant" in node:
            return pd.DataFrame(float(node["constant"]), index=reference.index, columns=reference.columns)
        op = node["op"]
        values = [evaluate(arg) for arg in node["args"]]
        left = values[0]
        window = node.get("window")
        if op == "neg":
            return -left
        if op == "abs":
            return left.abs()
        if op == "log":
            return np.log(left.where(left > 0))
        if op == "rank":
            return left.rank(axis=1, pct=True, method="average")
        if op in {"lag", "delta", "returns"}:
            previous = left.shift(window)
            return (
                previous
                if op == "lag"
                else left - previous
                if op == "delta"
                else left / previous.where(previous.abs() > config()["limits"]["epsilon"]) - 1
            )
        if op in {"mean", "std", "min", "max", "ts_rank", "corr"}:
            rolling = left.rolling(window, min_periods=window)
            if op == "std":
                return rolling.std(ddof=0)
            if op == "corr":
                return rolling.corr(values[1])
            if op == "ts_rank":
                return rolling.apply(lambda array: pd.Series(array).rank(pct=True).iloc[-1], raw=True)
            return getattr(rolling, op)()
        right = values[1]
        if op == "add":
            return left + right
        if op == "sub":
            return left - right
        if op == "mul":
            return left * right
        return left / right.where(right.abs() > config()["limits"]["epsilon"])

    return evaluate(expression).replace([np.inf, -np.inf], np.nan)


def python_source(expression: dict[str, Any]) -> str:
    validate_expression(expression)
    return (
        '"""Generated research adapter. Definition SHA256: ' + digest(expression) + '."""\n\n'
        "from src.alpha_mining.factors import evaluate_expression\n\n"
        "DEFINITION = " + pformat(expression, sort_dicts=True) + "\n\n\n"
        'def compute(panel):\n    """Use only causal registered operators."""\n'
        "    return evaluate_expression(DEFINITION, panel)\n"
    )


def causal_checks(expression: dict, panel: dict[str, pd.DataFrame]) -> dict:
    original = evaluate_expression(expression, panel)
    pivot = len(original) // 2
    changed = {key: frame.copy() for key, frame in panel.items()}
    for frame in changed.values():
        frame.iloc[pivot:] = frame.iloc[pivot:] * 2
    altered = evaluate_expression(expression, changed)
    future_safe = np.allclose(original.iloc[:pivot], altered.iloc[:pivot], equal_nan=True)
    reversed_panel = {key: frame.loc[:, list(reversed(frame.columns))] for key, frame in panel.items()}
    reordered = evaluate_expression(expression, reversed_panel).reindex(columns=original.columns)
    permutation_safe = np.allclose(original, reordered, equal_nan=True)
    return {
        "future_perturbation": bool(future_safe),
        "security_permutation": bool(permutation_safe),
        "passed": bool(future_safe and permutation_safe),
        "definition_digest": digest(expression),
    }
