# -*- coding: utf-8 -*-
"""配置 Sheet 读取器：从 Excel "配置" Sheet 读取配置，合并到 AppConfig

配置 Sheet 布局（键值对 + 列表混合）:
    Row 1: === 全局配置 ===
    Row 2: 配置项 | 值
    Row 3: 刷新间隔(秒) | 3
    Row 4: 预警弹窗 | true
    Row 5: 新闻条数 | 50
    Row 6: 配置重载间隔 | 5
    Row 7: (空行)
    Row 8: === 列表配置 ===
    Row 9: 自选股 | 指数
    Row 10+: 中国平安 | 上证指数
"""
from typing import Optional

import pandas as pd
import xlwings as xw

from excel_monitor.logger import get_logger
from excel_monitor.config_loader import AppConfig
from excel_monitor.core.excel_manager import ExcelManager


# 键值对配置项与 AppConfig 字段的映射
_SCALAR_MAP = {
    "刷新间隔": ("refresh_interval", int),
    "预警弹窗": ("alert_popup_enabled", lambda v: str(v).strip().lower() in ("true", "1", "yes", "是")),
    "新闻条数": ("news_max_rows", int),
    "配置重载间隔": ("config_reload_interval", int),
    "情绪条数": ("sentiment_max_rows", int),
    "资金情绪Sheet": ("sentiment_sheet_enabled", lambda v: str(v).strip().lower() in ("true", "1", "yes", "是")),
    "备选数据源": ("enabled_backup_sources",
                  lambda v: [s.strip() for s in str(v).split(",") if s.strip()]),
    "股票池Sheet": ("stock_pool_sheet_enabled",
                    lambda v: str(v).strip().lower() in ("true", "1", "yes", "是")),
    "股票池缓存天数": ("stock_pool_cache_days", int),
}


class ConfigSheetReader:
    """从 Excel 配置 Sheet 读取配置"""

    def __init__(self, excel_mgr: ExcelManager):
        self._logger = get_logger(self.__class__.__name__)
        self.excel_mgr = excel_mgr

    def read_config(self, sheet_name: str,
                    defaults: AppConfig) -> AppConfig:
        """从 Excel 配置 Sheet 读取配置，合并到 defaults 上

        Args:
            sheet_name: 配置 Sheet 名称
            defaults: 默认配置（YAML 加载的）

        Returns:
            合并后的 AppConfig
        """
        sheet = self.excel_mgr.get_sheet_by_name(sheet_name)
        if sheet is None:
            self._logger.warning(f"配置 Sheet '{sheet_name}' 不存在，使用默认配置")
            return defaults

        df, _, _ = self.excel_mgr.sheet_to_df(sheet)
        if df.empty:
            return defaults

        # 复制默认配置
        import copy
        cfg = copy.deepcopy(defaults)

        # 1. 读取键值对标量配置
        self._read_scalars(df, cfg)

        # 2. 读取列表配置（自选股、指数）
        self._read_lists(df, cfg)

        self._logger.info(f"Excel 配置加载完成")
        return cfg

    def _read_scalars(self, df: pd.DataFrame, cfg: AppConfig):
        """读取键值对标量配置"""
        # 找到"配置项"和"值"列
        if "配置项" not in df.columns or "值" not in df.columns:
            return

        for _, row in df.iterrows():
            key = str(row.get("配置项", "")).strip()
            val = row.get("值")

            if not key or key == "nan" or pd.isna(val):
                continue

            # 模糊匹配（去掉括号内容）
            key_clean = key.split("(")[0].strip()
            if key_clean in _SCALAR_MAP:
                field_name, converter = _SCALAR_MAP[key_clean]
                try:
                    converted = converter(val)
                    setattr(cfg, field_name, converted)
                    self._logger.info(f"配置项: {key} = {converted}")
                except (ValueError, TypeError) as e:
                    self._logger.warning(f"配置项 {key} 值无效: {val}, {e}")

    def _read_lists(self, df: pd.DataFrame, cfg: AppConfig):
        """读取列表配置（自选股、指数）"""
        if "自选股" in df.columns:
            stocks = df["自选股"].dropna().tolist()
            stocks = [str(s).strip() for s in stocks if str(s).strip() and str(s) != "nan"]
            if stocks:
                cfg.watch_stocks = stocks
                self._logger.info(f"自选股: {stocks}")

        if "指数" in df.columns:
            indices = df["指数"].dropna().tolist()
            indices = [str(i).strip() for i in indices if str(i).strip() and str(i) != "nan"]
            if indices:
                cfg.market_indices = indices
                self._logger.info(f"指数: {indices}")
