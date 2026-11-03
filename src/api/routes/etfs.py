"""ETF universe and source-backed snapshot routes."""

from fastapi import APIRouter

from src.api.route_guards import ValidatedRoute
from src.api.schemas.common import ok
from src.data.etf import ETFUniverseService

router = APIRouter(tags=["ETF投研"], route_class=ValidatedRoute)


@router.get("/etf/universes")
def universes():
    return ok(ETFUniverseService().list_universes())


@router.get("/etf/universes/{universe}")
def universe(universe: str):
    return ok(ETFUniverseService().universe(universe))


@router.get("/etf/universes/{universe}/snapshot")
def snapshot(universe: str):
    return ok(ETFUniverseService().snapshot(universe))
