"""Escaped offline reports explain raw, adjusted and executable research evidence."""

import json
from html import escape

from .config import config
from .store import AlphaStore


def _table(rows: list[dict], columns: list[str]) -> str:
    head = "".join("<th>" + escape(key) + "</th>" for key in columns)
    body = "".join(
        "<tr>" + "".join("<td>" + escape(str(row.get(key, ""))) + "</td>" for key in columns) + "</tr>" for row in rows
    )
    return "<table><thead><tr>" + head + "</tr></thead><tbody>" + body + "</tbody></table>"


def _curve(values: list[float], color: str, label: str) -> str:
    if len(values) < 2:
        return ""
    low, high = min(values), max(values)
    span = high - low or 1
    points = " ".join(
        f"{index / (len(values) - 1) * 720:.2f},{180 - (value - low) / span * 160:.2f}"
        for index, value in enumerate(values)
    )
    return f'<figure><figcaption>{escape(label)}</figcaption><svg viewBox="0 0 720 200" role="img" aria-label="{escape(label, quote=True)}"><polyline fill="none" stroke="{color}" stroke-width="2" points="{points}"/></svg></figure>'


def render(store: AlphaStore, study_id: int, study_override: dict | None = None) -> None:
    study = study_override or store.get("alpha_studies", study_id)
    result = study["result"]
    sections = [
        "<h1>" + escape(study["name"]) + "</h1>",
        "<p>" + escape(config()["ui"]["disclaimer"]) + "</p>",
        "<p>状态：" + escape(study["status"]) + " · 研究编号：" + str(study_id) + "</p>",
    ]
    if result.get("failures"):
        sections.append("<p><strong>模型错误决定已拒绝配置资金。完成处理不表示该模型结论通过验证。</strong></p>")
    if study["mode"] == "alpha":
        summaries = result.get("validation") or []
        if summaries:
            sections.append(
                "<h2>冻结验证与全部候选</h2><p>调整后p值按预登记家族和两个主检验计算。失败候选及未完成槽位不会从家族分母移除；通过仅表示研究门槛。</p>"
            )
            sections.append(
                _table(
                    summaries,
                    [
                        "candidate_id",
                        "rank_ic",
                        "coverage",
                        "adjusted_ic_p",
                        "adjusted_net_p",
                        "net_excess_return",
                        "passed",
                        "error",
                    ],
                )
            )
        final = result.get("final") or {}
        if final:
            sections.append(
                "<h2>一次性最终留出</h2>"
                + _table([final], ["candidate_id", "rank_ic", "net_excess_return", "passed", "error"])
            )
        for row in summaries:
            if not row.get("artifact"):
                continue
            detail = json.loads(store.artifact(study_id, row["artifact"]).read_text(encoding="utf-8"))
            equity = detail["backtest"]["strategy"]["curve"]["equity"]
            sections.append(
                _curve(
                    equity,
                    "#4461d7",
                    f"候选{row['candidate_id']}费用后净值；横轴为交易顺序，纵轴独立缩放，不用于跨图比较",
                )
            )
    elif study["mode"] == "theme":
        sections.extend(
            [
                "<h2>主题关联，非收益预测</h2><p>引用来自截止时点可得资料；关键词精炼不直接产生买卖信号。公司关联还需人工核对。</p>",
                _table(result.get("associations") or [], ["symbol", "document_id", "quote", "relation"]),
            ]
        )
    else:
        sections.extend(
            [
                "<h2>独立体制配置实验</h2><p>日期匿名和数据滞后不能消除模型历史记忆。权重来自冻结映射，未知体制保留现金；下表不是八个独立专家投票。</p>",
                _table(
                    result.get("decisions") or [],
                    ["configuration", "cutoff", "regime", "confidence", "weights", "validation_mode", "status"],
                ),
            ]
        )
    sections.append(
        "<details><summary>完整可追溯结果与门槛</summary><pre>"
        + escape(json.dumps(result, ensure_ascii=False, indent=2))
        + "</pre></details>"
    )
    html = (
        '<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Alpha研究报告</title><style>body{font:15px/1.65 system-ui,sans-serif;color:#23324c;background:#f3f6fc;max-width:1280px;margin:auto;padding:28px}table{border-collapse:collapse;background:white;width:100%;display:block;overflow:auto}td,th{padding:10px;border:1px solid #dce4f0;text-align:left}tr:nth-child(even){background:#eef3fc}h1,h2{color:#3053b1}pre{white-space:pre-wrap;overflow-wrap:anywhere}figure{background:white;border-radius:16px;padding:18px}svg{width:100%;max-height:240px}</style><body>'
        + "".join(sections)
        + "</body></html>"
    )
    store.write(study_id, "report.html", html)
    store.write(
        study_id,
        "report.md",
        "# "
        + study["name"]
        + "\n\n"
        + config()["ui"]["disclaimer"]
        + "\n\n```json\n"
        + json.dumps(result, ensure_ascii=False, indent=2)
        + "\n```\n",
    )
