"""Reject fabricated sources, invalid identities and dangling graph structures."""

import re
from collections import deque
from datetime import date
from hashlib import sha256

from src.core.network_policy import validate_url

from .config import config


def normalized(text):
    return re.sub(r"\s+", " ", str(text)).strip()


def validate_graph(value, corpus, request):
    limits = config()["limits"]
    if not isinstance(value.get("nodes"), list) or not isinstance(value.get("edges"), list):
        raise ValueError("Graph response requires nodes and edges arrays")
    if len(value["nodes"]) > limits["nodes"] or len(value["edges"]) > limits["edges"]:
        raise ValueError("Graph response exceeds size budget")
    target = request["symbol"]
    nodes = {target: {"id": target, "name": request.get("company_name") or target, "type": "stock", "is_center": True}}
    for row in value["nodes"]:
        if not isinstance(row, dict) or not isinstance(row.get("id"), str) or not isinstance(row.get("name"), str):
            raise ValueError("Invalid graph entity")
        identifier = row["id"].strip()
        if not identifier or len(identifier) > limits["input_chars"] or len(row["name"]) > limits["input_chars"]:
            raise ValueError("Graph entity exceeds input budget")
        if identifier in nodes and identifier != target:
            raise ValueError("Duplicate graph entity")
        if identifier == target:
            continue
        kind = row.get("type", "company")
        if kind not in config()["node_types"]:
            raise ValueError("Unsupported graph entity type")
        nodes[identifier] = {
            "id": identifier,
            "name": row["name"],
            "type": "company" if kind == "stock" else kind,
            "symbol": "",
            "identity_status": "unresolved_name",
        }
    originals = {row["id"]: row for row in corpus.sources}
    edges, seen = [], set()
    for row in value["edges"]:
        source, target_id, relation = row.get("source"), row.get("target"), row.get("relation_type")
        if (
            source not in nodes
            or target_id not in nodes
            or source == target_id
            or relation not in config()["relations"]
        ):
            raise ValueError("Invalid graph relation endpoints or type")
        classification = row.get("classification")
        if classification not in {"stated", "inference", "candidate"}:
            raise ValueError("Invalid relation classification")
        references = row.get("evidence")
        if not isinstance(references, list) or not references:
            raise ValueError("Every relation requires original evidence")
        validated = []
        for reference in references:
            original = originals.get(reference.get("source_id"))
            span_id = reference.get("quote_id")
            span = original.get("quote_spans", {}).get(span_id) if original and span_id else None
            if span_id and span is None:
                raise ValueError("Relation quote span is unknown")
            quoted = reference.get("quote", span or "")
            quote = normalized(quoted)
            if span is not None and quote != normalized(span):
                raise ValueError("Relation quote span was altered")
            if not original or not quote or quote not in normalized(original["text"]):
                raise ValueError("Relation citation is unknown or altered")
            if original["url"]:
                validate_url(original["url"])
            if request["as_of"] < date.today().isoformat() and not original["date_verified"]:
                classification = "candidate"
            validated.append(
                {
                    "source_id": original["id"],
                    "quote": quoted,
                    "quote_id": span_id,
                    "title": original["title"],
                    "url": original["url"],
                    "published_at": original["published_at"],
                    "first_seen_at": original["first_seen_at"],
                    "coverage": original["coverage"],
                    "sha256": original["sha256"],
                }
            )
        for date_key in ("valid_from", "valid_to"):
            if row.get(date_key):
                date.fromisoformat(row[date_key])
        if row.get("valid_from") and row.get("valid_to") and row["valid_from"] > row["valid_to"]:
            raise ValueError("Relation validity interval is reversed")
        if row.get("valid_from") and row["valid_from"] > request["as_of"]:
            raise ValueError("Relation begins after requested date")
        key = (
            source,
            target_id,
            relation,
            row.get("description"),
            row.get("valid_from"),
            row.get("valid_to"),
            tuple((ref["source_id"], ref["quote"]) for ref in validated),
        )
        if key in seen:
            continue
        seen.add(key)
        description = str(row.get("description") or "").strip()
        if not description or len(description) > limits["input_chars"]:
            raise ValueError("Relation requires a bounded description")
        edge_id = sha256(repr(key).encode()).hexdigest()[:24]
        edges.append(
            {
                "edge_id": edge_id,
                "source": source,
                "target": target_id,
                "relation_type": relation,
                "relation_label": config()["relations"][relation]["label"] + " [" + classification + "]",
                "classification": classification,
                "description": description,
                "evidence_items": validated,
                "valid_from": row.get("valid_from", ""),
                "valid_to": row.get("valid_to", ""),
                "expired": bool(row.get("valid_to") and row["valid_to"] < request["as_of"]),
                "temporal_status": "Source claim; continuing validity and source completeness require human review",
                "contradiction": str(row.get("contradiction") or ""),
                "weight": 1,
                "weight_kind": "display only; not a probability",
                "data_source": "cli-skill-research",
            }
        )
    adjacency: dict[str, set[str]] = {identifier: set() for identifier in nodes}
    for edge in edges:
        adjacency[edge["source"]].add(edge["target"])
        adjacency[edge["target"]].add(edge["source"])
    distances, queue = {target: 0}, deque([target])
    while queue:
        current = queue.popleft()
        for neighbor in adjacency[current]:
            if neighbor not in distances and distances[current] < request["depth"]:
                distances[neighbor] = distances[current] + 1
                queue.append(neighbor)
    edges = [row for row in edges if row["source"] in distances and row["target"] in distances]
    return {
        "nodes": [
            {**row, "layer": distances[identifier]} for identifier, row in nodes.items() if identifier in distances
        ],
        "edges": edges,
        "mode": "model",
        "as_of": request["as_of"],
    }


def apply_review(graph, review):
    decisions = review.get("decisions")
    if not isinstance(decisions, list):
        raise ValueError("Reviewer must return decisions")
    identifiers = {edge["edge_id"] for edge in graph["edges"]}
    if len({row.get("edge_id") for row in decisions}) != len(decisions):
        raise ValueError("Duplicate reviewer decisions")
    if {row.get("edge_id") for row in decisions} != identifiers:
        raise ValueError("Reviewer must decide every proposed edge")
    selected = []
    for row in decisions:
        if row.get("decision") not in {"accept", "infer", "reject"} or not isinstance(row.get("reason"), str):
            raise ValueError("Invalid reviewer decision")
        edge = next(edge for edge in graph["edges"] if edge["edge_id"] == row["edge_id"])
        if row["decision"] == "reject":
            continue
        selected.append(
            {
                **edge,
                "classification": "inference" if row["decision"] == "infer" else edge["classification"],
                "relation_label": config()["relations"][edge["relation_type"]]["label"]
                + " ["
                + ("inference" if row["decision"] == "infer" else edge["classification"])
                + "]",
                "review_reason": row["reason"],
                "review_scope": "same corpus; not independent confirmation",
            }
        )
    return connected_view({**graph, "edges": selected})


def connected_view(graph):
    """Filtering a bridge must also remove components disconnected from the target."""
    center = graph["nodes"][0]["id"]
    adjacency: dict[str, set[str]] = {node["id"]: set() for node in graph["nodes"]}
    for edge in graph["edges"]:
        adjacency[edge["source"]].add(edge["target"])
        adjacency[edge["target"]].add(edge["source"])
    reached, frontier = {center}, [center]
    while frontier:
        current = frontier.pop()
        for neighbor in adjacency[current] - reached:
            reached.add(neighbor)
            frontier.append(neighbor)
    return {
        **graph,
        "edges": [edge for edge in graph["edges"] if edge["source"] in reached and edge["target"] in reached],
        "nodes": [node for node in graph["nodes"] if node["id"] in reached],
    }
