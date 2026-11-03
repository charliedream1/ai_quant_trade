"""Date-aligned relationship branches with isolated mutable state."""

from __future__ import annotations

import copy
import math
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from typing import TYPE_CHECKING, Any, TypeVar

from src.core.logger import get_logger
from src.data.normalization import _empty_boards, _empty_rows, _number
from src.data.relation_evidence import dated_returns, graph_config, news_evidence, return_correlation
from src.data.symbols import SecuritySymbol

if TYPE_CHECKING:
    from src.data.eastmoney import EastmoneyDataSource

T = TypeVar("T")
DATA_LOG = get_logger("data.source")
SOURCE_NAME = "eastmoney-push2"
_GRAPH_PEER_LIMIT = graph_config()["branches"]["peers"]
_GRAPH_SECOND_HOP_LIMIT = graph_config()["branches"]["second_hop"]
_GRAPH_KLINE_COUNT = graph_config()["branches"]["bars"]
_GRAPH_CONCEPT_DEPTH_ONE = graph_config()["branches"]["concepts"]
_GRAPH_LAYER_TIMEOUT_SECONDS = graph_config()["branches"]["deadline_seconds"]


class _RelationGraphBuilder:
    """按 1-5 层深度组装真实关系图谱，单层失败时降级保留已取到的层次。"""

    def __init__(self, ds: EastmoneyDataSource, parsed: SecuritySymbol, quote: dict[str, Any]) -> None:
        self.ds = ds
        self.parsed = parsed
        self.center = parsed.code
        self.quote = quote
        self.nodes: dict[str, dict[str, Any]] = {}
        self.edges: list[dict[str, Any]] = []
        self.edge_keys: set[tuple[str, str, str]] = set()
        self.peer_codes: list[str] = []
        self.second_hop_codes: list[str] = []

    def build(self, depth: int) -> dict[str, Any]:
        self._add_node(
            self.center,
            str(self.quote.get("name") or self.center),
            "stock",
            _number(self.quote.get("change_pct")),
        )
        boards = self._safe(
            lambda: self.ds._stock_boards(self.parsed.qualified),
            _empty_boards(),
        )
        self._layer_boards(boards)
        if depth >= 2:
            self._run_layers([lambda branch: branch._layer_peers(boards), lambda branch: branch._layer_news(limit=3)])
        if depth >= 3:
            self._run_layers(
                [
                    lambda branch: branch._layer_holders(branch.center, limit=3),
                    lambda branch: branch._layer_peer_boards(boards),
                ]
            )
        if depth >= 4:
            depth_four_tasks = [lambda branch: branch._layer_second_hop(boards)]
            if self.peer_codes:
                depth_four_tasks.append(lambda branch: branch._layer_holders(branch.peer_codes[0], limit=2))
            self._run_layers(depth_four_tasks)
        if depth >= 5:
            self._run_layers([lambda branch: branch._layer_deep_expand()])
        return {"nodes": list(self.nodes.values()), "edges": self._unique_edges()}

    def _run_layers(self, tasks: list[Callable[[Any], None]]) -> None:
        """同层任务并发执行，单层超时或异常时降级，不阻塞其他层。"""
        if not tasks:
            return
        executor = ThreadPoolExecutor(max_workers=min(4, len(tasks)), thread_name_prefix="relation-layer")
        branches = [self._clone() for _ in tasks]
        futures = [executor.submit(self._branch, branch, task) for branch, task in zip(branches, tasks, strict=True)]
        deadline = time.monotonic() + _GRAPH_LAYER_TIMEOUT_SECONDS
        for future in futures:
            try:
                branch = future.result(timeout=max(deadline - time.monotonic(), 0))
                self.nodes.update(branch.nodes)
                for edge in branch.edges:
                    key = (edge["source"], edge["target"], edge["relation_type"])
                    if key not in self.edge_keys:
                        self.edge_keys.add(key)
                        self.edges.append(edge)
                if branch.peer_codes:
                    self.peer_codes = branch.peer_codes
                if branch.second_hop_codes:
                    self.second_hop_codes = branch.second_hop_codes
            except Exception as exc:
                DATA_LOG.warning("图谱分支未完成 | error_type={}", type(exc).__name__)
        executor.shutdown(wait=False, cancel_futures=True)

    def _clone(self):
        branch = copy.copy(self)
        for key in ("nodes", "edges", "edge_keys", "peer_codes", "second_hop_codes"):
            setattr(branch, key, copy.deepcopy(getattr(self, key)))
        return branch

    @staticmethod
    def _branch(branch, task):
        task(branch)
        return branch

    def _unique_edges(self) -> list[dict[str, Any]]:
        """并发层可能产生重复边，返回前按键去重。"""
        unique: list[dict[str, Any]] = []
        seen: set[tuple[str, str, str]] = set()
        for edge in self.edges:
            key = (str(edge.get("source")), str(edge.get("target")), str(edge.get("relation_type")))
            if key in seen:
                continue
            seen.add(key)
            unique.append(edge)
        return unique

    # ── 基础工具 ──────────────────────────────────────────────────────────
    def _add_node(self, node_id: str, name: str, node_type: str, change_pct: float = 0.0) -> None:
        self.nodes.setdefault(
            node_id,
            {
                "id": node_id,
                "name": name,
                "type": node_type,
                "change_pct": round(float(change_pct or 0.0), 2),
                "data_source": SOURCE_NAME,
            },
        )

    def _add_edge(
        self, source: str, target: str, relation_type: str, description: str, weight: float, **metadata: Any
    ) -> None:
        edge_key = (source, target, relation_type)
        if edge_key in self.edge_keys:
            return
        self.edge_keys.add(edge_key)
        self.edges.append(
            {
                "source": source,
                "target": target,
                "relation_type": relation_type,
                "description": description,
                "weight": round(max(float(weight), 0.0), 4),
                "data_source": SOURCE_NAME,
                **metadata,
            }
        )

    @staticmethod
    def _safe(loader: Callable[[], T], default: T) -> T:
        try:
            return loader()
        except Exception:
            return default

    @staticmethod
    def _correlation(left: list[float], right: list[float]) -> float | None:
        size = min(len(left), len(right))
        if size < 20:
            return None
        xs = left[-size:]
        ys = right[-size:]
        mean_x = sum(xs) / size
        mean_y = sum(ys) / size
        cov = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys, strict=True))
        var_x = sum((x - mean_x) ** 2 for x in xs)
        var_y = sum((y - mean_y) ** 2 for y in ys)
        if var_x <= 0 or var_y <= 0:
            return None
        return cov / math.sqrt(var_x * var_y)

    # ── 第一层：行业 / 概念 / 指数成分 ───────────────────────────────────
    def _layer_boards(self, boards: dict[str, Any]) -> None:
        industry = boards.get("industry")
        if industry:
            self._add_node(industry["code"], industry["name"], "sector")
            self._add_edge(industry["code"], self.center, "industry", "东方财富行业分类", 1.0)
        else:
            self._fallback_industry()
        for concept in (boards.get("concepts") or [])[:_GRAPH_CONCEPT_DEPTH_ONE]:
            self._add_node(concept["code"], concept["name"], "sector")
            self._add_edge(concept["code"], self.center, "concept", "个股资料核心题材概念", 0.82)
        for index in boards.get("indices") or []:
            self._add_node(index["code"], index["name"], "index")
            self._add_edge(index["code"], self.center, "index", "指数/宽基成分归属", 0.75)

    def _fallback_industry(self) -> None:
        industry = str(self.quote.get("industry") or "").strip()
        if not industry and self.parsed.market != "BJ":
            industry = self._safe(lambda: self.ds._stock_industry(self.parsed.qualified), "")
        if not industry:
            return
        normalized = industry.replace("Ⅰ", "").replace("Ⅱ", "").replace("Ⅲ", "")
        matched = next(
            (
                item
                for item in self._safe(lambda: self.ds.sectors(limit=100), _empty_rows())
                if normalized in item["name"] or item["name"] in normalized
            ),
            None,
        )
        node_id = str(matched["code"]) if matched else f"IND:{industry}"
        change_pct = float(matched["change_pct"]) if matched else 0.0
        self._add_node(node_id, industry, "sector", change_pct)
        self._add_edge(node_id, self.center, "industry", "行业分类（板块资料兜底）", 1.0)

    # ── 第二层：同板块关联标的、收益相关、新闻共现 ────────────────────────
    def _layer_peers(self, boards: dict[str, Any]) -> None:
        anchor = boards.get("industry") or next(iter(boards.get("concepts") or []), None)
        if not anchor:
            return
        members = [
            item
            for item in self._safe(lambda: self.ds._board_members(anchor["code"], anchor["name"]), _empty_rows())
            if str(item.get("code")) != self.center
        ][:_GRAPH_PEER_LIMIT]
        if not members:
            return
        codes = [str(item["code"]) for item in members]
        quotes = {
            str(item.get("symbol")): item for item in self._safe(lambda: self.ds.stock_quotes(codes), _empty_rows())
        }
        center_closes = self._closes(
            self._safe(
                lambda: self.ds._kline(self.parsed.qualified, "daily", _GRAPH_KLINE_COUNT),
                _empty_rows(),
            )
        )
        relation_type = "industry" if anchor is boards.get("industry") else "concept"
        with ThreadPoolExecutor(max_workers=4, thread_name_prefix="relation-kline") as executor:
            peer_closes = dict(
                zip(
                    codes,
                    executor.map(lambda code: self._closes(self._safe_kline(code)), codes),
                    strict=True,
                )
            )
        for member in members:
            code = str(member["code"])
            quote = quotes.get(code, {})
            name = str(quote.get("name") or member.get("name") or code)
            self._add_node(code, name, "stock", _number(quote.get("change_pct", member.get("change_pct"))))
            self._add_edge(anchor["code"], code, relation_type, f"与中心标的同属「{anchor['name']}」", 0.7)
            coefficient, evidence = return_correlation(center_closes, peer_closes.get(code, {}))
            if coefficient is not None:
                weight = 0.5 + abs(coefficient) * 0.5
                self._add_edge(
                    code,
                    self.center,
                    "correlation",
                    f"{evidence['start']}至{evidence['end']}，{evidence['sample_size']}个对齐收益区间，相关系数 {coefficient:+.2f}",
                    weight,
                    coefficient=coefficient,
                    evidence=evidence,
                    weight_kind="相关系数绝对值映射，仅用于边宽",
                )
        self.peer_codes = codes

    def _safe_kline(self, code: str) -> list[dict[str, Any]]:
        return self._safe(
            lambda: self.ds._kline(f"{self.parsed.market}{code}", "daily", _GRAPH_KLINE_COUNT),
            _empty_rows(),
        )

    @staticmethod
    def _closes(rows: list[dict[str, Any]]) -> dict[str, float]:
        return dated_returns(rows)

    def _layer_news(self, limit: int) -> None:
        news_items = self._safe(lambda: self.ds._stock_news(self.center), _empty_rows())[:limit]
        for item in news_items:
            evidence = news_evidence(item, self.center, str(self.quote.get("name") or ""))
            if not evidence:
                continue
            event_id = f"EVENT:{item.get('id')}"
            self._add_node(event_id, str(item.get("title") or "相关资讯"), "event")
            self.nodes[event_id]["evidence"] = evidence
            title = str(item.get("title") or "相关资讯")
            self._add_edge(event_id, self.center, "news_cooccurrence", title, 0.55, evidence=evidence)
            for code in self.peer_codes[:4]:
                name = str(self.nodes.get(code, {}).get("name") or "")
                peer_evidence = news_evidence(item, code, name)
                if peer_evidence:
                    peer_evidence["relation_class"] = "same_article_cooccurrence"
                    self._add_edge(
                        event_id, code, "news_cooccurrence", f"新闻同时提及「{name}」", 0.42, evidence=peer_evidence
                    )

    def _boards_with_prefix(self, code: str) -> dict[str, Any]:
        return self.ds._stock_boards(f"{self.parsed.market}{code}")

    # ── 第三层：股东机构 + 关联标的的概念/指数 ───────────────────────────
    def _layer_holders(self, symbol: str, limit: int) -> None:
        for holder in self._safe(lambda: self.ds._top_holders(symbol, limit), _empty_rows())[:limit]:
            rank = int(holder.get("rank") or 0)
            name = str(holder.get("name") or "").strip()
            if not name:
                continue
            holder_id = f"HOLDER:{symbol}:{rank or abs(hash(name)) % 100000}"
            self._add_node(holder_id, name[:14], "institution")
            description = f"{holder.get('end_date', '')[:10]} 第{rank}大股东".strip()
            self._add_edge(holder_id, symbol, "shareholder", description, round(0.96 - rank * 0.07, 2))

    def _layer_peer_boards(self, boards: dict[str, Any]) -> None:
        center_concepts = {item["code"] for item in boards.get("concepts") or []}
        center_indices = {item["code"] for item in boards.get("indices") or []}
        for code in self.peer_codes[:2]:
            peer_boards = self._safe(partial(self._boards_with_prefix, code), _empty_boards())
            for concept in (peer_boards.get("concepts") or [])[:2]:
                if concept["code"] in center_concepts:
                    continue
                self._add_node(concept["code"], concept["name"], "sector")
                self._add_edge(concept["code"], code, "concept", "关联标的的题材概念", 0.6)
            for index in (peer_boards.get("indices") or [])[:1]:
                if index["code"] in center_indices:
                    continue
                self._add_node(index["code"], index["name"], "index")
                self._add_edge(index["code"], code, "index", "关联标的同属宽基指数", 0.55)

    # ── 第四层：概念二跳标的 + 关联标的股东 ──────────────────────────────
    def _layer_second_hop(self, boards: dict[str, Any]) -> None:
        concept = next(iter(boards.get("concepts") or []), None)
        if not concept:
            return
        existing = set(self.nodes)
        members = [
            item
            for item in self._safe(lambda: self.ds._board_members(concept["code"], concept["name"]), _empty_rows())
            if str(item.get("code")) not in existing and str(item.get("code")) != self.center
        ][:_GRAPH_SECOND_HOP_LIMIT]
        codes = [str(item["code"]) for item in members]
        if not codes:
            return
        quotes = {
            str(item.get("symbol")): item for item in self._safe(lambda: self.ds.stock_quotes(codes), _empty_rows())
        }
        center_closes = self._closes(
            self._safe(
                lambda: self.ds._kline(self.parsed.qualified, "daily", _GRAPH_KLINE_COUNT),
                _empty_rows(),
            )
        )
        for member in members:
            code = str(member["code"])
            quote = quotes.get(code, {})
            name = str(quote.get("name") or member.get("name") or code)
            self._add_node(code, name, "stock", _number(quote.get("change_pct", member.get("change_pct"))))
            self._add_edge(concept["code"], code, "concept", f"二跳：同属「{concept['name']}」概念", 0.58)
            closes = self._closes(self._safe_kline(code))
            coefficient, evidence = return_correlation(center_closes, closes)
            if coefficient is not None:
                self._add_edge(
                    code,
                    self.center,
                    "correlation",
                    f"二跳标的近{_GRAPH_KLINE_COUNT}日相关系数 {coefficient:+.2f}",
                    0.45 + abs(coefficient) * 0.3,
                    evidence=evidence,
                )
        self.second_hop_codes = codes

    # ── 第五层：二跳标的的板块与更多新闻扩散 ─────────────────────────────
    def _layer_deep_expand(self) -> None:
        second_hop = self.second_hop_codes
        if second_hop:
            code = second_hop[0]
            peer_boards = self._safe(
                lambda: self.ds._stock_boards(f"{self.parsed.market}{code}"),
                _empty_boards(),
            )
            for concept in (peer_boards.get("concepts") or [])[:2]:
                if concept["code"] in self.nodes:
                    continue
                self._add_node(concept["code"], concept["name"], "sector")
                self._add_edge(concept["code"], code, "concept", "三跳题材概念", 0.5)
            for index in (peer_boards.get("indices") or [])[:1]:
                if index["code"] in self.nodes:
                    continue
                self._add_node(index["code"], index["name"], "index")
                self._add_edge(index["code"], code, "index", "三跳指数成分", 0.46)
        self._layer_news(limit=5)
