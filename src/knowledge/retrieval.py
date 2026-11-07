"""Ordinary model generation plans each bounded keyword-search round."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from json_repair import repair_json
from loguru import logger

from src.core.exceptions import BusinessError, ErrorCode
from src.core.repository import Repository

from .config import knowledge_config
from .files import KnowledgeFiles
from .search import KeywordSearch

if TYPE_CHECKING:
    from src.agent.llm_client import LLMClient


class RetrievalLoop:
    def __init__(self, repo: Repository, llm: LLMClient):
        self.repo, self.llm = repo, llm

    def run(
        self,
        question: str,
        history: str,
        *,
        library: str,
        session_id: str,
        limit: int,
        rounds: Any = None,
        category_id: int | None = None,
        scope: str = "all",
        model_id: int | None = None,
        document_id: int | None = None,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], str]:
        policy = knowledge_config()["search"]
        try:
            budget = int(rounds if rounds is not None else policy["default_rounds"])
        except (ValueError, TypeError) as exc:
            raise BusinessError(ErrorCode.INVALID_PARAM, "检索轮数必须是整数") from exc
        if not 1 <= budget <= policy["max_rounds"]:
            raise BusinessError(ErrorCode.INVALID_PARAM, "检索轮数超出配置范围")
        if not KnowledgeFiles(self.repo).documents(
            library, session_id=session_id, category_id=category_id, scope=scope, document_id=document_id
        ):
            return [], [], "no_hits"
        found: dict[tuple[int, int], dict[str, Any]] = {}
        trace: list[dict[str, Any]] = []
        searched: list[str] = []
        for index in range(budget):
            evidence = "\n".join(f"[{row['title']}] {row['chunk_content']}" for row in found.values())[
                : policy["evidence_chars"]
            ]
            prompt = policy["planner_prompt"].format(
                question=question, history=history, evidence=evidence, searched=json.dumps(searched, ensure_ascii=False)
            )
            try:
                response = self.llm.complete(prompt, purpose="问答", model_id=model_id)
                plan = repair_json(response["text"], return_objects=True)
                if not isinstance(plan, dict) or not isinstance(plan.get("keywords"), list):
                    raise ValueError("检索规划未返回关键词数组")
                if index and found and plan.get("sufficient") is True:
                    break
                keywords = list(
                    dict.fromkeys(
                        term.strip()[: policy["keyword_chars"]]
                        for term in plan["keywords"]
                        if isinstance(term, str) and term.strip() and "\n" not in term and "\x00" not in term
                    )
                )
                keywords = [term for term in keywords if term not in searched][: policy["max_keywords"]]
            except Exception as exc:
                logger.warning("知识检索规划失败 | round={} error={}", index + 1, type(exc).__name__)
                return list(found.values())[:limit], trace, "planner_unavailable"
            if not keywords:
                break
            hits = KeywordSearch(self.repo).search(
                keywords,
                library=library,
                limit=limit,
                session_id=session_id,
                category_id=category_id,
                scope=scope,
                document_id=document_id,
            )
            searched.extend(keywords)
            for row in hits:
                found[(row["id"], row["chunk_index"])] = row
            trace.append({"round": index + 1, "keywords": keywords, "hits": len(hits)})
            logger.info("知识文件检索 | round={} keywords={} hits={}", index + 1, len(keywords), len(hits))
        return list(found.values())[:limit], trace, "retrieved" if found else "no_hits"
