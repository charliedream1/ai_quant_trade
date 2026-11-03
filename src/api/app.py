"""FastAPI application factory."""

import os
import re
import sys
import time
from collections.abc import Iterable
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, Request, WebSocket
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from src.agent_strategies.service import shutdown as shutdown_agent_strategy_jobs
from src.alpha_mining.service import shutdown as shutdown_alpha_jobs
from src.api.errors import business_error_handler, unhandled_error_handler, validation_error_handler
from src.api.market_context import MarketContextMiddleware
from src.api.routes import (
    agent_strategies,
    ai_workspace,
    alpha_mining,
    backtests,
    cli_sessions,
    etfs,
    factors,
    file_previews,
    insights,
    jobs,
    kb,
    live,
    llm_models,
    market,
    market_analysis_reports,
    mcp_servers,
    news,
    notifications,
    paper_accounts,
    papers,
    qlib_workflows,
    quant_workflows,
    recommend_tasks,
    relations,
    reports,
    research_skills,
    research_team,
    settings,
    skills,
    stocks,
    strategies,
    strategy_pipelines,
    system,
    watchlist,
    workspace_resources,
)
from src.api.schemas.common import ok
from src.api.security import AccessControl, access_options
from src.api.ws_hub import ws_hub
from src.core.config import get_settings
from src.core.database import Database
from src.core.exceptions import BusinessError
from src.core.file_storage import FileStorage
from src.core.logger import get_logger, intercept_stdlib_logging, setup_logging, startup_banner
from src.documents.conversion import shutdown as shutdown_document_jobs
from src.engine.backtest.jobs import shutdown as shutdown_backtest_jobs
from src.engine.composition.monitor import PaperRiskMonitor
from src.engine.research.monitor_jobs import shutdown_monitor_jobs
from src.frontend.components.strategy_graph import mount_graph_assets
from src.frontend.mounting import LEGACY_FRONTEND_MOUNT_PATH, mount_gradio_apps, shutdown_gradio_apps
from src.frontend.registry import MODULES

SENSITIVE_QUERY_KEYS = ("key", "token", "secret", "password", "authorization", "credential")
FRONTEND_MOUNT_PATH = "/app"
FRONTEND_DEFAULT_PATH = "/app"
FRONTEND_INFO_PATHS = (
    FRONTEND_MOUNT_PATH,
    f"{FRONTEND_MOUNT_PATH}/",
    LEGACY_FRONTEND_MOUNT_PATH,
    f"{LEGACY_FRONTEND_MOUNT_PATH}/",
)
FRONTEND_INFO_PREFIXES = (
    f"{FRONTEND_MOUNT_PATH}/",
    f"{LEGACY_FRONTEND_MOUNT_PATH}/",
)
NOISY_HTTP_PATHS = ("/favicon.ico", "/manifest.json")
NOISY_HTTP_PREFIXES = ("/assets", "/static", "/app/assets", "/legacy-app/assets")
BACKEND_HTTP_PREFIXES = ("/api", "/ws")
STATIC_MOUNT_PATHS = ("/assets", "/static")


class StaticAssetCacheMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or "/assets/" not in scope.get("path", ""):
            await self.app(scope, receive, send)
            return

        async def send_with_cache(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers["cache-control"] = "public, max-age=31536000, immutable"
            await send(message)

        await self.app(scope, receive, send_with_cache)


def _is_noisy_http_path(path: str) -> bool:
    return path in NOISY_HTTP_PATHS or path.startswith(NOISY_HTTP_PREFIXES)


def _is_backend_http_path(path: str, api_prefix: str) -> bool:
    if path in {"/", "/api-meta"}:
        return True
    prefixes = tuple(dict.fromkeys((api_prefix, *BACKEND_HTTP_PREFIXES)))
    return path.startswith(prefixes)


def _is_frontend_info_path(path: str) -> bool:
    return path in FRONTEND_INFO_PATHS or path.startswith(FRONTEND_INFO_PREFIXES)


def _safe_query_items(items: Iterable[tuple[str, str]]) -> str:
    safe_items = []
    for key, value in items:
        normalized_key = key.lower()
        display_value = "***" if any(marker in normalized_key for marker in SENSITIVE_QUERY_KEYS) else value
        safe_items.append(f"{key}={display_value}")
    return "&".join(safe_items) or "-"


def _route_name(request: Request) -> str:
    route = request.scope.get("route")
    return getattr(route, "path", None) or "-"


def _endpoint_name(request: Request) -> str:
    endpoint = request.scope.get("endpoint")
    if endpoint is None:
        return "-"
    module = getattr(endpoint, "__module__", "")
    name = getattr(endpoint, "__name__", endpoint.__class__.__name__)
    return f"{module}.{name}" if module else name


def _client_host(request: Request) -> str:
    return request.client.host if request.client else "-"


def _user_agent(request: Request) -> str:
    value = request.headers.get("user-agent") or "-"
    return value[:180]


def _header_value(request: Request, name: str) -> str:
    value = request.headers.get(name) or "-"
    return value[:180]


def _context_text(context: dict[str, Any]) -> str:
    return " ".join(f"{key}={value}" for key, value in context.items()) or "-"


def _log_startup_phase(log: Any, phase: str, started: float, **context: Any) -> None:
    elapsed_ms = (time.perf_counter() - started) * 1000
    log.info(
        "backend startup phase completed | phase={} duration_ms={:.0f} context={}",
        phase,
        elapsed_ms,
        _context_text(context),
    )


def _log_route_summary(app: FastAPI, api_prefix: str, help_docs_mount_path: str, log: Any) -> None:
    route_paths = [str(getattr(route, "path", "") or "-") for route in app.routes]
    try:
        openapi_paths = app.openapi().get("paths", {})
        api_routes = sum(1 for path in openapi_paths if str(path).startswith(api_prefix))
    except Exception:
        api_routes = sum(1 for path in route_paths if path.startswith(api_prefix))
    frontend_routes = len(
        {
            path
            for path in route_paths
            if path == FRONTEND_MOUNT_PATH
            or path.startswith(f"{FRONTEND_MOUNT_PATH}/")
            or path == LEGACY_FRONTEND_MOUNT_PATH
        }
    )
    static_mounts = ",".join(path for path in route_paths if path in STATIC_MOUNT_PATHS or path == help_docs_mount_path)
    static_mounts = static_mounts or "-"
    log.info(
        "backend routes ready | total={} api_routes={} frontend_mounts={} static_mounts={} "
        "root_redirect={}/ modules={} legacy={}/ docs=/docs health={}/health",
        len(route_paths),
        api_routes,
        frontend_routes,
        static_mounts,
        FRONTEND_DEFAULT_PATH,
        len(MODULES),
        LEGACY_FRONTEND_MOUNT_PATH,
        api_prefix,
    )


def _mount_spa_fallback(app: FastAPI, web_dist: Path, log: Any) -> None:
    index_path = web_dist / "index.html"
    if not index_path.exists():
        log.warning("web dist fallback skipped | reason=index.html missing directory={}", web_dist)
        return

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa_fallback(full_path: str):
        path = Path(web_dist / full_path)
        if path.exists() and path.is_file():
            return FileResponse(path)
        return FileResponse(index_path)

    log.info("web dist fallback mounted | directory={}", web_dist)


def create_app() -> FastAPI:
    cfg = get_settings()
    setup_logging(cfg.data_dir / "logs", cfg.log_level)
    intercept_stdlib_logging()
    log = get_logger("startup")
    log.info(
        "backend app factory started | pid={} executable={} python={} cwd={} project_root={} data_dir={} db_path={} "
        "api_prefix={} frontend_default={}/ gradio_modules={} legacy_path={}/ frontend_root_path={}",
        os.getpid(),
        sys.executable,
        sys.version.split()[0],
        Path.cwd(),
        cfg.project_root,
        cfg.data_dir,
        cfg.db_path,
        cfg.api_prefix,
        FRONTEND_DEFAULT_PATH,
        len(MODULES),
        LEGACY_FRONTEND_MOUNT_PATH,
        cfg.frontend_root_path or "-",
    )
    phase_started = time.perf_counter()
    FileStorage(cfg.data_dir).ensure_dirs()
    os.environ.setdefault("GRADIO_TEMP_DIR", str(cfg.data_dir / "gradio_uploads"))
    _log_startup_phase(log, "file_storage.ensure_dirs", phase_started, data_dir=cfg.data_dir)
    phase_started = time.perf_counter()
    Database()
    _log_startup_phase(log, "database.init", phase_started, db_path=cfg.db_path)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        from src.data import DataSourceManager
        from src.scheduler import scheduler_runtime

        manager = DataSourceManager()
        mode_label = "mock 本地模拟数据" if manager.is_mock else "real 真实行情数据"
        started = time.perf_counter()
        scheduler_runtime.start()
        paper_risk_monitor = PaperRiskMonitor()
        paper_risk_monitor.start()
        log.info(
            "AIQuant智投后端启动 | 监听 {}:{} | 数据源模式={}（{}，源：{}） | "
            "调度器={} jobs={} | 日志级别={} | startup_ms={:.0f}",
            cfg.host,
            cfg.port,
            cfg.data_mode,
            mode_label,
            manager.source_name,
            scheduler_runtime.backend,
            scheduler_runtime.job_count,
            cfg.log_level,
            (time.perf_counter() - started) * 1000,
        )
        display_host = "127.0.0.1" if cfg.host in ("0.0.0.0", "::") else cfg.host
        web_url = f"http://{display_host}:{cfg.port}{FRONTEND_DEFAULT_PATH}/"
        api_url = f"http://{display_host}:{cfg.port}/docs"
        health_url = f"http://{display_host}:{cfg.port}{cfg.api_prefix}/health"
        startup_banner(
            log,
            app_name=cfg.app_name,
            web_url=web_url,
            api_url=api_url,
            health_url=health_url,
            github_url="https://github.com/charliedream1/ai_quant_trade",
            gitee_url="https://gitee.com/charlie1/ai_quant_trade.git",
        )
        log.info("=" * 66)
        log.info(
            "启动成功 | AIQuant智投已就绪 | Gradio前端 http://{}:{}{}/ | API 文档 http://{}:{}/docs | "
            "数据模式={} | 请求日志已降级 DEBUG，控制台仅显示业务日志 | 按 Ctrl+C 停止服务",
            display_host,
            cfg.port,
            FRONTEND_DEFAULT_PATH,
            display_host,
            cfg.port,
            cfg.data_mode,
        )
        log.info("=" * 66)
        try:
            yield
        finally:
            paper_risk_monitor.stop()
            shutdown_started = time.perf_counter()
            log.info(
                "AIQuant智投后端关闭开始 | pid={} | 监听 {}:{} | 调度器={} jobs={}",
                os.getpid(),
                cfg.host,
                cfg.port,
                scheduler_runtime.backend,
                scheduler_runtime.job_count,
            )
            shutdown_gradio_apps(_app, log)
            shutdown_monitor_jobs()
            shutdown_backtest_jobs()
            shutdown_document_jobs()
            shutdown_alpha_jobs()
            shutdown_agent_strategy_jobs()
            scheduler_runtime.stop()
            log.info(
                "AIQuant智投后端关闭完成 | pid={} | 监听 {}:{} | shutdown_ms={:.0f}",
                os.getpid(),
                cfg.host,
                cfg.port,
                (time.perf_counter() - shutdown_started) * 1000,
            )

    app = FastAPI(
        title="AIQuant智投 API",
        description="一体化量化交易平台后端",
        version=cfg.version,
        lifespan=lifespan,
    )
    mount_graph_assets(app)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(GZipMiddleware, minimum_size=1024, compresslevel=5)
    app.add_middleware(AccessControl, options=access_options(cfg))
    app.add_middleware(MarketContextMiddleware)
    app.add_middleware(StaticAssetCacheMiddleware)
    app.add_exception_handler(BusinessError, business_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(Exception, unhandled_error_handler)

    @app.middleware("http")
    async def backend_detail_log(request: Request, call_next):  # type: ignore[no-untyped-def]
        start = time.perf_counter()
        request_id = request.headers.get("X-Request-ID") or uuid4().hex[:12]
        if not re.fullmatch(r"[A-Za-z0-9_.:-]{1,128}", request_id):
            request_id = uuid4().hex[:12]
        request.state.request_id = request_id
        path = request.url.path
        should_log = not _is_noisy_http_path(path)
        query = _safe_query_items(request.query_params.multi_items())
        route = _route_name(request)
        endpoint = _endpoint_name(request)
        client = _client_host(request)
        user_agent = _user_agent(request)
        referer = _header_value(request, "referer")
        accept = _header_value(request, "accept")
        http_log = get_logger("backend.http")
        if should_log:
            http_log.debug(
                "backend request begin | request_id={} method={} path={} route={} endpoint={} query={} "
                "client={} user_agent={} referer={} accept={}",
                request_id,
                request.method,
                path,
                route,
                endpoint,
                query,
                client,
                user_agent,
                referer,
                accept,
            )
        try:
            response = await call_next(request)
        except Exception as exc:
            elapsed_ms = (time.perf_counter() - start) * 1000
            route = _route_name(request)
            endpoint = _endpoint_name(request)
            http_log.opt(exception=exc).error(
                "backend request failed | request_id={} method={} path={} route={} endpoint={} duration_ms={:.0f} "
                "client={} query={} user_agent={} referer={} accept={}",
                request_id,
                request.method,
                path,
                route,
                endpoint,
                elapsed_ms,
                client,
                query,
                user_agent,
                referer,
                accept,
            )
            raise

        elapsed_ms = (time.perf_counter() - start) * 1000
        route = _route_name(request)
        endpoint = _endpoint_name(request)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time-Ms"] = f"{elapsed_ms:.0f}"
        if not should_log and response.status_code < 400 and elapsed_ms < cfg.backend_slow_request_ms:
            return response

        route_missing = response.status_code == 404 and route == "-"
        if should_log is False and route_missing and response.status_code < 500:
            return response
        message = (
            "backend request completed | request_id={} method={} path={} route={} endpoint={} status={} "
            "duration_ms={:.0f} client={} query={} user_agent={} referer={} accept={} route_missing={}"
        )
        args = (
            request_id,
            request.method,
            path,
            route,
            endpoint,
            response.status_code,
            elapsed_ms,
            client,
            query,
            user_agent,
            referer,
            accept,
            route_missing,
        )
        if response.status_code >= 500:
            http_log.error(message, *args)
        elif response.status_code >= 400:
            http_log.warning(message, *args)
        else:
            # 正常请求只作为 DEBUG 诊断，不进入默认 INFO 控制台，避免接口流水掩盖业务日志。
            http_log.debug(message, *args)
        return response

    routers = [
        ai_workspace.router,
        system.router,
        notifications.router,
        news.router,
        market.router,
        watchlist.router,
        workspace_resources.router,
        relations.router,
        stocks.router,
        recommend_tasks.router,
        factors.router,
        file_previews.router,
        alpha_mining.router,
        agent_strategies.router,
        research_skills.router,
        etfs.router,
        reports.router,
        market_analysis_reports.router,
        papers.router,
        strategies.router,
        strategy_pipelines.router,
        cli_sessions.router,
        backtests.router,
        paper_accounts.router,
        live.router,
        qlib_workflows.router,
        quant_workflows.router,
        research_team.router,
        insights.router,
        kb.router,
        jobs.router,
        settings.router,
        llm_models.router,
        mcp_servers.router,
        skills.router,
    ]
    for router in routers:
        app.include_router(router, prefix=cfg.api_prefix)
    log.info("backend api routers registered | count={} api_prefix={}", len(routers), cfg.api_prefix)

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        await ws_hub.endpoint(websocket)

    @app.get("/", include_in_schema=False)
    def root():
        return RedirectResponse(url=f"{FRONTEND_DEFAULT_PATH}/")

    @app.get(FRONTEND_MOUNT_PATH, include_in_schema=False)
    def frontend_root():
        return RedirectResponse(url=f"{FRONTEND_DEFAULT_PATH}/")

    def module_redirect(destination: str):
        def redirect_to_module():
            return RedirectResponse(url=destination)

        return redirect_to_module

    for frontend_module in MODULES:
        app.add_api_route(
            frontend_module.mount_path,
            module_redirect(frontend_module.href),
            methods=["GET"],
            include_in_schema=False,
            name=f"frontend-{frontend_module.key}-without-slash",
        )

    @app.get(LEGACY_FRONTEND_MOUNT_PATH, include_in_schema=False)
    def legacy_frontend_without_slash():
        return RedirectResponse(url=f"{LEGACY_FRONTEND_MOUNT_PATH}/")

    @app.get("/api-meta")
    def api_meta():
        return ok({"name": cfg.app_name, "version": cfg.version, "docs": "/docs", "api_prefix": cfg.api_prefix})

    import gradio as gr

    frontend_assets = Path(__file__).resolve().parents[1] / "frontend" / "assets"
    if frontend_assets.exists():
        app.mount("/static", StaticFiles(directory=str(frontend_assets)), name="static")
        log.info("frontend static assets mounted | path=/static directory={}", frontend_assets)

        @app.get("/favicon.ico", include_in_schema=False)
        def favicon():
            return RedirectResponse(url="/static/logo.png")

    web_dist = cfg.project_root / "web" / "dist"
    spa_fallback_enabled = False
    if web_dist.exists():
        web_assets = web_dist / "assets"
        if web_assets.exists():
            app.mount("/assets", StaticFiles(directory=str(web_assets)), name="assets")
            log.info("web static assets mounted | path=/assets directory={}", web_assets)
        else:
            log.warning("web static assets skipped | reason=assets directory missing directory={}", web_assets)
        spa_fallback_enabled = True
    else:
        gradio_assets = Path(gr.__file__).parent / "templates" / "frontend" / "assets"
        if gradio_assets.exists():
            app.mount(
                "/assets",
                StaticFiles(directory=str(gradio_assets)),
                name="gradio-assets",
            )
            log.info("gradio static assets mounted | path=/assets directory={}", gradio_assets)

    from src.help_docs import mount_help_docs

    phase_started = time.perf_counter()
    help_docs_status = mount_help_docs(app, cfg)
    _log_startup_phase(
        log,
        "help_docs.mount",
        phase_started,
        path=f"{cfg.help_docs_mount_path}/",
        site_dir=help_docs_status.site_dir,
        built=help_docs_status.built,
        fallback=help_docs_status.fallback,
    )

    mounted_frontends = mount_gradio_apps(app, cfg, log)
    log.info(
        "modular gradio apps mounted lazily | paths={} gradio_version={} first_request_build=true",
        ",".join(mounted_frontends),
        gr.__version__,
    )
    if spa_fallback_enabled:
        _mount_spa_fallback(app, web_dist, log)
    _log_route_summary(app, cfg.api_prefix, cfg.help_docs_mount_path, log)
    log.info(
        "backend interface layout ready | frontend=gradio_modular default={}/ legacy={}/ "
        "callback_service=FrontendService external_api_prefix={} websocket_prefix=/ws help_docs_path={}/",
        FRONTEND_DEFAULT_PATH,
        LEGACY_FRONTEND_MOUNT_PATH,
        cfg.api_prefix,
        cfg.help_docs_mount_path,
    )
    return app


app = create_app()
