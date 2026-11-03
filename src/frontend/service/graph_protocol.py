"""Typed graph updates never replace the editable component value with a stale snapshot."""

from time import monotonic_ns
from uuid import UUID, uuid4, uuid5

import gradio as gr


def sequence() -> str:
    return str(monotonic_ns())


def graph_patch(kind: str, current: dict, started: str, **changes):
    return gr.update(
        patch={
            "kind": kind,
            "doc_id": current.get("doc_id", ""),
            "edit_revision": int(current.get("edit_revision", 0)),
            "sequence": started,
            **changes,
        }
    )


def layout_identity(current: dict, pipeline_id=None, origin: str = "") -> tuple[str, str]:
    session = current.get("layout_session") or uuid4().hex
    key = (
        "pipeline:" + str(int(pipeline_id))
        if pipeline_id
        else "draft:" + uuid5(UUID(session), origin or current.get("layout_origin") or "initial").hex
    )
    return session, key
