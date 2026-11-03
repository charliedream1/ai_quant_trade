"""Floating assistant callback boundary."""

from .base import DomainHandler


class AssistantHandler(DomainHandler):
    domain = "assistant"
    allowed_methods = frozenset(
        {"floating_cli_chat_stream", "kb_qa", "ai_console_model_choices", "ai_console_send_stream"}
    )
