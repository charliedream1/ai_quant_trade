"""PDF 研报下载器

负责将研报 PDF 下载到本地缓存，支持：
- 命名规则：{机构}_{股票代码}_{日期}.pdf（去除非法字符）
- 去重：info_code 已存在则跳过
- 过期清理：超过缓存有效期的文件自动清理
"""
from __future__ import annotations

import logging
import os
import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import requests

from eastmoney_adapter import ReportMeta

LOGGER = logging.getLogger(__name__)

USER_AGENT = "Mozilla/5.0 (compatible; broker-research-analyst/1.0)"


def _safe_filename(name: str) -> str:
    """将字符串转为合法文件名片段"""
    return re.sub(r"[\\/:*?\"<>|]", "_", name).strip() or "unknown"


class PdfDownloader:
    def __init__(
        self,
        cache_dir: str = "./cache",
        expire_days: int = 30,
        timeout: int = 30,
        interval: float = 1.0,
    ):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.expire_days = expire_days
        self.timeout = timeout
        self.interval = interval
        self._last_request_ts = 0.0
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})

    def _throttle(self) -> None:
        elapsed = time.time() - self._last_request_ts
        if elapsed < self.interval:
            time.sleep(self.interval - elapsed)
        self._last_request_ts = time.time()

    def _build_filename(self, meta: ReportMeta) -> str:
        org = _safe_filename(meta.org_sname or "unknown")
        code = _safe_filename(meta.stock_code or "industry")
        date = meta.publish_date or "nodate"
        # info_code 作为唯一标识，避免标题同名冲突
        return f"{org}_{code}_{date}_{meta.info_code}.pdf"

    def get_local_path(self, meta: ReportMeta) -> Path:
        return self.cache_dir / self._build_filename(meta)

    def is_cached(self, meta: ReportMeta) -> bool:
        path = self.get_local_path(meta)
        return path.exists() and path.stat().st_size > 0

    def download(self, meta: ReportMeta, force: bool = False) -> Optional[Path]:
        """下载单篇研报 PDF

        :return: 本地文件路径；失败返回 None
        """
        if not meta.pdf_url:
            LOGGER.warning("研报无 PDF 链接: %s", meta.title)
            return None

        local_path = self.get_local_path(meta)
        if not force and self.is_cached(meta):
            LOGGER.debug("命中缓存: %s", local_path.name)
            return local_path

        self._throttle()
        try:
            resp = self.session.get(meta.pdf_url, timeout=self.timeout, stream=True)
            resp.raise_for_status()
            with open(local_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            LOGGER.info("已下载: %s (%.1f KB)", local_path.name, local_path.stat().st_size / 1024)
            return local_path
        except requests.RequestException as e:
            LOGGER.error("下载失败 [%s]: %s", meta.info_code, e)
            return None

    def download_batch(self, reports: list[ReportMeta], force: bool = False) -> dict:
        """批量下载

        :return: {"success": [Path...], "failed": [ReportMeta...], "cached": [Path...]}
        """
        success, failed, cached = [], [], []
        for meta in reports:
            if not force and self.is_cached(meta):
                cached.append(self.get_local_path(meta))
                continue
            path = self.download(meta, force=force)
            if path:
                success.append(path)
            else:
                failed.append(meta)
        LOGGER.info("下载完成: 成功 %d, 缓存 %d, 失败 %d", len(success), len(cached), len(failed))
        return {"success": success, "cached": cached, "failed": failed}

    def cleanup_expired(self) -> int:
        """清理过期缓存，返回清理文件数"""
        if not self.cache_dir.exists():
            return 0
        cutoff = datetime.now() - timedelta(days=self.expire_days)
        count = 0
        for f in self.cache_dir.glob("*.pdf"):
            mtime = datetime.fromtimestamp(f.stat().st_mtime)
            if mtime < cutoff:
                f.unlink()
                count += 1
        if count:
            LOGGER.info("清理过期缓存 %d 个", count)
        return count
