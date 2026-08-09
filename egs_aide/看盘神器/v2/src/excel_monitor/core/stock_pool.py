# -*- coding: utf-8 -*-
"""股票池管理器：全 A 股列表拉取 + 本地缓存 + 模糊搜索

数据来源：
    - 主源：akshare `stock_info_a_code_name()`（轻量，仅代码+名称）
    - 备选：akshare `stock_zh_a_spot_em()`（含行情，较慢）
    - 兜底：efinance

缓存策略：
    - 首次拉取后保存为本地 JSON（含时间戳）
    - 下次启动优先读缓存，缓存超过 N 天自动刷新
    - 拉取失败时若有过期缓存，继续使用过期缓存（保底）

模糊搜索：
    - 支持代码、名称、拼音首字母匹配
    - 例如 "pa" 匹配 "平安银行"、"600519" 匹配 "贵州茅台"
"""
import json
import os
import time
from typing import List, Optional

import pandas as pd

from excel_monitor.logger import get_logger


def _pinyin_first_letters(name: str) -> str:
    """提取中文的拼音首字母（简化版，仅常见汉字）

    完整拼音库太大，这里用一个小型映射覆盖常用字。
    未覆盖的字返回空字符，不影响匹配（用户用代码或名称即可）。
    """
    # 常见股票名称用字的首字母映射（A-Z）
    # 覆盖率有限，但够用；未覆盖字符返回 ""
    mapping = {
        "平": "p", "安": "a", "银": "y", "行": "h", "万": "w", "科": "k",
        "招": "z", "商": "s", "浦": "p", "发": "f", "民": "m", "生": "s",
        "兴": "x", "业": "y", "华": "h", "夏": "x", "幸": "x", "福": "f",
        "贵": "g", "州": "z", "茅": "m", "台": "t", "五": "w", "粮": "l",
        "液": "y", "宁": "n", "德": "d", "时": "s", "代": "d", "比": "b",
        "迪": "d", "东": "d", "方": "f", "财": "c", "富": "f", "海": "h",
        "康": "k", "美": "m", "的": "d", "集": "j", "团": "t", "股": "g",
        "份": "f", "有": "y", "限": "x", "公": "g", "司": "s", "中": "z",
        "国": "g", "石": "s", "油": "y", "化": "h", "工": "g", "农": "n",
        "建": "j", "交": "j", "通": "t", "大": "d", "地": "d", "产": "c",
        "保": "b", "险": "x", "人": "r", "寿": "s", "太": "t", "平": "p",
        "电": "d", "力": "l", "能": "n", "源": "y", "钢": "g", "铁": "t",
        "铝": "l", "铜": "t", "金": "j", "山": "s", "西": "x", "煤": "m",
        "长": "c", "江": "j", "河": "h", "湖": "h", "南": "n", "北": "b",
        "京": "j", "津": "t", "沪": "h", "深": "s", "渝": "y", "陕": "s",
        "甘": "g", "青": "q", "藏": "z", "蒙": "m", "疆": "j", "辽": "l",
        "吉": "j", "黑": "h", "苏": "s", "浙": "z", "皖": "w", "闽": "f",
        "赣": "g", "豫": "y", "鄂": "e", "湘": "x", "粤": "y", "琼": "q",
        "云": "y", "贵": "g", "川": "c", "藏": "z", "蒙": "m",
        "新": "x", "光": "g", "芯": "x", "半": "b", "导": "d", "体": "t",
        "软": "r", "件": "j", "硬": "y", "机": "j", "械": "x", "设": "s",
        "备": "b", "技": "j", "术": "s", "科": "k", "学": "x", "研": "y",
        "究": "j", "院": "y", "所": "s", "校": "x", "厂": "c", "店": "d",
        "场": "c", "市": "s", "镇": "z", "村": "c", "县": "x", "区": "q",
        "州": "z", "府": "f", "都": "d", "城": "c", "郭": "g", "陵": "l",
    }
    result = []
    for ch in str(name):
        if ch.isascii():
            result.append(ch.lower())
        else:
            result.append(mapping.get(ch, ""))
    return "".join(result)


class StockPool:
    """股票池管理器

    Attributes:
        cache_path: 本地缓存文件路径
        cache_days: 缓存有效天数（超过则刷新）
        df: 当前股票池 DataFrame（列：代码、名称、市场）
    """

    def __init__(self, cache_path: str = "stock_pool.json",
                 cache_days: int = 1):
        self.cache_path = cache_path
        self.cache_days = cache_days
        self._logger = get_logger(self.__class__.__name__)
        self.df: pd.DataFrame = pd.DataFrame()

    # =================================================================
    # 数据拉取
    # =================================================================
    def _fetch_from_akshare(self) -> pd.DataFrame:
        """从 akshare 拉取全 A 股代码名称（主源）"""
        try:
            import akshare as ak
            # stock_info_a_code_name 返回: code, name（轻量接口）
            df = ak.stock_info_a_code_name()
            if df is None or df.empty:
                return pd.DataFrame()
            # 统一列名
            df = df.rename(columns={"code": "代码", "name": "名称"})
            df["代码"] = df["代码"].astype(str).str.zfill(6)
            df["市场"] = df["代码"].apply(self._detect_market)
            df["拼音"] = df["名称"].apply(_pinyin_first_letters)
            return df[["代码", "名称", "市场", "拼音"]].reset_index(drop=True)
        except Exception as e:
            self._logger.warning(f"akshare 拉取股票池失败: {e}")
            return pd.DataFrame()

    def _fetch_from_efinance(self) -> pd.DataFrame:
        """从 efinance 拉取（备选源）"""
        try:
            import efinance as ef
            df = ef.stock.get_realtime_quotes()
            if df is None or df.empty:
                return pd.DataFrame()
            # efinance 返回列名：股票代码、股票名称
            df = df.rename(columns={"股票代码": "代码", "股票名称": "名称"})
            df["代码"] = df["代码"].astype(str).str.zfill(6)
            df["市场"] = df["代码"].apply(self._detect_market)
            df["拼音"] = df["名称"].apply(_pinyin_first_letters)
            return df[["代码", "名称", "市场", "拼音"]].reset_index(drop=True)
        except Exception as e:
            self._logger.warning(f"efinance 拉取股票池失败: {e}")
            return pd.DataFrame()

    @staticmethod
    def _detect_market(code: str) -> str:
        """根据代码判断市场：沪市/深圳/北交所"""
        code = str(code).strip()
        if code.startswith(("60", "68", "9", "11", "13")):
            return "沪市"
        if code.startswith(("00", "30", "12")):
            return "深圳"
        if code.startswith(("43", "83", "87", "88")):
            return "北交所"
        return "其他"

    def fetch(self) -> pd.DataFrame:
        """拉取股票池（akshare 主源 → efinance 备选）"""
        df = self._fetch_from_akshare()
        if df.empty:
            self._logger.info("akshare 失败，尝试 efinance 备选源")
            df = self._fetch_from_efinance()
        if df.empty:
            self._logger.error("所有数据源拉取股票池失败")
        return df

    # =================================================================
    # 缓存读写
    # =================================================================
    def load_cache(self) -> bool:
        """从本地缓存加载股票池

        Returns:
            True 表示加载成功且缓存未过期，False 表示需要重新拉取
        """
        if not os.path.exists(self.cache_path):
            return False
        try:
            with open(self.cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            ts = data.get("timestamp", 0)
            records = data.get("records", [])
            if not records:
                return False
            # 检查是否过期
            age_days = (time.time() - ts) / 86400
            self.df = pd.DataFrame(records)
            self._logger.info(
                f"加载股票池缓存: {len(self.df)} 只 "
                f"(缓存年龄 {age_days:.1f} 天)"
            )
            return age_days < self.cache_days
        except Exception as e:
            self._logger.warning(f"读取股票池缓存失败: {e}")
            return False

    def save_cache(self):
        """保存股票池到本地缓存"""
        if self.df.empty:
            return
        try:
            data = {
                "timestamp": time.time(),
                "records": self.df.to_dict(orient="records"),
            }
            with open(self.cache_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
            self._logger.info(f"股票池已缓存: {self.cache_path} ({len(self.df)} 只)")
        except Exception as e:
            self._logger.warning(f"保存股票池缓存失败: {e}")

    def load_or_fetch(self) -> pd.DataFrame:
        """优先读缓存，缓存不存在/过期时拉取并保存

        拉取失败时若有过期缓存，继续使用过期缓存（保底）
        """
        # 1. 尝试读缓存
        fresh = self.load_cache()
        if fresh and not self.df.empty:
            return self.df
        # 2. 缓存过期或不存在，拉取最新
        df = self.fetch()
        if not df.empty:
            self.df = df
            self.save_cache()
            return self.df
        # 3. 拉取失败，若有过期缓存，继续用（保底）
        if not self.df.empty:
            self._logger.warning("拉取失败，使用过期缓存（保底）")
            return self.df
        # 4. 完全没有数据
        self._logger.error("股票池为空：无缓存且拉取失败")
        return pd.DataFrame()

    # =================================================================
    # 模糊搜索
    # =================================================================
    def search(self, keyword: str, limit: int = 100) -> pd.DataFrame:
        """模糊搜索股票

        匹配规则（大小写不敏感）：
            1. 代码前缀匹配（"600" → 600xxx）
            2. 名称包含匹配（"平安" → 平安银行/中国平安）
            3. 拼音首字母匹配（"pa" → 平安银行/中国平安）

        Args:
            keyword: 搜索关键字
            limit: 最多返回条数（避免下拉框过长）

        Returns:
            匹配的 DataFrame（代码、名称、市场、拼音）
        """
        if self.df.empty or not keyword:
            return self.df.head(limit) if self.df is not None else pd.DataFrame()
        kw = str(keyword).strip().lower()
        if not kw:
            return self.df.head(limit)

        # 三种匹配条件取并集
        mask_code = self.df["代码"].astype(str).str.startswith(kw)
        mask_name = self.df["名称"].astype(str).str.contains(kw, na=False)
        mask_pinyin = self.df["拼音"].astype(str).str.startswith(kw)
        mask = mask_code | mask_name | mask_pinyin

        result = self.df[mask].head(limit)
        self._logger.info(f"搜索 '{keyword}': 匹配 {len(result)} 条")
        return result.reset_index(drop=True)

    def get_codes(self) -> List[str]:
        """获取全部股票代码列表（用于下拉框数据验证）"""
        if self.df.empty:
            return []
        return self.df["代码"].astype(str).tolist()
