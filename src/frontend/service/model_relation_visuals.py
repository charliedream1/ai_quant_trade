"""Research graph labels preserve business semantics without rule-weight claims."""

from html import escape
from math import cos, radians, sin
from textwrap import wrap
from typing import Any

from src.engine.market.model_graph.config import config

from .relation_layout import positions
from .visuals import relation_figure


def model_relation_figure(graph, center):
    nodes, edges = graph["nodes"], graph["edges"]
    style = config()["ui"]
    coordinates = positions(nodes, edges, center)
    if len(nodes) == 3:
        # Opposite ring neighbors place their mutual edge directly through the
        # target. A fan keeps a direct peer link visually separate from the target.
        neighbors = sorted(identifier for identifier in coordinates if identifier != center)
        for index, identifier in enumerate(neighbors):
            angle = radians(style["small_graph_arc_degrees"]) * (index - 0.5)
            coordinates[identifier] = (cos(angle), sin(angle))
    figure = relation_figure(nodes, edges, center, coordinates=coordinates)
    pairs: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for edge in edges:
        if config()["relations"][edge["relation_type"]]["direction"] != "undirected":
            sx, sy = coordinates[edge["source"]]
            tx, ty = coordinates[edge["target"]]
            figure.add_annotation(
                x=sx + (tx - sx) * style["arrow_end_fraction"],
                y=sy + (ty - sy) * style["arrow_end_fraction"],
                ax=sx + (tx - sx) * style["arrow_start_fraction"],
                ay=sy + (ty - sy) * style["arrow_start_fraction"],
                xref="x",
                yref="y",
                axref="x",
                ayref="y",
                showarrow=True,
                arrowhead=style["arrow_head"],
                arrowsize=style["arrow_size"],
                text="",
            )
        pair = tuple(sorted((edge["source"], edge["target"])))
        pairs.setdefault(pair, []).append(edge)
    for (source, target), relations in list(pairs.items())[: style["edge_label_limit"]]:
        sx, sy = coordinates[source]
        tx, ty = coordinates[target]
        text = "<br>".join(
            "<br>".join(escape(line) for line in wrap(edge["relation_label"], style["edge_label_chars"]))
            for edge in relations
        )
        figure.add_annotation(
            x=(sx + tx) / 2,
            y=(sy + ty) / 2,
            text=text,
            showarrow=False,
            bgcolor=style["label_background"],
            font={"size": style["edge_font_size"]},
        )
    for trace in figure.data:
        if trace.mode == "lines":
            relation = str(trace.legendgroup).removesuffix("_inference")
            trace.line.color = style["relation_colors"].get(relation, style["relation_colors"]["default"])
            matching = [
                edge
                for edge in edges
                if edge["relation_type"] == relation
                and (edge["classification"] != "stated") == str(trace.legendgroup).endswith("_inference")
            ]
            trace.hovertext = [
                text
                for edge in matching
                for text in (
                    escape(edge["relation_label"] + ": " + edge["description"]),
                    escape(edge["relation_label"] + ": " + edge["description"]),
                    None,
                )
            ]
        elif trace.mode == "markers+text":
            trace.name = "Selected listing" if trace.customdata[0][1] == "stock" else trace.name
            trace.text = ["<br>".join(wrap(label, style["node_label_chars"])) for label in trace.text]
            trace.hovertemplate = (
                "<b>%{customdata[6]}</b><br>Entity %{customdata[0]}"
                "<br>Type %{customdata[1]}<br>Hop %{customdata[3]}<extra></extra>"
            )
    figure.update_layout(
        title=f"Company relationship research<br><sup>{len(nodes)} entities / {len(edges)} claims</sup>"
    )
    return figure
