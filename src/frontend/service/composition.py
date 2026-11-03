"""Thin presentation callbacks for the strategy workshop and resource-pool entry."""

import json
from html import escape
from typing import Any

import yaml

import gradio as gr
from src.data.manager import current_market
from src.engine.market.resource_pool import ResourcePoolService
from src.strategy.composition.accounts import PipelineAccounts
from src.strategy.composition.config import config, fail, merge, template, templates
from src.strategy.composition.service import PipelineService, component_catalog
from src.strategy.composition.validation import compile_plan, digest

from . import composition_editor as editor
from .composition_graph import CompositionGraphMixin


def _inputs(text: str, overrides: str) -> tuple[dict[str, Any], dict[str, Any]]:
    definition = yaml.safe_load(text)
    params = json.loads(overrides) if overrides and overrides.strip() else {}
    if not isinstance(definition, dict) or not isinstance(params, dict):
        raise fail("invalid")
    return definition, params


def _view(service: PipelineService, run: dict[str, Any], events: list[dict[str, Any]]) -> tuple:
    result = run.get("result") or {}
    cfg = config()
    status = f"{cfg['ui']['statuses'].get(run['status'], run['status'])} · {run['id']}"
    if result.get("error"):
        status += " · " + result["error"]
    if result.get("agent_validation_mode") == "off" and any(
        row.get("component") in {"cn_analysis", "cn_debate", "contest_data", "contest_research"}
        for row in result.get("diagnostics", {}).get("stages", [])
    ):
        status += " · Agent未执行：当前为纯量化对照"
    process = "\n\n".join(
        f"{row['time']} · {row['kind']} · {row['text']}\n{json.dumps(row.get('data'), ensure_ascii=False)[:1500]}"
        for row in events
    )[-cfg["defaults"]["agent"]["max_event_chars"] :]
    preview, download = "", None
    if run["status"] not in {"running", "cancelling"}:
        try:
            file = service.store.artifact(run["id"], "report.html")
            preview = f'<iframe title="策略工坊报告" sandbox="allow-scripts" style="width:100%;height:850px;border:0;border-radius:16px" srcdoc="{escape(file.read_text(encoding="utf-8"), quote=True)}"></iframe>'
            download = str(file)
        except ValueError:
            pass
    return (
        status,
        process,
        preview,
        gr.update(value=download, visible=bool(download)),
        run["id"],
        result.get("account_id") or None,
        run["version_id"],
    )


class CompositionServiceMixin(CompositionGraphMixin):
    pipeline_editor_state = staticmethod(editor.state)
    pipeline_node_detail = staticmethod(editor.detail)
    pipeline_edit_node = staticmethod(editor.apply_node)
    pipeline_edit_settings = staticmethod(editor.settings)
    pipeline_edit_sleeves = staticmethod(editor.sleeves)

    def pipeline_move_up(self, text, selected):
        return editor.move(text, selected, -1)

    def pipeline_move_down(self, text, selected):
        return editor.move(text, selected, 1)

    def pipeline_templates(self):
        choices = [("预置 / " + row["definition"]["name"], row["id"]) for row in templates()]
        rows = PipelineService().store.repo.db.query(
            "SELECT v.id,v.version,v.pipeline_id,p.name FROM strategy_pipeline_versions v JOIN strategy_pipelines p ON p.id=v.pipeline_id WHERE p.status!='disabled' ORDER BY v.id DESC LIMIT ?",
            (config()["defaults"]["history_limit_runs"],),
        )
        return choices + [
            (
                f"已发布 / {row['name']} · 方案#{row['pipeline_id']} v{row['version']} · 版本#{row['id']}",
                f"version:{row['id']}",
            )
            for row in rows
        ]

    def pipeline_components(self):
        return [
            {
                "类型": row["kind"],
                "组件": row.get("label", row["id"]),
                "标识": row["id"],
                "参数": json.dumps(row.get("defaults", row.get("default")), ensure_ascii=False),
            }
            for row in component_catalog()
        ]

    def pipeline_load(self, template_id: str):
        version = (
            PipelineService().store.version(int(template_id.split(":", 1)[1]))
            if template_id.startswith("version:")
            else None
        )
        definition = version["definition"] if version else template(template_id)
        return (
            yaml.safe_dump(definition, allow_unicode=True, sort_keys=False),
            gr.update(choices=list(definition.get("variants") or {"baseline": {}}), value="baseline"),
            version["pipeline_id"] if version else None,
            version["id"] if version else None,
            "",
        )

    def pipeline_preview(self, text: str, overrides: str, variant: str):
        definition, params = _inputs(text, overrides)
        return json.dumps(PipelineService().preview(definition, params, variant), ensure_ascii=False, indent=2)

    def pipeline_publish(self, text: str, overrides: str, variant: str, pipeline_id: Any):
        definition, params = _inputs(text, overrides)
        compile_plan(definition, params, variant)
        resolved = merge(merge(definition, (definition.get("variants") or {"baseline": {}})[variant]), params)
        resolved["variants"] = {"baseline": {}}
        service = PipelineService()
        draft = service.store.save_draft(resolved, int(pipeline_id) if pipeline_id else None)
        version = service.store.publish(draft["id"])
        return (
            f"{draft['name']} · 方案 {draft['id']} / 版本 {version['version']} / 策略 {version['strategy_id']}",
            draft["id"],
            version["id"],
        )

    def pipeline_run(
        self,
        text,
        overrides,
        variant,
        version_id,
        symbols,
        mode,
        backend,
        model_id,
        model_name,
        effort,
        start,
        end,
        account_id,
        refresh_decision,
        replay_ids="",
        snapshot_id="",
        graph_value=None,
        execution_costs=None,
        agent_documents_dataset_id=None,
        agent_strategy_options=None,
        agent_mode=None,
    ):
        definition, params = _inputs(text, overrides)
        if isinstance(graph_value, dict) and graph_value.get("document"):
            if digest(compile_plan(graph_value["document"], params, variant)) != digest(
                compile_plan(definition, params, variant)
            ):
                raise fail("invalid", "图形修改尚未应用到策略草稿，请先应用后再运行")
        request = {
            "definition": definition,
            "overrides": params,
            "variant": variant,
            "mode": mode,
            "market": current_market(),
            "symbols": [s.strip() for s in (symbols or "").split(",") if s.strip()] or None,
            "backend": backend,
            "model_id": int(model_id) if model_id else None,
            "model_name": model_name or "",
            "reasoning_effort": effort or "",
            "start_date": start or "",
            "end_date": end or "",
            "account_id": int(account_id) if account_id else None,
            "refresh_decision": bool(refresh_decision),
            "agent_replay": [key.strip() for key in (replay_ids or "").split(",") if key.strip()],
            "snapshot_id": (snapshot_id or "").strip() or None,
            "execution_costs": execution_costs,
            "agent_documents_dataset_id": int(agent_documents_dataset_id) if agent_documents_dataset_id else None,
            "agent_strategy_options": agent_strategy_options or {},
            "agent_mode": agent_mode,
        }
        service = PipelineService()
        if version_id:
            version = service.store.version(int(version_id), True)
            if digest(compile_plan(definition, params, variant)) != version["digest"]:
                raise fail("immutable")
            request.update(version_id=int(version_id), variant="baseline", overrides={})
        run = service.start(request)
        events = []
        for update in service.follow(run["id"]):
            events.extend(update["events"])
            yield _view(service, update["run"], events)

    def pipeline_open(self, run_id):
        service = PipelineService()
        return _view(service, service.detail(run_id), service.store.events(run_id))

    def pipeline_cancel(self, run_id):
        status = PipelineService().cancel(run_id)["status"]
        return config()["ui"]["statuses"].get(status, status)

    def pipeline_history(self):
        return gr.update(
            choices=[
                (f"{row['request']['mode']} · {row['created_at']} · {row['status']}", row["id"])
                for row in PipelineService().store.runs(config()["defaults"]["history_limit_runs"])
            ]
        )

    def pipeline_account_monitor(self, account_id, enabled):
        account = PipelineAccounts().monitor(int(account_id), bool(enabled))
        return f"{account['name']} · monitor={account['state']['monitor_enabled']}"

    def pipeline_account_reset(self, account_id):
        return str(PipelineAccounts().reset_risk(int(account_id))["id"])

    def pipeline_pool_run(self, template_id, pool_id, backend, snapshot_id=""):
        service = PipelineService()
        run = service.start(
            {
                **(
                    {"version_id": int(template_id.split(":", 1)[1])}
                    if template_id.startswith("version:")
                    else {"template": template_id}
                ),
                "resource_pool_id": int(pool_id) if pool_id else ResourcePoolService().default_pool_id(),
                "market": current_market(),
                "mode": "screen",
                "backend": backend,
                "snapshot_id": (snapshot_id or "").strip() or None,
            }
        )
        events = []
        for update in service.follow(run["id"]):
            events.extend(update["events"])
            view = _view(service, update["run"], events)
            yield view[0], view[1], view[2]
