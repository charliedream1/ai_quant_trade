"""Gradio callbacks for bounded graph changes, layouts and actual node evidence."""

from typing import Protocol, cast
from uuid import uuid4

import yaml

import gradio as gr

from .graph_documents import document_payload, graph_config, validate_submission
from .graph_evidence import evidence
from .graph_protocol import graph_patch, layout_identity, sequence
from .graph_storage import GraphLayouts


class PipelineLoader(Protocol):
    def pipeline_load(self, template_id) -> tuple: ...


class CompositionGraphMixin:
    def pipeline_graph_sync(self, text, current, pipeline_id, run_id):
        started = sequence()
        prior = current if isinstance(current, dict) else {}
        try:
            value = document_payload(text, prior)
        except (ValueError, TypeError, KeyError, yaml.YAMLError) as exc:
            return graph_patch("issues", prior, started, issues=[str(exc)])
        session, key = layout_identity(prior, pipeline_id)
        value.update(layout_session=session, layout_key=key)
        return graph_patch("sync", prior, started, payload=value)

    def pipeline_graph_load(self, template_id, current):
        started = sequence()
        text, variant, pipeline_id, version_id, status = cast(PipelineLoader, self).pipeline_load(template_id)
        prior = current if isinstance(current, dict) else {}
        session, key = layout_identity(prior, pipeline_id, template_id)
        saved = GraphLayouts().load(key)
        value = document_payload(text)
        layout = saved["layout"] if saved.get("definition_digest") == value["base_digest"] else {}
        value.update(
            doc_id=uuid4().hex,
            layout_session=session,
            layout_origin=template_id,
            layout_key=key,
            layout=layout,
            layout_revision=saved["revision"],
            evidence=prior.get("evidence", {}),
        )
        return text, variant, pipeline_id, version_id, status, graph_patch("load", prior, started, payload=value)

    def pipeline_graph_binding(self, text, current, pipeline_id):
        started = sequence()
        session, key = layout_identity(current, pipeline_id)
        saved = GraphLayouts().load(key)
        return graph_patch(
            "binding",
            current,
            started,
            layout_key=key,
            layout_session=session,
            layout_revision=saved["revision"],
            layout=saved["layout"],
        )

    def pipeline_graph_apply(self, value, text):
        started = sequence()
        try:
            document = validate_submission(value, text)
            result = yaml.safe_dump(document, allow_unicode=True, sort_keys=False)
            applied = document_payload(result, value)
            applied["applied_revision"] = int(value.get("applied_revision", 0)) + 1
            return (
                result,
                graph_config()["ui"]["applied"],
                None,
                graph_patch("applied", value, started, payload=applied),
            )
        except (ValueError, TypeError, KeyError) as exc:
            return (
                gr.skip(),
                graph_config()["ui"]["error"] + ": " + str(exc),
                gr.skip(),
                graph_patch("issues", value, started, issues=[str(exc)]),
            )

    def pipeline_graph_layout(self, value):
        started = sequence()
        saved = GraphLayouts().save(
            value["layout_key"], value["base_digest"], value.get("layout") or {}, int(value.get("layout_revision") or 0)
        )
        return graph_patch(
            "layout", value, started, layout_key=value["layout_key"], layout_revision=saved["revision"]
        ), graph_config()["ui"]["saved"]

    def pipeline_graph_results(self, run_id, value):
        started = sequence()
        return graph_patch("evidence", value, started, evidence=evidence(run_id))

    def pipeline_graph_poll(self, run_id, value):
        started = sequence()
        data = evidence(run_id)
        return graph_patch("evidence", value, started, evidence=data), gr.update(
            active=data.get("status") in {"running", "cancelling"}
        )
