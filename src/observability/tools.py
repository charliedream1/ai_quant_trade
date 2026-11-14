"""Observe approved evidence reads after the domain has validated tool access."""

from .instrumentation import traced


@traced("tool.evidence_read", "tool")
def read_item(tool: str, values: dict, key: str):
    return values[key]
