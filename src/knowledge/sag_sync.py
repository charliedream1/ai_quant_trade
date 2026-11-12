"""Retired remote ingestion hook; local SAG2 indexes are built from current chunks."""


def auto_sync_document(repo, identifier):
    """Imports need no network or model calls; query-time indexing handles revisions."""
    return None
