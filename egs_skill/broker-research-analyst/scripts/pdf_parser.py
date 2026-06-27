"""PDF 研报文本解析器

优先使用 pdfplumber（中文支持好），失败回退 PyPDF2。
抽取正文文本，并尝试识别关键段落（投资要点/盈利预测/风险提示）。
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

LOGGER = logging.getLogger(__name__)

# 关键段落标题正则（容错：中英文、空格、标点）
SECTION_PATTERNS = {
    "investment_points": r"(投资要点|核心观点|投资建议|要点总结)",
    "earnings_forecast": r"(盈利预测|业绩预测|财务预测)",
    "risk_warning": r"(风险提示|风险因素|风险揭示|风险分析)",
    "valuation": r"(估值|目标价|估值分析)",
}


@dataclass
class ParsedReport:
    """解析后的研报文本结构"""
    file_path: str
    full_text: str
    sections: dict  # {section_key: text}
    page_count: int
    char_count: int
    parse_success: bool
    error: str = ""

    def get_section(self, key: str) -> str:
        return self.sections.get(key, "")

    def excerpt(self, max_chars: int = 2000) -> str:
        """返回前 N 字摘要"""
        return self.full_text[:max_chars]


def _try_pdfplumber(file_path: Path) -> tuple[str, int]:
    """使用 pdfplumber 抽取文本"""
    import pdfplumber
    texts, pages = [], 0
    with pdfplumber.open(str(file_path)) as pdf:
        pages = len(pdf.pages)
        for page in pdf.pages:
            t = page.extract_text() or ""
            texts.append(t)
    return "\n".join(texts), pages


def _try_pypdf2(file_path: Path) -> tuple[str, int]:
    """使用 PyPDF2 兜底抽取"""
    from PyPDF2 import PdfReader
    reader = PdfReader(str(file_path))
    texts = []
    for page in reader.pages:
        texts.append(page.extract_text() or "")
    return "\n".join(texts), len(reader.pages)


def extract_sections(full_text: str) -> dict:
    """从全文中识别关键段落

    策略：用正则定位段落标题，截取到下一个标题或文末
    """
    sections = {}
    # 合并所有标题正则，统一匹配
    all_titles = "|".join(f"(?:{p})" for p in SECTION_PATTERNS.values())
    matches = list(re.finditer(all_titles, full_text))
    if not matches:
        return sections

    # 反向映射：通过匹配到的文本找到 section_key
    title_to_key = {}
    for key, pattern in SECTION_PATTERNS.items():
        for m in re.finditer(pattern, full_text):
            title_to_key[m.group()] = key

    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(full_text)
        chunk = full_text[start:end].strip()
        if not chunk:
            continue
        key = title_to_key.get(m.group())
        if key and key not in sections:
            sections[key] = chunk[:3000]  # 单段落上限 3000 字
    return sections


def parse_pdf(file_path: str | Path) -> ParsedReport:
    """解析单个 PDF 文件

    :param file_path: PDF 本地路径
    :return: ParsedReport
    """
    file_path = Path(file_path)
    if not file_path.exists():
        return ParsedReport(
            file_path=str(file_path), full_text="", sections={}, page_count=0,
            char_count=0, parse_success=False, error="文件不存在"
        )

    full_text, pages, error = "", 0, ""
    # 优先 pdfplumber
    try:
        full_text, pages = _try_pdfplumber(file_path)
    except Exception as e:
        LOGGER.warning("pdfplumber 解析失败，回退 PyPDF2: %s", e)
        try:
            full_text, pages = _try_pypdf2(file_path)
        except Exception as e2:
            error = f"pdfplumber: {e} | PyPDF2: {e2}"
            LOGGER.error("PDF 解析全部失败 [%s]: %s", file_path.name, error)

    full_text = full_text.strip()
    sections = extract_sections(full_text) if full_text else {}
    success = bool(full_text)

    return ParsedReport(
        file_path=str(file_path),
        full_text=full_text,
        sections=sections,
        page_count=pages,
        char_count=len(full_text),
        parse_success=success,
        error=error,
    )


def parse_batch(file_paths: list[str | Path]) -> list[ParsedReport]:
    """批量解析"""
    return [parse_pdf(p) for p in file_paths]
