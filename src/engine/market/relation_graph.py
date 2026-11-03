"""Relation graph service."""

from collections import Counter
from typing import Any

from src.core.logger import get_logger
from src.core.repository import Repository
from src.data import DataSourceManager

LOG = get_logger("relation_graph")

RELATION_TYPE_LABELS = {
    "industry": "行业",
    "concept": "概念",
    "index": "指数成分",
    "supply_chain": "产业链",
    "shareholder": "股东/机构",
    "news_cooccurrence": "新闻共现",
    "correlation": "收益相关",
    "task": "关联任务",
    "analysis": "分析构建",
    "relation": "其他关系",
}

RELATION_TYPE_ALIASES = {
    "industry": "industry",
    "sector": "industry",
    "板块成分": "industry",
    "行业": "industry",
    "concept": "concept",
    "概念": "concept",
    "index": "index",
    "constituent": "index",
    "指数": "index",
    "指数成分": "index",
    "supply-chain": "supply_chain",
    "supply_chain": "supply_chain",
    "产业链": "supply_chain",
    "shareholder": "shareholder",
    "holder": "shareholder",
    "股东": "shareholder",
    "机构": "shareholder",
    "news": "news_cooccurrence",
    "cooccurrence": "news_cooccurrence",
    "news_cooccurrence": "news_cooccurrence",
    "共现": "news_cooccurrence",
    "correlation": "correlation",
    "corr": "correlation",
    "收益相关": "correlation",
    "task": "task",
    "workflow": "task",
    "job": "task",
    "任务": "task",
    "关联任务": "task",
    "analysis": "analysis",
    "constructed": "analysis",
    "分析": "analysis",
    "分析构建": "analysis",
}

NODE_GROUP_LABELS = {
    "center": "中心标的",
    "industry": "关联行业",
    "company": "关联公司",
    "sector": "关联板块",
    "index": "关联指数",
    "supply_chain": "产业链节点",
    "institution": "股东机构",
    "news": "关联新闻",
    "task": "关联任务",
    "factor": "风险/风格因子",
    "analysis": "分析构建",
    "other": "其他关联",
}
NODE_GROUP_ORDER = {
    "center": 0,
    "industry": 1,
    "company": 2,
    "sector": 3,
    "index": 4,
    "supply_chain": 5,
    "institution": 6,
    "news": 7,
    "task": 8,
    "factor": 9,
    "analysis": 10,
    "other": 11,
}
NODE_GROUP_MONITORS = {
    "center": "作为图谱中心，只用于承接周边关系，不单独解释强弱。",
    "industry": "观察行业强弱、成分扩散和同业同步性。",
    "company": "重点核验同行、收益相关和新闻共振是否同步增强。",
    "sector": "跟踪概念、主题和指数板块的轮动变化。",
    "index": "用于判断指数成分、宽基或风格指数联动。",
    "supply_chain": "用于观察上下游传导、供需变化和二级供应链扩散。",
    "institution": "关注股东、机构持仓和交叉持仓变化。",
    "news": "结合新闻标题、关键词和发布时间核验证据链。",
    "task": "回看本地推荐、回测、Qlib 或定时任务形成的研究证据。",
    "factor": "作为风险、流动性或风格解释，不作为确定关系。",
    "analysis": "服务层补充的解释节点，需要结合原始关系核验。",
    "other": "保留未归类关系，后续可补充数据源映射。",
}

MAX_GRAPH_DEPTH = 5
MIN_ANALYZED_NODES = 8
MIN_ANALYZED_EDGES = 8


class RelationGraphService:
    def __init__(self, repo: Repository | None = None, data: DataSourceManager | None = None) -> None:
        self.repo = repo or Repository()
        self.data = data or DataSourceManager()

    def graph(
        self,
        symbol: str,
        relation_types: list[str] | None = None,
        depth: int = 1,
    ) -> dict[str, Any]:
        """按当前深度实时构建关系图谱。

        历史实现先读 stock_relations 表缓存，导致深度调整后仍只返回单跳旧数据；
        图谱属于可重建的派生数据，统一由数据源按 depth 实时生成，再做类型过滤。
        """
        selected_types = self._normalize_relation_types(relation_types)
        bounded_depth = max(1, min(int(depth or 1), MAX_GRAPH_DEPTH))
        graph = self.data.relation_graph(symbol=symbol, depth=bounded_depth)
        graph = self._augment_task_relations(graph, symbol, selected_types)
        graph["construction_notes"] = list(graph.get("construction_notes") or []) + [
            f"最多探索{bounded_depth}跳；仅展示数据源与本地任务实际提供的关系，不补齐层级。",
            f"来源：{getattr(self.data, 'source_name', '未标注')}；模拟来源仅用于演示。",
        ]
        return self._finalize_graph(graph, symbol, selected_types)

    @staticmethod
    def _normalize_relation_type(value: Any) -> str:
        text = str(value or "relation").strip()
        return RELATION_TYPE_ALIASES.get(text, text)

    def _normalize_relation_types(self, values: list[str] | None) -> set[str] | None:
        normalized = {self._normalize_relation_type(value) for value in values or [] if str(value or "").strip()}
        return normalized or None

    def _finalize_graph(
        self,
        graph: dict[str, Any],
        center_symbol: str,
        relation_types: set[str] | None,
    ) -> dict[str, Any]:
        nodes_by_id: dict[str, dict[str, Any]] = {}
        for node in graph.get("nodes") or []:
            node_id = str(node.get("id") or "").strip()
            if not node_id:
                continue
            nodes_by_id[node_id] = dict(node, id=node_id)

        filtered_edges: list[dict[str, Any]] = []
        degree: Counter[str] = Counter()
        relation_counts: Counter[str] = Counter()
        node_relations: dict[str, Counter[str]] = {}
        for edge in graph.get("edges") or []:
            source = str(edge.get("source") or "").strip()
            target = str(edge.get("target") or "").strip()
            if not source or not target:
                continue
            relation_type = self._normalize_relation_type(edge.get("relation_type"))
            if relation_types and relation_type not in relation_types:
                continue
            weight = float(edge.get("weight") or 1.0)
            filtered_edges.append(
                {
                    **edge,
                    "source": source,
                    "target": target,
                    "relation_type": relation_type,
                    "relation_label": RELATION_TYPE_LABELS.get(relation_type, relation_type),
                    "description": edge.get("description") or edge.get("source_note") or "",
                    "weight": round(weight, 4),
                }
            )
            relation_counts[relation_type] += 1
            degree[source] += 1
            degree[target] += 1
            node_relations.setdefault(source, Counter())[relation_type] += 1
            node_relations.setdefault(target, Counter())[relation_type] += 1
            nodes_by_id.setdefault(source, {"id": source, "name": source, "type": "relation", "change_pct": 0})
            nodes_by_id.setdefault(target, {"id": target, "name": target, "type": "relation", "change_pct": 0})

        if center_symbol not in nodes_by_id:
            nodes_by_id[center_symbol] = {
                "id": center_symbol,
                "name": center_symbol,
                "type": "stock",
                "change_pct": 0,
            }

        layers, parents = self._node_layer_details(center_symbol, filtered_edges)
        nodes: list[dict[str, Any]] = []
        for node_id, node in nodes_by_id.items():
            node_degree = int(degree[node_id])
            is_center = node_id == center_symbol
            node_type = "stock" if is_center else str(node.get("type") or "relation")
            node_size = 38 if is_center else min(34, 20 + node_degree * 4)
            node_group = self._node_group(node_id, node, node_type, is_center, node_relations.get(node_id, Counter()))
            layer = int(layers.get(node_id, 0 if is_center else 9))
            nodes.append(
                {
                    **node,
                    "id": node_id,
                    "type": node_type,
                    "group": node_group,
                    "group_label": NODE_GROUP_LABELS.get(node_group, NODE_GROUP_LABELS["other"]),
                    "layer": layer,
                    "parent_id": parents.get(node_id, ""),
                    "path": self._node_path_text(node_id, parents, nodes_by_id),
                    "degree": node_degree,
                    "node_size": node_size,
                    "is_center": is_center,
                }
            )

        nodes.sort(
            key=lambda item: (
                not item.get("is_center"),
                NODE_GROUP_ORDER.get(str(item.get("group") or "other"), NODE_GROUP_ORDER["other"]),
                int(item.get("layer") or 9),
                -int(item.get("degree") or 0),
                str(item.get("id")),
            )
        )
        key_nodes = [
            {
                "id": node["id"],
                "name": node.get("name") or node["id"],
                "type": node.get("type", "relation"),
                "group_label": node.get("group_label", ""),
                "degree": node.get("degree", 0),
                "layer": node.get("layer", 0),
            }
            for node in nodes
            if not node.get("is_center") and int(node.get("degree") or 0) > 0
        ][:6]
        layer_path_rows = self._layer_path_rows(center_symbol, nodes_by_id, filtered_edges, layers, parents)
        chain_paths = [str(item.get("path")) for item in layer_path_rows if int(item.get("layer") or 0) > 1][:5]
        if not chain_paths:
            chain_paths = self._chain_paths(center_symbol, filtered_edges, nodes_by_id)
        group_counts = Counter(str(node.get("group_label") or NODE_GROUP_LABELS["other"]) for node in nodes)
        relation_groups = self._relation_group_summary(nodes, filtered_edges)
        layer_counts = Counter(
            "未连接" if int(node.get("layer") or 9) > MAX_GRAPH_DEPTH else f"L{int(node.get('layer') or 0)}"
            for node in nodes
        )
        summary = {
            "center": center_symbol,
            "node_count": len(nodes),
            "edge_count": len(filtered_edges),
            "max_layer": max(
                (int(node.get("layer") or 0) for node in nodes if int(node.get("layer") or 0) <= MAX_GRAPH_DEPTH),
                default=0,
            ),
            "layer_counts": dict(layer_counts.most_common()),
            "layer_paths": layer_path_rows[:12],
            "relation_counts": {
                RELATION_TYPE_LABELS.get(key, key): value for key, value in relation_counts.most_common()
            },
            "group_counts": dict(group_counts.most_common()),
            "relation_groups": relation_groups,
            "selected_relation_types": sorted(relation_types) if relation_types else [],
            "dominant_relation": RELATION_TYPE_LABELS.get(relation_counts.most_common(1)[0][0], "-")
            if relation_counts
            else "-",
            "key_nodes": key_nodes,
            "chain_paths": chain_paths,
            "construction_notes": graph.get("construction_notes") or [],
        }
        return {
            "nodes": nodes,
            "edges": filtered_edges,
            "summary": summary,
            "data_source": getattr(self.data, "source_name", "未标注"),
            "is_mock": bool(getattr(self.data, "is_mock", False)),
        }

    def _augment_task_relations(
        self,
        graph: dict[str, Any],
        center_symbol: str,
        relation_types: set[str] | None,
    ) -> dict[str, Any]:
        """Attach local research tasks that explicitly reference the center symbol."""
        if relation_types is not None and "task" not in relation_types:
            return graph
        nodes = [dict(item) for item in graph.get("nodes") or []]
        edges = [dict(item) for item in graph.get("edges") or []]
        node_ids = {str(node.get("id")) for node in nodes}
        edge_keys = {
            (str(edge.get("source")), str(edge.get("target")), self._normalize_relation_type(edge.get("relation_type")))
            for edge in edges
        }
        task_rows = self._task_relation_rows(center_symbol)
        if not task_rows:
            return graph

        def add_task_node(row: dict[str, Any]) -> None:
            node_id = str(row["node_id"])
            if node_id not in node_ids:
                node_ids.add(node_id)
                nodes.append(
                    {
                        "id": node_id,
                        "name": row["name"],
                        "type": "task",
                        "group": "task",
                        "change_pct": 0,
                        "status": row.get("status") or "-",
                        "task_type": row.get("task_type") or "-",
                        "created_at": row.get("created_at") or "",
                    }
                )
            key = (node_id, center_symbol, "task")
            if key in edge_keys:
                return
            edge_keys.add(key)
            edges.append(
                {
                    "source": node_id,
                    "target": center_symbol,
                    "relation_type": "task",
                    "description": row["description"],
                    "weight": row["weight"],
                }
            )

        for row in task_rows:
            add_task_node(row)
        LOG.info(
            "relation graph task evidence attached | symbol={} tasks={}",
            center_symbol,
            len(task_rows),
        )
        notes = list(graph.get("construction_notes") or [])
        notes.append(f"已关联本地任务证据 {len(task_rows)} 条。")
        return {"nodes": nodes, "edges": edges, "construction_notes": notes}

    def _task_relation_rows(self, symbol: str) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        rows.extend(self._recommend_task_rows(symbol))
        rows.extend(self._backtest_task_rows(symbol))
        rows.extend(self._qlib_task_rows(symbol))
        rows.extend(self._scheduled_task_rows(symbol))
        deduped: list[dict[str, Any]] = []
        seen: set[str] = set()
        for row in rows:
            key = str(row.get("node_id") or "")
            if not key or key in seen:
                continue
            seen.add(key)
            deduped.append(row)
        return deduped[:8]

    def _recommend_task_rows(self, symbol: str) -> list[dict[str, Any]]:
        try:
            rows = self.repo.db.query(
                """
                SELECT t.id, t.path, t.status, t.created_at, r.rank, r.score, r.reason
                  FROM recommend_tasks t
                  JOIN recommend_results r ON r.task_id = t.id
                 WHERE r.symbol = ?
                 ORDER BY t.created_at DESC, r.rank ASC
                 LIMIT 3
                """,
                (symbol,),
            )
        except Exception as exc:
            LOG.debug("relation graph recommend task lookup skipped | symbol={} error={}", symbol, exc)
            return []
        return [
            {
                "node_id": f"TASK:RECOMMEND:{row.get('id')}",
                "name": f"推荐任务 #{row.get('id')}",
                "task_type": "recommend",
                "status": row.get("status") or "-",
                "created_at": row.get("created_at") or "",
                "description": (
                    f"推荐结果包含 {symbol}，排名 {row.get('rank', '-')}，"
                    f"评分 {float(row.get('score') or 0):.1f}，路径 {row.get('path') or '-'}"
                ),
                "weight": 0.84,
            }
            for row in rows
        ]

    def _backtest_task_rows(self, symbol: str) -> list[dict[str, Any]]:
        try:
            rows = self.repo.db.query(
                """
                SELECT id, strategy_id, engine, symbols, status, created_at
                  FROM backtest_tasks
                 ORDER BY created_at DESC
                 LIMIT 20
                """
            )
        except Exception as exc:
            LOG.debug("relation graph backtest task lookup skipped | symbol={} error={}", symbol, exc)
            return []
        matched = [row for row in rows if self._text_contains_symbol(row.get("symbols"), symbol)][:3]
        return [
            {
                "node_id": f"TASK:BACKTEST:{row.get('id')}",
                "name": f"回测任务 #{row.get('id')}",
                "task_type": "backtest",
                "status": row.get("status") or "-",
                "created_at": row.get("created_at") or "",
                "description": (
                    f"回测股票池包含 {symbol}，策略 {row.get('strategy_id') or '-'}，"
                    f"引擎 {row.get('engine') or 'simple'}"
                ),
                "weight": 0.78,
            }
            for row in matched
        ]

    def _qlib_task_rows(self, symbol: str) -> list[dict[str, Any]]:
        try:
            rows = self.repo.db.query(
                """
                SELECT id, run_type, status, params, artifacts, created_at
                  FROM qlib_runs
                 ORDER BY created_at DESC
                 LIMIT 20
                """
            )
        except Exception as exc:
            LOG.debug("relation graph qlib task lookup skipped | symbol={} error={}", symbol, exc)
            return []
        matched = [
            row
            for row in rows
            if self._text_contains_symbol(row.get("params"), symbol)
            or self._text_contains_symbol(row.get("artifacts"), symbol)
        ][:2]
        return [
            {
                "node_id": f"TASK:QLIB:{row.get('id')}",
                "name": f"Qlib运行 #{row.get('id')}",
                "task_type": "qlib",
                "status": row.get("status") or "-",
                "created_at": row.get("created_at") or "",
                "description": f"Qlib {row.get('run_type') or 'workflow'} 运行参数或产物提及 {symbol}",
                "weight": 0.7,
            }
            for row in matched
        ]

    def _scheduled_task_rows(self, symbol: str) -> list[dict[str, Any]]:
        try:
            rows = self.repo.db.query(
                """
                SELECT id, name, job_type, job_params, enabled, created_at
                  FROM scheduled_jobs
                 ORDER BY updated_at DESC
                 LIMIT 30
                """
            )
        except Exception as exc:
            LOG.debug("relation graph scheduled task lookup skipped | symbol={} error={}", symbol, exc)
            return []
        matched = [row for row in rows if self._text_contains_symbol(row.get("job_params"), symbol)][:2]
        return [
            {
                "node_id": f"TASK:SCHEDULED:{row.get('id')}",
                "name": str(row.get("name") or f"定时任务 #{row.get('id')}"),
                "task_type": "scheduled",
                "status": "启用" if int(row.get("enabled") or 0) else "停用",
                "created_at": row.get("created_at") or "",
                "description": f"定时任务 {row.get('job_type') or '-'} 参数提及 {symbol}",
                "weight": 0.62,
            }
            for row in matched
        ]

    @staticmethod
    def _text_contains_symbol(value: Any, symbol: str) -> bool:
        return symbol in str(value or "")

    def _node_group(
        self,
        node_id: str,
        node: dict[str, Any],
        node_type: str,
        is_center: bool,
        relations: Counter[str],
    ) -> str:
        explicit = str(node.get("group") or "").strip()
        if explicit in NODE_GROUP_LABELS:
            return explicit
        if is_center:
            return "center"
        if node_type == "task" or relations.get("task"):
            return "task"
        if node_type == "event" or relations.get("news_cooccurrence"):
            return "news"
        if node_type in {"stock", "company"}:
            return "company"
        if node_type == "index" or relations.get("index"):
            return "index"
        if node_type == "institution" or relations.get("shareholder"):
            return "institution"
        if relations.get("industry") or node_type == "industry":
            return "industry"
        if relations.get("concept") or node_type in {"sector", "concept"}:
            return "sector"
        if relations.get("supply_chain"):
            return "supply_chain"
        if node_type == "factor":
            return "factor"
        if node_type == "analysis" or str(node_id).startswith("ANALYSIS:"):
            return "analysis"
        return "other"

    def _relation_group_summary(
        self,
        nodes: list[dict[str, Any]],
        edges: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        relation_counts_by_group: dict[str, Counter[str]] = {}
        group_nodes: dict[str, list[dict[str, Any]]] = {}
        nodes_by_id = {str(node.get("id")): node for node in nodes}
        for node in nodes:
            group_nodes.setdefault(str(node.get("group") or "other"), []).append(node)
        for edge in edges:
            relation_type = str(edge.get("relation_type") or "relation")
            for node_id in (str(edge.get("source") or ""), str(edge.get("target") or "")):
                matched_node = nodes_by_id.get(node_id)
                if not matched_node:
                    continue
                group = str(matched_node.get("group") or "other")
                relation_counts_by_group.setdefault(group, Counter())[relation_type] += 1

        rows: list[dict[str, Any]] = []
        for group, items in group_nodes.items():
            if group == "center":
                continue
            active_nodes = [item for item in items if int(item.get("degree") or 0) > 0]
            if not active_nodes:
                continue
            active_nodes.sort(key=lambda item: (-int(item.get("degree") or 0), str(item.get("id"))))
            relation_counter = relation_counts_by_group.get(group, Counter())
            evidence = "、".join(
                f"{RELATION_TYPE_LABELS.get(relation, relation)} {count} 条"
                for relation, count in relation_counter.most_common(3)
            )
            rows.append(
                {
                    "group": group,
                    "label": NODE_GROUP_LABELS.get(group, NODE_GROUP_LABELS["other"]),
                    "count": len(active_nodes),
                    "key_nodes": "、".join(str(item.get("name") or item.get("id")) for item in active_nodes[:4]),
                    "evidence": evidence or "暂无边证据",
                    "monitor": NODE_GROUP_MONITORS.get(group, NODE_GROUP_MONITORS["other"]),
                }
            )
        rows.sort(key=lambda item: NODE_GROUP_ORDER.get(str(item.get("group") or "other"), NODE_GROUP_ORDER["other"]))
        return rows

    @staticmethod
    def _node_layer_details(center_symbol: str, edges: list[dict[str, Any]]) -> tuple[dict[str, int], dict[str, str]]:
        adjacency: dict[str, set[str]] = {center_symbol: set()}
        for edge in edges:
            source = str(edge.get("source") or "")
            target = str(edge.get("target") or "")
            if not source or not target:
                continue
            adjacency.setdefault(source, set()).add(target)
            adjacency.setdefault(target, set()).add(source)
        layers = {center_symbol: 0}
        parents: dict[str, str] = {}
        frontier = [center_symbol]
        for layer in range(1, MAX_GRAPH_DEPTH + 1):
            next_frontier = []
            for node_id in frontier:
                for neighbor in sorted(adjacency.get(node_id, set())):
                    if neighbor not in layers:
                        layers[neighbor] = layer
                        parents[neighbor] = node_id
                        next_frontier.append(neighbor)
            frontier = next_frontier
            if not frontier:
                break
        return layers, parents

    @staticmethod
    def _node_layers(center_symbol: str, edges: list[dict[str, Any]]) -> dict[str, int]:
        layers, _ = RelationGraphService._node_layer_details(center_symbol, edges)
        return layers

    @staticmethod
    def _node_path_text(node_id: str, parents: dict[str, str], nodes_by_id: dict[str, dict[str, Any]]) -> str:
        path_nodes = RelationGraphService._node_path_nodes(node_id, parents)
        names = [str(nodes_by_id.get(item, {}).get("name") or item) for item in path_nodes]
        return " → ".join(names)

    @staticmethod
    def _node_path_nodes(node_id: str, parents: dict[str, str]) -> list[str]:
        path = [node_id]
        cursor = node_id
        seen = {node_id}
        while cursor in parents:
            cursor = parents[cursor]
            if cursor in seen:
                break
            seen.add(cursor)
            path.append(cursor)
        path.reverse()
        return path

    @staticmethod
    def _layer_path_rows(
        center_symbol: str,
        nodes_by_id: dict[str, dict[str, Any]],
        edges: list[dict[str, Any]],
        layers: dict[str, int],
        parents: dict[str, str],
    ) -> list[dict[str, Any]]:
        edge_lookup: dict[tuple[str, str], dict[str, Any]] = {}
        for edge in edges:
            source = str(edge.get("source") or "")
            target = str(edge.get("target") or "")
            if not source or not target:
                continue
            edge_lookup[(source, target)] = edge
            edge_lookup[(target, source)] = edge

        rows: list[dict[str, Any]] = []
        for node_id, layer in sorted(layers.items(), key=lambda item: (item[1], item[0])):
            if node_id == center_symbol or layer <= 0:
                continue
            path_nodes = RelationGraphService._node_path_nodes(node_id, parents)
            relation_labels: list[str] = []
            evidence: list[str] = []
            for source, target in zip(path_nodes, path_nodes[1:], strict=False):
                edge = edge_lookup.get((source, target), {})
                relation_type = str(edge.get("relation_type") or "relation")
                relation_labels.append(RELATION_TYPE_LABELS.get(relation_type, relation_type))
                description = str(edge.get("description") or "").strip()
                if description:
                    evidence.append(description)
            names = [str(nodes_by_id.get(item, {}).get("name") or item) for item in path_nodes]
            rows.append(
                {
                    "layer": int(layer),
                    "node_id": node_id,
                    "node_name": str(nodes_by_id.get(node_id, {}).get("name") or node_id),
                    "path": " → ".join(names),
                    "relations": " / ".join(relation_labels) or "-",
                    "evidence": "；".join(evidence[:3]) or "-",
                }
            )
        rows.sort(key=lambda item: (-int(item.get("layer") or 0), str(item.get("node_id") or "")))
        return rows

    @staticmethod
    def _chain_paths(
        center_symbol: str, edges: list[dict[str, Any]], nodes_by_id: dict[str, dict[str, Any]]
    ) -> list[str]:
        candidates = sorted(
            edges,
            key=lambda edge: (
                str(edge.get("target")) != center_symbol and str(edge.get("source")) != center_symbol,
                -float(edge.get("weight") or 0),
            ),
        )
        paths: list[str] = []
        for edge in candidates[:5]:
            source = str(edge.get("source") or "")
            target = str(edge.get("target") or "")
            relation = RELATION_TYPE_LABELS.get(str(edge.get("relation_type")), str(edge.get("relation_type") or "-"))
            source_name = str(nodes_by_id.get(source, {}).get("name") or source)
            target_name = str(nodes_by_id.get(target, {}).get("name") or target)
            paths.append(f"{source_name} --{relation}--> {target_name}")
        return paths
