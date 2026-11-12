"""Original SAG service is retired. Use sag2_service for local retrieval."""

from .sag2_service import readiness as readiness


def sync_documents(payload, repo=None):
    """Reject retired synchronization rather than contacting an original SAG server."""
    raise ValueError("Original SAG is retired; use sag2_service.prepare_index")
