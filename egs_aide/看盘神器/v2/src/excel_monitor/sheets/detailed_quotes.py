# -*- coding: utf-8 -*-
"""详细行情 Sheet：自选股实时行情 + 龙虎榜 + 盘口异动"""
import pandas as pd

from excel_monitor.logger import get_logger
from excel_monitor.sheets.base import BaseSheet
from excel_monitor.config_loader import AppConfig


class DetailedQuotesSheet(BaseSheet):
    """详细行情 Sheet Handler"""

    def __init__(self, name, excel_mgr, data_provider, config=None):
        super().__init__(name, excel_mgr, data_provider)
        self.config = config or AppConfig()
        self._logger = get_logger(self.__class__.__name__)
        self._stock_codes: list = []

    def init(self):
        """从 Excel Sheet 读取自选股代码"""
        df, _, _ = self.excel_mgr.sheet_to_df(self.sheet)
        if not df.empty and "代码" in df.columns:
            self._stock_codes = df["代码"].dropna().tolist()
            self._logger.info(f"自选股加载完成: {self._stock_codes}")
        else:
            # 如果 Excel 中没有自选股，使用配置默认值
            self._stock_codes = self.config.watch_stocks
            self._logger.info(f"使用默认自选股: {self._stock_codes}")

    def refresh(self):
        """刷新详细行情

        每个数据块独立处理：数据源未刷到时保留上次数据不变。
        """
        self._logger.info("刷新详细行情...")

        # 1. 自选股实时行情
        if self._stock_codes:
            df_rt = self.data.get_stock_realtime(self._stock_codes)
            if not df_rt.empty:
                self._write(df_rt, start_row=1, start_col=1)
                row_offset = len(df_rt) + 3
            else:
                self._logger.info("自选股行情未刷到，保留上次数据")
                row_offset = 1
        else:
            row_offset = 1

        # 2. 龙虎榜
        df_billboard = self.data.get_billboard()
        if not df_billboard.empty:
            self._write(df_billboard, start_row=row_offset, start_col=1)
            row_offset += len(df_billboard) + 2
        else:
            self._logger.info("龙虎榜未刷到，保留上次数据")

        # 3. 盘口异动
        df_change = self.data.get_realtime_change()
        if not df_change.empty:
            self._write(df_change, start_row=row_offset, start_col=1)
        else:
            self._logger.info("盘口异动未刷到，保留上次数据")
