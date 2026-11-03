"""Presentation adapters use the same frozen research services as REST and CLI."""

import json
from pathlib import Path

import yaml

import gradio as gr
from src.alpha_mining.approvals import approve
from src.alpha_mining.config import config, contained, digest, invalid
from src.alpha_mining.data_io import attest, parse_upload, register_snapshot
from src.alpha_mining.export import export_draft
from src.alpha_mining.service import AlphaService
from src.core.config import get_settings
from src.documents.store import PreviewStore
from src.documents.view import launcher


def _object(value):
    result = yaml.safe_load(str(value or "{}"))
    if not isinstance(result, dict):
        raise invalid("高级配置或复核证据必须为对象")
    return result


def _dataset_choices(service):
    return [
        (f"#{row['id']} · {row['kind']} · {row['name']}", row["id"]) for row in service.store.list("alpha_datasets")
    ]


class AlphaUIMixin:
    def alpha_catalog(self, selected=None):
        service = AlphaService()
        studies = service.store.list("alpha_studies")
        models = service.store.repo.list("llm_models", "enabled=1")
        return (
            gr.update(
                choices=[(f"#{row['id']} · {row['name']} · {row['status']}", row["id"]) for row in studies],
                value=selected,
            ),
            gr.update(choices=_dataset_choices(service)),
            gr.update(choices=[(f"#{row['id']} · {row['name']}", row["id"]) for row in models]),
        )

    def alpha_import(self, kind, value):
        if not value:
            raise invalid("请先选择CSV、JSON或YAML数据")
        path = contained(Path(str(value)))
        if path.stat().st_size > config()["limits"]["max_upload_bytes"]:
            raise invalid("研究导入文件超过上限")
        service = AlphaService()
        row = service.register_dataset(path.name, kind, parse_upload(kind, path.name, path.read_bytes()))
        return gr.update(choices=_dataset_choices(service), value=row["id"]), f"已导入数据#{row['id']}；来源待核验"

    def alpha_snapshot(self, identifier):
        service = AlphaService()
        row = register_snapshot(service, str(identifier).strip())
        return gr.update(choices=_dataset_choices(service), value=row["id"]), f"已读取服务器归档，数据#{row['id']}"

    def alpha_attest(self, dataset_id, reviewer, evidence):
        service = AlphaService()
        row = attest(service, int(dataset_id), reviewer, _object(evidence))
        return gr.update(
            choices=_dataset_choices(service), value=row["id"]
        ), f"已登记人工来源核验，新数据版本#{row['id']}；旧研究保持原版本"

    def alpha_create(
        self,
        name,
        mode,
        dataset_id,
        model_id,
        reasoning,
        budget,
        batch,
        purpose,
        cutoff,
        costs,
        advanced,
        backend="api",
        model_name="",
    ):
        request = {
            "name": name,
            "mode": mode,
            "dataset_id": int(dataset_id),
            "purpose": purpose,
            "batch_size": int(batch),
            "model_call_budget": int(budget),
            "cutoff": cutoff,
            "execution_costs": {"profile": costs},
        }
        if model_id or backend != "api":
            selection = {"backend": backend, "model_name": model_name, "reasoning_effort": reasoning or ""}
            if backend == "api" and model_id:
                selection["model_id"] = int(model_id)
            request["models"] = {"default": selection}
            if mode == "regime":
                request["configurations"] = [selection]
        request.update(_object(advanced))
        service = AlphaService()
        study = service.create(request)
        return self.alpha_catalog(study["id"])[0], f"研究#{study['id']}已登记，政策与数据已冻结；点击执行"

    def alpha_operate(self, study_id, action, candidate_id, stage):
        service = AlphaService()
        identifier = int(study_id)
        if action == "start":
            study = service.store.get("alpha_studies", identifier)
            action = "discover" if study["mode"] == "alpha" else "run"
        if action == "seal":
            service.seal(identifier)
        elif action == "cancel":
            service.cancel(identifier)
        else:
            service.start(identifier, action, int(candidate_id) if candidate_id else None)
        return self.alpha_poll(identifier, stage, candidate_id)

    def alpha_add(self, study_id, hypothesis, implementation, stage):
        AlphaService().candidate(int(study_id), _object(hypothesis), _object(implementation))
        return self.alpha_poll(study_id, stage, None)

    def alpha_poll(self, study_id, stage="假设", candidate_id=None):
        if not study_id:
            return (
                "请选择或新建研究",
                gr.update(choices=[], value=None),
                "",
                {},
                "",
                "",
                gr.update(choices=[], value=None),
                gr.update(active=False),
            )
        service = AlphaService()
        study = service.detail(int(study_id))
        candidates = study["candidates"]
        selected = next((row for row in candidates if row["id"] == candidate_id), candidates[0] if candidates else None)
        choices = [
            (f"#{row['id']} · {row['hypothesis'].get('title', '')} · {row['status']}", row["id"]) for row in candidates
        ]
        status = f"#{study_id} · {config()['ui']['states'].get(study['status'], study['status'])} · 事件链{'有效' if study['event_chain_valid'] else '异常'}"
        if study["result"].get("error"):
            status += " · " + study["result"]["error"]
        if study["status"] == "validated":
            passed = sum(bool(row.get("passed")) for row in study["result"].get("validation", []))
            status += f" · 通过候选{passed}个；只有通过的候选可进入最终留出"
        if study["result"].get("failures"):
            status += f" · 模型错误{len(study['result']['failures'])}项；错误决定已弃权，不能配置资金"
        events = sorted(service.store.list("alpha_events", int(study_id)), key=lambda row: row["id"])
        process = "\n\n".join(
            f"{row['id']} · {row['created_at']} · {row['kind']}\n{json.dumps(row['payload'], ensure_ascii=False)}"
            for row in events
        )[-config()["limits"]["max_response_chars"] :]
        inspection = self._alpha_inspection(study, stage, selected)
        code = ""
        if selected:
            source = service.store.artifact(int(study_id), f"candidate-{selected['id']}.py")
            code = source.read_text(encoding="utf-8") if source.is_file() else "该候选尚未获得通过契约的Python实现"
        report = service.store.artifact(int(study_id), "report.html")
        html = (
            f'<iframe title="Alpha研究报告" sandbox="allow-same-origin" style="width:100%;height:680px;border:0" src="{get_settings().api_prefix}/alpha/studies/{int(study_id)}/files/report.html?v={digest(study["result"])}"></iframe>'
            if report.is_file()
            else ""
        )
        files = (
            sorted(
                path.name
                for path in report.parent.iterdir()
                if path.is_file() and path.suffix in {".md", ".py", ".html", ".json"}
            )
            if report.parent.is_dir()
            else []
        )
        return (
            status,
            gr.update(choices=choices, value=selected["id"] if selected else None),
            process,
            inspection,
            code,
            html,
            gr.update(choices=files, value="report.html" if "report.html" in files else files[0] if files else None),
            gr.update(active=study["status"] in {"discovering", "validating", "testing"}),
        )

    @staticmethod
    def _alpha_inspection(study, stage, selected):
        if stage == "假设":
            return {
                "政策": study["config"]["policy"],
                "候选": [
                    {"id": row["id"], "origin": row["origin"], "hypothesis": row["hypothesis"]}
                    for row in study["candidates"]
                ],
            }
        if stage == "实现":
            return selected or {"status": "等待候选实现"}
        if stage == "复核":
            return {
                "reviews": study["reviews"],
                "final": study["result"].get("final"),
                "身份边界": "本地操作者记录，不等于独立双人认证",
            }
        return study["result"]

    def alpha_review(self, study_id, candidate_id, track, decision, reviewer, evidence, stage):
        service = AlphaService()
        study = service.store.get("alpha_studies", int(study_id))
        approve(
            service.store,
            int(study_id),
            int(candidate_id) if candidate_id and study["mode"] == "alpha" else None,
            track,
            decision,
            reviewer,
            _object(evidence),
        )
        return self.alpha_poll(study_id, stage, candidate_id)

    def alpha_export(self, study_id, candidate_id, configuration):
        service = AlphaService()
        study = service.store.get("alpha_studies", int(study_id))
        result = export_draft(
            service.store,
            int(study_id),
            int(candidate_id) if candidate_id and study["mode"] == "alpha" else None,
            int(configuration),
        )
        return f"已导出工坊草稿#{result['pipeline_id']}；下一步发布并进行前向模拟，未自动实盘"

    def alpha_open_artifact(self, study_id, name):
        service = AlphaService()
        path = service.store.artifact(int(study_id), str(name))
        if not path.is_file():
            raise invalid("请选择已生成的产物")
        previews = PreviewStore()
        row = previews.upload(path.name, path.read_bytes(), source="alpha_artifact")
        row["editable"] = False
        previews.save(row)
        return launcher(row)
