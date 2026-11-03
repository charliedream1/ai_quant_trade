"""Build explicit sample documents with real Office formats for UI and conversion checks."""

import argparse
import subprocess
from pathlib import Path
from uuid import uuid4

import yaml
from docx import Document
from docx.oxml.ns import qn
from docx.shared import Inches
from loguru import logger
from openpyxl import Workbook
from openpyxl.chart import BarChart, Reference
from PIL import Image, ImageDraw

from src.core.config import PROJECT_ROOT
from src.documents.conversion import _profile_uri, executable

FIXTURE = yaml.safe_load((PROJECT_ROOT / "tests/fixtures/file_preview.yaml").read_text(encoding="utf-8"))


def export(source: Path, target: str, output: Path) -> Path:
    profile = output / ("fixture-profile-" + uuid4().hex[:8])
    profile.mkdir()
    result = subprocess.run(
        [
            executable(),
            "-env:UserInstallation=" + _profile_uri(profile),
            "--headless",
            "--convert-to",
            target,
            "--outdir",
            str(output),
            str(source),
        ],
        capture_output=True,
        timeout=FIXTURE["timeout_seconds"],
    )
    expected = output / (source.stem + "." + target)
    assert result.returncode == 0 and expected.is_file(), (result.stdout, result.stderr)
    return expected


def build(output: Path, legacy: bool = True) -> dict[str, Path]:
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    picture = output / "illustration.png"
    image = Image.new("RGB", tuple(FIXTURE["image_size"]), "white")
    drawing = ImageDraw.Draw(image)
    for index, row in enumerate(FIXTURE["rows"]):
        drawing.rectangle((30 + index * 140, 210 - row[1], 110 + index * 140, 210), fill=(50, 100 + index * 30, 200))
    image.save(picture)
    word = output / "中文研报样本.docx"
    document = Document()
    document.styles["Normal"].font.name = "Microsoft YaHei"
    document.styles["Normal"]._element.rPr.rFonts.set(qn("w:eastAsia"), "Microsoft YaHei")
    document.add_heading(FIXTURE["title"], 0)
    document.add_paragraph(FIXTURE["disclaimer"])
    document.add_paragraph(FIXTURE["body"])
    table = document.add_table(rows=1, cols=len(FIXTURE["headers"]))
    table.style = "Table Grid"
    for cell, value in zip(table.rows[0].cells, FIXTURE["headers"], strict=True):
        cell.text = str(value)
    for row in FIXTURE["rows"]:
        for cell, value in zip(table.add_row().cells, row, strict=True):
            cell.text = str(value)
    document.add_picture(str(picture), width=Inches(4))
    document.add_page_break()
    document.add_heading(FIXTURE["second_page"], 1)
    document.add_paragraph(FIXTURE["body"])
    document.save(word)
    spreadsheet = output / "组合配置样本.xlsx"
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "阅读样本"
    sheet.append([FIXTURE["title"]])
    sheet.append(FIXTURE["headers"])
    for row in FIXTURE["rows"]:
        sheet.append(row)
    sheet.column_dimensions["A"].width = 22
    sheet.column_dimensions["C"].width = 35
    chart = BarChart()
    chart.add_data(Reference(sheet, min_col=2, min_row=2, max_row=5), titles_from_data=True)
    chart.set_categories(Reference(sheet, min_col=1, min_row=3, max_row=5))
    sheet.add_chart(chart, "A8")
    workbook.save(spreadsheet)
    slide = export(PROJECT_ROOT / "tests/fixtures/file_preview/presentation.fodp", "pptx", output)
    markdown = output / "阅读笔记.md"
    markdown.write_text(FIXTURE["markdown"], encoding="utf-8")
    html = output / "sample.html"
    html.write_text("<!doctype html><meta charset='utf-8'><h1>HTML阅读样本</h1><p>仅为功能验收。</p>", encoding="utf-8")
    result = {"docx": word, "xlsx": spreadsheet, "pptx": slide, "markdown": markdown, "html": html, "image": picture}
    if legacy:
        for name, extension in (
            ("docx", "doc"),
            ("xlsx", "xls"),
            ("pptx", "ppt"),
            ("docx", "odt"),
            ("xlsx", "ods"),
            ("pptx", "odp"),
        ):
            result[extension] = export(result[name], extension, output)
    logger.info("Real Office fixture files ready: {}", list(result))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    build(parser.parse_args().output)
