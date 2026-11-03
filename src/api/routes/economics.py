"""On-demand economic observations and immutable research snapshots."""

from fastapi import APIRouter, Query

from src.api.route_guards import ValidatedRoute
from src.api.schemas.common import ok
from src.engine.economics.service import EconomicAnalysis

router = APIRouter(tags=["Economic research"], route_class=ValidatedRoute)


@router.get("/economics/macro")
def macro(series: str = "", refresh: bool = False, market: str | None = None):
    return ok(EconomicAnalysis().macro(series.split(",") if series else None, refresh=refresh, market=market))


@router.get("/economics/fundamentals/{symbol}")
def fundamentals(
    symbol: str,
    period: str = "",
    peers: str = Query(default="", max_length=200),
    refresh: bool = False,
    market: str | None = None,
):
    return ok(
        EconomicAnalysis().fundamentals(
            symbol,
            period=period,
            peers=[item.strip() for item in peers.split(",") if item.strip()],
            refresh=refresh,
            market=market,
        )
    )


@router.get("/economics/snapshots/{identifier}")
def snapshot(identifier: str):
    return ok(EconomicAnalysis().store.read(identifier))
