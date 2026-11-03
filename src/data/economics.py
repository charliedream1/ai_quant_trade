"""Bounded public-source requests using the platform's pinned network policy."""

import json
import re
import time
from datetime import datetime

from loguru import logger

from src.core.network_policy import network_session
from src.core.stream_control import stream_cancelled
from src.core.timeutil import utc_now_iso
from src.engine.economics.config import economics_config
from src.engine.economics.store import EconomicStore, digest


class EconomicDataSource:
    def __init__(self, store: EconomicStore | None = None):
        self.store = store or EconomicStore()
        self.config = economics_config()

    def fetch(self, name: str, *, symbol: str = "", refresh: bool = False) -> dict:
        config, sources = self.config, self.config["sources"]
        social = name == "social_finance"
        definition = config["statements" if symbol else "macro"][name]
        params = (
            {}
            if social
            else {
                **sources["params"],
                "reportName": definition["report"],
                "pageSize": config["defaults"]["financial_rows" if symbol else "source_rows"],
                "sortColumns": definition.get("date", "REPORT_DATE"),
            }
        )
        if symbol:
            if not re.fullmatch(r"\d{6}\.(SH|SZ|BJ)", symbol):
                raise ValueError("Invalid A-share source identifier")
            params["filter"] = f'(SECUCODE="{symbol}")'
        url = sources["social_finance" if social else "eastmoney"]
        key = digest({"url": url, "params": params})
        cached = self.store.cached(key)
        if cached and not refresh:
            age = time.time() - datetime.fromisoformat(cached["checked_at"]).timestamp()
            if age < config["defaults"]["cache_seconds"]:
                return cached
        body = self._request(url, params, social)
        rows = body if social else (body.get("result") or {}).get("data")
        if not isinstance(rows, list) or not rows or any(not isinstance(row, dict) for row in rows):
            raise ValueError(config["messages"]["empty"])
        now = utc_now_iso()
        revision = self.store.save({"source_key": key, "raw": body})
        first_seen = self.store.first_seen(revision["snapshot_id"], now)
        result = {
            "rows": rows,
            "checked_at": now,
            "first_seen_at": first_seen,
            "version": revision["snapshot_id"],
            "source": "MOFCOM" if social else "Eastmoney",
            "url": sources["social_reference"]
            if social
            else sources["financial_reference"]
            if symbol
            else sources["macro_reference"] + definition["reference"],
            "historical_pit_eligible": False,
        }
        self.store.cache(key, result)
        return result

    def _request(self, url: str, params: dict, social: bool):
        policy = self.config["defaults"]
        started = time.monotonic()
        with network_session(public_only=True) as session:
            with session.request(
                "POST" if social else "GET",
                url,
                params=params,
                timeout=(policy["connect_seconds"], policy["read_seconds"]),
                allow_redirects=False,
                stream=True,
            ) as response:
                response.raise_for_status()
                if response.status_code >= 300:
                    raise ValueError("Economic sources cannot redirect requests")
                content = bytearray()
                for chunk in response.iter_content(chunk_size=policy["read_chunk_bytes"]):
                    if stream_cancelled() or time.monotonic() - started > policy["fetch_seconds"]:
                        raise TimeoutError("Economic source request cancelled or timed out")
                    content.extend(chunk)
                    if len(content) > policy["max_response_bytes"]:
                        raise ValueError("Economic source response exceeds the configured budget")
        logger.info(
            "Economic source fetched | bytes={} duration_ms={:.1f}", len(content), (time.monotonic() - started) * 1000
        )
        return json.loads(content)
