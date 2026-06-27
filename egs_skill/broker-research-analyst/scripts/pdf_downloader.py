"""PDF 研报下载器

负责将研报 PDF 下载到本地缓存，支持：
- 命名规则：{机构}_{股票代码}_{日期}.pdf（去除非法字符）
- 去重：info_code 已存在则跳过
- 过期清理：超过缓存有效期的文件自动清理
- 反爬绕过：东方财富 pdf.dfcfw.com 对机器人请求返回 JS 挑战页
  （设置 __tst_status / EO_Bot_Ssid cookie 后重定向）。
  本下载器检测挑战页，调用 node 执行其 JS 解算 cookie，注入会话后重试，
  并校验响应首字节为 %PDF 才落盘，避免把挑战页误存为 .pdf。
"""
from __future__ import annotations

import logging
import re
import shutil
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import requests

from eastmoney_adapter import ReportMeta

LOGGER = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
BROWSER_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "application/pdf,*/*",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Referer": "https://data.eastmoney.com/report/",
}

# 反爬挑战页 <script>JS</script>，用 node 执行以解算 cookie
# node 通过 stdin 接收纯 JS，shim document/location，stdout 输出 cookie JSON
_NODE_RUNNER = r"""
const js = require('fs').readFileSync(0, 'utf8');
const cookies = {};
const document = {
  set cookie(v) {
    const parts = v.split(';')[0].split('=');
    if (parts.length >= 2) cookies[parts[0]] = parts.slice(1).join('=').replace(/#$/, '');
  },
  get cookie() { return ''; }
};
const location = { set href(_) {}, get href() { return ''; } };
let setTimeout = () => {};
try { eval(js); } catch (e) { process.stderr.write('eval error: ' + e.message + '\n'); }
process.stdout.write(JSON.stringify(cookies));
"""

# 缓存 node 是否可用，避免每次下载都探测
_NODE_AVAILABLE: Optional[bool] = None


def _safe_filename(name: str) -> str:
    """将字符串转为合法文件名片段"""
    return re.sub(r"[\\/:*?\"<>|]", "_", name).strip() or "unknown"


def _is_real_pdf(content: bytes) -> bool:
    """校验响应是否为真实 PDF（首字节 %PDF-）"""
    return bool(content) and content[:5].startswith(b"%PDF")


def _is_challenge_page(content: bytes) -> bool:
    """识别东方财富反爬挑战页（含 <script> 且非 PDF）"""
    if not content or _is_real_pdf(content):
        return False
    return b"<script" in content[:500] and b"document" in content


def _check_node_available() -> bool:
    """探测 node 是否可用（结果缓存）"""
    global _NODE_AVAILABLE
    if _NODE_AVAILABLE is not None:
        return _NODE_AVAILABLE
    node_bin = shutil.which("node")
    if not node_bin:
        LOGGER.warning("未找到 node，无法解算反爬 cookie；挑战页将无法绕过")
        _NODE_AVAILABLE = False
        return False
    try:
        proc = subprocess.run(
            [node_bin, "-e", "process.stdout.write('ok')"],
            capture_output=True, timeout=10,
        )
        _NODE_AVAILABLE = proc.returncode == 0 and proc.stdout.strip() == b"ok"
    except Exception as e:
        LOGGER.warning("node 探测失败: %s", e)
        _NODE_AVAILABLE = False
    if not _NODE_AVAILABLE:
        LOGGER.warning("node 不可用，反爬挑战页将无法绕过")
    return _NODE_AVAILABLE


def _solve_challenge(body: bytes, cookie_domain: str = ".dfcfw.com") -> dict:
    """执行挑战页 JS，解算出需设置的 cookie

    :return: {cookie_name: value}；失败返回空 dict
    """
    if not _check_node_available():
        return {}
    m = re.search(rb"<script[^>]*>(.*?)</script>", body, re.DOTALL)
    if not m:
        LOGGER.warning("挑战页未找到 <script> 标签")
        return {}
    js_bytes = m.group(1).strip()
    try:
        proc = subprocess.run(
            ["node", "-e", _NODE_RUNNER],
            input=js_bytes, capture_output=True, timeout=15,
        )
    except subprocess.TimeoutExpired:
        LOGGER.warning("node 执行超时")
        return {}
    except Exception as e:
        LOGGER.warning("node 执行异常: %s", e)
        return {}
    if proc.stderr:
        LOGGER.debug("node stderr: %s", proc.stderr.decode()[:200])
    try:
        import json
        return json.loads(proc.stdout)
    except Exception as e:
        LOGGER.warning("node 输出解析失败: %s, stdout=%r", e, proc.stdout[:200])
        return {}


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
        self.session.headers.update(BROWSER_HEADERS)
        # 统计：本次实例遇到的挑战次数、解算成功次数
        self.challenge_hits = 0
        self.challenge_solved = 0

    def _throttle(self) -> None:
        elapsed = time.time() - self._last_request_ts
        if elapsed < self.interval:
            time.sleep(self.interval - elapsed)
        self._last_request_ts = time.time()

    def _build_filename(self, meta: ReportMeta) -> str:
        org = _safe_filename(meta.org_sname or "unknown")
        code = _safe_filename(meta.stock_code or "industry")
        date = meta.publish_date or "nodate"
        return f"{org}_{code}_{date}_{meta.info_code}.pdf"

    def get_local_path(self, meta: ReportMeta) -> Path:
        return self.cache_dir / self._build_filename(meta)

    def is_cached(self, meta: ReportMeta) -> bool:
        """缓存命中需同时满足：文件存在、体积>0、且首字节为 %PDF

        旧版可能把挑战页误存为 .pdf，此处会识别并视为未缓存，触发重新下载。
        """
        path = self.get_local_path(meta)
        if not path.exists() or path.stat().st_size <= 0:
            return False
        # 校验是否真实 PDF（淘汰历史误存的挑战页）
        try:
            with open(path, "rb") as f:
                head = f.read(5)
        except OSError:
            return False
        return head.startswith(b"%PDF")

    def _fetch(self, url: str) -> Optional[bytes]:
        """单次请求，返回响应体 bytes（失败返回 None）"""
        try:
            resp = self.session.get(url, timeout=self.timeout)
            resp.raise_for_status()
            return resp.content
        except requests.RequestException as e:
            LOGGER.error("请求失败 [%s]: %s", url, e)
            return None

    def download(self, meta: ReportMeta, force: bool = False) -> Optional[Path]:
        """下载单篇研报 PDF（含反爬绕过与真实 PDF 校验）

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
        content = self._fetch(meta.pdf_url)
        if content is None:
            return None

        # 反爬挑战页：解算 cookie 后重试
        if _is_challenge_page(content):
            self.challenge_hits += 1
            LOGGER.info("检测到反爬挑战页 [%s]，调用 node 解算 cookie", meta.info_code)
            cookies = _solve_challenge(content)
            if not cookies:
                LOGGER.warning("cookie 解算失败，放弃 [%s]", meta.info_code)
                return None
            for k, v in cookies.items():
                self.session.cookies.set(k, v, domain=".dfcfw.com")
            self.challenge_solved += 1
            time.sleep(1.2)  # 模拟浏览器 setTimeout 后的重定向间隔
            content = self._fetch(meta.pdf_url)
            if content is None:
                return None

        # 最终校验：必须是真实 PDF
        if not _is_real_pdf(content):
            LOGGER.warning("响应非真实 PDF [%s]，首字节=%r", meta.info_code, content[:8] if content else None)
            return None

        with open(local_path, "wb") as f:
            f.write(content)
        LOGGER.info("已下载: %s (%.1f KB)", local_path.name, local_path.stat().st_size / 1024)
        return local_path

    def download_batch(self, reports: list[ReportMeta], force: bool = False) -> dict:
        """批量下载

        :return: {"paths": [Path|None]（与输入 reports 同序对齐）,
                  "success": [Path...], "cached": [Path...], "failed": [ReportMeta...]}
        """
        paths: list[Optional[Path]] = []
        success, failed, cached = [], [], []
        for meta in reports:
            path = self.download(meta, force=force)
            paths.append(path)
            if path is None:
                failed.append(meta)
            elif self.is_cached(meta) and not force:
                # download() 内部命中缓存时也会返回路径
                cached.append(path)
            else:
                success.append(path)
        LOGGER.info("下载完成: 成功 %d, 缓存 %d, 失败 %d（挑战命中 %d, 解算成功 %d）",
                    len(success), len(cached), len(failed),
                    self.challenge_hits, self.challenge_solved)
        return {"paths": paths, "success": success, "cached": cached, "failed": failed}

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
