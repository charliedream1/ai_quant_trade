"""Scoped callback access for modular Gradio applications."""

from __future__ import annotations

from typing import Any, ClassVar

from ..service_dispatch import CallbackService


class DomainHandler:
    """Expose only the callback methods owned by one frontend domain."""

    domain: ClassVar[str]
    allowed_methods: ClassVar[frozenset[str]]

    def __init__(self, service: CallbackService) -> None:
        self._service = service

    def __getattr__(self, name: str) -> Any:
        if name not in self.allowed_methods:
            raise AttributeError(f"{self.domain} frontend handler cannot access {name!r}")
        return self._service.callback(name)
