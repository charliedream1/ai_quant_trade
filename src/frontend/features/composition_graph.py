"""Graph component binding using supported Gradio value and event contracts."""

import gradio as gr
from src.frontend.components.strategy_graph import StrategyGraph, supported
from src.frontend.service.graph_documents import document_payload, graph_config


def render_graph(service, definition, version_id, pipeline_id, run_id, template_id=""):
    cfg = graph_config()
    if not supported():
        gr.Markdown(cfg["ui"]["min_version"])
        return
    initial = document_payload(definition.value)
    initial["layout_origin"] = template_id
    graph = StrategyGraph(value=initial, elem_id="strategy-graph-editor")
    status = gr.Markdown(elem_classes=["status-strip"])
    refresh = gr.Button(cfg["ui"]["select_result"])
    timer = gr.Timer(value=cfg["limits"]["evidence_poll_seconds"], active=False)
    run_id.change(lambda value: gr.update(active=bool(value)), inputs=run_id, outputs=timer, queue=False)
    timer.tick(service.pipeline_graph_poll, inputs=[run_id, graph], outputs=[graph, timer], queue=False)
    definition.input(
        service.pipeline_graph_sync,
        inputs=[definition, graph, pipeline_id, run_id],
        outputs=graph,
        queue=False,
        trigger_mode="always_last",
    )
    pipeline_id.change(
        service.pipeline_graph_binding, inputs=[definition, graph, pipeline_id], outputs=graph, queue=False
    )
    # Initialize the session's layout identity only after this lazy component is mounted.
    graph.load(service.pipeline_graph_sync, inputs=[definition, graph, pipeline_id, run_id], outputs=graph, queue=False)
    graph.submit(
        service.pipeline_graph_apply,
        inputs=[graph, definition],
        outputs=[definition, status, version_id, graph],
        queue=False,
    )
    graph.input(service.pipeline_graph_layout, inputs=graph, outputs=[graph, status], queue=False)
    refresh.click(service.pipeline_graph_results, inputs=[run_id, graph], outputs=graph, queue=False)
    return graph
