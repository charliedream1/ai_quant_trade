"""东方财富研报接口适配器

数据源：东方财富研报中心公开接口（无需 API Key）
- 列表接口：https://reportapi.eastmoney.com/report/list
- PDF 链接：https://pdf.dfcfw.com/pdf/H3_{infoCode}_1.pdf

返回字段说明（节选）：
- title        研报标题
- stockName    股票名称
- stockCode    股票代码
- orgSName     机构简称（如"中信证券"）
- orgName      机构全称
- publishDate  发布日期
- infoCode     PDF 唯一标识（用于构造下载链接）
- emRatingName 东方财富标准化评级（买入/增持/中性/减持/卖出）
- sRatingName  机构原始评级
- researcher   分析师
- predictThisYearEps / Pe  当年盈利预测
- predictNextYearEps / Pe  次年盈利预测
- predictNextTwoYearEps/Pe 第三年盈利预测
- industryName 行业名称
- attachPages  PDF 页数
"""
from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import urlencode

import requests

LOGGER = logging.getLogger(__name__)

# 研报类型映射（qType 参数）
REPORT_TYPE_STOCK = "0"      # 个股研报
REPORT_TYPE_INDUSTRY = "1"   # 行业研报
REPORT_TYPE_STRATEGY = "2"   # 策略研报
REPORT_TYPE_MACRO = "3"      # 宏观研报

DEFAULT_LIST_API = "https://reportapi.eastmoney.com/report/list"
DEFAULT_PDF_BASE = "https://pdf.dfcfw.com/pdf/H3_{infoCode}_1.pdf"
DEFAULT_TIMEOUT = 20
DEFAULT_INTERVAL = 1.0  # 秒，请求间隔，控制频率
USER_AGENT = "Mozilla/5.0 (compatible; broker-research-analyst/1.0)"


@dataclass
class ReportMeta:
    """研报元数据（标准化结构）"""
    title: str
    stock_name: str = ""
    stock_code: str = ""
    org_sname: str = ""          # 机构简称
    org_name: str = ""           # 机构全称
    publish_date: str = ""       # YYYY-MM-DD
    info_code: str = ""          # PDF 标识
    em_rating: str = ""          # 东方财富标准化评级
    org_rating: str = ""         # 机构原始评级
    last_rating: str = ""        # 上次评级
    rating_change: str = ""      # 评级变动
    researcher: str = ""         # 分析师
    industry_name: str = ""      # 行业
    predict_this_year_eps: Optional[float] = None
    predict_this_year_pe: Optional[float] = None
    predict_next_year_eps: Optional[float] = None
    predict_next_year_pe: Optional[float] = None
    predict_next_two_year_eps: Optional[float] = None
    predict_next_two_year_pe: Optional[float] = None
    pdf_url: str = ""
    pdf_pages: Optional[int] = None
    report_type: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def _to_float(val) -> Optional[float]:
    """安全转 float，空字符串/None 返回 None"""
    if val is None or val == "":
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _to_int(val) -> Optional[int]:
    if val is None or val == "":
        return None
    try:
        return int(val)
    except (TypeError, ValueError):
        return None


def _parse_date(date_str: str) -> str:
    """从 '2026-05-25 00:00:00.000' 提取 '2026-05-25'"""
    if not date_str:
        return ""
    return date_str[:10]


class EastmoneyReportAdapter:
    """东方财富研报接口适配器"""

    def __init__(
        self,
        list_api: str = DEFAULT_LIST_API,
        pdf_base: str = DEFAULT_PDF_BASE,
        timeout: int = DEFAULT_TIMEOUT,
        interval: float = DEFAULT_INTERVAL,
    ):
        self.list_api = list_api
        self.pdf_base = pdf_base
        self.timeout = timeout
        self.interval = interval
        self._last_request_ts = 0.0
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})

    def _throttle(self) -> None:
        """请求节流，避免高频请求被封"""
        elapsed = time.time() - self._last_request_ts
        if elapsed < self.interval:
            time.sleep(self.interval - elapsed)
        self._last_request_ts = time.time()

    def build_pdf_url(self, info_code: str) -> str:
        return self.pdf_base.format(infoCode=info_code)

    def fetch_report_list(
        self,
        code: str = "",
        industry_code: str = "",
        q_type: str = REPORT_TYPE_STOCK,
        begin_date: str = "",
        end_date: str = "",
        page_size: int = 50,
        page_no: int = 1,
        org_code: str = "",
        author: str = "",
    ) -> dict:
        """拉取研报列表

        :param code:        股票代码（个股研报必填，如 "600519"）
        :param industry_code: 行业代码（行业研报用，如 "473" 表示证券Ⅱ）
        :param q_type:      研报类型（0个股/1行业/2策略/3宏观）
        :param begin_date:  起始日期 YYYY-MM-DD
        :param end_date:    截止日期 YYYY-MM-DD
        :param page_size:   每页条数
        :param page_no:     页码
        :return: 原始 JSON dict（含 hits/size/data）
        """
        self._throttle()
        params = {
            "industryCode": industry_code,
            "pageSize": page_size,
            "pageNo": page_no,
            "beginTime": begin_date.replace("-", "") if begin_date else "",
            "endTime": end_date.replace("-", "") if end_date else "",
            "fields": "",
            "qType": q_type,
            "orgCode": org_code,
            "author": author,
            "code": code,
        }
        # 移除空值
        params = {k: v for k, v in params.items() if v}
        url = f"{self.list_api}?{urlencode(params)}"
        LOGGER.debug("请求研报列表: %s", url)
        resp = self.session.get(url, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def fetch_stock_reports(
        self,
        stock_code: str,
        days: int = 90,
        page_size: int = 50,
    ) -> list[ReportMeta]:
        """获取个股研报列表（便捷方法）

        :param stock_code:  股票代码，如 "600519"
        :param days:        回溯天数
        :return: ReportMeta 列表
        """
        end_date = datetime.now().strftime("%Y-%m-%d")
        begin_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        raw = self.fetch_report_list(
            code=stock_code,
            q_type=REPORT_TYPE_STOCK,
            begin_date=begin_date,
            end_date=end_date,
            page_size=page_size,
        )
        return self._normalize(raw, q_type=REPORT_TYPE_STOCK)

    def fetch_industry_reports(
        self,
        industry_code: str,
        days: int = 90,
        page_size: int = 50,
    ) -> list[ReportMeta]:
        """获取行业研报列表"""
        end_date = datetime.now().strftime("%Y-%m-%d")
        begin_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        raw = self.fetch_report_list(
            industry_code=industry_code,
            q_type=REPORT_TYPE_INDUSTRY,
            begin_date=begin_date,
            end_date=end_date,
            page_size=page_size,
        )
        return self._normalize(raw, q_type=REPORT_TYPE_INDUSTRY)

    def fetch_strategy_reports(self, days: int = 30, page_size: int = 50) -> list[ReportMeta]:
        """获取策略研报"""
        end_date = datetime.now().strftime("%Y-%m-%d")
        begin_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        raw = self.fetch_report_list(
            q_type=REPORT_TYPE_STRATEGY,
            begin_date=begin_date,
            end_date=end_date,
            page_size=page_size,
        )
        return self._normalize(raw, q_type=REPORT_TYPE_STRATEGY)

    def _normalize(self, raw: dict, q_type: str) -> list[ReportMeta]:
        """将原始 JSON 转为 ReportMeta 列表"""
        data = raw.get("data") or []
        result: list[ReportMeta] = []
        for item in data:
            info_code = item.get("infoCode", "")
            meta = ReportMeta(
                title=item.get("title", "").strip(),
                stock_name=item.get("stockName", ""),
                stock_code=item.get("stockCode", ""),
                org_sname=item.get("orgSName", ""),
                org_name=item.get("orgName", ""),
                publish_date=_parse_date(item.get("publishDate", "")),
                info_code=info_code,
                em_rating=item.get("emRatingName", ""),
                org_rating=item.get("sRatingName", ""),
                last_rating=item.get("lastEmRatingName", ""),
                rating_change=self._rating_change_desc(item.get("ratingChange")),
                researcher=item.get("researcher", ""),
                industry_name=item.get("industryName", "") or item.get("indvInduName", ""),
                predict_this_year_eps=_to_float(item.get("predictThisYearEps")),
                predict_this_year_pe=_to_float(item.get("predictThisYearPe")),
                predict_next_year_eps=_to_float(item.get("predictNextYearEps")),
                predict_next_year_pe=_to_float(item.get("predictNextYearPe")),
                predict_next_two_year_eps=_to_float(item.get("predictNextTwoYearEps")),
                predict_next_two_year_pe=_to_float(item.get("predictNextTwoYearPe")),
                pdf_url=self.build_pdf_url(info_code) if info_code else "",
                pdf_pages=_to_int(item.get("attachPages")),
                report_type=q_type,
            )
            result.append(meta)
        LOGGER.info("已获取 %d 篇研报（类型=%s）", len(result), q_type)
        return result

    @staticmethod
    def _rating_change_desc(code) -> str:
        """评级变动描述"""
        mapping = {1: "首次", 2: "上调", 3: "维持", 4: "下调", 5: "撤销"}
        try:
            return mapping.get(int(code), "")
        except (TypeError, ValueError):
            return ""


# 便捷函数：CLI 直接调用
def main():
    import argparse
    import json

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="东方财富研报列表抓取")
    parser.add_argument("--code", help="股票代码，如 600519")
    parser.add_argument("--industry", help="行业代码，如 473")
    parser.add_argument("--type", default="0", choices=["0", "1", "2", "3"],
                        help="研报类型: 0个股 1行业 2策略 3宏观")
    parser.add_argument("--days", type=int, default=90, help="回溯天数")
    parser.add_argument("--size", type=int, default=20, help="条数")
    args = parser.parse_args()

    adapter = EastmoneyReportAdapter()
    if args.type == REPORT_TYPE_STOCK:
        if not args.code:
            parser.error("个股研报需指定 --code")
        reports = adapter.fetch_stock_reports(args.code, days=args.days, page_size=args.size)
    elif args.type == REPORT_TYPE_INDUSTRY:
        if not args.industry:
            parser.error("行业研报需指定 --industry")
        reports = adapter.fetch_industry_reports(args.industry, days=args.days, page_size=args.size)
    else:
        reports = adapter.fetch_strategy_reports(days=args.days, page_size=args.size)

    print(json.dumps([r.to_dict() for r in reports], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
