"""PDF 研报文本解析器（三层架构）

解析优先级：
1. MarkItDown（微软，LLM 友好，表格/结构保留好）— 主路径
2. pdfplumber（中文支持好）— 兜底 1
3. PyPDF2（最简纯文本）— 兜底 2

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

# 解析器优先级（用于结果中的 parser_used 字段标识）
PARSER_MARKITDOWN = "markitdown"
PARSER_PDFPLUMBER = "pdfplumber"
PARSER_PYPDF2 = "pypdf2"


@dataclass
class ParsedReport:
    """解析后的研报文本结构"""
    file_path: str
    full_text: str
    sections: dict  # {section_key: text}
    page_count: int
    char_count: int
    parse_success: bool
    parser_used: str = ""  # 实际使用的解析器
    error: str = ""

    def get_section(self, key: str) -> str:
        return self.sections.get(key, "")

    def excerpt(self, max_chars: int = 2000) -> str:
        """返回前 N 字摘要"""
        return self.full_text[:max_chars]


def _try_markitdown(file_path: Path) -> tuple[str, int]:
    """使用 MarkItDown 抽取文本（主路径）

    MarkItDown 输出 LLM 友好的 Markdown：
    - 保留标题层级、列表、表格结构
    - 财务预测表格转为 Markdown 表格
    - 中文支持良好（基于 pdfminer.six）
    """
    from markitdown import MarkItDown
    md = MarkItDown()
    result = md.convert(str(file_path))
    text = result.text_content or ""
    # MarkItDown 不直接返回页数，用 attachPages 元信息或文本规模估算
    pages = _estimate_pages(text)
    return text, pages


def _try_pdfplumber(file_path: Path) -> tuple[str, int]:
    """使用 pdfplumber 抽取文本（兜底 1）"""
    import pdfplumber
    texts, pages = [], 0
    with pdfplumber.open(str(file_path)) as pdf:
        pages = len(pdf.pages)
        for page in pdf.pages:
            t = page.extract_text() or ""
            texts.append(t)
    return "\n".join(texts), pages


def _try_pypdf2(file_path: Path) -> tuple[str, int]:
    """使用 PyPDF2 兜底抽取（兜底 2）"""
    from PyPDF2 import PdfReader
    reader = PdfReader(str(file_path))
    texts = []
    for page in reader.pages:
        texts.append(page.extract_text() or "")
    return "\n".join(texts), len(reader.pages)


def _estimate_pages(text: str) -> int:
    """无页数信息时，按文本规模粗估页数（每页约 1500 字符）"""
    if not text:
        return 0
    return max(1, len(text) // 1500)


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


def parse_pdf(file_path: str | Path, prefer_parser: str = "") -> ParsedReport:
    """解析单个 PDF 文件（三层兜底）

    解析优先级：MarkItDown → pdfplumber → PyPDF2
    任一解析器成功即返回，不再尝试下一层。

    :param file_path: PDF 本地路径
    :param prefer_parser: 强制指定解析器（markitdown/pdfplumber/pypdf2），空则按默认优先级
    :return: ParsedReport
    """
    file_path = Path(file_path)
    if not file_path.exists():
        return ParsedReport(
            file_path=str(file_path), full_text="", sections={}, page_count=0,
            char_count=0, parse_success=False, error="文件不存在"
        )

    # 解析器链：默认顺序或用户指定优先
    default_chain = [
        (PARSER_MARKITDOWN, _try_markitdown),
        (PARSER_PDFPLUMBER, _try_pdfplumber),
        (PARSER_PYPDF2, _try_pypdf2),
    ]
    if prefer_parser:
        # 指定优先：把 prefer_parser 提到链首
        chain = sorted(default_chain, key=lambda x: 0 if x[0] == prefer_parser else 1)
    else:
        chain = default_chain

    full_text, pages, error, used = "", 0, "", ""
    for name, fn in chain:
        try:
            full_text, pages = fn(file_path)
            if full_text and full_text.strip():
                used = name
                LOGGER.debug("使用 %s 解析成功 [%s]", name, file_path.name)
                break
        except ImportError:
            LOGGER.debug("%s 未安装，跳过", name)
            continue
        except Exception as e:
            LOGGER.warning("%s 解析失败 [%s]: %s", name, file_path.name, e)
            error = f"{name}: {e}"

    full_text = full_text.strip()
    if not full_text:
        return ParsedReport(
            file_path=str(file_path), full_text="", sections={}, page_count=0,
            char_count=0, parse_success=False, parser_used="",
            error=error or "所有解析器均未产出文本",
        )

    sections = extract_sections(full_text)
    return ParsedReport(
        file_path=str(file_path),
        full_text=full_text,
        sections=sections,
        page_count=pages,
        char_count=len(full_text),
        parse_success=True,
        parser_used=used,
        error="",
    )


def parse_batch(file_paths: list[str | Path], prefer_parser: str = "") -> list[ParsedReport]:
    """批量解析"""
    return [parse_pdf(p, prefer_parser=prefer_parser) for p in file_paths]


# CLI 入口：用于单独测试解析效果
def main():
    import argparse
    import json

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="PDF 研报解析器（三层架构）")
    parser.add_argument("pdf", help="PDF 文件路径")
    parser.add_argument("--parser", default="", choices=["", PARSER_MARKITDOWN, PARSER_PDFPLUMBER, PARSER_PYPDF2],
                        help="指定解析器（空=自动选择最优）")
    parser.add_argument("--excerpt", type=int, default=0, help="仅打印前 N 字（0=全文）")
    parser.add_argument("--sections", action="store_true", help="打印识别到的段落")
    args = parser.parse_args()

    result = parse_pdf(args.pdf, prefer_parser=args.parser)
    print(f"解析器: {result.parser_used}")
    print(f"成功: {result.parse_success} | 字符数: {result.char_count} | 估算页数: {result.page_count}")
    if result.error:
        print(f"错误: {result.error}")
    print("---")
    if args.sections:
        print("识别段落:")
        print(json.dumps(result.sections, ensure_ascii=False, indent=2))
        print("---")
    text = result.excerpt(args.excerpt) if args.excerpt else result.full_text
    print(text)


if __name__ == "__main__":
    main()
