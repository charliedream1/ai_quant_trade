# -*- coding: utf-8 -*-
"""大盘 Sheet：指数行情 + 行业板块 + 概念板块 + 涨停板"""
from excel_monitor.logger import get_logger
from excel_monitor.sheets.base import BaseSheet
from excel_monitor.config_loader import AppConfig


class MarketOverviewSheet(BaseSheet):
    """大盘总览 Sheet Handler"""

    def __init__(self, name, excel_mgr, data_provider, config=None):
        super().__init__(name, excel_mgr, data_provider)
        self.config = config or AppConfig()
        self._logger = get_logger(self.__class__.__name__)

    def init(self):
        """大盘 Sheet 无需静态初始化"""
        self._logger.info("大盘 Sheet 初始化完成")

    def refresh(self):
        """刷新大盘数据

        每个数据块独立处理：数据源未刷到时保留上次数据不变。
        """
        self._logger.info("刷新大盘数据...")

        # 1. 主要指数行情（从第1行开始）
        df_index = self.data.get_index_realtime(self.config.market_indices)
        if not df_index.empty:
            self._write(df_index, start_row=1, start_col=1)
        else:
            self._logger.info("指数行情未刷到，保留上次数据")

        # 2. 行业板块涨幅榜（空2行后写入）
        row_offset = len(df_index) + 3 if not df_index.empty else 1
        df_industry = self.data.get_industry_boards()
        if not df_industry.empty:
            self._write(df_industry, start_row=row_offset, start_col=1)
            row_offset += len(df_industry) + 2
        else:
            self._logger.info("行业板块未刷到，保留上次数据")

        # 3. 概念板块涨幅榜
        df_concept = self.data.get_concept_boards()
        if not df_concept.empty:
            self._write(df_concept, start_row=row_offset, start_col=1)
            row_offset += len(df_concept) + 2
        else:
            self._logger.info("概念板块未刷到，保留上次数据")

        # 4. 涨停板
        df_zt = self.data.get_limit_up_pool()
        if not df_zt.empty:
            self._write(df_zt, start_row=row_offset, start_col=1)
        else:
            self._logger.info("涨停板未刷到，保留上次数据")
