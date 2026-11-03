"""Small AI workspace actions; full configuration has one canonical editor."""

import gradio as gr

from ..common.callbacks import safe
from ..common.components import table
from ..common.navigation import workspace_link


def render_automation_quick(service):
    gr.HTML(
        "<section class='ai-shell-page-head'><div><strong>自动化任务</strong>"
        + workspace_link("新增或编辑定时任务", "admin", "jobs")
        + "</div></section>"
    )
    with gr.Row():
        refresh = gr.Button("刷新任务")
        identifier = gr.Number(label="任务 ID", precision=0)
        buttons = [
            (gr.Button(label), action)
            for label, action in [("触发任务", "trigger"), ("开启任务", "enable"), ("关闭任务", "disable")]
        ]
        history_refresh = gr.Button("查看历史")
    status = gr.Markdown(elem_classes=["status-strip"])
    listing = table("定时任务", 300)
    history = table("执行历史", 220)
    refresh.click(safe(service.jobs), outputs=listing, queue=False)
    history_refresh.click(safe(service.job_histories), inputs=identifier, outputs=history, queue=False)
    for button, action in buttons:
        button.click(
            safe(lambda value, selected=action: service.job_action(value, selected)),
            inputs=identifier,
            outputs=[status, listing, history],
        )
    return listing


def render_mcp_quick(service):
    gr.HTML(
        "<section class='ai-shell-page-head'><div><strong>MCP 服务</strong>"
        + workspace_link("新增或编辑MCP服务", "admin", "settings", tab="MCP 服务")
        + "</div></section>"
    )
    with gr.Row():
        refresh = gr.Button("刷新 MCP")
        identifier = gr.Number(label="MCP 服务 ID", precision=0)
        buttons = [
            (gr.Button(label), action)
            for label, action in [("测试连接", "test"), ("启用", "enable"), ("停用", "disable")]
        ]
    with gr.Row():
        tool = gr.Textbox(label="工具名")
        arguments = gr.Code(value="{}", language="json", label="工具参数")
        call = gr.Button("调用工具", variant="primary")
    status = gr.Markdown(elem_classes=["status-strip"])
    listing = table("MCP 服务", 300)
    refresh.click(safe(service.mcp_servers), outputs=listing, queue=False)
    for button, action in buttons:
        button.click(
            safe(lambda value, selected=action: service.mcp_action(value, selected)),
            inputs=identifier,
            outputs=[status, listing],
        )
    call.click(safe(service.mcp_call), inputs=[identifier, tool, arguments], outputs=[status, listing])
    return listing


def render_skill_quick(service):
    gr.HTML(
        "<section class='ai-shell-page-head'><div><strong>Skill 能力</strong>"
        + workspace_link("登记或配置Skill", "admin", "settings", tab="Skill 配置")
        + "</div></section>"
    )
    with gr.Row():
        refresh = gr.Button("刷新 Skill")
        identifier = gr.Number(label="Skill ID", precision=0)
        buttons = [
            (gr.Button(label), action) for label, action in [("运行", "run"), ("启用", "enable"), ("停用", "disable")]
        ]
    arguments = gr.Code(value="{}", language="json", label="本次Skill参数")
    status = gr.Markdown(elem_classes=["status-strip"])
    listing = table("Skill 列表", 300)
    refresh.click(safe(service.skills), outputs=listing, queue=False)
    for button, action in buttons:
        button.click(
            safe(lambda value, params, selected=action: service.skill_action(value, selected, params)),
            inputs=[identifier, arguments],
            outputs=[status, listing],
        )
    return listing


def render_knowledge_quick(service):
    gr.HTML(
        "<section class='ai-shell-page-head'><div><strong>知识与资料</strong>"
        + workspace_link("打开带引用的AI问答", "knowledge", "qa")
        + " · "
        + workspace_link("上传文档、笔记与分类管理", "knowledge", "library")
        + "</div></section>"
    )
    refresh = gr.Button("刷新知识资料")
    categories = table("知识分类", 180)
    documents = table("最近文档", 280)
    refresh.click(safe(service.kb_categories), outputs=categories, queue=False)
    refresh.click(safe(lambda: service.kb_search("", None, "all")), outputs=documents, queue=False)
    return categories, documents
