"""Real market-data provider with independent public-source fallbacks."""

from __future__ import annotations

import copy
import hashlib
import html
import json
import math
import re
import socket
import threading
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from typing import Any, TypeVar
from urllib.parse import urlparse
from xml.etree import ElementTree
from zoneinfo import ZoneInfo

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src.core.config import get_settings
from src.core.env_file import resolve_env_value
from src.core.exceptions import BusinessError, ErrorCode
from src.core.logger import get_logger
from src.core.timeutil import utc_now_iso
from src.data.normalization import _number
from src.data.provider_output import provider_call
from src.data.relation_graph import _RelationGraphBuilder
from src.data.symbols import SecuritySymbol, parse_symbol

T = TypeVar("T")
SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")
SOURCE_NAME = "eastmoney-push2"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/142 Safari/537.36"
DATA_LOG = get_logger("data.source")

_CACHE: dict[str, tuple[float, Any]] = {}
_CACHE_LOCK = threading.Lock()
_KEY_LOCKS: dict[str, threading.Lock] = {}
_RETRY_AFTER: dict[str, tuple[float, str]] = {}
_BAOSTOCK_LOCK = threading.Lock()
_HEALTH_LOCK = threading.Lock()
_HEALTH: dict[str, dict[str, Any]] = {}
FAILURE_COOLDOWN_SECONDS = 60
# ── 东财防封策略（参考 a-stock-data V3.7） ──────────────────────────────
# 社区实测封禁阈值：>5 次/秒、单 IP 并发≥10、1 分钟≥200 次 → IP 级封禁数小时
# 默认 1.0s 最小间隔 + 0.1~0.5s 随机抖动，QPS ≤ 2；批量筛选建议调大到 1.5~2s
EASTMONEY_MIN_INTERVAL_SECONDS = max(float(resolve_env_value("ALL_IN_ONE_EASTMONEY_MIN_INTERVAL_SECONDS") or "1.0"), 0)
EASTMONEY_JITTER_MIN = max(float(resolve_env_value("ALL_IN_ONE_EASTMONEY_JITTER_MIN") or "0.1"), 0)
EASTMONEY_JITTER_MAX = max(float(resolve_env_value("ALL_IN_ONE_EASTMONEY_JITTER_MAX") or "0.5"), 0)
_EASTMONEY_REQUEST_LOCK = threading.Lock()
_EASTMONEY_LAST_REQUEST_AT = 0.0

_FINANCIAL_TERMS = (
    "A股",
    "港股",
    "美股",
    "央行",
    "利率",
    "汇率",
    "人民币",
    "美元",
    "黄金",
    "原油",
    "期货",
    "债券",
    "基金",
    "券商",
    "银行",
    "保险",
    "半导体",
    "人工智能",
    "新能源",
    "房地产",
    "消费",
    "医药",
    "汽车",
    "算力",
    "通胀",
    "财报",
    "营收",
    "利润",
    "并购",
    "政策",
)


def _session() -> requests.Session:
    """HTTP 会话工厂。

    真实行情源默认不继承系统代理，避免本机代理异常导致页面回调长时间卡住。
    如运行环境必须通过代理访问外网，可显式设置 ALL_IN_ONE_DATA_HTTP_TRUST_ENV=true。

    - 403 **不重试**：东财风控信号，重试反而加重封禁；按 EASTMONEY_MIN_INTERVAL 降频应对
    - 429 / 5xx：按配置退避重试，默认只重试 1 次以应对临时服务端波动
    - 连接/读取错误：不重试，失败后进入数据源冷却，避免页面按钮长时间等待
    """
    settings = get_settings()
    retries = max(int(settings.data_http_retries), 0)
    session = requests.Session()
    session.trust_env = bool(settings.data_http_trust_env)
    retry = Retry(
        total=retries,
        connect=0,
        read=0,
        status=retries,
        backoff_factor=max(float(settings.data_http_backoff_seconds), 0.0),
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET"}),
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=12, pool_maxsize=12)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update({"User-Agent": USER_AGENT, "Referer": "https://quote.eastmoney.com/"})
    return session


_HTTP = _session()


def _compact_error_message(value: Any, limit: int = 240) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if len(text) <= limit:
        return text
    return f"{text[: limit - 3]}..."


def _request_error_reason(exc: requests.exceptions.RequestException) -> str:
    if isinstance(exc, requests.exceptions.ProxyError):
        return "代理连接失败"
    if isinstance(exc, requests.exceptions.ConnectTimeout):
        return "连接超时"
    if isinstance(exc, requests.exceptions.ReadTimeout):
        return "读取超时"
    if isinstance(exc, requests.exceptions.Timeout):
        return "请求超时"
    if isinstance(exc, requests.exceptions.ConnectionError):
        return "网络连接失败"
    return "HTTP 请求失败"


def _error_reason(exc: Exception) -> str:
    if isinstance(exc, requests.exceptions.RequestException):
        return _request_error_reason(exc)
    return _compact_error_message(exc)


def _integer(value: Any, default: int = 0) -> int:
    return int(_number(value, float(default)))


def _timestamp(value: Any) -> str:
    seconds = _integer(value)
    if seconds <= 0:
        return datetime.now(SHANGHAI_TZ).replace(microsecond=0).isoformat()
    return datetime.fromtimestamp(seconds, tz=timezone.utc).astimezone(SHANGHAI_TZ).isoformat()


def _stable_id(value: str) -> int:
    return int(hashlib.sha1(value.encode("utf-8"), usedforsecurity=False).hexdigest()[:15], 16)


def _normalize_symbol(symbol: str, *, stock_only: bool = False) -> str:
    return parse_symbol(symbol, stock_only=stock_only).code


def _normalize_price_adjustment(value: str) -> str:
    selected = str(value or "qfq").strip().lower()
    aliases = {
        "forward": "qfq",
        "pre": "qfq",
        "前复权": "qfq",
        "backward": "hfq",
        "post": "hfq",
        "后复权": "hfq",
        "raw": "none",
        "none": "none",
        "不复权": "none",
        "bfq": "none",
    }
    return aliases.get(selected, selected if selected in {"qfq", "hfq", "none"} else "qfq")


def _secid(symbol: str) -> str:
    return parse_symbol(symbol).secid


def _market(symbol: str) -> str:
    return parse_symbol(symbol).market


def _provider_from_host(hostname: str) -> str:
    normalized = hostname.lower()
    if normalized.endswith("eastmoney.com"):
        return SOURCE_NAME
    if normalized.endswith("gtimg.cn"):
        return "tencent-qt"
    if normalized.endswith("sina.com.cn") or normalized.endswith("sinajs.cn"):
        return "sina"
    if normalized.endswith("baostock.com"):
        return "baostock"
    return normalized or "unknown"


def _http_get(url: str, **kwargs: Any) -> requests.Response:
    """Serialize Eastmoney traffic with rate-limiting + jitter.

    东财子域名（push2 / datacenter-web / reportapi / search-api / np-weblist 等）
    共用同一套 WAF 风控，全部串行化 + 最小间隔 + 随机抖动，避免高频被封 IP。
    非东财域名（腾讯/新浪/巨潮/baostock 等）独立风控面，直接放行不受影响。
    （参考 a-stock-data V3.7 em_get() 节流入口实现）
    """
    import random as _random

    parsed = urlparse(url)
    hostname = parsed.hostname or ""
    provider = _provider_from_host(hostname)
    started = time.perf_counter()
    throttled = bool(re.search(r"(^|\.)eastmoney\.com$", hostname, re.IGNORECASE))
    try:
        if not throttled:
            response = _HTTP.get(url, **kwargs)
        else:
            global _EASTMONEY_LAST_REQUEST_AT
            with _EASTMONEY_REQUEST_LOCK:
                base_wait = EASTMONEY_MIN_INTERVAL_SECONDS - (time.monotonic() - _EASTMONEY_LAST_REQUEST_AT)
                jitter = _random.uniform(EASTMONEY_JITTER_MIN, EASTMONEY_JITTER_MAX)
                wait = max(base_wait, 0.0) + jitter
                if wait > 0:
                    time.sleep(wait)
                _EASTMONEY_LAST_REQUEST_AT = time.monotonic()
                response = _HTTP.get(url, **kwargs)
    except requests.exceptions.RequestException as exc:
        DATA_LOG.warning(
            "market data request failed | provider={} host={} path={} duration_ms={:.0f} "
            "error_type={} reason={} trust_env={} retries={}",
            provider,
            hostname or "-",
            parsed.path or "/",
            (time.perf_counter() - started) * 1000,
            exc.__class__.__name__,
            _request_error_reason(exc),
            getattr(_HTTP, "trust_env", "-"),
            get_settings().data_http_retries,
        )
        raise
    except Exception as exc:
        DATA_LOG.opt(exception=exc).error(
            "market data request crashed | provider={} host={} path={} duration_ms={:.0f} error_type={} reason={}",
            provider,
            hostname or "-",
            parsed.path or "/",
            (time.perf_counter() - started) * 1000,
            exc.__class__.__name__,
            _compact_error_message(exc),
        )
        raise
    DATA_LOG.log(
        "WARNING" if response.status_code >= 400 else "DEBUG",
        "market data request completed | provider={} host={} path={} status={} duration_ms={:.0f} throttled={}",
        provider,
        hostname or "-",
        parsed.path or "/",
        response.status_code,
        (time.perf_counter() - started) * 1000,
        throttled,
    )
    return response


def _mark_health(capability: str, source: str, status: str, error: str = "") -> None:
    with _HEALTH_LOCK:
        _HEALTH[capability] = {
            "status": status,
            "active_source": source,
            "mode": "real",
            "checked_at": utc_now_iso(),
            "last_error": error,
        }


def _key_lock(key: str) -> threading.Lock:
    with _CACHE_LOCK:
        return _KEY_LOCKS.setdefault(key, threading.Lock())


def _market_cache_ttl(trading_seconds: int, closed_seconds: int) -> int:
    now = datetime.now(SHANGHAI_TZ)
    minute = now.hour * 60 + now.minute
    trading = now.weekday() < 5 and (555 <= minute <= 695 or 780 <= minute <= 905)
    base_ttl = trading_seconds if trading else closed_seconds
    ttl_cap = int(getattr(get_settings(), "data_cache_ttl_seconds", 0) or 0)
    return min(base_ttl, ttl_cap) if ttl_cap > 0 else base_ttl


def _cached(
    key: str,
    ttl: int,
    capability: str,
    source: str,
    loader: Callable[[], T],
    *,
    force_refresh: bool = False,
) -> T:
    now = time.monotonic()
    with _CACHE_LOCK:
        cached = _CACHE.get(key)
        retry_after = _RETRY_AFTER.get(key)
        if cached and not force_refresh and now - cached[0] < ttl:
            return copy.deepcopy(cached[1])
        if retry_after and now < retry_after[0]:
            if cached:
                return copy.deepcopy(cached[1])
            raise BusinessError(
                ErrorCode.DATA_SOURCE_ERROR,
                f"真实数据源 {source} 处于失败冷却期",
                {
                    "provider": source,
                    "capability": capability,
                    "reason": retry_after[1],
                    "retry_after_seconds": round(retry_after[0] - now, 1),
                },
            )

    with _key_lock(key):
        now = time.monotonic()
        with _CACHE_LOCK:
            cached = _CACHE.get(key)
            retry_after = _RETRY_AFTER.get(key)
            if cached and not force_refresh and now - cached[0] < ttl:
                return copy.deepcopy(cached[1])
            if retry_after and now < retry_after[0]:
                if cached:
                    return copy.deepcopy(cached[1])
                raise BusinessError(
                    ErrorCode.DATA_SOURCE_ERROR,
                    f"真实数据源 {source} 处于失败冷却期",
                    {
                        "provider": source,
                        "capability": capability,
                        "reason": retry_after[1],
                        "retry_after_seconds": round(retry_after[0] - now, 1),
                    },
                )
            stale = copy.deepcopy(cached[1]) if cached else None
        try:
            value = loader()
        except Exception as exc:
            reason = _error_reason(exc)
            _mark_health(capability, source, "degraded", reason)
            with _CACHE_LOCK:
                _RETRY_AFTER[key] = (time.monotonic() + FAILURE_COOLDOWN_SECONDS, reason)
            if stale is not None:
                return stale
            if isinstance(exc, BusinessError):
                raise
            raise BusinessError(
                ErrorCode.DATA_SOURCE_ERROR,
                f"真实数据源 {source} 暂时不可用",
                {"provider": source, "capability": capability, "reason": reason},
            ) from exc
        with _CACHE_LOCK:
            _CACHE[key] = (time.monotonic(), copy.deepcopy(value))
            _RETRY_AFTER.pop(key, None)
        active_source = source
        sample = value[0] if isinstance(value, list) and value else value
        if isinstance(sample, dict):
            active_source = str(sample.get("data_source") or sample.get("source") or source)
        _mark_health(capability, active_source, "ok")
        return value


# ═══════════════════════════════════════════════════════════════════════════
# mootdx 通达信 TCP 行情客户端（参考 a-stock-data V3.7 tdx_client()）
# 可选单票备用：TCP 7709 二进制协议，不提供 PE/PB/市值且 K 线不复权。
# 规避 mootdx 0.11.x BESTIP 空串 bug —— 显式传服务器 + 真实取数验活
# ═══════════════════════════════════════════════════════════════════════════
_TDX_SERVERS = [
    # 实测可用的通达信行情服务器（按延迟排序，2026-08 验证）
    ("119.97.185.59", 7709),
    ("124.70.133.119", 7709),
    ("116.205.183.150", 7709),
    ("123.60.73.44", 7709),
    ("116.205.163.254", 7709),
    ("121.36.225.169", 7709),
    ("123.60.70.228", 7709),
    ("124.71.9.153", 7709),
    ("110.41.147.114", 7709),
    ("124.71.187.122", 7709),
]
_TDX_CLIENT_LOCK = threading.Lock()
_TDX_CLIENT: Any = None
_TDX_RETRY_AFTER = 0.0
TDX_ENABLED = (resolve_env_value("ALL_IN_ONE_TDX_ENABLED") or "false").strip().lower() in {"1", "true", "yes", "on"}
TDX_PROBE_TIMEOUT_SECONDS = max(float(resolve_env_value("ALL_IN_ONE_TDX_PROBE_TIMEOUT_SECONDS") or "0.4"), 0.1)
TDX_MAX_PROBE_SERVERS = max(1, int(resolve_env_value("ALL_IN_ONE_TDX_MAX_PROBE_SERVERS") or "3"))
TDX_FAILURE_COOLDOWN_SECONDS = max(float(resolve_env_value("ALL_IN_ONE_TDX_FAILURE_COOLDOWN_SECONDS") or "300"), 1)


def _tdx_probe(ip: str, port: int, timeout: float = TDX_PROBE_TIMEOUT_SECONDS) -> bool:
    """TCP 握手探测（快速粗筛）。注意：握手成功 ≠ 能取数，需再经 _tdx_validate 验活。"""
    try:
        with socket.create_connection((ip, port), timeout=timeout):
            return True
    except Exception:
        return False


def _tdx_validate(client: Any) -> bool:
    """真实取数验活：坏服务器可 TCP 握手通过却回 2 字节空 body → 静默空表。"""
    try:
        df = client.bars(symbol="000001", frequency=9, offset=1)
        return df is not None and not getattr(df, "empty", True)
    except Exception:
        return False


def _tdx_client() -> Any:
    """Return a validated optional TDX client without blocking normal HTTP quotes."""
    global _TDX_CLIENT, _TDX_RETRY_AFTER
    if not TDX_ENABLED:
        raise RuntimeError("mootdx 未启用；如需使用请设置 ALL_IN_ONE_TDX_ENABLED=true")
    if _TDX_CLIENT is not None:
        return _TDX_CLIENT
    if time.monotonic() < _TDX_RETRY_AFTER:
        raise RuntimeError("mootdx 处于连接失败冷却期")
    with _TDX_CLIENT_LOCK:
        if _TDX_CLIENT is not None:
            return _TDX_CLIENT
        try:
            from mootdx.quotes import Quotes as _Quotes
        except ImportError as exc:
            raise RuntimeError("未安装 mootdx（pip install mootdx）") from exc
        for ip, port in _TDX_SERVERS[:TDX_MAX_PROBE_SERVERS]:
            if not _tdx_probe(ip, port):
                continue
            try:
                c = _Quotes.factory(market="std", server=(ip, port))
                if _tdx_validate(c):
                    _TDX_CLIENT = c
                    return c
            except Exception:
                continue
        _TDX_RETRY_AFTER = time.monotonic() + TDX_FAILURE_COOLDOWN_SECONDS
        raise RuntimeError("通达信 (mootdx) 预置服务器均取不到数据；已进入冷却期并回退腾讯/新浪/东方财富")


# ═══════════════════════════════════════════════════════════════════════════
# 关系图谱：基于个股资料（所属板块）、板块成分、行情相关、新闻、十大股东分层扩展
# ═══════════════════════════════════════════════════════════════════════════
_INDEX_BOARD_KEYWORDS = (
    "HS300",
    "沪深300",
    "上证50",
    "上证180",
    "创业板指",
    "科创50",
    "中证500",
    "深证成指",
)
_INDEX_BOARD_DISPLAY_NAMES = {
    "500": "沪深300",
    "611": "上证50",
    "612": "上证180",
    "610": "央视50",
    "905": "中证500",
    "1622": "深证成指",
}


class EastmoneyDataSource:
    """Normalized real-data facade with bounded requests and shared TTL caches."""

    source_name = SOURCE_NAME

    def __init__(self, timeout_seconds: float = 12.0) -> None:
        self.timeout = (3.05, max(float(timeout_seconds), 3.0))

    def health(self) -> dict[str, Any]:
        with _HEALTH_LOCK:
            health = copy.deepcopy(_HEALTH)
        optional_tdx = " / mootdx-tdx" if TDX_ENABLED else ""
        defaults = {
            "quotes": f"tencent-qt{optional_tdx} / sina-hq / eastmoney-push2",
            "history": "tencent-fqkline / eastmoney-push2his / baostock",
            "news": "eastmoney-fast-news / sina-7x24",
            "reports": "eastmoney-report",
            "papers": "arxiv",
        }
        return {
            capability: health.get(
                capability,
                {
                    "status": "unknown",
                    "active_source": source,
                    "mode": "real",
                    "checked_at": None,
                    "last_error": "",
                },
            )
            for capability, source in defaults.items()
        }

    def indices(self, refresh: bool = False) -> list[dict[str, Any]]:
        return _cached(
            "indices",
            _market_cache_ttl(15, 300),
            "quotes",
            "eastmoney / sina",
            self._load_indices,
            force_refresh=refresh,
        )

    def _load_indices(self) -> list[dict[str, Any]]:
        try:
            payload = self._get_json(
                "https://push2.eastmoney.com/api/qt/ulist.np/get",
                {
                    "fltt": 2,
                    "invt": 2,
                    "fields": "f12,f14,f2,f3,f4,f5,f6,f124",
                    "secids": "1.000001,0.399001,0.399006,1.000688",
                },
            )
            rows = (payload.get("data") or {}).get("diff") or []
            if not rows:
                raise RuntimeError("指数接口返回空数据")
            return [
                {
                    "code": item.get("f12"),
                    "name": item.get("f14"),
                    "price": _number(item.get("f2")),
                    "change": _number(item.get("f4")),
                    "change_pct": _number(item.get("f3")),
                    "volume": _number(item.get("f5")),
                    "amount": _number(item.get("f6")),
                    "data_source": SOURCE_NAME,
                    "updated_at": _timestamp(item.get("f124")),
                }
                for item in rows
            ]
        except Exception:
            return self._load_indices_sina()

    def _load_indices_sina(self) -> list[dict[str, Any]]:
        symbols = "s_sh000001,s_sz399001,s_sz399006,s_sh000688"
        response = _http_get(
            f"https://hq.sinajs.cn/list={symbols}",
            headers={"Referer": "https://finance.sina.com.cn/"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        text = response.content.decode("gbk", errors="replace")
        rows = []
        for key, value in re.findall(r'hq_str_s_(\w+)="([^"]*)"', text):
            parts = value.split(",")
            if len(parts) < 6:
                continue
            rows.append(
                {
                    "code": key[2:] if key.startswith(("sh", "sz")) else key,
                    "name": parts[0],
                    "price": _number(parts[1]),
                    "change": _number(parts[2]),
                    "change_pct": _number(parts[3]),
                    "volume": _number(parts[4]) * 100,
                    "amount": _number(parts[5]) * 10000,
                    "data_source": "sina-hq",
                    "updated_at": datetime.now(SHANGHAI_TZ).replace(microsecond=0).isoformat(),
                }
            )
        if not rows:
            raise RuntimeError("新浪指数接口返回空数据")
        return rows

    def sectors(self, board: str = "industry", limit: int = 20) -> list[dict[str, Any]]:
        board_value = "concept" if board == "concept" else "industry"
        limit_value = max(1, min(int(limit), 100))
        items = _cached(
            f"sectors:{board_value}",
            _market_cache_ttl(60, 600),
            "quotes",
            "eastmoney / sina",
            lambda: self._load_sectors(board_value, 100),
        )
        return items[:limit_value]

    def _load_sectors(self, board: str, limit: int) -> list[dict[str, Any]]:
        try:
            board_type = 3 if board == "concept" else 2
            payload = self._get_json(
                "https://17.push2.eastmoney.com/api/qt/clist/get",
                {
                    "pn": 1,
                    "pz": limit,
                    "po": 1,
                    "np": 1,
                    "ut": "bd1d9ddb04089700cf9c27f6f7426281",
                    "fltt": 2,
                    "invt": 2,
                    "fid": "f3",
                    "fs": f"m:90 t:{board_type} f:!50",
                    "fields": "f2,f3,f6,f12,f14,f104,f105,f128,f140,f124",
                },
            )
            rows = (payload.get("data") or {}).get("diff") or []
            if not rows:
                raise RuntimeError("板块接口返回空数据")
            return [
                {
                    "code": item.get("f12"),
                    "name": item.get("f14"),
                    "price": _number(item.get("f2")),
                    "change_pct": _number(item.get("f3")),
                    "leader": item.get("f128") or "-",
                    "leader_code": item.get("f140") or "-",
                    "amount": _number(item.get("f6")),
                    "up_count": _integer(item.get("f104")),
                    "down_count": _integer(item.get("f105")),
                    "board": board,
                    "data_source": SOURCE_NAME,
                    "updated_at": _timestamp(item.get("f124")),
                }
                for item in rows
            ]
        except Exception:
            return self._load_sectors_sina(board, limit)

    def _load_sectors_sina(self, board: str, limit: int) -> list[dict[str, Any]]:
        if board == "concept":
            url = "https://money.finance.sina.com.cn/q/view/newFLJK.php"
            params = {"param": "class"}
        else:
            url = "https://vip.stock.finance.sina.com.cn/q/view/newSinaHy.php"
            params = {}
        response = _http_get(
            url,
            params=params,
            headers={"Referer": "https://finance.sina.com.cn/stock/sl/"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        text = response.content.decode("gbk", errors="replace")
        payload = json.loads(text[text.find("{") :])
        rows = []
        for value in payload.values():
            parts = value.split(",")
            if len(parts) < 13:
                continue
            rows.append(
                {
                    "code": parts[0],
                    "name": parts[1],
                    "price": _number(parts[3]),
                    "change_pct": _number(parts[5]),
                    "leader": parts[12] or "-",
                    "leader_code": re.sub(r"^(sh|sz|bj)", "", parts[8]),
                    "amount": _number(parts[7]),
                    "up_count": None,
                    "down_count": None,
                    "board": board,
                    "data_source": "sina-sector",
                    "updated_at": datetime.now(SHANGHAI_TZ).replace(microsecond=0).isoformat(),
                }
            )
        rows.sort(key=lambda item: float(item["change_pct"]), reverse=True)
        if not rows:
            raise RuntimeError("新浪板块接口返回空数据")
        return rows[:limit]

    def stock_quote(self, symbol: str) -> dict[str, Any]:
        parsed = parse_symbol(symbol)
        return _cached(
            f"stock-quote:{parsed.cache_key}",
            _market_cache_ttl(15, 300),
            "quotes",
            "tencent-qt / mootdx-tdx(optional) / sina-hq / eastmoney-push2",
            lambda: self._load_stock_quote(parsed),
        )

    def _load_stock_quote(self, symbol: SecuritySymbol) -> dict[str, Any]:
        try:
            return self._load_stock_quote_tencent(symbol)
        except Exception as tencent_error:
            try:
                return self._load_stock_quote_tdx(symbol)
            except Exception as tdx_error:
                try:
                    return self._load_stock_quote_sina(symbol)
                except Exception as sina_error:
                    try:
                        return self._load_stock_quote_eastmoney(symbol)
                    except Exception as eastmoney_error:
                        raise RuntimeError(
                            f"TDX(mootdx): {tdx_error}; Tencent: {tencent_error}; Sina: {sina_error}; Eastmoney: {eastmoney_error}"
                        ) from eastmoney_error

    def _load_stock_quote_tdx(self, symbol: SecuritySymbol) -> dict[str, Any]:
        """Optional TDX quote fallback for Shanghai and Shenzhen securities."""
        if symbol.market == "BJ":
            raise RuntimeError("mootdx 标准行情不支持北交所证券")
        tdx = _tdx_client()
        df = tdx.quotes(symbol=[symbol.code])
        if df is None or getattr(df, "empty", True):
            raise RuntimeError(f"mootdx 未返回 {symbol.code} 报价")
        row = df.iloc[0]
        returned_code = str(row.get("code", "") or row.get("f57", ""))
        if returned_code and returned_code != symbol.code:
            raise RuntimeError(f"mootdx 返回代码 {returned_code}，与请求 {symbol.code} 不一致")
        price = _number(row.get("price") or row.get("f43"))
        previous_close = _number(row.get("last_close") or row.get("f60"))
        volume = _number(row.get("vol") or row.get("f47"))
        if price <= 0:
            raise RuntimeError(f"mootdx {symbol.qualified} 返回无效价格 {price}")
        change = _number(row.get("price") or 0) - previous_close if previous_close > 0 else _number(row.get("f169"))
        change_pct = (change / previous_close * 100) if previous_close > 0 else _number(row.get("f170"))
        is_stale, stale_reason = self._stale_quote(symbol, price, previous_close, volume)
        return {
            "symbol": symbol.code,
            "name": str(row.get("name") or row.get("f58") or symbol.code),
            "market": symbol.market,
            "price": price,
            "latest_price": price,
            "previous_close": previous_close,
            "change": change,
            "change_pct": change_pct,
            "volume": volume,
            "amount": _number(row.get("amount") or row.get("f48")),
            "turnover_rate": 0.0,  # mootdx 无此字段，由上层腾讯/东财补充
            "pe": 0.0,  # 同上
            "pb": 0.0,  # 同上
            "market_cap": 0.0,  # 同上
            "float_market_cap": 0.0,  # 同上
            "total_shares": _number(row.get("f84")),
            "float_shares": _number(row.get("f85")),
            "industry": "",
            "updated_at": datetime.now(SHANGHAI_TZ).replace(microsecond=0).isoformat(),
            "data_source": "mootdx-tdx",
            "is_stale": is_stale,
            "stale_reason": stale_reason,
        }

    def _load_stock_quote_eastmoney(self, symbol: SecuritySymbol) -> dict[str, Any]:
        payload = self._get_json(
            "https://push2.eastmoney.com/api/qt/stock/get",
            {
                "secid": symbol.secid,
                "fltt": 2,
                "invt": 2,
                "fields": "f57,f58,f43,f60,f169,f170,f47,f48,f116,f117,f162,f167,f168,f124,f127,f84,f85",
            },
        )
        item = payload.get("data") or {}
        if not item or item.get("f43") in (None, "-"):
            raise RuntimeError(f"未找到证券 {symbol.qualified}")
        returned_code = str(item.get("f57") or "")
        if returned_code != symbol.code:
            raise RuntimeError(f"东财返回代码 {returned_code or '(空)'}，与请求 {symbol.code} 不一致")
        price = _number(item.get("f43"))
        previous_close = _number(item.get("f60"))
        volume = _number(item.get("f47"))
        is_stale, stale_reason = self._stale_quote(symbol, price, previous_close, volume)
        return {
            "symbol": returned_code,
            "name": item.get("f58") or symbol.code,
            "market": symbol.market,
            "price": price,
            "latest_price": price,
            "previous_close": previous_close,
            "change": _number(item.get("f169")),
            "change_pct": _number(item.get("f170")),
            "volume": volume,
            "amount": _number(item.get("f48")),
            "turnover_rate": _number(item.get("f168")),
            "pe": _number(item.get("f162")),
            "pb": _number(item.get("f167")),
            "market_cap": _number(item.get("f116")),
            "float_market_cap": _number(item.get("f117")),
            "total_shares": _number(item.get("f84")),
            "float_shares": _number(item.get("f85")),
            "industry": item.get("f127") if item.get("f127") not in (None, "-") else "",
            "updated_at": _timestamp(item.get("f124")),
            "data_source": SOURCE_NAME,
            "is_stale": is_stale,
            "stale_reason": stale_reason,
        }

    def _load_stock_quote_tencent(self, symbol: SecuritySymbol) -> dict[str, Any]:
        response = _http_get(
            f"https://qt.gtimg.cn/q={symbol.qualified}",
            headers={"Referer": "https://gu.qq.com/"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        text = response.content.decode("gbk", errors="replace")
        matched = re.search(r'="(.*)"', text)
        if not matched:
            raise RuntimeError(f"腾讯行情未找到股票 {symbol}")
        item = matched.group(1).split("~")
        if len(item) < 53:
            raise RuntimeError("腾讯行情字段不完整")
        return self._parse_tencent_quote(symbol, item)

    def _parse_tencent_quote(self, symbol: SecuritySymbol, item: list[str]) -> dict[str, Any]:
        returned_code = str(item[2] or "")
        if returned_code != symbol.code:
            raise RuntimeError(f"腾讯返回代码 {returned_code or '(空)'}，与请求 {symbol.code} 不一致")
        price = _number(item[3])
        previous_close = _number(item[4])
        volume = _number(item[36]) * 100
        if price <= 0:
            raise RuntimeError(f"腾讯行情 {symbol.qualified} 返回无效价格")
        trade_data = item[35].split("/")
        amount = (
            _number(trade_data[2]) if len(trade_data) >= 3 else (_number(item[57]) * 10000 if len(item) > 57 else 0)
        )
        try:
            quote_time = datetime.strptime(item[30], "%Y%m%d%H%M%S").replace(tzinfo=SHANGHAI_TZ).isoformat()
        except ValueError:
            quote_time = datetime.now(SHANGHAI_TZ).replace(microsecond=0).isoformat()
        is_stale, stale_reason = self._stale_quote(symbol, price, previous_close, volume)
        return {
            "symbol": returned_code,
            "name": item[1] or symbol.code,
            "market": symbol.market,
            "price": price,
            "latest_price": price,
            "previous_close": previous_close,
            "change": _number(item[31]),
            "change_pct": _number(item[32]),
            "volume": volume,
            "amount": amount,
            "turnover_rate": _number(item[38]),
            "pe": _number(item[52] or item[39]),
            "pb": _number(item[46]),
            "market_cap": _number(item[45]) * 100000000,
            "float_market_cap": _number(item[44]) * 100000000,
            "industry": "",
            "updated_at": quote_time,
            "data_source": "tencent-qt",
            "is_stale": is_stale,
            "stale_reason": stale_reason,
        }

    def _load_stock_quote_sina(self, symbol: SecuritySymbol) -> dict[str, Any]:
        result = self._load_stock_quotes_sina([symbol])
        try:
            return result[symbol.cache_key]
        except KeyError as exc:
            raise RuntimeError(f"Sina quote did not return {symbol.qualified}") from exc

    def _parse_sina_quote(self, symbol: SecuritySymbol, item: list[str]) -> dict[str, Any]:
        if len(item) < 32:
            raise RuntimeError(f"Sina quote fields are incomplete for {symbol.qualified}")
        price = _number(item[3])
        previous_close = _number(item[2])
        volume = _number(item[8])
        if not item[0] or price <= 0:
            raise RuntimeError(f"Sina quote returned an invalid price for {symbol.qualified}")
        change = price - previous_close
        change_pct = change / previous_close * 100 if previous_close > 0 else 0
        try:
            quote_time = datetime.strptime(f"{item[30]} {item[31]}", "%Y-%m-%d %H:%M:%S")
            updated_at = quote_time.replace(tzinfo=SHANGHAI_TZ).isoformat()
        except ValueError:
            updated_at = datetime.now(SHANGHAI_TZ).replace(microsecond=0).isoformat()
        is_stale, stale_reason = self._stale_quote(symbol, price, previous_close, volume)
        return {
            "symbol": symbol.code,
            "name": item[0],
            "market": symbol.market,
            "price": price,
            "latest_price": price,
            "previous_close": previous_close,
            "change": change,
            "change_pct": change_pct,
            "volume": volume,
            "amount": _number(item[9]),
            "turnover_rate": 0,
            "pe": 0,
            "pb": 0,
            "market_cap": 0,
            "float_market_cap": 0,
            "industry": "",
            "updated_at": updated_at,
            "data_source": "sina-hq",
            "is_stale": is_stale,
            "stale_reason": stale_reason,
        }

    def stock_quotes(self, symbols: list[str]) -> list[dict[str, Any]]:
        parsed = [parse_symbol(symbol) for symbol in symbols]
        if not parsed:
            return []
        key = ",".join(item.cache_key for item in parsed)
        return _cached(
            f"stock-quotes:{key}",
            _market_cache_ttl(15, 300),
            "quotes",
            "tencent-qt / sina-hq / eastmoney-push2",
            lambda: self._load_stock_quotes(parsed),
        )

    def _load_stock_quotes(self, symbols: list[SecuritySymbol]) -> list[dict[str, Any]]:
        by_key: dict[str, dict[str, Any]] = {}
        try:
            by_key.update(self._load_stock_quotes_tencent(symbols))
        except Exception:
            pass
        missing = [symbol for symbol in symbols if symbol.cache_key not in by_key]
        if missing:
            try:
                by_key.update(self._load_stock_quotes_sina(missing))
            except Exception:
                pass
        for symbol in symbols:
            if symbol.cache_key not in by_key:
                by_key[symbol.cache_key] = self._load_stock_quote_eastmoney(symbol)
        return [copy.deepcopy(by_key[symbol.cache_key]) for symbol in symbols]

    def _load_stock_quotes_tencent(self, symbols: list[SecuritySymbol]) -> dict[str, dict[str, Any]]:
        response = _http_get(
            f"https://qt.gtimg.cn/q={','.join(symbol.qualified for symbol in symbols)}",
            headers={"Referer": "https://gu.qq.com/"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        text = response.content.decode("gbk", errors="replace")
        requested = {symbol.qualified: symbol for symbol in symbols}
        results: dict[str, dict[str, Any]] = {}
        for qualified, raw in re.findall(r'v_(\w+)="([^"]*)"', text):
            symbol = requested.get(qualified.lower())
            item = raw.split("~")
            if symbol is None or len(item) < 53:
                continue
            results[symbol.cache_key] = self._parse_tencent_quote(symbol, item)
        if not results:
            raise RuntimeError("腾讯批量行情返回空数据")
        return results

    def _load_stock_quotes_sina(self, symbols: list[SecuritySymbol]) -> dict[str, dict[str, Any]]:
        response = _http_get(
            f"https://hq.sinajs.cn/list={','.join(symbol.qualified for symbol in symbols)}",
            headers={"Referer": "https://finance.sina.com.cn/"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        text = response.content.decode("gbk", errors="replace")
        requested = {symbol.qualified: symbol for symbol in symbols}
        results: dict[str, dict[str, Any]] = {}
        for qualified, raw in re.findall(r'var hq_str_(\w+)="([^"]*)";', text):
            symbol = requested.get(qualified.lower())
            if symbol is None or not raw:
                continue
            try:
                results[symbol.cache_key] = self._parse_sina_quote(symbol, raw.split(","))
            except RuntimeError:
                continue
        if not results:
            raise RuntimeError("新浪批量行情返回空数据")
        return results

    @staticmethod
    def _stale_quote(symbol: SecuritySymbol, price: float, previous_close: float, volume: float) -> tuple[bool, str]:
        stale = volume == 0 and previous_close > 0 and math.isclose(price, previous_close, rel_tol=0, abs_tol=1e-8)
        if not stale:
            return False, ""
        if symbol.is_legacy_beijing:
            return True, "北交所旧号段零成交定格报价，可能已迁移至 920xxx"
        return True, "成交量为 0 且最新价等于昨收，证券可能停牌或报价未更新"

    def _stock_industry(self, symbol: str) -> str:
        parsed = parse_symbol(symbol, stock_only=True)
        return _cached(
            f"stock-industry:{parsed.cache_key}",
            86400,
            "quotes",
            "baostock / eastmoney-push2",
            lambda: self._load_stock_industry(parsed),
        )

    def _load_stock_industry(self, symbol: SecuritySymbol) -> str:
        try:
            industry = self._load_stock_industry_baostock(symbol.qualified).strip()
            if industry:
                return industry
        except Exception:
            pass
        return str(self._load_stock_quote_eastmoney(symbol).get("industry") or "").strip()

    def _load_stock_industry_baostock(self, symbol: str) -> str:
        parsed = parse_symbol(symbol, stock_only=True)
        if parsed.market == "BJ":
            raise RuntimeError("BaoStock 不支持北交所证券")
        try:
            import baostock as bs
        except ImportError as exc:
            raise RuntimeError("未安装 baostock") from exc
        code = f"{parsed.prefix}.{parsed.code}"
        with _BAOSTOCK_LOCK:
            login = provider_call(bs.login)
            if login.error_code != "0":
                raise RuntimeError(login.error_msg)
            try:
                result = bs.query_stock_industry(code=code)
                if result.error_code != "0":
                    raise RuntimeError(result.error_msg)
                frame = result.get_data()
            finally:
                provider_call(bs.logout)
        if frame.empty:
            return ""
        return str(frame.iloc[0].get("industry") or "")

    def stock_detail(
        self,
        symbol: str,
        kline_count: int = 60,
        kline_period: str = "daily",
        price_adjustment: str = "qfq",
    ) -> dict[str, Any]:
        parsed = parse_symbol(symbol)
        code = parsed.code
        quote = self.stock_quote(parsed.qualified)
        adjustment = _normalize_price_adjustment(price_adjustment)

        def load_industry() -> str:
            if quote.get("industry") or parsed.market == "BJ":
                return str(quote.get("industry") or "")
            try:
                return self._stock_industry(parsed.qualified)
            except BusinessError:
                return ""

        def load_reports() -> list[dict[str, Any]]:
            try:
                return self.reports(symbol=code)[:3]
            except BusinessError:
                return []

        def load_news() -> list[dict[str, Any]]:
            try:
                return self._stock_news(code)[:5]
            except BusinessError:
                return []

        with ThreadPoolExecutor(max_workers=4, thread_name_prefix="stock-detail") as executor:
            kline_future = executor.submit(self._kline, parsed.qualified, kline_period, kline_count, adjustment)
            industry_future = executor.submit(load_industry)
            reports_future = executor.submit(load_reports)
            news_future = executor.submit(load_news)
            kline = kline_future.result()
            industry = industry_future.result()
            reports = reports_future.result()
            news = news_future.result()
        if industry and not quote.get("industry"):
            quote = dict(quote, industry=industry)
        finance = {
            "pe": quote.get("pe"),
            "pb": quote.get("pb"),
            "market_cap": quote.get("market_cap"),
            "float_market_cap": quote.get("float_market_cap"),
            "turnover_rate": quote.get("turnover_rate"),
        }
        return {
            "symbol": code,
            "quote": quote,
            "kline": kline,
            "finance": finance,
            "news": news,
            "score": self._score(kline, quote),
            "reports": reports,
        }

    def strategy_snapshot(
        self, symbol: str, kline_count: int = 60, kline_period: str = "daily", price_adjustment: str = "none"
    ) -> dict[str, Any]:
        """Price/volume and classification only; strategy stages do not need reports or news."""
        parsed = parse_symbol(symbol)
        quote = self.stock_quote(parsed.qualified)
        kline = self._kline(parsed.qualified, kline_period, kline_count, _normalize_price_adjustment(price_adjustment))
        industry = str(quote.get("industry") or "")
        if not industry and parsed.market != "BJ":
            try:
                industry = self._stock_industry(parsed.qualified)
            except BusinessError:
                industry = ""
        return {"symbol": parsed.code, "quote": quote, "kline": kline, "industry": industry}

    def _kline(self, symbol: str, period: str, count: int, price_adjustment: str = "qfq") -> list[dict[str, Any]]:
        period_value = period if period in {"daily", "weekly", "monthly"} else "daily"
        count_value = max(1, min(int(count), 240))
        adjustment = _normalize_price_adjustment(price_adjustment)
        key = f"kline:{symbol}:{period_value}:{count_value}:{adjustment}"

        def load() -> list[dict[str, Any]]:
            try:
                return self._load_kline_tencent(symbol, period_value, count_value, adjustment)
            except Exception as tencent_error:
                try:
                    return self._load_kline_eastmoney(symbol, period_value, count_value, adjustment)
                except Exception as eastmoney_error:
                    try:
                        return self._load_kline_baostock(symbol, period_value, count_value, adjustment)
                    except Exception as baostock_error:
                        raise RuntimeError(
                            f"Tencent: {tencent_error}; Eastmoney: {eastmoney_error}; BaoStock: {baostock_error}"
                        ) from baostock_error

        return _cached(
            key,
            _market_cache_ttl(300, 1800),
            "history",
            "tencent-fqkline / eastmoney-push2his / baostock",
            load,
        )

    def _load_kline_tencent(
        self,
        symbol: str,
        period: str,
        count: int,
        price_adjustment: str = "qfq",
        start_date: str = "",
        end_date: str = "",
    ) -> list[dict[str, Any]]:
        parsed = parse_symbol(symbol)
        frequency = {"daily": "day", "weekly": "week", "monthly": "month"}[period]
        adjustment = _normalize_price_adjustment(price_adjustment)
        fq_param = {"qfq": "qfq", "hfq": "hfq", "none": ""}[adjustment]
        response = _http_get(
            "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get",
            params={"param": f"{parsed.qualified},{frequency},{start_date},{end_date},{count},{fq_param}"},
            headers={"Referer": "https://gu.qq.com/"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict) or payload.get("code") not in (None, 0):
            raise RuntimeError(
                f"腾讯 K 线接口返回错误码 {payload.get('code') if isinstance(payload, dict) else 'unknown'}"
            )
        data = (payload.get("data") or {}).get(parsed.qualified) or {}
        prefix = "" if adjustment == "none" else adjustment
        values = data.get(f"{prefix}{frequency}") or data.get(frequency) or []
        rows = [
            {
                "date": item[0],
                "open": _number(item[1]),
                "close": _number(item[2]),
                "high": _number(item[3]),
                "low": _number(item[4]),
                "volume": _number(item[5]) * 100,
                "amount": _number(item[6]) if len(item) > 6 and not isinstance(item[6], dict) else 0,
                "adjust": adjustment,
                "data_source": f"tencent-fqkline-{adjustment}",
            }
            for item in values[-count:]
            if isinstance(item, list) and len(item) >= 6
        ]
        return self._validate_kline(rows, "腾讯")

    def _load_kline_eastmoney(
        self,
        symbol: str,
        period: str,
        count: int,
        price_adjustment: str = "qfq",
        start_date: str = "",
        end_date: str = "",
    ) -> list[dict[str, Any]]:
        klt = {"daily": 101, "weekly": 102, "monthly": 103}[period]
        adjustment = _normalize_price_adjustment(price_adjustment)
        fqt = {"none": 0, "qfq": 1, "hfq": 2}[adjustment]
        payload = self._get_json(
            "https://push2his.eastmoney.com/api/qt/stock/kline/get",
            {
                "secid": _secid(symbol),
                "klt": klt,
                "fqt": fqt,
                "lmt": count,
                "beg": start_date.replace("-", "") if start_date else "0",
                "end": end_date.replace("-", "") if end_date else 20500101,
                "fields1": "f1,f2,f3,f4,f5,f6,f7,f8",
                "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
            },
        )
        data = payload.get("data") or {}
        returned_code = str(data.get("code") or "")
        requested_code = _normalize_symbol(symbol)
        if returned_code and returned_code != requested_code:
            raise RuntimeError(f"东财 K 线返回代码 {returned_code}，与请求 {requested_code} 不一致")
        values = data.get("klines") or []
        if not values:
            raise RuntimeError("历史行情接口返回空数据")
        rows = []
        for value in values:
            parts = value.split(",")
            if len(parts) < 11:
                continue
            rows.append(
                {
                    "date": parts[0],
                    "open": _number(parts[1]),
                    "close": _number(parts[2]),
                    "high": _number(parts[3]),
                    "low": _number(parts[4]),
                    "volume": _number(parts[5]),
                    "amount": _number(parts[6]),
                    "amplitude": _number(parts[7]),
                    "change_pct": _number(parts[8]),
                    "change": _number(parts[9]),
                    "turnover_rate": _number(parts[10]),
                    "adjust": adjustment,
                    "data_source": f"eastmoney-push2his-{adjustment}",
                }
            )
        return self._validate_kline(rows, "东财")

    def _load_kline_baostock(
        self,
        symbol: str,
        period: str,
        count: int,
        price_adjustment: str = "qfq",
        start_date: str = "",
        end_date: str = "",
    ) -> list[dict[str, Any]]:
        parsed = parse_symbol(symbol)
        if parsed.market == "BJ":
            raise RuntimeError("BaoStock 不支持北交所历史行情")
        try:
            import baostock as bs
        except ImportError as exc:
            raise RuntimeError("未安装 baostock") from exc
        frequency = {"daily": "d", "weekly": "w", "monthly": "m"}[period]
        adjustment = _normalize_price_adjustment(price_adjustment)
        adjustflag = {"hfq": "1", "qfq": "2", "none": "3"}[adjustment]
        code = f"{parsed.prefix}.{parsed.code}"
        end = datetime.fromisoformat(end_date).date() if end_date else datetime.now(SHANGHAI_TZ).date()
        start = datetime.fromisoformat(start_date).date() if start_date else end - timedelta(days=max(count * 3, 400))
        with _BAOSTOCK_LOCK:
            login = provider_call(bs.login)
            if login.error_code != "0":
                raise RuntimeError(login.error_msg)
            try:
                result = bs.query_history_k_data_plus(
                    code,
                    "date,open,high,low,close,volume,amount,pctChg,turn",
                    start_date=start.isoformat(),
                    end_date=end.isoformat(),
                    frequency=frequency,
                    adjustflag=adjustflag,
                )
                records = []
                while result.error_code == "0" and result.next():
                    records.append(result.get_row_data())
                if result.error_code != "0":
                    raise RuntimeError(result.error_msg)
            finally:
                provider_call(bs.logout)
        rows = [
            {
                "date": item[0],
                "open": _number(item[1]),
                "high": _number(item[2]),
                "low": _number(item[3]),
                "close": _number(item[4]),
                "volume": _number(item[5]),
                "amount": _number(item[6]),
                "change_pct": _number(item[7]),
                "turnover_rate": _number(item[8]),
                "adjust": adjustment,
                "data_source": f"baostock-{adjustment}",
            }
            for item in records[-count:]
        ]
        return self._validate_kline(rows, "BaoStock")

    @staticmethod
    def _validate_kline(rows: list[dict[str, Any]], source: str) -> list[dict[str, Any]]:
        if not rows:
            raise RuntimeError(f"{source} 返回空 K 线")
        dates = [str(row.get("date") or "") for row in rows]
        if dates != sorted(dates) or len(dates) != len(set(dates)):
            raise RuntimeError(f"{source} K 线日期无序或重复")
        for row in rows:
            open_price = float(row.get("open") or 0)
            close_price = float(row.get("close") or 0)
            high = float(row.get("high") or 0)
            low = float(row.get("low") or 0)
            if min(open_price, close_price, high, low) <= 0 or high < max(open_price, close_price, low):
                raise RuntimeError(f"{source} K 线包含无效 OHLC 数据")
            if low > min(open_price, close_price, high):
                raise RuntimeError(f"{source} K 线包含无效最低价")
        return rows

    def list_news(self, category: str | None = None, keyword: str | None = None) -> list[dict[str, Any]]:
        items = _cached(
            "global-news",
            120,
            "news",
            "eastmoney-fast-news / sina-7x24",
            self._load_global_news_with_fallback,
        )
        if category:
            items = [item for item in items if item["category"] == category]
        if keyword:
            items = [item for item in items if keyword in f"{item['title']}{item['summary']}"]
        return items

    def _load_global_news_with_fallback(self) -> list[dict[str, Any]]:
        try:
            items = self._load_global_news()
            if items:
                return items
        except Exception:
            pass
        return self._load_global_news_sina()

    def _load_global_news(self) -> list[dict[str, Any]]:
        payload = self._get_json(
            "https://np-weblist.eastmoney.com/comm/web/getFastNewsList",
            {
                "client": "web",
                "biz": "web_724",
                "fastColumn": "102",
                "sortEnd": "",
                "pageSize": 100,
                "req_trace": str(int(time.time() * 1000)),
            },
            referer="https://kuaixun.eastmoney.com/7_24.html",
        )
        values = (payload.get("data") or {}).get("fastNewsList") or []
        if not values:
            raise RuntimeError("财经快讯接口返回空数据")
        fetched_at = utc_now_iso()
        items = []
        for index, value in enumerate(values, start=1):
            title = html.unescape(str(value.get("title") or "")).strip()
            summary = html.unescape(str(value.get("summary") or "")).strip()
            code = str(value.get("code") or index)
            stock_list = value.get("stockList") or []
            symbols = []
            for stock in stock_list:
                raw_code = stock.get("code") if isinstance(stock, dict) else stock
                if raw_code:
                    symbols.append(str(raw_code).split(".")[-1])
            items.append(
                {
                    "id": _stable_id(code),
                    "source": "东方财富财经快讯",
                    "category": self._news_category(title, summary, bool(stock_list)),
                    "title": title,
                    "summary": summary,
                    "url": f"https://finance.eastmoney.com/a/{code}.html",
                    "published_at": self._news_time(value.get("showTime")),
                    "fetched_at": fetched_at,
                    "keywords": self._keywords(f"{title} {summary}"),
                    "sentiment": self._sentiment(f"{title} {summary}"),
                    "symbols": symbols,
                }
            )
        return items

    def _load_global_news_sina(self) -> list[dict[str, Any]]:
        values = self._load_sina_feed(50)
        fetched_at = utc_now_iso()
        items = []
        for value in values:
            try:
                extension, symbols = self._parse_sina_extension(value)
            except (TypeError, ValueError, json.JSONDecodeError):
                continue
            content = self._strip_tags(value.get("rich_text") or "")
            if not content:
                continue
            title_match = re.match(r"^【([^】]+)】", content)
            title = title_match.group(1) if title_match else content[:60]
            url = extension.get("docurl") or value.get("docurl") or "https://finance.sina.com.cn/7x24/"
            items.append(
                {
                    "id": _stable_id(str(value.get("id") or url or content)),
                    "source": "新浪7x24",
                    "category": self._news_category(title, content, bool(symbols)),
                    "title": title,
                    "summary": content,
                    "url": url,
                    "published_at": self._news_time(value.get("create_time")),
                    "fetched_at": fetched_at,
                    "keywords": self._keywords(content),
                    "sentiment": self._sentiment(content),
                    "symbols": symbols,
                }
            )
        if not items:
            raise RuntimeError("新浪 7x24 返回空数据")
        return items

    def _stock_news(self, symbol: str) -> list[dict[str, Any]]:
        return _cached(
            f"stock-news:{symbol}",
            300,
            "news",
            "eastmoney-search / sina-7x24",
            lambda: self._load_stock_news_with_fallback(symbol),
        )

    def _load_stock_news_with_fallback(self, symbol: str) -> list[dict[str, Any]]:
        try:
            items = self._load_stock_news(symbol)
            if items:
                return items
        except Exception:
            pass
        return self._load_stock_news_sina(symbol)

    def _load_stock_news(self, symbol: str) -> list[dict[str, Any]]:
        callback = f"jQuery{int(time.time() * 1000)}"
        inner = {
            "uid": "",
            "keyword": symbol,
            "type": ["cmsArticleWebOld"],
            "client": "web",
            "clientType": "web",
            "clientVersion": "curr",
            "param": {
                "cmsArticleWebOld": {
                    "searchScope": "default",
                    "sort": "default",
                    "pageIndex": 1,
                    "pageSize": 10,
                    "preTag": "<em>",
                    "postTag": "</em>",
                }
            },
        }
        response = _http_get(
            "https://search-api-web.eastmoney.com/search/jsonp",
            params={"cb": callback, "param": json.dumps(inner, ensure_ascii=False), "_": int(time.time() * 1000)},
            headers={"Referer": f"https://so.eastmoney.com/news/s?keyword={symbol}"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        text = response.text.strip()
        start = text.find("(")
        end = text.rfind(")")
        if start < 0 or end <= start:
            raise RuntimeError("个股新闻接口格式异常")
        payload = json.loads(text[start + 1 : end])
        values = (payload.get("result") or {}).get("cmsArticleWebOld") or []
        if not isinstance(values, list):
            raise RuntimeError("个股新闻接口文章字段格式异常")
        fetched_at = utc_now_iso()
        items = []
        for value in values:
            title = self._strip_tags(value.get("title") or "")
            summary = self._strip_tags(value.get("content") or "")
            code = str(value.get("code") or title)
            items.append(
                {
                    "id": _stable_id(code),
                    "source": value.get("mediaName") or "东方财富",
                    "category": "company",
                    "title": title,
                    "summary": summary,
                    "url": f"https://finance.eastmoney.com/a/{code}.html",
                    "published_at": self._news_time(value.get("date")),
                    "fetched_at": fetched_at,
                    "keywords": [symbol, *self._keywords(f"{title} {summary}")[:4]],
                    "sentiment": self._sentiment(f"{title} {summary}"),
                    "symbols": [symbol],
                    "source_symbols": [],
                    "entity_source": "search_query",
                }
            )
        return items

    def _load_stock_news_sina(self, symbol: str) -> list[dict[str, Any]]:
        values = self._load_sina_feed(100)
        fetched_at = utc_now_iso()
        items = []
        for value in values:
            try:
                extension, codes = self._parse_sina_extension(value)
            except (TypeError, ValueError, json.JSONDecodeError):
                continue
            if symbol not in codes:
                continue
            content = self._strip_tags(value.get("rich_text") or "")
            title_match = re.match(r"^【([^】]+)】", content)
            title = title_match.group(1) if title_match else content[:60]
            url = extension.get("docurl") or value.get("docurl") or "https://finance.sina.com.cn/7x24/"
            items.append(
                {
                    "id": _stable_id(str(value.get("id") or url or content)),
                    "source": "新浪7x24",
                    "category": "company",
                    "title": title,
                    "summary": content,
                    "url": url,
                    "published_at": self._news_time(value.get("create_time")),
                    "fetched_at": fetched_at,
                    "keywords": [symbol, *self._keywords(content)[:4]],
                    "sentiment": self._sentiment(content),
                    "symbols": [symbol],
                    "source_symbols": codes,
                    "entity_source": "provider_security_tags",
                }
            )
        return items

    def _load_sina_feed(self, page_size: int) -> list[dict[str, Any]]:
        response = _http_get(
            "https://zhibo.sina.com.cn/api/zhibo/feed",
            params={"zhibo_id": 152, "page_size": max(1, min(page_size, 100)), "dire": "f"},
            headers={"Referer": "https://finance.sina.com.cn/", "User-Agent": USER_AGENT},
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        values = (((payload.get("result") or {}).get("data") or {}).get("feed") or {}).get("list") or []
        if not isinstance(values, list):
            raise RuntimeError("新浪 7x24 返回格式异常")
        return values

    @staticmethod
    def _parse_sina_extension(value: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
        if not isinstance(value, dict):
            raise TypeError("新浪 7x24 条目格式异常")
        extension = value.get("ext") or {}
        if isinstance(extension, str):
            extension = json.loads(extension)
        if not isinstance(extension, dict):
            raise TypeError("新浪 7x24 ext 字段格式异常")
        stocks = extension.get("stocks") or []
        codes = [
            re.sub(r"^(?:sh|sz|bj)", "", str(stock.get("symbol") or "")) for stock in stocks if isinstance(stock, dict)
        ]
        return extension, [code for code in codes if code]

    def keyword_cloud(self, category: str | None = None, top_n: int = 50) -> list[dict[str, Any]]:
        counts: dict[str, int] = {}
        for item in self.list_news(category=category):
            for keyword in item.get("keywords") or []:
                counts[keyword] = counts.get(keyword, 0) + 1
        total = max(sum(counts.values()), 1)
        return [
            {
                "keyword": keyword,
                "count": count,
                "weight": round(count / total, 4),
                "sentiment": "neutral",
            }
            for keyword, count in sorted(counts.items(), key=lambda pair: pair[1], reverse=True)[:top_n]
        ]

    def reports(self, keyword: str | None = None, symbol: str | None = None) -> list[dict[str, Any]]:
        code = _normalize_symbol(symbol, stock_only=True) if symbol else ""
        items = _cached(
            f"reports:{code or 'latest'}",
            900,
            "reports",
            "eastmoney-report",
            lambda: self._load_reports(code),
        )
        if keyword:
            items = [item for item in items if keyword in f"{item['title']}{item['org']}{item['analyst']}"]
        return items

    def _load_reports(self, symbol: str) -> list[dict[str, Any]]:
        today = datetime.now(SHANGHAI_TZ).date()
        payload = self._get_json(
            "https://reportapi.eastmoney.com/report/list",
            {
                "industryCode": "*",
                "pageSize": 50,
                "industry": "*",
                "rating": "*",
                "ratingChange": "*",
                "beginTime": (today - timedelta(days=400)).isoformat(),
                "endTime": (today + timedelta(days=1)).isoformat(),
                "pageNo": 1,
                "fields": "",
                "qType": 0,
                "orgCode": "",
                "code": symbol,
                "rcode": "",
                "p": 1,
                "pageNum": 1,
                "pageNumber": 1,
            },
            referer="https://data.eastmoney.com/report/stock.jshtml",
        )
        values = payload.get("data") or []
        if not values:
            raise RuntimeError("研报接口返回空数据")
        items = []
        for value in values:
            info_code = str(value.get("infoCode") or value.get("title"))
            stock_code = str(value.get("stockCode") or "")
            items.append(
                {
                    "id": _stable_id(info_code),
                    "title": value.get("title") or "",
                    "org": value.get("orgSName") or value.get("orgName") or "",
                    "analyst": value.get("researcher") or "",
                    "rating": value.get("emRatingName") or "",
                    "symbols": [stock_code] if stock_code else [],
                    "stock_name": value.get("stockName") or "",
                    "industry": value.get("indvInduName") or "",
                    "pages": _integer(value.get("attachPages")),
                    "publish_date": str(value.get("publishDate") or "")[:10],
                    "source": "eastmoney-report",
                    "url": f"https://pdf.dfcfw.com/pdf/H3_{info_code}_1.pdf",
                    "body": "",
                }
            )
        return items

    def report_detail(self, report_id: int) -> dict[str, Any] | None:
        for item in self.reports():
            if int(item["id"]) == int(report_id):
                return dict(item, charts=[])
        return None

    def paper_search(
        self,
        keyword: str = "",
        year_from: int | None = None,
        year_to: int | None = None,
    ) -> list[dict[str, Any]]:
        query = f'all:"{keyword}" AND cat:q-fin.*' if keyword else "cat:q-fin.*"
        items = _cached(
            f"arxiv:{query}",
            1800,
            "papers",
            "arxiv",
            lambda: self._load_arxiv(query),
        )
        if year_from:
            items = [item for item in items if int(item["published_at"][:4]) >= year_from]
        if year_to:
            items = [item for item in items if int(item["published_at"][:4]) <= year_to]
        return items

    def _load_arxiv(self, query: str) -> list[dict[str, Any]]:
        response = _http_get(
            "https://export.arxiv.org/api/query",
            params={
                "search_query": query,
                "start": 0,
                "max_results": 50,
                "sortBy": "submittedDate",
                "sortOrder": "descending",
            },
            headers={"User-Agent": "b001-all-in-one/0.1 research@example.invalid"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        root = ElementTree.fromstring(response.content)
        atom = "{http://www.w3.org/2005/Atom}"
        items = []
        for entry in root.findall(f"{atom}entry"):
            identifier = (entry.findtext(f"{atom}id") or "").strip()
            title = " ".join((entry.findtext(f"{atom}title") or "").split())
            abstract = " ".join((entry.findtext(f"{atom}summary") or "").split())
            published = (entry.findtext(f"{atom}published") or "")[:10]
            authors = [(author.findtext(f"{atom}name") or "").strip() for author in entry.findall(f"{atom}author")]
            items.append(
                {
                    "id": _stable_id(identifier),
                    "title": title,
                    "authors": authors,
                    "abstract": abstract,
                    "source": "arXiv",
                    "published_at": published,
                    "url": identifier,
                    "is_favorite": False,
                }
            )
        if not items:
            raise RuntimeError("arXiv 返回空数据")
        return items

    def heatmap(
        self,
        level: str = "industry",
        board: str | None = None,
        threshold: float = 0.0,
    ) -> list[dict[str, Any]]:
        return [
            {
                "name": item["name"],
                "code": item["code"],
                "value": item["amount"],
                "change_pct": item["change_pct"],
                "children": [],
                "data_source": SOURCE_NAME,
            }
            for item in self.sectors(board=board or level, limit=100)
            if float(item["amount"]) >= threshold
        ]

    def relation_graph(self, symbol: str, depth: int = 1) -> dict[str, Any]:
        parsed = parse_symbol(symbol, stock_only=True)
        quote = self.stock_quote(parsed.qualified)
        bounded_depth = max(1, min(int(depth or 1), 5))
        return _RelationGraphBuilder(self, parsed, quote).build(bounded_depth)

    def _stock_boards(self, symbol: str) -> dict[str, Any]:
        """个股资料中的所属板块：一级行业、精确概念、宽基指数（日级缓存）。"""
        parsed = parse_symbol(symbol, stock_only=True)
        return _cached(
            f"stock-boards:{parsed.cache_key}",
            86400,
            "quotes",
            "eastmoney-f10-coreconception",
            lambda: self._load_stock_boards(parsed),
        )

    def _load_stock_boards(self, symbol: SecuritySymbol) -> dict[str, Any]:
        payload = self._get_json(
            "https://emweb.securities.eastmoney.com/PC_HSF10/CoreConception/PageAjax",
            {"code": f"{symbol.market}{symbol.code}"},
            referer="https://emweb.securities.eastmoney.com/",
        )
        rows = payload.get("ssbk") or []
        industry: dict[str, str] | None = None
        concepts: list[dict[str, str]] = []
        indices: list[dict[str, str]] = []
        for row in rows:
            code = str(row.get("BOARD_CODE") or "").strip()
            name = str(row.get("BOARD_NAME") or "").strip()
            if not code or not name:
                continue
            board_code = f"BK{code.zfill(4)}"
            rank = int(row.get("BOARD_RANK") or 0)
            if rank == 1:
                industry = {"code": board_code, "name": name}
            elif self._is_index_board(name):
                display_name = _INDEX_BOARD_DISPLAY_NAMES.get(code, name.rstrip("_"))
                indices.append({"code": f"IDX:{code}", "name": display_name})
            elif str(row.get("IS_PRECISE")) == "1":
                concepts.append({"code": board_code, "name": name})
        return {"industry": industry, "concepts": concepts[:6], "indices": indices[:4]}

    @staticmethod
    def _is_index_board(name: str) -> bool:
        return any(keyword in name for keyword in _INDEX_BOARD_KEYWORDS)

    def _board_members(self, board_code: str, board_name: str = "") -> list[dict[str, Any]]:
        """板块成分股（按涨幅排序，30 分钟缓存，push2 多主机失败后回退新浪节点）。"""
        return _cached(
            f"board-members:{board_code}",
            1800,
            "quotes",
            "eastmoney-push2 / sina-node",
            lambda: self._load_board_members(board_code, board_name),
        )

    def _load_board_members(self, board_code: str, board_name: str = "") -> list[dict[str, Any]]:
        params = {
            "pn": 1,
            "pz": 30,
            "po": 1,
            "np": 1,
            "ut": "bd1d9ddb04089700cf9c27f6f7426281",
            "fltt": 2,
            "invt": 2,
            "fid": "f3",
            "fs": f"b:{board_code}",
            "fields": "f12,f14,f3",
        }
        last_error: Exception | None = None
        for host in ("17.push2.eastmoney.com", "1.push2.eastmoney.com", "82.push2.eastmoney.com"):
            try:
                payload = self._get_json(f"https://{host}/api/qt/clist/get", params)
                rows = (payload.get("data") or {}).get("diff") or []
                if isinstance(rows, dict):
                    rows = list(rows.values())
                if rows:
                    return [
                        {
                            "code": str(item.get("f12") or ""),
                            "name": item.get("f14") or item.get("f12"),
                            "change_pct": _number(item.get("f3")),
                            "data_source": SOURCE_NAME,
                        }
                        for item in rows
                        if item.get("f12")
                    ]
            except Exception as exc:  # noqa: BLE001
                last_error = exc
        try:
            return self._load_board_members_sina(board_name)
        except Exception as sina_error:  # noqa: BLE001
            raise RuntimeError(
                f"板块 {board_code} 成分接口不可用：push2={last_error}; sina={sina_error}"
            ) from sina_error

    def _load_board_members_sina(self, board_name: str) -> list[dict[str, Any]]:
        node_code = self._sina_board_node(board_name)
        if not node_code:
            raise RuntimeError(f"新浪板块节点未匹配到 {board_name or '(空名称)'}")
        response = _http_get(
            "https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeData",
            params={
                "page": 1,
                "num": 30,
                "sort": "changepercent",
                "asc": 0,
                "node": node_code,
                "symbol": "",
                "_s_r_a": "sort",
            },
            headers={"Referer": "https://finance.sina.com.cn/"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        rows = json.loads(response.text)
        if not isinstance(rows, list) or not rows:
            raise RuntimeError(f"新浪节点 {node_code} 返回空成分数据")
        return [
            {
                "code": str(item.get("code") or ""),
                "name": item.get("name") or item.get("code"),
                "change_pct": _number(item.get("changepercent")),
                "data_source": "sina-node",
            }
            for item in rows
            if item.get("code")
        ]

    def _sina_board_node(self, board_name: str) -> str:
        candidates: list[dict[str, Any]] = []
        for board in ("industry", "concept"):
            try:
                candidates.extend(self.sectors(board=board, limit=100))
            except Exception:  # noqa: BLE001
                continue
        target = board_name.strip()
        if not target or not candidates:
            return ""
        exact = next((item for item in candidates if str(item.get("name")) == target), None)
        if exact:
            return str(exact["code"])
        substring = next(
            (item for item in candidates if target in str(item.get("name")) or str(item.get("name")) in target),
            None,
        )
        if substring:
            return str(substring["code"])
        # 分类口径不同（如东财「食品饮料」对新浪「食品行业」），取最相近节点兜底
        best_item, best_ratio = max(
            ((item, SequenceMatcher(None, target, str(item.get("name"))).ratio()) for item in candidates),
            key=lambda pair: pair[1],
            default=(None, 0.0),
        )
        return str(best_item["code"]) if best_item is not None and best_ratio >= 0.5 else ""

    def _top_holders(self, symbol: str, limit: int = 3) -> list[dict[str, Any]]:
        """最新一期十大股东（日级缓存）。"""
        parsed = parse_symbol(symbol, stock_only=True)
        return _cached(
            f"stock-holders:{parsed.cache_key}",
            86400,
            "quotes",
            "eastmoney-datacenter",
            lambda: self._load_top_holders(parsed, limit),
        )

    def _load_top_holders(self, symbol: SecuritySymbol, limit: int) -> list[dict[str, Any]]:
        response = _http_get(
            "https://datacenter.eastmoney.com/securities/api/data/v1/get",
            params={
                "reportName": "RPT_F10_EH_HOLDERS",
                "columns": "END_DATE,HOLDER_NAME,HOLDER_RANK",
                "filter": f'(SECUCODE="{symbol.code}.{symbol.market}")',
                "pageNumber": 1,
                "pageSize": max(1, min(int(limit), 10)),
                "sortColumns": "END_DATE,HOLDER_RANK",
                "sortTypes": "-1,1",
                "source": "F10",
                "client": "PC",
            },
            headers={"Referer": "https://emweb.securities.eastmoney.com/"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        rows = ((response.json().get("result") or {}).get("data")) or []
        if not rows:
            raise RuntimeError(f"{symbol.qualified} 十大股东接口返回空数据")
        latest_date = str(rows[0].get("END_DATE") or "")
        return [
            {
                "rank": int(row.get("HOLDER_RANK") or 0),
                "name": str(row.get("HOLDER_NAME") or "").strip(),
                "end_date": str(row.get("END_DATE") or "")[:10],
            }
            for row in rows
            if str(row.get("END_DATE") or "")[:10] == latest_date[:10] and row.get("HOLDER_NAME")
        ][:limit]

    def _get_json(
        self,
        url: str,
        params: dict[str, Any],
        referer: str | None = None,
    ) -> dict[str, Any]:
        headers = {"Referer": referer} if referer else None
        response = _http_get(url, params=params, headers=headers, timeout=self.timeout)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise RuntimeError("接口未返回 JSON 对象")
        if payload.get("rc") not in (None, 0):
            raise RuntimeError(f"接口返回错误码 {payload.get('rc')}")
        return payload

    @staticmethod
    def _news_time(value: Any) -> str:
        text = str(value or "").strip()
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            return datetime.now(SHANGHAI_TZ).replace(microsecond=0).isoformat()
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=SHANGHAI_TZ)
        return parsed.isoformat()

    @staticmethod
    def _strip_tags(value: str) -> str:
        return html.unescape(re.sub(r"<[^>]+>", "", str(value))).replace("\u3000", " ").strip()

    @staticmethod
    def _keywords(text: str) -> list[str]:
        matched = [term for term in _FINANCIAL_TERMS if term.lower() in text.lower()]
        if matched:
            return matched[:6]
        candidates = re.findall(r"[A-Za-z]{2,12}|[\u4e00-\u9fff]{2,4}", text)
        stopwords = {"表示", "目前", "相关", "进行", "已经", "以及", "其中", "今日", "消息"}
        return list(dict.fromkeys(item for item in candidates if item not in stopwords))[:5]

    @staticmethod
    def _news_category(title: str, summary: str, has_stocks: bool) -> str:
        text = f"{title}{summary}"
        if has_stocks or any(word in text for word in ("公司", "股份", "集团", "中报", "年报")):
            return "company"
        if any(word in text for word in ("美国", "欧洲", "海外", "日本", "韩国", "伊朗", "俄乌", "美联储")):
            return "international"
        if any(word in text for word in ("国务院", "国家", "我国", "中国", "部门", "政策")):
            return "domestic"
        return "finance"

    @staticmethod
    def _sentiment(text: str) -> str:
        positive = sum(word in text for word in ("增长", "上涨", "突破", "改善", "利好", "盈利", "增持"))
        negative = sum(word in text for word in ("下降", "下跌", "亏损", "风险", "减持", "违约", "袭击"))
        if positive > negative:
            return "positive"
        if negative > positive:
            return "negative"
        return "neutral"

    @staticmethod
    def _score(kline: list[dict[str, Any]], quote: dict[str, Any]) -> dict[str, float]:
        closes = [float(item["close"]) for item in kline]
        volumes = [float(item["volume"]) for item in kline]
        latest = closes[-1]
        ma20 = sum(closes[-20:]) / min(len(closes), 20)
        momentum = (latest / closes[max(0, len(closes) - 20)] - 1) if len(closes) > 1 else 0.0
        trend = max(0.0, min(100.0, 50 + (latest / max(ma20, 0.01) - 1) * 500))
        momentum_score = max(0.0, min(100.0, 50 + momentum * 250))
        average_volume = sum(volumes[-20:]) / min(len(volumes), 20)
        volume_score = max(0.0, min(100.0, 50 + (volumes[-1] / max(average_volume, 1) - 1) * 30))
        pe = float(quote.get("pe") or 0)
        pb = float(quote.get("pb") or 0)
        valuation = 50.0
        if pe > 0:
            valuation += max(-25.0, min(25.0, (25 - pe) * 1.2))
        if pb > 0:
            valuation += max(-15.0, min(15.0, (3 - pb) * 4))
        valuation = max(0.0, min(100.0, valuation))
        total = trend * 0.35 + momentum_score * 0.25 + volume_score * 0.15 + valuation * 0.25
        return {
            "total": round(total, 1),
            "trend": round(trend, 1),
            "momentum": round(momentum_score, 1),
            "volume": round(volume_score, 1),
            "valuation": round(valuation, 1),
        }
