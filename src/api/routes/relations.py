"""Relation graph routes."""

from typing import Annotated

from fastapi import APIRouter, Query

from src.api.route_guards import ValidatedRoute
from src.api.schemas.common import ok
from src.engine.market import RelationGraphService

router = APIRouter(tags=["市场分析-关系图"], route_class=ValidatedRoute)


@router.get("/relations/graph")
def graph(
    symbol: str,
    relation_types: Annotated[list[str] | None, Query()] = None,
    depth: Annotated[int, Query(ge=1, le=5)] = 1,
):
    return ok(RelationGraphService().graph(symbol=symbol, relation_types=relation_types, depth=depth))
