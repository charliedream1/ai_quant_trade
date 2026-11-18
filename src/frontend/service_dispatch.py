"""Lazy callback ownership keeps modular pages independent of the legacy Mixin facade."""

import importlib
import inspect
from collections.abc import Callable
from functools import lru_cache, wraps
from typing import Any, Protocol

import yaml

from src.core.config import PROJECT_ROOT


class CallbackService(Protocol):
    def callback(self, name: str) -> Callable[..., Any]: ...


@lru_cache(maxsize=1)
def callback_registry() -> dict:
    return yaml.safe_load((PROJECT_ROOT / "egs/config/ui/frontend_services.yaml").read_text(encoding="utf-8"))[
        "methods"
    ]


def lookup_method(name: str):
    owner = callback_registry().get(name)
    if not owner:
        return None
    module, class_name = owner
    return getattr(getattr(importlib.import_module(module), class_name), name)


class CallbackServices:
    frontend_callback_service = True

    def callback(self, name: str) -> Callable[..., Any]:
        return getattr(self, name)

    def __getattr__(self, name: str):
        owner = callback_registry().get(name)
        if not owner:
            raise AttributeError("未登记的页面服务方法：" + name)
        module, class_name = owner
        cls = getattr(importlib.import_module(module), class_name)
        method = getattr(cls, name)
        descriptor = inspect.getattr_static(cls, name)
        bound = method if isinstance(descriptor, (staticmethod, classmethod)) else method.__get__(self, type(self))
        from src.core.page_work import CURRENT_PAGE, check, policy

        if name in policy()["read_methods"]:
            original = bound

            @wraps(original)
            def transient(*args, **kwargs):
                check()
                if CURRENT_PAGE.get() is not None:
                    from .page_reads import read

                    return read(name, args, kwargs)
                return original(*args, **kwargs)

            bound = transient
        from src.core.page_analysis_snapshot import analysis_config, capture

        if name not in policy()["read_methods"] and any(
            name in item["reads"] for item in analysis_config()["presets"].values()
        ):
            observed = bound

            @wraps(observed)
            def recorded(*args, **kwargs):
                value = observed(*args, **kwargs)
                try:
                    capture(name, observed, args, kwargs, value)
                except (ValueError, TypeError, AttributeError):
                    from src.core.logger import get_logger

                    get_logger("page.analysis").warning(
                        "Rule result retained; analysis snapshot unavailable | method={}", name
                    )
                return value

            bound = recorded
        setattr(self, name, bound)
        return bound
