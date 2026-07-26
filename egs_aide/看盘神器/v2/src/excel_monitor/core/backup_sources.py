# -*- coding: utf-8 -*-
"""备选数据源集合：当主数据源 (qstock) 失败时提供 fallback

本模块参考 egs_data/ 目录下的数据源示例实现，封装了以下数据源：
    - AKShare     (egs_data/akshare/akshare_demo.py, egs_data/news/news_demo.py)
    - 东方财富 API (egs_data/eastmoney/eastmoney_api.py, egs_data/eastmoney/eastmoney_news_guba.py)
    - 腾讯财经 API (egs_data/tencent/tencent_api.py)
    - 网易财经 API (egs_data/netease/netease_api.py)
    - efinance    (egs_data/efinance/efinance_demo.py)

设计原则：
    1. 延迟导入：akshare/efinance 等较重的库在首次调用时才 import，避免启动时拖慢
    2. 单点失败不影响整体：每个方法独立 try-except，失败返回空 DataFrame
    3. 统一返回 DataFrame，列名与 qstock 风格对齐（"代码" / "名称" / "最新" / "涨幅" 等）
    4. 同一数据类型可能有多个备选源，由 DataProvider 决定调用顺序
"""
import traceback
from typing import List, Optional

import pandas as pd

from excel_monitor.logger import get_logger


# === HTTP 公共配置（仅 eastmoney / tencent / netease 直接请求时用） ===
_HTTP_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://quote.eastmoney.com/",
}

# 国内财经 API 不应走系统代理（用户多为科学上网场景，代理对国内站点反而失败）
_NO_PROXY = {"http": None, "https": None}


def _safe_int(val, default=0):
    """安全转 int，失败返回 default"""
    try:
        if val is None or val == "":
            return default
        return int(float(val))
    except (ValueError, TypeError):
        return default


def _safe_float(val, default=None):
    """安全转 float，失败返回 default"""
    try:
        if val is None or val == "":
            return default
        return float(val)
    except (ValueError, TypeError):
        return default


def _detect_market_prefix(code: str) -> str:
    """根据 6 位代码判断市场前缀
    返回值用于 eastmoney/tencent/netease 等接口：
        沪市: "1" (eastmoney secid 第一段) / "sh" (tencent)
        深市: "0" / "sz"
    此函数返回 "sh" / "sz" / "bj" 三种之一
    """
    code = str(code).strip()
    # 已带前缀
    if code.lower().startswith(("sh", "sz", "bj")):
        return code.lower()[:2]
    # 6 位代码
    if code.startswith(("60", "68", "9", "11", "13")):
        return "sh"  # 沪市主板/科创板/B股/可转债
    if code.startswith(("00", "30", "12")):
        return "sz"  # 深市主板/创业板/可转债
    if code.startswith(("43", "83", "87", "88")):
        return "bj"  # 北交所
    return "sh"  # 默认按沪市处理


def _normalize_codes(code_list: List[str]) -> List[str]:
    """代码归一化：去除 .SH/.SZ 后缀，保留 6 位数字代码"""
    result = []
    for c in code_list:
        c = str(c).strip()
        if not c:
            continue
        # 去后缀
        if "." in c:
            c = c.split(".")[0]
        # 去市场前缀
        for prefix in ("sh", "sz", "bj"):
            if c.lower().startswith(prefix):
                c = c[2:]
                break
        result.append(c)
    return result


# =====================================================================
# 数据源类
# =====================================================================
class BackupSources:
    """备选数据源集合

    所有方法均返回 pandas.DataFrame（失败时返回空 DataFrame）。
    调用方无需关心底层库是否安装——延迟导入 + 异常捕获保证健壮性。
    """

    def __init__(self, config=None):
        self._logger = get_logger(self.__class__.__name__)
        # config 可为 AppConfig 或 dict，仅用于开关控制
        self._config = config or {}
        # 缓存已加载的库（避免重复 import）
        self._akshare = None
        self._efinance = None
        self._requests = None

    # === 库延迟加载（私有） ===
    def _get_akshare(self):
        if self._akshare is None:
            import akshare as ak
            self._akshare = ak
        return self._akshare

    def _get_baostock(self):
        """延迟加载 baostock（TCP 连接，登录一次后复用）"""
        if not hasattr(self, "_baostock") or self._baostock is None:
            import baostock as bs
            lg = bs.login()
            if lg.error_code != "0":
                self._logger.warning(f"[baostock] 登录失败: {lg.error_msg}")
                self._baostock = None
            else:
                self._baostock = bs
        return self._baostock

    def _get_efinance(self):
        if self._efinance is None:
            import efinance as ef
            self._efinance = ef
        return self._efinance

    def _get_requests(self):
        if self._requests is None:
            import requests
            self._requests = requests
        return self._requests

    # =================================================================
    # AKShare 备选源（参考 egs_data/akshare/akshare_demo.py + egs_data/news/news_demo.py）
    # =================================================================
    def akshare_stock_realtime(self, code_list: List[str]) -> pd.DataFrame:
        """AKShare: A 股实时行情（新浪主，东方财富备）

        返回字段对齐 qstock 风格：代码/名称/最新价/涨跌幅/涨跌额/成交量/成交额/
                                 换手率/最高/最低/今开/昨收

        注：
            1. code_list 可能是代码也可能是名称，两种都匹配
            2. 优先用新浪接口（更稳定，反爬少）；东方财富被反爬频率高
            3. 新浪接口返回的代码列带 sh/sz/bj 前缀，需归一化以方便后续匹配
        """
        try:
            ak = self._get_akshare()
            codes = _normalize_codes(code_list)
            if not codes and not code_list:
                return pd.DataFrame()

            # 优先用新浪接口（稳定）
            df = ak.stock_zh_a_spot()
            if df is not None and not df.empty:
                self._logger.info(f"[akshare] 使用新浪接口获取 {len(df)} 条实时行情")
                code_col = "代码" if "代码" in df.columns else df.columns[0]
                name_col = "名称" if "名称" in df.columns else df.columns[1]
                # 归一化代码列（去 sh/sz 前缀）以便匹配
                df[code_col] = df[code_col].astype(str).str.replace(
                    r"^(sh|sz|bj)", "", regex=True
                )
                mask_code = df[code_col].astype(str).isin(codes) if codes else pd.Series([False]*len(df))
                mask_name = df[name_col].astype(str).isin([str(c) for c in code_list if c and not str(c).strip().isdigit()])
                df = df[mask_code | mask_name].copy()
                return df.reset_index(drop=True)

            # 备选：东方财富接口
            try:
                df = ak.stock_zh_a_spot_em()
                if df is not None and not df.empty:
                    self._logger.info(f"[akshare] 使用东方财富接口获取 {len(df)} 条实时行情")
                    mask_code = df["代码"].astype(str).isin(codes) if codes else pd.Series([False]*len(df))
                    mask_name = df["名称"].astype(str).isin([str(c) for c in code_list if c and not str(c).strip().isdigit()])
                    df = df[mask_code | mask_name].copy()
                    rename = {
                        "最新价": "最新", "涨跌幅": "涨幅",
                        "成交量": "成交量", "成交额": "成交额", "换手率": "换手率",
                        "最高": "最高", "最低": "最低", "今开": "开盘", "昨收": "昨收",
                    }
                    df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})
                    return df.reset_index(drop=True)
            except Exception as e_em:
                self._logger.warning(f"[akshare] 东方财富接口失败: {e_em}")
            return pd.DataFrame()
        except Exception as e:
            self._logger.warning(f"[akshare] 获取个股实时行情失败: {e}")
            return pd.DataFrame()

    def akshare_index_realtime(self, code_list: List[str]) -> pd.DataFrame:
        """AKShare: 指数实时行情（优先新浪，东方财富备）

        qstock 接受指数简称（如 "上证指数"），akshare 需要代码（如 "000001"）。
        本方法尽量把常见简称映射到代码，未匹配的会被跳过。
        """
        try:
            ak = self._get_akshare()
            # 名称 → akshare 代码映射（覆盖 config.yaml 默认 7 个指数）
            name_to_code = {
                "上证指数": "000001", "深证成指": "399001",
                "创业板指": "399006", "沪深300": "000300",
                "上证50": "000016", "中证500": "000905",
                "科创50": "000688",
            }
            codes = []
            for c in code_list:
                c = str(c).strip()
                codes.append(name_to_code.get(c, c))
            if not codes:
                return pd.DataFrame()

            # 优先尝试新浪指数接口（稳定，反爬少）
            try:
                df = ak.stock_zh_index_spot_sina()
                if df is not None and not df.empty:
                    self._logger.info(f"[akshare] 使用新浪接口获取指数 {len(df)} 条")
                    # 新浪返回 "代码" 和 "名称" 列
                    if "代码" in df.columns:
                        df["代码"] = df["代码"].astype(str)
                        matched = df[df["代码"].isin([str(c) for c in codes])]
                        if not matched.empty:
                            rename = {
                                "最新价": "最新", "涨跌幅": "涨幅",
                                "涨跌额": "涨跌额", "成交量": "成交量",
                                "成交额": "成交额",
                            }
                            matched = matched.rename(columns={
                                k: v for k, v in rename.items() if k in matched.columns
                            })
                            return matched.reset_index(drop=True)
            except Exception as e_sina:
                self._logger.warning(f"[akshare] 新浪指数接口失败: {e_sina}")

            # 备选：东方财富指数接口
            try:
                df = ak.stock_zh_index_spot_em()
                if df is None or df.empty:
                    return pd.DataFrame()
                self._logger.info(f"[akshare] 使用东方财富接口获取指数 {len(df)} 条")
                rows = []
                for code in codes:
                    row = df[df["代码"].astype(str) == str(code)]
                    if not row.empty:
                        rows.append(row.iloc[0])
                if not rows:
                    return pd.DataFrame()
                df = pd.DataFrame(rows)
                rename = {
                    "最新价": "最新", "涨跌幅": "涨幅", "涨跌额": "涨跌额",
                    "成交量": "成交量", "成交额": "成交额",
                }
                df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})
                return df.reset_index(drop=True)
            except Exception as e_em:
                self._logger.warning(f"[akshare] 东方财富指数接口失败: {e_em}")

            # 最终备选：直接调用新浪行情接口（http://hq.sinajs.cn）
            return self._sina_index_direct(code_list)
        except Exception as e:
            self._logger.warning(f"[akshare] 获取指数行情失败: {e}")
            return pd.DataFrame()

    def _sina_index_direct(self, code_list: List[str]) -> pd.DataFrame:
        """新浪财经指数行情直连接口（最后兜底）

        接口: http://hq.sinajs.cn/list=sh000001,sz399001
        返回: var hq_str_sh000001="上证指数,3094.67,..."
        """
        try:
            requests = self._get_requests()
            name_to_sina = {
                "上证指数": "sh000001", "深证成指": "sz399001",
                "创业板指": "sz399006", "沪深300": "sh000300",
                "上证50": "sh000016", "中证500": "sh000905",
                "科创50": "sh000688",
            }
            sina_codes = []
            for c in code_list:
                c = str(c).strip()
                sina_codes.append(name_to_sina.get(c, c))
            if not sina_codes:
                return pd.DataFrame()
            url = f"http://hq.sinajs.cn/list={','.join(sina_codes)}"
            headers = {
                "User-Agent": _HTTP_HEADERS["User-Agent"],
                "Referer": "https://finance.sina.com.cn/",
            }
            r = requests.get(url, headers=headers, timeout=10, proxies=_NO_PROXY)
            r.encoding = "gbk"
            rows = []
            for line, orig_code in zip(r.text.strip().split("\n"), code_list):
                if "=" not in line:
                    continue
                try:
                    content = line.split("=", 1)[1].strip().strip(";").strip('"')
                    fields = content.split(",")
                    if len(fields) < 6:
                        continue
                    # 新浪指数格式：名称,开盘,昨收,最新,最高,最低,...
                    name = fields[0]
                    open_p = _safe_float(fields[1])
                    pre_close = _safe_float(fields[2])
                    price = _safe_float(fields[3])
                    high = _safe_float(fields[4])
                    low = _safe_float(fields[5])
                    change = (price - pre_close) if (price and pre_close) else None
                    change_pct = (change / pre_close * 100) if (change is not None and pre_close) else None
                    rows.append({
                        "代码": str(orig_code),
                        "名称": name,
                        "最新": price,
                        "开盘": open_p,
                        "昨收": pre_close,
                        "最高": high,
                        "最低": low,
                        "涨跌额": change,
                        "涨幅": change_pct,
                    })
                except Exception:
                    continue
            return pd.DataFrame(rows) if rows else pd.DataFrame()
        except Exception as e:
            self._logger.warning(f"[sina] 直连指数接口失败: {e}")
            return pd.DataFrame()

    def _call_with_timeout(self, fn, args=(), kwargs=None, timeout_sec=15):
        """线程方式调用函数并设置超时（避免 akshare 内部卡死）

        注意：线程无法真正终止正在执行的 Python 代码，但能让主线程
        不被卡住，继续执行后续逻辑。
        """
        import threading
        kwargs = kwargs or {}
        result = [None]
        error = [None]
        done = [False]

        def worker():
            try:
                result[0] = fn(*args, **kwargs)
            except Exception as e:
                error[0] = e
            finally:
                done[0] = True

        t = threading.Thread(target=worker, daemon=True)
        t.start()
        t.join(timeout=timeout_sec)
        if not done[0]:
            raise TimeoutError(f"调用超时（{timeout_sec}s）")
        if error[0]:
            raise error[0]
        return result[0]

    def akshare_news_cls(self) -> pd.DataFrame:
        """AKShare: 财联社电报快讯

        对齐 qstock qs.news_data() 返回字段：标题/内容/发布时间/发布日期
        注：akshare 财联社接口偶尔会卡住，加了 15 秒超时保护。
        """
        try:
            ak = self._get_akshare()
            df = self._call_with_timeout(
                ak.stock_info_global_cls,
                kwargs={"symbol": "全部"},
                timeout_sec=15,
            )
            if df is None or df.empty:
                return pd.DataFrame()
            # akshare 返回字段：标题、内容、发布时间
            for col in ("发布时间", "发布日期"):
                if col in df.columns:
                    df[col] = df[col].astype(str)
            return df.reset_index(drop=True)
        except TimeoutError as e:
            self._logger.warning(f"[akshare] 获取财联社电报超时: {e}")
            return pd.DataFrame()
        except Exception as e:
            self._logger.warning(f"[akshare] 获取财联社电报失败: {e}")
            return pd.DataFrame()

    def akshare_news_js(self) -> pd.DataFrame:
        """AKShare: 东方财富全球财经快讯（替代金十数据）

        作为 qstock news_data('js') 的备选
        注：加了 15 秒超时保护。
        """
        try:
            ak = self._get_akshare()
            df = self._call_with_timeout(
                ak.stock_info_global_em, timeout_sec=15,
            )
            if df is None or df.empty:
                return pd.DataFrame()
            return df.reset_index(drop=True)
        except TimeoutError as e:
            self._logger.warning(f"[akshare] 获取全球快讯超时: {e}")
            return pd.DataFrame()
        except Exception as e:
            self._logger.warning(f"[akshare] 获取全球快讯失败: {e}")
            return pd.DataFrame()

    def akshare_news_sina(self) -> pd.DataFrame:
        """AKShare: 新浪财经全球快讯（新增数据源）"""
        try:
            ak = self._get_akshare()
            df = ak.stock_info_global_sina()
            if df is None or df.empty:
                return pd.DataFrame()
            return df.reset_index(drop=True)
        except Exception as e:
            self._logger.warning(f"[akshare] 获取新浪快讯失败: {e}")
            return pd.DataFrame()

    def akshare_news_caixin(self) -> pd.DataFrame:
        """AKShare: 财新网主要财经新闻（新增数据源）"""
        try:
            ak = self._get_akshare()
            df = ak.stock_news_main_cx()
            if df is None or df.empty:
                return pd.DataFrame()
            return df.reset_index(drop=True)
        except Exception as e:
            self._logger.warning(f"[akshare] 获取财新网新闻失败: {e}")
            return pd.DataFrame()

    def akshare_news_cctv(self, date_str: Optional[str] = None) -> pd.DataFrame:
        """AKShare: 新闻联播文字稿（新增数据源）

        Args:
            date_str: 日期 YYYYMMDD，默认今天
        """
        try:
            ak = self._get_akshare()
            if date_str is None:
                import datetime
                date_str = datetime.datetime.now().strftime("%Y%m%d")
            df = ak.news_cctv(date=date_str)
            if df is None or df.empty:
                return pd.DataFrame()
            return df.reset_index(drop=True)
        except Exception as e:
            self._logger.warning(f"[akshare] 获取新闻联播失败: {e}")
            return pd.DataFrame()

    def akshare_stock_news(self, code: str) -> pd.DataFrame:
        """AKShare: 个股新闻（东方财富）"""
        try:
            ak = self._get_akshare()
            code = _normalize_codes([code])[0]
            df = ak.stock_news_em(symbol=code)
            if df is None or df.empty:
                return pd.DataFrame()
            return df.reset_index(drop=True)
        except Exception as e:
            self._logger.warning(f"[akshare] 获取个股新闻失败: {e}")
            return pd.DataFrame()

    def akshare_kline(self, code: str, count: int = 60,
                      freq: str = "d") -> pd.DataFrame:
        """AKShare: 历史日 K 线

        返回字段统一为 mplfinance 需要的 Open/High/Low/Close/Volume，索引为日期。
        """
        try:
            ak = self._get_akshare()
            code = _normalize_codes([code])[0]
            period_map = {"d": "daily", "w": "weekly", "m": "monthly"}
            period = period_map.get(freq, "daily")
            # 计算起始日期
            import datetime
            end = datetime.datetime.now().strftime("%Y%m%d")
            start = (datetime.datetime.now() - datetime.timedelta(days=count * 2 + 30)).strftime("%Y%m%d")
            df = ak.stock_zh_a_hist(
                symbol=code, period=period, start_date=start, end_date=end,
                adjust="qfq",
            )
            if df is None or df.empty:
                return pd.DataFrame()
            col_map = {
                "开盘": "Open", "最高": "High", "最低": "Low",
                "收盘": "Close", "成交量": "Volume",
                "日期": "date",
            }
            df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})
            if "date" in df.columns:
                df["date"] = pd.to_datetime(df["date"])
                df = df.set_index("date")
            return df.tail(count).head(count)
        except Exception as e:
            self._logger.warning(f"[akshare] 获取 K 线失败: {e}")
            return pd.DataFrame()

    def akshare_north_money(self) -> pd.DataFrame:
        """AKShare: 北向资金每日净流入（新增数据类型）

        字段：日期、当日净流入、当日余额
        """
        try:
            ak = self._get_akshare()
            df = ak.stock_hsgt_hist_em(symbol="北向资金")
            if df is None or df.empty:
                return pd.DataFrame()
            return df.tail(30).reset_index(drop=True)
        except Exception as e:
            self._logger.warning(f"[akshare] 获取北向资金失败: {e}")
            return pd.DataFrame()

    def akshare_weibo_sentiment(self) -> pd.DataFrame:
        """AKShare: 微博舆情报告（新增数据类型）

        原始字段：name, rate（akshare 接口返回）
        统一重命名为：股票名称, 舆情指数
        """
        try:
            ak = self._get_akshare()
            df = self._call_with_timeout(
                ak.stock_js_weibo_report,
                kwargs={"time_period": "CNHOUR12"},
                timeout_sec=15,
            )
            if df is None or df.empty:
                return pd.DataFrame()
            # 字段重命名（akshare 返回英文列名，统一为中文）
            rename = {
                "name": "股票名称",
                "rate": "舆情指数",
            }
            df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})
            return df.head(50).reset_index(drop=True)
        except Exception as e:
            self._logger.warning(f"[akshare] 获取微博舆情失败: {e}")
            return pd.DataFrame()

    def akshare_news_sentiment(self) -> pd.DataFrame:
        """AKShare: 新闻情绪指数（新增数据类型）

        字段：日期、新闻情绪指数
        接口失败时返回空 DataFrame（不影响其他数据块写入）
        """
        try:
            ak = self._get_akshare()
            df = self._call_with_timeout(
                ak.index_news_sentiment_scope,
                timeout_sec=15,
            )
            if df is None or df.empty:
                return pd.DataFrame()
            return df.tail(30).reset_index(drop=True)
        except Exception as e:
            self._logger.warning(f"[akshare] 获取新闻情绪指数失败: {e}")
            return pd.DataFrame()

    # =================================================================
    # 东方财富 Web API 备选源（参考 egs_data/eastmoney/）
    # =================================================================
    def _eastmoney_secid(self, code: str) -> str:
        """代码 → eastmoney secid（格式 市场.代码，沪市 1，深市 0）"""
        code = _normalize_codes([code])[0]
        prefix = _detect_market_prefix(code)
        market = "1" if prefix == "sh" else "0"
        return f"{market}.{code}"

    def eastmoney_stock_realtime(self, code_list: List[str]) -> pd.DataFrame:
        """东方财富: 批量实时行情"""
        try:
            requests = self._get_requests()
            codes = _normalize_codes(code_list)
            if not codes:
                return pd.DataFrame()
            # 使用批量接口 secids=1.600000,0.000001
            secids = ",".join(self._eastmoney_secid(c) for c in codes)
            url = "https://push2.eastmoney.com/api/qt/ulist.np/get"
            params = {
                "fltt": "2", "fields": "f2,f3,f4,f5,f6,f7,f8,f12,f14,f15,f16,f17,f18",
                "secids": secids,
                "ut": "fa5fd1943c7b386f172d6893dbbd1",
            }
            r = requests.get(url, params=params, headers=_HTTP_HEADERS,
                             timeout=10, proxies=_NO_PROXY)
            payload = r.json() or {}
            data = (payload.get("data") or {}).get("diff") or []
            if not data:
                return pd.DataFrame()
            rows = []
            for d in data:
                rows.append({
                    "代码": d.get("f12"), "名称": d.get("f14"),
                    "最新": d.get("f2"), "涨幅": d.get("f3"),
                    "涨跌额": d.get("f4"), "成交量": d.get("f5"),
                    "成交额": d.get("f6"), "振幅": d.get("7"),
                    "换手率": d.get("f8"), "最高": d.get("f15"),
                    "最低": d.get("f16"), "开盘": d.get("f17"),
                    "昨收": d.get("f18"),
                })
            return pd.DataFrame(rows)
        except Exception as e:
            self._logger.warning(f"[eastmoney] 获取个股实时行情失败: {e}")
            return pd.DataFrame()

    def eastmoney_kline(self, code: str, count: int = 60,
                        freq: str = "d") -> pd.DataFrame:
        """东方财富: 历史 K 线

        参考 egs_data/eastmoney/eastmoney_api.py
        """
        try:
            requests = self._get_requests()
            secid = self._eastmoney_secid(code)
            klt_map = {"d": 101, "w": 102, "m": 103}
            klt = klt_map.get(freq, 101)
            url = "http://push2his.eastmoney.com/api/qt/stock/kline/get"
            params = {
                "secid": secid, "klt": klt, "fqt": 1,
                "beg": "0", "end": "20500101",
                "fields1": "f1,f2,f3,f4,f5,f6",
                "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
                "ut": "fa5fd1943c7b386f172d6893dbbd1",
            }
            r = requests.get(url, params=params, headers=_HTTP_HEADERS,
                             timeout=10, proxies=_NO_PROXY)
            payload = r.json() or {}
            klines = (payload.get("data") or {}).get("klines") or []
            if not klines:
                return pd.DataFrame()
            rows = [k.split(",") for k in klines]
            df = pd.DataFrame(rows, columns=[
                "date", "Open", "Close", "High", "Low", "Volume",
                "成交额", "振幅", "涨跌幅", "涨跌额", "换手率",
            ])
            for col in ["Open", "Close", "High", "Low", "Volume"]:
                df[col] = pd.to_numeric(df[col], errors="coerce")
            df["date"] = pd.to_datetime(df["date"])
            df = df.set_index("date")
            return df.tail(count).head(count)
        except Exception as e:
            self._logger.warning(f"[eastmoney] 获取 K 线失败: {e}")
            return pd.DataFrame()

    def eastmoney_money_flow(self, code: str) -> pd.DataFrame:
        """东方财富: 个股资金流向（日级）

        参考 egs_data/eastmoney/eastmoney_api.py
        字段：日期、主力净流入、小单净流入、中单净流入、大单净流入、超大单净流入
        """
        try:
            requests = self._get_requests()
            secid = self._eastmoney_secid(code)
            url = "http://push2his.eastmoney.com/api/qt/stock/fflow/daykline/get"
            params = {
                "secid": secid, "klt": 101,
                "fields1": "f1,f2,f3,f7",
                "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63,f64,f65",
                "ut": "b2884a393a59ad64002292a3e90d46a5",
            }
            r = requests.get(url, params=params, headers=_HTTP_HEADERS,
                             timeout=10, proxies=_NO_PROXY)
            payload = r.json() or {}
            klines = (payload.get("data") or {}).get("klines") or []
            if not klines:
                return pd.DataFrame()
            rows = [k.split(",") for k in klines]
            df = pd.DataFrame(rows, columns=[
                "日期", "主力净流入", "小单净流入", "中单净流入",
                "大单净流入", "超大单净流入",
            ])
            for col in df.columns[1:]:
                df[col] = pd.to_numeric(df[col], errors="coerce")
            return df.tail(30).reset_index(drop=True)
        except Exception as e:
            self._logger.warning(f"[eastmoney] 获取资金流向失败: {e}")
            return pd.DataFrame()

    def eastmoney_guba_hot(self, page_size: int = 20) -> pd.DataFrame:
        """东方财富: 热门个股排行榜（替代原股吧热门接口）

        原 guba.eastmoney.com/list,000001,f_1.html 接口已不返回 article_list 变量，
        改用 akshare 的 stock_hot_rank_em（东财人气榜）作为数据源，
        返回字段：股票代码、股票名称、当前排名、排名较昨日变化
        """
        try:
            ak = self._get_akshare()
            df = self._call_with_timeout(
                ak.stock_hot_rank_em,
                timeout_sec=15,
            )
            if df is None or df.empty:
                return pd.DataFrame()
            # 取前 page_size 条
            df = df.head(page_size)
            # 重命名为中文（akshare 返回字段：股票代码, 股票名称, 排名, 排名较昨日变化）
            rename = {
                "股票代码": "代码",
                "股票名称": "名称",
                "排名": "排名",
                "排名较昨日变化": "排名变化",
            }
            df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})
            return df.reset_index(drop=True)
        except Exception as e:
            self._logger.warning(f"[eastmoney] 获取热门个股排行失败: {e}")
            return pd.DataFrame()

    def eastmoney_guba_posts(self, code: str, page_size: int = 20) -> pd.DataFrame:
        """东方财富: 个股股吧帖子

        参考 egs_data/eastmoney/eastmoney_news_guba.py
        """
        try:
            import re
            import json
            requests = self._get_requests()
            code = _normalize_codes([code])[0]
            headers = {
                "User-Agent": _HTTP_HEADERS["User-Agent"],
                "Referer": f"https://guba.eastmoney.com/list,{code}.html",
            }
            url = f"https://guba.eastmoney.com/list,{code},f_1.html"
            r = requests.get(url, headers=headers, timeout=15, proxies=_NO_PROXY)
            match = re.search(r"var article_list=(\{.*?\});", r.text, re.DOTALL)
            if not match:
                return pd.DataFrame()
            data = json.loads(match.group(1))
            posts = data.get("re", []) or []
            rows = []
            for p in posts[:page_size]:
                title = p.get("post_title", "") or (p.get("post_content", "") or "")[:50]
                rows.append({
                    "标题": title,
                    "发布时间": p.get("post_publish_time", ""),
                    "阅读量": p.get("post_click_count", 0),
                    "评论数": p.get("post_comment_count", 0),
                    "点赞数": p.get("post_like_count", 0),
                    "来源": p.get("post_from", ""),
                })
            return pd.DataFrame(rows)
        except Exception as e:
            self._logger.warning(f"[eastmoney] 获取个股股吧失败: {e}")
            return pd.DataFrame()

    def eastmoney_stock_news(self, code: str, page_size: int = 20) -> pd.DataFrame:
        """东方财富: 个股公告新闻

        参考 egs_data/eastmoney/eastmoney_news_guba.py
        """
        try:
            import json
            requests = self._get_requests()
            code = _normalize_codes([code])[0]
            url = "https://np-anotice-stock.eastmoney.com/api/security/ann"
            params = {
                "cb": "jQuery", "sr": "-1", "page_size": page_size,
                "page_index": 1, "ann_type": "A", "client_source": "web",
                "stock_list": code, "f_node": "0", "s_node": "0",
            }
            r = requests.get(url, params=params, headers=_HTTP_HEADERS,
                             timeout=15, proxies=_NO_PROXY)
            text = r.text
            if text.startswith("jQuery"):
                text = text[text.index("(") + 1: text.rindex(")")]
            data = json.loads(text) or {}
            items = (data.get("data") or {}).get("list") or []
            if not items:
                return pd.DataFrame()
            rows = []
            for item in items:
                codes = item.get("codes", [{}])
                rows.append({
                    "标题": item.get("title", ""),
                    "发布时间": item.get("notice_date", ""),
                    "股票代码": codes[0].get("stock_code", "") if codes else "",
                    "股票名称": codes[0].get("short_name", "") if codes else "",
                    "公告类型": item.get("columns", [{}])[0].get("column_name", "") if item.get("columns") else "",
                })
            return pd.DataFrame(rows)
        except Exception as e:
            self._logger.warning(f"[eastmoney] 获取个股公告失败: {e}")
            return pd.DataFrame()

    # =================================================================
    # 腾讯财经 Web API 备选源（参考 egs_data/tencent/tencent_api.py）
    # =================================================================
    def _tencent_code(self, code: str) -> str:
        """代码 → 腾讯格式 sh600000 / sz000001"""
        code = _normalize_codes([code])[0]
        prefix = _detect_market_prefix(code)
        return f"{prefix}{code}"

    def tencent_stock_realtime(self, code_list: List[str]) -> pd.DataFrame:
        """腾讯: 批量实时行情"""
        try:
            requests = self._get_requests()
            codes = [_normalize_codes([c])[0] for c in code_list if c]
            if not codes:
                return pd.DataFrame()
            tencent_codes = [self._tencent_code(c) for c in codes]
            url = f"http://qt.gtimg.cn/q={','.join(tencent_codes)}"
            r = requests.get(url, timeout=10, proxies=_NO_PROXY)
            r.encoding = "gbk"
            rows = []
            for line in r.text.strip().split("\n"):
                if "=" not in line:
                    continue
                try:
                    content = line.split("=", 1)[1].strip().strip(";").strip('"')
                    fields = content.split("~")
                    if len(fields) < 50:
                        continue
                    rows.append({
                        "代码": fields[2], "名称": fields[1],
                        "最新": _safe_float(fields[3]),
                        "昨收": _safe_float(fields[4]),
                        "开盘": _safe_float(fields[5]),
                        "成交量": _safe_int(fields[6]),
                        "最高": _safe_float(fields[33]),
                        "最低": _safe_float(fields[34]),
                        "成交额": _safe_float(fields[37]),
                        "换手率": _safe_float(fields[38]),
                        "涨幅": _safe_float(fields[32]),
                    })
                except Exception:
                    continue
            return pd.DataFrame(rows)
        except Exception as e:
            self._logger.warning(f"[tencent] 获取个股实时行情失败: {e}")
            return pd.DataFrame()

    def tencent_kline(self, code: str, count: int = 60,
                      freq: str = "d") -> pd.DataFrame:
        """腾讯: 历史日 K 线

        参考 egs_data/tencent/tencent_api.py
        """
        try:
            requests = self._get_requests()
            tencent_code = self._tencent_code(code)
            url = "http://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
            params = {"param": f"{tencent_code},day,,,{count},qfq"}
            r = requests.get(url, params=params, timeout=10, proxies=_NO_PROXY)
            payload = r.json() or {}
            data = payload.get("data") or {}
            data = data.get(tencent_code) or {}
            day_data = (data.get("day") or data.get("qfqday")
                        or data.get("hfqday") or [])
            rows = [row[:6] for row in day_data]
            df = pd.DataFrame(rows, columns=["date", "Open", "Close",
                                             "High", "Low", "Volume"])
            for col in ["Open", "Close", "High", "Low", "Volume"]:
                df[col] = pd.to_numeric(df[col], errors="coerce")
            df["date"] = pd.to_datetime(df["date"])
            df = df.set_index("date")
            return df.tail(count).head(count)
        except Exception as e:
            self._logger.warning(f"[tencent] 获取 K 线失败: {e}")
            return pd.DataFrame()

    # =================================================================
    # 网易财经 Web API 备选源（参考 egs_data/netease/netease_api.py）
    # =================================================================
    def netease_kline(self, code: str, count: int = 60,
                      freq: str = "d") -> pd.DataFrame:
        """网易: 历史 K 线（CSV 下载方式）

        参考 egs_data/netease/netease_api.py
        网易只有日 K，freq 参数仅用于接口对齐
        """
        try:
            from io import StringIO
            requests = self._get_requests()
            code = _normalize_codes([code])[0]
            # 沪市前缀 0，深市前缀 1
            prefix = "0" if code.startswith(("6", "9", "11", "13")) else "1"
            # 计算日期范围
            import datetime
            end = datetime.datetime.now().strftime("%Y%m%d")
            start = (datetime.datetime.now() - datetime.timedelta(days=count * 2 + 30)).strftime("%Y%m%d")
            url = "http://quotes.money.163.com/service/chddata.html"
            params = {
                "code": f"{prefix}{code}",
                "start": start, "end": end,
                "fields": "TCLOSE;HIGH;LOW;TOPEN;LCLOSE;CHG;PCHG;TURNOVER;VOTURNOVER;VATURNOVER;TCAP;MCAP",
            }
            r = requests.get(url, params=params, timeout=15, proxies=_NO_PROXY)
            r.encoding = "gbk"
            df = pd.read_csv(StringIO(r.text))
            if df is None or df.empty:
                return pd.DataFrame()
            col_map = {
                "日期": "date", "开盘价": "Open", "收盘价": "Close",
                "最高价": "High", "最低价": "Low", "成交量": "Volume",
            }
            df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})
            if "date" in df.columns:
                df["date"] = pd.to_datetime(df["date"])
                df = df.set_index("date")
            for col in ["Open", "Close", "High", "Low", "Volume"]:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce")
            return df.tail(count).head(count)
        except Exception as e:
            self._logger.warning(f"[netease] 获取 K 线失败: {e}")
            return pd.DataFrame()

    # =================================================================
    # efinance 备选源（参考 egs_data/efinance/efinance_demo.py）
    # =================================================================
    def efinance_stock_realtime(self, code_list: List[str]) -> pd.DataFrame:
        """efinance: 实时行情

        注意：efinance 无大盘指数接口（参考 egs_data README 说明），
        但个股/板块行情可用作备选。
        """
        try:
            ef = self._get_efinance()
            codes = _normalize_codes(code_list)
            if not codes and not code_list:
                return pd.DataFrame()
            df = ef.stock.get_realtime_quotes()
            if df is None or df.empty:
                return pd.DataFrame()
            mask_code = df["股票代码"].astype(str).isin(codes) if codes else pd.Series([False]*len(df))
            mask_name = df["股票名称"].astype(str).isin([str(c) for c in code_list if c and not str(c).strip().isdigit()])
            df = df[mask_code | mask_name].copy()
            rename = {
                "股票代码": "代码", "股票名称": "名称",
                "最新价": "最新", "涨跌幅": "涨幅", "涨跌额": "涨跌额",
                "成交量": "成交量", "成交额": "成交额", "换手率": "换手率",
                "最高": "最高", "最低": "最低", "今开": "开盘", "昨收": "昨收",
            }
            df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})
            return df.reset_index(drop=True)
        except Exception as e:
            self._logger.warning(f"[efinance] 获取个股实时行情失败: {e}")
            return pd.DataFrame()

    def efinance_kline(self, code: str, count: int = 60,
                       freq: str = "d") -> pd.DataFrame:
        """efinance: 历史日 K 线"""
        try:
            ef = self._get_efinance()
            code = _normalize_codes([code])[0]
            df = ef.stock.get_quote_history(code, klt=101)
            if df is None or df.empty:
                return pd.DataFrame()
            col_map = {
                "日期": "date", "开盘": "Open", "收盘": "Close",
                "最高": "High", "最低": "Low", "成交量": "Volume",
            }
            df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})
            if "date" in df.columns:
                df["date"] = pd.to_datetime(df["date"])
                df = df.set_index("date")
            return df.tail(count).head(count)
        except Exception as e:
            self._logger.warning(f"[efinance] 获取 K 线失败: {e}")
            return pd.DataFrame()

    # =================================================================
    # BaoStock 备选源（TCP 10030 端口，绕开 HTTP 反爬限制）
    # 参考 money_maker/egs_quant_trade/a001_news_track 项目实现
    # =================================================================
    def baostock_kline(self, code: str, count: int = 60,
                       freq: str = "d") -> pd.DataFrame:
        """BaoStock: 历史 K 线（日频）

        BaoStock 使用 TCP 10030 端口，不受 HTTP 反爬限制，
        作为 K 线数据的高可用备用源。
        """
        try:
            bs = self._get_baostock()
            if bs is None:
                return pd.DataFrame()
            code = _normalize_codes([code])[0]
            prefix = _detect_market_prefix(code)
            bs_code = f"{prefix}.{code}"
            import datetime
            end_date = datetime.datetime.now().strftime("%Y-%m-%d")
            start_date = (datetime.datetime.now() -
                          datetime.timedelta(days=count * 2 + 60)).strftime("%Y-%m-%d")
            fields = "date,open,high,low,close,volume"
            rs = bs.query_history_k_data_plus(
                bs_code, fields,
                start_date=start_date, end_date=end_date,
                frequency="d", adjustflag="2",
            )
            if rs.error_code != "0":
                self._logger.warning(f"[baostock] K线查询失败: {rs.error_msg}")
                return pd.DataFrame()
            data_list = []
            while (rs.error_code == "0") and rs.next():
                data_list.append(rs.get_row_data())
            if not data_list:
                return pd.DataFrame()
            df = pd.DataFrame(data_list, columns=["date", "Open", "High", "Low", "Close", "Volume"])
            for col in ["Open", "High", "Low", "Close", "Volume"]:
                df[col] = pd.to_numeric(df[col], errors="coerce")
            df["date"] = pd.to_datetime(df["date"])
            df = df.set_index("date")
            return df.tail(count).head(count)
        except Exception as e:
            self._logger.warning(f"[baostock] 获取 K 线失败: {e}")
            return pd.DataFrame()

    def baostock_stock_realtime(self, code_list: List[str]) -> pd.DataFrame:
        """BaoStock: 实时行情快照（通过当日 K 线近似获取）

        BaoStock 没有真正的"实时"行情接口，但可以通过 query_today_stock_kline
        获取当日已成交的 K 线近似实时价格，作为最后 fallback 选项。
        """
        try:
            bs = self._get_baostock()
            if bs is None:
                return pd.DataFrame()
            codes = _normalize_codes(code_list)
            if not codes:
                return pd.DataFrame()
            rows = []
            for code in codes:
                try:
                    prefix = _detect_market_prefix(code)
                    bs_code = f"{prefix}.{code}"
                    rs = bs.query_today_stock_kline(
                        code=bs_code, ktype="5",
                    )
                    if rs.error_code != "0":
                        continue
                    data_list = []
                    while (rs.error_code == "0") and rs.next():
                        data_list.append(rs.get_row_data())
                    if not data_list:
                        continue
                    # 取最后一根 K 线近似最新价
                    last = data_list[-1]
                    rows.append({
                        "代码": code,
                        "名称": code,
                        "最新": _safe_float(last[3]),
                        "涨幅": None,
                        "成交量": _safe_int(last[5]),
                    })
                except Exception:
                    continue
            return pd.DataFrame(rows) if rows else pd.DataFrame()
        except Exception as e:
            self._logger.warning(f"[baostock] 获取实时行情失败: {e}")
            return pd.DataFrame()
