"""Optional application observations; no SDK import or network work when disabled."""

from .instrumentation import traced, traced_stream
from .runtime import current_observation, get_observer, shutdown_observability

__all__ = ["traced", "traced_stream", "get_observer", "current_observation", "shutdown_observability"]
