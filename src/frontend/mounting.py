"""Lazy ASGI mounting for independent Gradio applications."""

from __future__ import annotations

import asyncio
import inspect
import threading
from time import perf_counter
from typing import Any
from urllib.parse import parse_qs, urlencode

from starlette.responses import RedirectResponse
from starlette.types import Receive, Scope, Send

from src.core.async_work import blocking_call
from src.core.logger import capture_stdout_to_loguru

from .common.navigation import resolve_destination
from .registry import LEGACY_MODULES, MODULES

LEGACY_FRONTEND_MOUNT_PATH = "/legacy-app"
SHELL_FRONTEND_MOUNT_PATH = "/app"
SHELL_MODULE_KEY = "__shell__"


class LazyGradioASGI:
    """Build and mount one Gradio application on its first request."""

    def __init__(self, cfg: Any, log: Any, mount_path: str, module_key: str | None) -> None:
        self._cfg = cfg
        self._log = log
        self._mount_path = mount_path
        self._module_key = module_key
        self._lock = threading.Lock()
        self._startup_lock = asyncio.Lock()
        self._app: Any | None = None
        self._blocks: Any | None = None
        self._started = False

    @property
    def is_built(self) -> bool:
        return self._app is not None

    @property
    def is_started(self) -> bool:
        return self._started

    def _ensure_app(self) -> Any:
        if self._app is not None:
            return self._app
        with self._lock:
            if self._app is not None:
                return self._app

            from fastapi import FastAPI

            import gradio as gr

            started = perf_counter()
            self._log.info(
                "lazy gradio build started | module={} path={}/",
                self._module_key or "legacy",
                self._mount_path,
            )
            with capture_stdout_to_loguru("frontend.gradio.stdout", level="DEBUG"):
                if self._module_key is None:
                    from .app import build_gradio_app, gradio_mount_options

                    gradio_app = build_gradio_app()
                    mount_options = gradio_mount_options(self._cfg.ui_theme)
                    from .theme import HOME_CSS

                    if "css" in mount_options:
                        mount_options["css"] += HOME_CSS
                elif self._module_key == SHELL_MODULE_KEY:
                    from .shell import build_gradio_shell, shell_gradio_mount_options

                    gradio_app = build_gradio_shell(self._cfg.ui_theme)
                    mount_options = shell_gradio_mount_options(self._cfg.ui_theme)
                else:
                    from .modular import build_gradio_module, modular_gradio_mount_options

                    gradio_app = build_gradio_module(self._module_key)
                    mount_options = modular_gradio_mount_options(self._cfg.ui_theme, self._module_key)

            if self._cfg.frontend_root_path and "root_path" in inspect.signature(gr.mount_gradio_app).parameters:
                mount_options["root_path"] = self._cfg.frontend_root_path

            inner_app = FastAPI()
            with capture_stdout_to_loguru("frontend.gradio.stdout", level="DEBUG"):
                mounted_app = gr.mount_gradio_app(
                    inner_app,
                    gradio_app,
                    path="/",
                    show_error=True,
                    **mount_options,
                )
            self._blocks = gradio_app
            self._app = mounted_app
            self._log.info(
                "lazy gradio build finished | module={} path={}/ duration_ms={:.0f} gradio_version={}",
                self._module_key or "legacy",
                self._mount_path,
                (perf_counter() - started) * 1000,
                gr.__version__,
            )
            return self._app

    async def _ensure_started(self) -> None:
        if self._started:
            return
        async with self._startup_lock:
            if self._started:
                return
            if self._blocks is None:
                raise RuntimeError("Gradio application must be built before startup")

            started = perf_counter()
            self._log.info(
                "lazy gradio startup started | module={} path={}/",
                self._module_key or "legacy",
                self._mount_path,
            )
            self._blocks.run_startup_events()
            await self._blocks.run_extra_startup_events()
            self._started = True
            self._log.info(
                "lazy gradio startup finished | module={} path={}/ duration_ms={:.0f}",
                self._module_key or "legacy",
                self._mount_path,
                (perf_counter() - started) * 1000,
            )

    def shutdown(self) -> None:
        if not self._started or self._blocks is None:
            return
        self._blocks.close(verbose=False)
        self._started = False

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        app = self._app if self._app is not None else await blocking_call(self._ensure_app, group="ui_build")
        await self._ensure_started()
        await app(scope, receive, send)


class LegacyResearchASGI:
    """Redirect bookmarked page roots; preserve older config/API endpoints during migration."""

    def __init__(self, app: LazyGradioASGI):
        self.app = app

    @property
    def is_built(self) -> bool:
        return self.app.is_built

    @property
    def is_started(self) -> bool:
        return self.app.is_started

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        path = scope.get("path", "")
        if scope["type"] == "http" and scope.get("method") == "GET" and path.rstrip("/").endswith("/app/research"):
            query = parse_qs(scope.get("query_string", b"").decode())
            target = resolve_destination("research", query.get("view", [""])[0])
            if target["module"] == "research":
                target = resolve_destination("research", "")
            prefix = path.rsplit("/app/research", 1)[0]
            response = RedirectResponse(prefix + "/app/?" + urlencode(target))
            await response(scope, receive, send)
            return
        await self.app(scope, receive, send)


def mount_gradio_apps(app: Any, cfg: Any, log: Any) -> list[str]:
    mounted_paths: list[str] = []
    mounted_apps: list[LazyGradioASGI] = []
    for module in (*MODULES, *LEGACY_MODULES):
        mounted_app = LazyGradioASGI(cfg, log, module.mount_path, module.key)
        app.mount(
            module.mount_path,
            LegacyResearchASGI(mounted_app) if module.key == "research" else mounted_app,
            name=f"gradio-{module.key}",
        )
        mounted_apps.append(mounted_app)
        mounted_paths.append(module.mount_path)

    legacy_app = LazyGradioASGI(cfg, log, LEGACY_FRONTEND_MOUNT_PATH, None)
    app.mount(
        LEGACY_FRONTEND_MOUNT_PATH,
        legacy_app,
        name="gradio-legacy",
    )
    mounted_apps.append(legacy_app)
    mounted_paths.append(LEGACY_FRONTEND_MOUNT_PATH)

    # The parent mount must be registered after every /app/<module> mount so
    # Starlette resolves direct module routes before falling back to the shell.
    shell_app = LazyGradioASGI(cfg, log, SHELL_FRONTEND_MOUNT_PATH, SHELL_MODULE_KEY)
    app.mount(
        SHELL_FRONTEND_MOUNT_PATH,
        shell_app,
        name="gradio-shell",
    )
    mounted_apps.append(shell_app)
    mounted_paths.append(SHELL_FRONTEND_MOUNT_PATH)
    app.state.lazy_gradio_apps = tuple(mounted_apps)
    return mounted_paths


def shutdown_gradio_apps(app: Any, log: Any) -> None:
    mounted_apps = getattr(app.state, "lazy_gradio_apps", ())
    started_apps = [mounted_app for mounted_app in mounted_apps if mounted_app.is_started]
    for mounted_app in started_apps:
        mounted_app.shutdown()
    log.info("lazy gradio apps stopped | count={}", len(started_apps))
