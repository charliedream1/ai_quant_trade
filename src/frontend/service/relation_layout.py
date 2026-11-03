"""Compact graph coordinates and escaped, inspectable relation evidence."""

from __future__ import annotations

import json
from collections import deque
from html import escape
from math import cos, pi, sin
from typing import Any
from urllib.parse import urlparse

from src.data.relation_evidence import graph_config


def plot_metadata(value: Any) -> dict[str, Any]:
    """Gradio callbacks receive PlotData; direct service calls receive go.Figure."""
    if hasattr(value, "layout"):
        return value.layout.meta or {}
    if hasattr(value, "plot"):
        value = value.plot
    if isinstance(value, str):
        value = json.loads(value)
    if isinstance(value, dict) and "plot" in value:
        return plot_metadata(value["plot"])
    return (value or {}).get("layout", {}).get("meta", {})


def positions(nodes: list[dict[str, Any]], edges: list[dict[str, Any]], center: str):
    adjacency: dict[str, set[str]] = {str(node["id"]): set() for node in nodes}
    for edge in edges:
        source, target = str(edge["source"]), str(edge["target"])
        if source in adjacency and target in adjacency:
            adjacency[source].add(target)
            adjacency[target].add(source)
    distances = {center: 0}
    queue = deque([center])
    while queue:
        source = queue.popleft()
        for target in sorted(adjacency.get(source, [])):
            if target not in distances:
                distances[target] = distances[source] + 1
                queue.append(target)
    rings: dict[int, list[str]] = {}
    for node in nodes:
        identifier = str(node["id"])
        if identifier != center:
            rings.setdefault(distances.get(identifier, max(distances.values(), default=0) + 1), []).append(identifier)
    result = {center: (0.0, 0.0)}
    for ordinal, (layer, identifiers) in enumerate(sorted(rings.items())):
        offset = 2 * pi * ordinal / max(len(rings), 1) - pi / 2
        for index, identifier in enumerate(sorted(identifiers)):
            angle = offset + 2 * pi * index / len(identifiers)
            result[identifier] = (layer * cos(angle), layer * sin(angle))
    return result


def bounds(coordinates: dict[str, tuple[float, float]]) -> tuple[list[float], list[float]]:
    cfg = graph_config()["layout"]
    ranges = []
    for index in (0, 1):
        values = [position[index] for position in coordinates.values()] or [0.0]
        low, high = min(values), max(values)
        span = max(high - low, cfg["minimum_span"])
        center = (low + high) / 2
        ranges.append(
            [center - span * (0.5 + cfg["padding_fraction"]), center + span * (0.5 + cfg["padding_fraction"])]
        )
    return ranges[0], ranges[1]


def evidence_html(edge: dict[str, Any]) -> str:
    evidence = edge.get("evidence") or {}
    details = {
        "关系": edge.get("relation_label") or edge.get("relation_type"),
        "说明": edge.get("description"),
        "来源": evidence.get("source") or edge.get("data_source"),
        "标题": evidence.get("title"),
        "发布时间": evidence.get("published_at"),
        "匹配实体": evidence.get("matched_entity"),
        "证据位置": evidence.get("matched_field"),
        "原文片段": evidence.get("excerpt"),
        "方法": evidence.get("method"),
        "证据范围": evidence.get("scope"),
        "样本数": evidence.get("sample_size"),
        "区间起点": evidence.get("start"),
        "区间终点": evidence.get("end"),
        "相关系数": edge.get("coefficient"),
        "权重含义": edge.get("weight_kind") or evidence.get("weight_kind") or "来源关系权重，非概率",
    }
    rows = "".join(
        f"<dt>{escape(key)}</dt><dd>{escape(str(value))}</dd>"
        for key, value in details.items()
        if value is not None and value != ""
    )
    url = str(evidence.get("url") or "")
    link = (
        f'<a href="{escape(url, quote=True)}" target="_blank" rel="noopener noreferrer">查看原文</a>'
        if urlparse(url).scheme in {"http", "https"}
        else ""
    )
    return f'<section class="relation-evidence"><h3>关联依据</h3><dl>{rows}</dl>{link}</section>'
