"""路由调度器

串联整个研报分析流程：
  获取研报 → 质量门禁 → PDF下载(可选) → 解析(可选) → 生成报告 → 校验/质量评估/幻觉检查

提供 CLI 入口，可独立运行产出 Markdown 报告。
LLM 多专家分析环节由 TRAE Skill 编排（不在本脚本内），本脚本负责数据准备与报告骨架。
全流程错误写入 error_log（error_logger.py），并保存为 ./cache/logs/error_*.log。
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
from error_logger import ErrorLog
from report_validator import assess_report

LOGGER = logging.getLogger(__name__)


def analyze_stock(
    stock_code: str,
    stock_name: str = "",
    days: int = 90,
    download_pdf: bool = False,
    output: str = "",
    require_whitelist: bool = True,
    log_dir: str = "./cache/logs",
) -> dict:
    """分析个股研报

    :return: {"reports": [...], "quality": {...}, "report_path": "...", "error_log": "..."}
    """
    error_log = ErrorLog()
    error_log.add_info("fetch", f"开始分析 {stock_code}（{stock_name}），近 {days} 天")

    adapter = EastmoneyReportAdapter()
    LOGGER.info("开始获取 %s 的研报（近 %d 天）", stock_code, days)
    try:
        reports = adapter.fetch_stock_reports(stock_code, days=days, page_size=50)
    except Exception as e:
        error_log.add_error("fetch", f"获取研报失败: {e}", stock_code=stock_code)
        error_log.save(log_dir)
        return {"reports": [], "quality": {}, "report_path": "", "error_log_path": error_log.log_file_path}

    if not reports:
        error_log.add_warning("fetch", "未获取到任何研报", stock_code=stock_code)
        error_log.save(log_dir)
        return {"reports": [], "quality": {}, "report_path": "", "error_log_path": error_log.log_file_path}

    error_log.add_info("fetch", f"获取研报 {len(reports)} 篇", stock_code=stock_code)

    # 质量门禁
    quality = run_quality_gate(
        reports,
        expire_days=90,
        require_whitelist=require_whitelist,
        min_count=3,
    )
    passed = quality.passed_reports
    error_log.add_info("quality_gate",
                       f"质量门禁: 通过 {quality.valid}/{quality.total}",
                       expired=quality.expired, non_whitelist=quality.non_whitelist)
    if quality.conflict_of_interest:
        error_log.add_warning("quality_gate", f"利益冲突: {quality.conflict_of_interest}")

    # 可选：下载并解析 PDF（含图片提取）
    parsed_texts = {}
    pdf_images = {}  # {info_code: [图片路径...]}
    total_images = 0
    # 读取 PDF 解析配置（支持 MinerU 高精度路径开关）
    enable_mineru = False
    try:
        cfg_path = Path(__file__).parent.parent / "config" / "settings.json"
        if cfg_path.exists():
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
            enable_mineru = cfg.get("pdf_parser", {}).get("enable_mineru", False)
    except Exception as e:
        error_log.add_warning("parse", f"读取配置失败，使用默认值: {e}")

    if download_pdf and passed:
        downloader = PdfDownloader(cache_dir="./cache", expire_days=30)
        try:
            result = downloader.download_batch(passed)
        except Exception as e:
            error_log.add_error("download", f"批量下载失败: {e}")
            result = {"paths": [None] * len(passed), "success": [], "cached": [], "failed": passed}

        # paths 与 passed 同序对齐，逐篇解析；None 表示下载失败（如反爬未绕过）
        paths = result.get("paths") or [None] * len(passed)
        download_ok = sum(1 for p in paths if p is not None)
        error_log.add_info("download",
                           f"下载完成: 成功 {download_ok}/{len(passed)}，"
                           f"反爬挑战命中 {downloader.challenge_hits}，解算成功 {downloader.challenge_solved}")
        if downloader.challenge_hits:
            error_log.add_warning("download",
                                  f"遇到东方财富反爬挑战 {downloader.challenge_hits} 次，"
                                  f"已通过 node 解算 cookie 绕过 {downloader.challenge_solved} 次")
        for meta in result.get("failed", []):
            error_log.add_warning("download", f"PDF 下载失败",
                                  info_code=meta.info_code, pdf_url=meta.pdf_url)

        for meta, path in zip(passed, paths):
            if path is None:
                continue
            try:
                parsed = parse_pdf(
                    path,
                    extract_imgs=True,
                    image_output_dir="./cache/images",
                    enable_mineru=enable_mineru,
                )
                if parsed.parse_success:
                    parsed_texts[meta.info_code] = (
                        f"[parser: {parsed.parser_used}]\n{parsed.excerpt(3000)}"
                    )
                else:
                    error_log.add_warning("parse", f"PDF 解析失败: {parsed.error}",
                                          info_code=meta.info_code, pdf_path=str(path))
                if parsed.image_count > 0:
                    pdf_images[meta.info_code] = parsed.image_paths()
                    total_images += parsed.image_count
            except Exception as e:
                error_log.add_error("parse", f"解析 PDF 异常: {e}",
                                    info_code=meta.info_code, pdf_path=str(path))
        if total_images:
            error_log.add_info("image", f"共提取图片 {total_images} 张")

    # 生成报告
    subject = f"{stock_name}（{stock_code}）" if stock_name else stock_code
    md = generate_report(subject, passed, quality, llm_analysis={
        "pdf_excerpts": parsed_texts,
        "pdf_images": pdf_images,
        "total_images": total_images,
    })

    # 质量评估与幻觉检查
    try:
        assessment = assess_report(md, passed, quality, parsed_texts, error_log)
        # 带评估结果重新生成报告
        md = generate_report(subject, passed, quality, llm_analysis={
            "pdf_excerpts": parsed_texts,
            "pdf_images": pdf_images,
            "total_images": total_images,
        }, quality_assessment=assessment)
        error_log.add_info("validate",
                           f"质量评估: 评分 {assessment.overall_score:.0f}, 置信度 {assessment.confidence}")
    except Exception as e:
        error_log.add_error("validate", f"质量评估异常: {e}")

    report_path = ""
    if output:
        report_path = save_report(md, output)
    else:
        print(md)

    # 保存错误日志
    log_path = error_log.save(log_dir)

    return {
        "reports": [r.to_dict() for r in passed],
        "quality": quality.to_dict(),
        "report_path": report_path,
        "parsed_count": len(parsed_texts),
        "error_log_path": log_path,
        "error_summary": error_log.summary(),
    }


def analyze_industry(
    industry_code: str,
    industry_name: str = "",
    days: int = 90,
    output: str = "",
    log_dir: str = "./cache/logs",
) -> dict:
    """分析行业研报"""
    error_log = ErrorLog()
    error_log.add_info("fetch", f"开始分析行业 {industry_code}（{industry_name}）")

    adapter = EastmoneyReportAdapter()
    try:
        reports = adapter.fetch_industry_reports(industry_code, days=days, page_size=50)
    except Exception as e:
        error_log.add_error("fetch", f"获取行业研报失败: {e}")
        error_log.save(log_dir)
        return {"reports": [], "quality": {}, "report_path": ""}

    if not reports:
        error_log.add_warning("fetch", "未获取到行业研报")
        error_log.save(log_dir)
        return {"reports": [], "quality": {}, "report_path": ""}

    quality = run_quality_gate(reports, expire_days=90, require_whitelist=False, min_count=1)
    passed = quality.passed_reports

    subject = f"{industry_name}（行业代码 {industry_code}）" if industry_name else f"行业 {industry_code}"
    md = generate_report(subject, passed, quality)

    # 质量评估
    try:
        assessment = assess_report(md, passed, quality, {}, error_log)
        md = generate_report(subject, passed, quality, quality_assessment=assessment)
    except Exception as e:
        error_log.add_error("validate", f"质量评估异常: {e}")

    if output:
        save_report(md, output)
    else:
        print(md)

    log_path = error_log.save(log_dir)

    return {
        "reports": [r.to_dict() for r in passed],
        "quality": quality.to_dict(),
        "error_log_path": log_path,
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
    p_stock.add_argument("--log-dir", default="./cache/logs", help="错误日志目录")

    p_ind = sub.add_parser("industry", help="分析行业研报")
    p_ind.add_argument("--code", required=True, help="行业代码，如 473")
    p_ind.add_argument("--name", default="", help="行业名称")
    p_ind.add_argument("--days", type=int, default=90)
    p_ind.add_argument("--output", default="")
    p_ind.add_argument("--log-dir", default="./cache/logs")

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
            log_dir=args.log_dir,
        )
        if not args.output:
            LOGGER.info("完成: 通过 %d 篇", result["quality"].get("valid", 0))
        if result.get("error_log_path"):
            LOGGER.info("错误日志: %s", result["error_log_path"])
    elif args.cmd == "industry":
        analyze_industry(args.code, args.name, args.days, args.output, args.log_dir)
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
