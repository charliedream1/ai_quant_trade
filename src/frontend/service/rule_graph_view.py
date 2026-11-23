"""Render one saved rule-graph artifact without additional provider reads."""

from src.core.diagnostics_config import diagnostics_config

from .foundation import RELATION_EDGE_COLUMNS, RELATION_NODE_COLUMNS, RELATION_PATH_COLUMNS, to_frame
from .visuals import relation_analysis_frame, relation_figure


def rule_graph_view(graph):
    nodes, edges = graph.get("nodes", []), graph.get("edges", [])
    summary = graph.get("summary", {})
    status = (
        f"Run `{graph.get('run_id', '')}` · {graph.get('status', 'completed')} · "
        f"{graph.get('stage', '')} · {graph.get('elapsed_ms', 0)} ms"
    )
    if graph.get("partial_reason"):
        status += "\n\n" + graph["partial_reason"]
    request = graph.get("request", {})
    status += (
        f"\n\n**Rule/data graph** · {graph.get('market', '')} · maximum hops {request.get('depth', '-')} · "
        f"{len(nodes)} entities / {len(edges)} links · source: {graph.get('data_source', 'unavailable')}."
    )
    status += "\n\nProvider and local-task relationships do not establish causality. Weights are not correctness probabilities."
    if graph.get("is_mock"):
        status += "\n\n**Explicit development fixture; simulated data.**"
    policy = diagnostics_config()["rules"]
    nodes_preview = sorted(nodes, key=lambda node: (str(node["id"]) != graph["symbol"], node.get("depth") or 0))[
        : policy["preview_nodes"]
    ]
    identifiers = {row["id"] for row in nodes_preview}
    edges_preview = [row for row in edges if row["source"] in identifiers and row["target"] in identifiers][
        : policy["preview_edges"]
    ]
    if len(nodes_preview) < len(nodes) or len(edges_preview) < len(edges):
        status += f"\n\nInteractive preview: {len(nodes_preview)} entities / {len(edges_preview)} links. Download the full graph."
    figure = relation_figure(nodes_preview, edges_preview, graph["symbol"])
    figure.update_layout(title=f"Rule relationships ({len(nodes_preview)} entities / {len(edges_preview)} links)")
    return (
        status,
        relation_analysis_frame(summary),
        to_frame(summary.get("layer_paths", []), RELATION_PATH_COLUMNS),
        to_frame(nodes, RELATION_NODE_COLUMNS),
        to_frame(edges, RELATION_EDGE_COLUMNS),
        figure,
    )
