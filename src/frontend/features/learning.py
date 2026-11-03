"""Lightweight, ordered quantitative curriculum; no trading or model side effects."""

from functools import lru_cache

import yaml

import gradio as gr
from src.core.config import PROJECT_ROOT, get_settings
from src.help_docs.links import handbook_markdown


@lru_cache(maxsize=1)
def curriculum():
    config = yaml.safe_load((PROJECT_ROOT / "egs/quant_curriculum.yaml").read_text(encoding="utf-8"))
    root = (PROJECT_ROOT / config["root"]).resolve()
    if not root.is_relative_to((PROJECT_ROOT / "docs/principles").resolve()):
        raise ValueError("课程目录必须位于原理文档内")
    chapters = []
    for item in config["chapters"]:
        path = (root / item["file"]).resolve()
        if not path.is_relative_to(root) or path.suffix != ".md":
            raise ValueError("课程章节路径无效")
        chapters.append({**item, "path": path, "content": path.read_text(encoding="utf-8")})
    return config["title"], chapters


def chapter_values(chapter_id):
    _, chapters = curriculum()
    index = next((i for i, item in enumerate(chapters) if item["id"] == chapter_id), None)
    if index is None:
        raise ValueError("课程章节不存在")
    item = chapters[index]
    return (
        handbook_markdown(item["content"], item["path"], get_settings()),
        f"{index + 1} / {len(chapters)} · {item['title']}",
        gr.update(interactive=index > 0),
        gr.update(interactive=index < len(chapters) - 1),
    )


def adjacent_chapter(chapter_id, direction):
    _, chapters = curriculum()
    index = next(i for i, item in enumerate(chapters) if item["id"] == chapter_id)
    return chapters[min(max(index + direction, 0), len(chapters) - 1)]["id"]


def render_learning() -> None:
    title, chapters = curriculum()
    initial = chapters[0]["id"]
    with gr.Tab("学习空间"):
        with gr.Tabs(elem_classes=["module-tabs"]):
            with gr.Tab(title):
                gr.Markdown(
                    "## 量化学习空间\n\n从概念到可核对的研究。课程无需模型或行情调用；教学数字均为明确标注的合成示例。"
                )
                with gr.Row():
                    with gr.Column(scale=1, min_width=240):
                        chapter = gr.Radio(
                            [(item["title"], item["id"]) for item in chapters],
                            value=initial,
                            label="课程章节",
                            elem_id="quant-course-chapters",
                        )
                    with gr.Column(scale=3, min_width=420):
                        progress = gr.Markdown(chapter_values(initial)[1])
                        with gr.Row():
                            previous = gr.Button("上一章", interactive=False)
                            following = gr.Button("下一章")
                        body = gr.Markdown(chapter_values(initial)[0], elem_id="quant-course-content")
                chapter.change(
                    chapter_values, inputs=chapter, outputs=[body, progress, previous, following], queue=False
                )
                previous.click(lambda key: adjacent_chapter(key, -1), inputs=chapter, outputs=chapter, queue=False)
                following.click(lambda key: adjacent_chapter(key, 1), inputs=chapter, outputs=chapter, queue=False)
