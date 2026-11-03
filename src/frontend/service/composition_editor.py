"""Structured draft edits; publication remains guarded by the domain compiler."""

import json
from typing import Any

import pandas as pd
import yaml

import gradio as gr
from src.strategy.composition.config import config, fail


def read(text: str) -> dict[str, Any]:
    value = yaml.safe_load(text)
    if not isinstance(value, dict):
        raise fail("invalid")
    return value


def dump(value: dict[str, Any]) -> str:
    return yaml.safe_dump(value, allow_unicode=True, sort_keys=False)


def state(text: str, selected: str):
    plan = read(text)
    nodes = plan.get("nodes") or []
    identifiers = [node["id"] for node in nodes]
    table = pd.DataFrame(
        [{"阶段": n["id"], "组件": n["component"], "输入": ",".join(n.get("inputs") or ["universe"])} for n in nodes],
        columns=["阶段", "组件", "输入"],
    )
    sleeves = pd.DataFrame(
        [{k: row.get(k) for k in ("id", "template", "budget")} for row in plan.get("sleeves") or []],
        columns=["id", "template", "budget"],
    )
    return (
        table,
        gr.update(
            choices=[("新增阶段", "")] + [(i, i) for i in identifiers],
            value=selected if selected in identifiers else "",
        ),
        plan["name"],
        plan.get("portfolio", {}).get("component", "equal"),
        json.dumps(plan.get("portfolio", {}).get("params", {}), ensure_ascii=False),
        json.dumps(plan.get("risk", {}), ensure_ascii=False),
        sleeves,
        gr.update(choices=["universe", *identifiers], value=plan.get("output", "universe")),
    )


def detail(text: str, selected: str):
    node: dict[str, Any] = next((node for node in read(text).get("nodes", []) if node["id"] == selected), {})
    return (
        node.get("id", ""),
        node.get("component", "trend"),
        ",".join(node.get("inputs") or ["universe"]),
        json.dumps(node.get("params", {}), ensure_ascii=False),
    )


def apply_node(text: str, node_id: str, component: str, parents: str, parameters: str):
    plan = read(text)
    params = json.loads(parameters or "{}")
    if not isinstance(params, dict):
        raise fail("invalid")
    node: dict[str, Any] = {
        "id": node_id.strip(),
        "component": component,
        "inputs": [v.strip() for v in parents.split(",") if v.strip()],
        "params": params,
    }
    nodes = plan.setdefault("nodes", [])
    index = next((i for i, row in enumerate(nodes) if row["id"] == node["id"]), None)
    if index is None:
        nodes.append(node)
    else:
        nodes[index] = node
    return dump(plan)


def move(text: str, selected: str, direction: int):
    plan = read(text)
    nodes = plan.get("nodes", [])
    index = next((i for i, row in enumerate(nodes) if row["id"] == selected), None)
    if index is not None and 0 <= index + direction < len(nodes):
        nodes[index], nodes[index + direction] = nodes[index + direction], nodes[index]
    return dump(plan)


def settings(text: str, name: str, method: str, parameters: str, risk: str, output: str):
    plan = read(text)
    if method not in config()["portfolios"]:
        raise fail("invalid")
    plan.update(
        name=name,
        portfolio={"component": method, "params": json.loads(parameters or "{}")},
        risk=json.loads(risk or "{}"),
        output=output,
    )
    return dump(plan)


def sleeves(text: str, table):
    plan = read(text)
    rows = table.to_dict("records") if isinstance(table, pd.DataFrame) else table
    values = []
    for row in rows:
        if pd.isna(row.get("id")) or not str(row.get("id") or "").strip():
            continue
        values.append(
            {"id": str(row["id"]).strip(), "template": str(row["template"]).strip(), "budget": float(row["budget"])}
        )
    plan.update(sleeves=values, nodes=[], output="universe")
    plan["portfolio"] = {"component": "fixed_budget", "params": {}}
    return dump(plan)
