import ast
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest

from src.frontend.handlers import build_frontend_handlers
from src.frontend.handlers.dashboard import DashboardHandler
from src.frontend.services import FrontendService

FEATURE_DIR = Path("src/frontend/features")
DOMAIN_NAMES = {
    "admin",
    "ai",
    "assistant",
    "dashboard",
    "knowledge",
    "live",
    "market",
    "research",
    "simulation",
    "strategy",
}

EXPECTED_SERVICE_MODULES = {
    "alpha",
    "report_library",
    "execution_costs",
    "backtest_quick",
    "rag_chat",
    "monitoring",
    "resource_import_ui",
    "admin",
    "ai",
    "assistant",
    "dashboard",
    "knowledge",
    "live",
    "market",
    "etf",
    "parameters",
    "research",
    "research_team",
    "insights",
    "composition",
    "composition_graph",
    "simulation",
    "strategy",
}


def _service_methods(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {
        node.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "service"
    }


def test_feature_modules_only_use_their_scoped_handler_methods():
    handlers = build_frontend_handlers(FrontendService())

    for domain in DOMAIN_NAMES:
        used_methods = _service_methods(FEATURE_DIR / f"{domain}.py")
        if domain == "dashboard":
            used_methods |= _service_methods(FEATURE_DIR / "home.py")
        if domain == "ai":
            for panel in FEATURE_DIR.glob("ai_*.py"):
                used_methods |= _service_methods(panel)
            # Console action methods keep their scoped service on the instance.
            action_tree = ast.parse((FEATURE_DIR / "ai_console_actions.py").read_text(encoding="utf-8"))
            used_methods |= {
                node.attr
                for node in ast.walk(action_tree)
                if isinstance(node, ast.Attribute)
                and isinstance(node.value, ast.Attribute)
                and ast.unparse(node.value) == "self.service"
            }
            used_methods |= _service_methods(FEATURE_DIR / "quick_tools.py")
            used_methods |= _service_methods(FEATURE_DIR / "research_team.py")
            used_methods |= _service_methods(FEATURE_DIR / "insights.py")
        if domain == "knowledge":
            used_methods |= _service_methods(FEATURE_DIR / "research.py")
            used_methods |= _service_methods(FEATURE_DIR / "report_library.py")
            used_methods |= _service_methods(FEATURE_DIR / "rag_chat.py")
            used_methods |= _service_methods(FEATURE_DIR / "knowledge_ingest.py")
        if domain in {"strategy", "simulation"}:
            used_methods |= _service_methods(FEATURE_DIR / "parameters.py")
            used_methods |= _service_methods(FEATURE_DIR / "execution_costs.py")
        if domain == "simulation":
            used_methods |= _service_methods(FEATURE_DIR / "analysis.py")
        if domain == "strategy":
            used_methods |= _service_methods(FEATURE_DIR / "alpha.py")
            used_methods |= _service_methods(FEATURE_DIR / "factor_monitor.py")
        if domain == "strategy":
            used_methods |= _service_methods(FEATURE_DIR / "composition.py")
            used_methods |= _service_methods(FEATURE_DIR / "composition_editor.py")
            used_methods |= _service_methods(FEATURE_DIR / "composition_graph.py")
        allowed_methods = getattr(handlers, domain).allowed_methods
        assert used_methods == allowed_methods, domain
        assert all(hasattr(FrontendService, method) for method in allowed_methods)


def test_domain_handler_rejects_cross_domain_callback_access():
    callbacks = SimpleNamespace(dashboard_summary=lambda: "ok", live_start=lambda: "wrong domain")
    service = SimpleNamespace(callback=lambda name: getattr(callbacks, name))
    handler = DashboardHandler(cast(Any, service))

    assert handler.dashboard_summary() == "ok"
    with pytest.raises(AttributeError, match="dashboard frontend handler"):
        handler.live_start()


def test_frontend_service_facade_is_composed_from_domain_modules():
    service_modules = {
        base.__module__.rsplit(".", maxsplit=1)[-1]
        for base in FrontendService.__mro__
        if base.__module__.startswith("src.frontend.service.")
    }

    assert service_modules == EXPECTED_SERVICE_MODULES
    assert len(Path("src/frontend/services.py").read_text(encoding="utf-8").splitlines()) < 150


def test_scoped_handler_methods_resolve_to_modular_service_implementations():
    handlers = build_frontend_handlers(FrontendService())

    for domain in DOMAIN_NAMES:
        handler = getattr(handlers, domain)
        for method_name in handler.allowed_methods:
            owner = next(base for base in FrontendService.__mro__ if method_name in base.__dict__)
            assert owner.__module__.startswith("src.frontend.service."), (domain, method_name)
