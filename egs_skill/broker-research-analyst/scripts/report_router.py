"""路由调度器

串联整个研报分析流程：
  获取研报 → 质量门禁 → PDF下载(可选) → 解析(可选) → 生成报告

提供 CLI 入口，可独立运行产出 Markdown 报告。
LLM 多专家分析环节由 TRAE Skill 编排（不在本脚本内），本脚本负责数据准备与报告骨架。
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import asdict
from pathlib import Path

# 保证 scripts 目录内模块互导
sys.path.insert(0, str(Path(__file__).parent))

from eastmoney_adapter import (
    EastmoneyReportAdapter,
    ReportMeta,
    REPORT_TYPE_STOCK,
    REPORT_TYPE_INDUSTRY,
    REPORT_TYPE_STRATEGY,
)
from pdf_downloader import PdfDownloader
from pdf_parser import parse_pdf
from report_quality_gate import run_quality_gate
from generate_report import generate_report, save_report

LOGGER = logging.getLogger(__name__)


def analyze_stock(
    stock_code: str,
    stock_name: str = "",
    days: int = 90,
    download_pdf: bool = False,
    output: str = "",
    require_whitelist: bool = True,
) -> dict:
    """分析个股研报

    :return: {"reports": [...], "quality": {...}, "report_path": "..."}
    """
    adapter = EastmoneyReportAdapter()
    LOGGER.info("开始获取 %s 的研报（近 %d 天）", stock_code, days)
    reports = adapter.fetch_stock_reports(stock_code, days=days, page_size=50)

    if not reports:
        LOGGER.warning("未获取到任何研报")
        return {"reports": [], "quality": {}, "report_path": ""}

    # 质量门禁
    quality = run_quality_gate(
        reports,
        expire_days=90,
        require_whitelist=require_whitelist,
        min_count=3,
    )
    passed = quality.passed_reports

    # 可选：下载并解析 PDF
    parsed_texts = {}
    if download_pdf and passed:
        downloader = PdfDownloader(cache_dir="./cache", expire_days=30)
        result = downloader.download_batch(passed)
        for meta, path in zip(passed, result["success"] + result["cached"]):
            try:
                parsed = parse_pdf(path)
                if parsed.parse_success:
                    parsed_texts[meta.info_code] = parsed.excerpt(3000)
            except Exception as e:
                LOGGER.warning("解析 PDF 失败 %s: %s", meta.info_code, e)

    # 生成报告
    subject = f"{stock_name}（{stock_code}）" if stock_name else stock_code
    md = generate_report(subject, passed, quality, llm_analysis={
        "pdf_excerpts": parsed_texts,
    })
    report_path = ""
    if output:
        report_path = save_report(md, output)
    else:
        print(md)

    return {
        "reports": [r.to_dict() for r in passed],
        "quality": quality.to_dict(),
        "report_path": report_path,
        "parsed_count": len(parsed_texts),
    }


def analyze_industry(
    industry_code: str,
    industry_name: str = "",
    days: int = 90,
    output: str = "",
) -> dict:
    """分析行业研报"""
    adapter = EastmoneyReportAdapter()
    reports = adapter.fetch_industry_reports(industry_code, days=days, page_size=50)
    if not reports:
        return {"reports": [], "quality": {}, "report_path": ""}

    quality = run_quality_gate(reports, expire_days=90, require_whitelist=False, min_count=1)
    passed = quality.passed_reports

    subject = f"{industry_name}（行业代码 {industry_code}）" if industry_name else f"行业 {industry_code}"
    md = generate_report(subject, passed, quality)
    if output:
        save_report(md, output)
    else:
        print(md)

    return {
        "reports": [r.to_dict() for r in passed],
        "quality": quality.to_dict(),
    }


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="券商研报分析 Skill - 路由调度器")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_stock = sub.add_parser("stock", help="分析个股研报")
    p_stock.add_argument("--code", required=True, help="股票代码，如 600519")
    p_stock.add_argument("--name", default="", help="股票名称，如 贵州茅台")
    p_stock.add_argument("--days", type=int, default=90, help="回溯天数")
    p_stock.add_argument("--download", action="store_true", help="是否下载 PDF 并解析")
    p_stock.add_argument("--output", default="", help="输出 Markdown 路径")
    p_stock.add_argument("--no-whitelist", action="store_true", help="不要求机构白名单")

    p_ind = sub.add_parser("industry", help="分析行业研报")
    p_ind.add_argument("--code", required=True, help="行业代码，如 473")
    p_ind.add_argument("--name", default="", help="行业名称")
    p_ind.add_argument("--days", type=int, default=90)
    p_ind.add_argument("--output", default="")

    p_list = sub.add_parser("list", help="仅列出研报元数据（JSON）")
    p_list.add_argument("--code", default="")
    p_list.add_argument("--industry", default="")
    p_list.add_argument("--days", type=int, default=90)
    p_list.add_argument("--size", type=int, default=20)

    args = parser.parse_args()

    if args.cmd == "stock":
        result = analyze_stock(
            args.code, args.name, args.days,
            download_pdf=args.download,
            output=args.output,
            require_whitelist=not args.no_whitelist,
        )
        if not args.output:
            # 已 print 报告，这里只打印统计
            LOGGER.info("完成: 通过 %d 篇", result["quality"].get("valid", 0))
    elif args.cmd == "industry":
        analyze_industry(args.code, args.name, args.days, args.output)
    elif args.cmd == "list":
        adapter = EastmoneyReportAdapter()
        if args.code:
            reports = adapter.fetch_stock_reports(args.code, days=args.days, page_size=args.size)
        elif args.industry:
            reports = adapter.fetch_industry_reports(args.industry, days=args.days, page_size=args.size)
        else:
            reports = adapter.fetch_strategy_reports(days=args.days, page_size=args.size)
        print(json.dumps([r.to_dict() for r in reports], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
