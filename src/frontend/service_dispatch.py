"""Lazy callback ownership keeps modular pages independent of the legacy Mixin facade."""

import importlib
import inspect
from collections.abc import Callable
from functools import lru_cache
from typing import Any, Protocol

import yaml

from src.core.config import PROJECT_ROOT


class CallbackService(Protocol):
    def callback(self, name: str) -> Callable[..., Any]: ...


@lru_cache(maxsize=1)
def callback_registry() -> dict:
    return yaml.safe_load((PROJECT_ROOT / "egs/frontend_services.yaml").read_text(encoding="utf-8"))["methods"]


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
        setattr(self, name, bound)
        return bound
