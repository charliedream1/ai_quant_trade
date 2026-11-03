"""Escaped, static research reports with visible phase evidence and budget status."""

import json
from html import escape


def render(run: dict, events: list[dict]) -> str:
    result = run["result"]
    sections = []
    for key, label in (
        ("analysts", "事实分析"),
        ("roles", "多空论证"),
        ("information", "数据竞赛"),
        ("proposals", "研究提案"),
        ("research_forecasts", "成熟成绩与效用"),
        ("budgets", "研究预算"),
        ("decision", "最终决定"),
        ("shadow_updates", "延迟成绩更新"),
    ):
        if key in result:
            sections.append(
                "<section><h2>"
                + label
                + "</h2><pre>"
                + escape(json.dumps(result[key], ensure_ascii=False, indent=2))
                + "</pre></section>"
            )
    usage: dict[str, int] = {}
    requests = 0
    for event in events:
        requests += event["kind"] == "llm_request"
        if event["kind"] == "llm_response":
            for key, value in (event["payload"].get("usage") or {}).items():
                if type(value) is int:
                    usage[key] = usage.get(key, 0) + value
    return (
        "<!doctype html><html lang='zh-CN'><meta charset='utf-8'><meta name='viewport' content='width=device-width'>"
        "<title>Agent策略研究</title><style>body{font:16px/1.65 system-ui,sans-serif;background:#eef5fc;color:#19324d;margin:0;padding:24px}"
        "main{max-width:1200px;margin:auto}section,header{background:white;border:1px solid #d8e7f3;border-radius:18px;padding:20px;margin:16px 0}"
        "pre{white-space:pre-wrap;overflow-wrap:anywhere;font:14px/1.6 ui-monospace,monospace}h1,h2{color:#1766ad}small{color:#506880}</style><main>"
        "<header><h1>"
        + escape(run["config"]["definition"]["name"])
        + "</h1><p>状态："
        + escape(run["status"])
        + " · 时点："
        + escape(run["as_of"])
        + "</p>"
        "<p>资料："
        + escape(str(run["evidence"]["coverage_status"]))
        + "；缺口："
        + escape(str(run["evidence"]["missing"]))
        + "</p>"
        "<p>实际请求：" + str(requests) + "；已返回usage：" + escape(str(usage)) + "。缺失用量为未知。</p>"
        "<p>冷启动或负效用可以保持现金；流程结束不等于策略有效。当前模型历史研究存在训练记忆风险。</p>"
        "<small>独立实现公开方法；角色观点不代表独立事实验证。账户AR/IC/回撤请查看关联组合账本报告。</small></header>"
        + "".join(sections)
        + "<section><h2>状态与限制</h2><pre>"
        + escape(
            json.dumps(
                {
                    k: v
                    for k, v in result.items()
                    if k in {"error", "cold_start", "can_allocate", "cash", "validation_mode"}
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        + "</pre></section></main></html>"
    )
