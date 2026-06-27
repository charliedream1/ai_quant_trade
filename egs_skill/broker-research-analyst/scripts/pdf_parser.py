"""PDF 研报文本解析器（三层架构 + 图片提取）

解析优先级：
1. MarkItDown（微软，LLM 友好，表格/结构保留好）— 主路径
2. pdfplumber（中文支持好）— 兜底 1
3. PyPDF2（最简纯文本）— 兜底 2

图片提取：使用 PyMuPDF（fitz）独立提取图片本体并保存到磁盘，
与文本解析解耦，无论文本用哪个解析器都能获取图片。

抽取正文文本，并尝试识别关键段落（投资要点/盈利预测/风险提示）。
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
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

# 图片提取相关常量
IMAGE_PARSER_PYMUPDF = "pymupdf"
IMAGE_MIN_WIDTH = 80   # 过滤小图标（如页眉logo），宽度 < 80px 不保存
IMAGE_MIN_HEIGHT = 80


@dataclass
class ExtractedImage:
    """从 PDF 提取的图片信息"""
    page_no: int           # 来源页码（1-based）
    img_index: int         # 该页内序号
    save_path: str         # 本地保存路径
    width: int
    height: int
    ext: str               # 图片格式（jpeg/png/...）
    size_bytes: int


@dataclass
class ParsedReport:
    """解析后的研报文本结构"""
    file_path: str
    full_text: str
    sections: dict  # {section_key: text}
    page_count: int
    char_count: int
    parse_success: bool
    parser_used: str = ""  # 实际使用的文本解析器
    images: list = field(default_factory=list)  # list[ExtractedImage]
    image_count: int = 0
    image_dir: str = ""    # 图片保存目录
    error: str = ""

    def get_section(self, key: str) -> str:
        return self.sections.get(key, "")

    def excerpt(self, max_chars: int = 2000) -> str:
        """返回前 N 字摘要"""
        return self.full_text[:max_chars]

    def image_paths(self) -> list[str]:
        """返回所有图片本地路径，便于后续 LLM 多模态分析"""
        return [img.save_path for img in self.images]


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


def extract_images(
    file_path: str | Path,
    output_dir: str | Path,
    min_width: int = IMAGE_MIN_WIDTH,
    min_height: int = IMAGE_MIN_HEIGHT,
) -> list[ExtractedImage]:
    """从 PDF 提取图片并保存到磁盘

    使用 PyMuPDF（fitz）独立提取，与文本解析解耦。
    研报中的图表（营收走势、毛利率趋势、批发价走势等）对分析有重要价值。

    :param file_path: PDF 路径
    :param output_dir: 图片保存目录
    :param min_width: 最小宽度阈值，过滤小图标（页眉logo等）
    :param min_height: 最小高度阈值
    :return: ExtractedImage 列表
    """
    try:
        import fitz  # PyMuPDF
    except ImportError:
        LOGGER.warning("PyMuPDF 未安装，跳过图片提取。安装：pip install PyMuPDF")
        return []

    file_path = Path(file_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 图片保存子目录命名：{pdf名}_images/
    pdf_stem = file_path.stem
    img_subdir = output_dir / f"{pdf_stem}_images"
    img_subdir.mkdir(parents=True, exist_ok=True)

    images: list[ExtractedImage] = []
    try:
        doc = fitz.open(str(file_path))
    except Exception as e:
        LOGGER.warning("PyMuPDF 打开 PDF 失败 [%s]: %s", file_path.name, e)
        return []

    seen_xrefs = set()  # 去重：同一 xref 可能被多页引用
    for pno in range(len(doc)):
        page = doc[pno]
        for img_idx, img_info in enumerate(page.get_images(full=True)):
            xref = img_info[0]
            if xref in seen_xrefs:
                continue
            seen_xrefs.add(xref)

            try:
                base = doc.extract_image(xref)
            except Exception as e:
                LOGGER.debug("提取图片失败 p%d xref=%d: %s", pno + 1, xref, e)
                continue

            w, h = base.get("width", 0), base.get("height", 0)
            # 过滤小图标（页眉 logo、装饰元素等）
            if w < min_width or h < min_height:
                continue

            ext = base.get("ext", "png")
            img_bytes = base.get("image")
            if not img_bytes:
                continue

            fname = f"p{pno + 1}_img{img_idx + 1}.{ext}"
            fpath = img_subdir / fname
            fpath.write_bytes(img_bytes)

            images.append(ExtractedImage(
                page_no=pno + 1,
                img_index=img_idx + 1,
                save_path=str(fpath),
                width=w,
                height=h,
                ext=ext,
                size_bytes=len(img_bytes),
            ))

    doc.close()
    LOGGER.info("从 %s 提取图片 %d 张（保存至 %s）", file_path.name, len(images), img_subdir)
    return images


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


def parse_pdf(
    file_path: str | Path,
    prefer_parser: str = "",
    extract_imgs: bool = True,
    image_output_dir: str | Path = "./cache/images",
) -> ParsedReport:
    """解析单个 PDF 文件（三层兜底 + 图片提取）

    解析优先级：MarkItDown → pdfplumber → PyPDF2
    任一解析器成功即返回，不再尝试下一层。
    图片提取独立于文本解析，使用 PyMuPDF，无论文本走哪条路径都能获取图片。

    :param file_path: PDF 本地路径
    :param prefer_parser: 强制指定文本解析器（markitdown/pdfplumber/pypdf2），空则按默认优先级
    :param extract_imgs: 是否提取图片（默认 True）
    :param image_output_dir: 图片保存目录
    :return: ParsedReport（含 images 字段）
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

    # 图片提取（独立于文本解析，PyMuPDF）
    images: list[ExtractedImage] = []
    if extract_imgs:
        try:
            images = extract_images(file_path, image_output_dir)
        except Exception as e:
            LOGGER.warning("图片提取失败 [%s]: %s", file_path.name, e)

    if not full_text:
        return ParsedReport(
            file_path=str(file_path), full_text="", sections={}, page_count=0,
            char_count=0, parse_success=False, parser_used="",
            images=images, image_count=len(images),
            image_dir=str(Path(image_output_dir) / f"{file_path.stem}_images"),
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
        images=images,
        image_count=len(images),
        image_dir=str(Path(image_output_dir) / f"{file_path.stem}_images") if images else "",
        error="",
    )


def parse_batch(
    file_paths: list[str | Path],
    prefer_parser: str = "",
    extract_imgs: bool = True,
    image_output_dir: str | Path = "./cache/images",
) -> list[ParsedReport]:
    """批量解析"""
    return [
        parse_pdf(p, prefer_parser=prefer_parser,
                  extract_imgs=extract_imgs,
                  image_output_dir=image_output_dir)
        for p in file_paths
    ]


# CLI 入口：用于单独测试解析效果
def main():
    import argparse
    import json

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="PDF 研报解析器（三层架构 + 图片提取）")
    parser.add_argument("pdf", help="PDF 文件路径")
    parser.add_argument("--parser", default="", choices=["", PARSER_MARKITDOWN, PARSER_PDFPLUMBER, PARSER_PYPDF2],
                        help="指定文本解析器（空=自动选择最优）")
    parser.add_argument("--excerpt", type=int, default=0, help="仅打印前 N 字（0=全文）")
    parser.add_argument("--sections", action="store_true", help="打印识别到的段落")
    parser.add_argument("--no-images", action="store_true", help="跳过图片提取")
    parser.add_argument("--image-dir", default="./cache/images", help="图片保存目录")
    args = parser.parse_args()

    result = parse_pdf(
        args.pdf,
        prefer_parser=args.parser,
        extract_imgs=not args.no_images,
        image_output_dir=args.image_dir,
    )
    print(f"文本解析器: {result.parser_used}")
    print(f"成功: {result.parse_success} | 字符数: {result.char_count} | 估算页数: {result.page_count}")
    print(f"图片数: {result.image_count} | 图片目录: {result.image_dir or '(无)'}")
    if result.error:
        print(f"错误: {result.error}")
    print("---")
    if args.sections:
        print("识别段落:")
        print(json.dumps(result.sections, ensure_ascii=False, indent=2))
        print("---")
    if result.images:
        print("图片清单:")
        for img in result.images:
            print(f"  p{img.page_no} img{img.img_index}: {img.width}x{img.height} "
                  f"{img.ext} {img.size_bytes//1024}KB -> {img.save_path}")
        print("---")
    text = result.excerpt(args.excerpt) if args.excerpt else result.full_text
    print(text)


if __name__ == "__main__":
    main()
