"""Thin adapters reuse the existing stores, data gates, models and cost ledgers."""

from threading import Event

from src.agent.research_team import ResearchTeam
from src.agent_strategies.service import AgentStrategyService
from src.alpha_mining.data_io import parse_upload
from src.alpha_mining.service import AlphaService
from src.engine.insights.service import InsightReportService
from src.strategy.composition.service import PipelineService

from .catalog import local_file, settings


def import_data(plan: dict) -> dict:
    request = dict(plan["request"])
    if not plan["imports"]:
        return request
    service = AlphaService()
    for item in plan["imports"]:
        path = local_file(item["file"])
        row = service.register_dataset(
            item.get("name") or path.name, item["kind"], parse_upload(item["kind"], path.name, path.read_bytes())
        )
        request[item["target"]] = row["id"]
    return request


def _wait(detail, events, active, cancelled, cancel, emit):
    cursor = 0
    cancellation_sent = False
    while True:
        row = detail()
        page = events()
        for event in page[cursor:]:
            emit("domain_event", event)
        cursor = len(page)
        if row["status"] not in active:
            return row
        if cancelled() and not cancellation_sent:
            cancel()
            cancellation_sent = True
        Event().wait(settings()["limits"]["poll_seconds"])


def insight(request, provider, cancelled, emit):
    service = InsightReportService()
    run = service.start({**provider, **request}, cancelled=cancelled)
    emit("domain_run", {"family": "insight", "id": run["run_id"]})
    result = _wait(
        lambda: service.detail(run["run_id"]),
        lambda: service.store.events(run["run_id"]),
        {"running"},
        cancelled,
        lambda: None,
        emit,
    )
    return result, service.store.directory(run["run_id"]) / "report.html"


def team(request, provider, cancelled, emit):
    service = ResearchTeam()
    result = None
    cursor = 0
    for row in service.run_stream(
        request["backtest_id"],
        request["objective"],
        request.get("model_id"),
        request["workflow"],
        provider,
        request.get("role_models"),
        cancelled,
    ):
        if result is None:
            emit("domain_run", {"family": "team", "id": row["run_id"]})
        for event in row["events"][cursor:]:
            emit("domain_event", event)
        cursor, result = len(row["events"]), row
    return result, None


def alpha(request, provider, cancelled, emit):
    service = AlphaService()
    request = {**request, "models": {"default": provider, **request.get("models", {})}}
    request = dict(request)
    study_id = request.pop("study_id", None)
    candidate_id = request.pop("candidate_id", None)
    action = request.pop("action", None)
    study = service.store.get("alpha_studies", int(study_id)) if study_id else service.create(request)
    if study["mode"] != request["mode"]:
        raise ValueError("现有研究与Skill模式不一致")
    emit("domain_run", {"family": "alpha", "id": study["id"]})
    action = action or ("discover" if study["mode"] == "alpha" else "run")
    if action == "seal":
        result = service.seal(study["id"])
        return result, service.store.artifact(study["id"], "report.html")
    service.start(study["id"], action, candidate_id)
    result = _wait(
        lambda: service.detail(study["id"]),
        lambda: service.store.list("alpha_events", study["id"]),
        {"discovering", "validating", "testing"},
        cancelled,
        lambda: service.cancel(study["id"]),
        emit,
    )
    return result, service.store.artifact(study["id"], "report.html")


def agents(request, provider, cancelled, emit):
    service = AgentStrategyService()
    run = service.start({**provider, **request})
    emit("domain_run", {"family": "agents", "id": run["id"]})
    result = _wait(
        lambda: service.store.get(run["id"]),
        lambda: service.all_events(run["id"]),
        {"created", "running", "prepared"},
        cancelled,
        lambda: service.cancel(run["id"]),
        emit,
    )
    return result, service.store.artifact(run["id"], "report.html")


def composition(request, provider, cancelled, emit):
    service = PipelineService()
    run = service.start({**provider, **request})
    emit("domain_run", {"family": "composition", "id": run["id"]})
    result = _wait(
        lambda: service.detail(run["id"]),
        lambda: service.store.events(run["id"]),
        {"running", "cancelling"},
        cancelled,
        lambda: service.cancel(run["id"]),
        emit,
    )
    return result, service.store.artifact(run["id"], "report.html")


HANDLERS = {"insight": insight, "team": team, "alpha": alpha, "agents": agents, "composition": composition}
