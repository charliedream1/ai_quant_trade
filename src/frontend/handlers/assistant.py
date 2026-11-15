"""Floating assistant callback boundary."""

from .base import DomainHandler


class AssistantHandler(DomainHandler):
    domain = "assistant"
    allowed_methods = frozenset(
        {"floating_cli_chat_stream", "floating_models", "floating_send", "floating_qa", "floating_citation"}
    )
