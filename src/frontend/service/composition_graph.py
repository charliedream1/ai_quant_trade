"""Gradio callbacks for bounded graph changes, layouts and actual node evidence."""

from typing import Protocol, cast
from uuid import uuid4

import gradio as gr
import yaml

from src.strategy.composition.store import LOCK, PipelineStore

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
        if version_id and GraphLayouts().load(f"version:{version_id}")["revision"]:
            key = f"version:{version_id}"
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
        if isinstance(current, dict) and str(current.get("layout_key", "")).startswith("version:"):
            return gr.skip()
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

    def pipeline_graph_save(self, value, text, pipeline_id, version_id):
        started = sequence()
        try:
            document = validate_submission(value, text)
            layout = value.get("layout") or {}
            layouts = GraphLayouts()
            layouts.validate(layout)
            store = PipelineStore(layouts.repo)
            result = yaml.safe_dump(document, allow_unicode=True, sort_keys=False)
            with LOCK, store.repo.db.transaction():
                previous = store.version(int(version_id)) if version_id else None
                if previous and previous["pipeline_id"] != pipeline_id:
                    raise ValueError("The selected version belongs to another strategy")
                saved_layout = layouts.load(f"version:{previous['id']}") if previous else {"layout": None}
                if previous and previous["definition"] == document and saved_layout["layout"] == layout:
                    version = previous
                else:
                    draft = store.save_draft(document, int(pipeline_id) if pipeline_id else None)
                    version = store.publish(draft["id"], register=False)
                    layouts.save(f"version:{version['id']}", document_payload(result)["base_digest"], layout, 0)
            applied = document_payload(result, value)
            applied.update(
                layout_key=f"version:{version['id']}",
                layout_revision=1,
                applied_revision=int(value.get("applied_revision", 0)) + 1,
            )
            return (
                result,
                f"{graph_config()['ui']['version_saved']} v{version['version']}",
                version["pipeline_id"],
                version["id"],
                graph_patch("applied", value, started, payload=applied),
            )
        except (ValueError, TypeError, KeyError) as exc:
            return (
                gr.skip(),
                graph_config()["ui"]["error"] + ": " + str(exc),
                gr.skip(),
                gr.skip(),
                graph_patch("issues", value, started, issues=[str(exc)]),
            )

    def pipeline_graph_layout(self, value):
        if str(value.get("layout_key", "")).startswith("version:"):
            raise ValueError("Edit and save a new version to change a saved layout")
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
