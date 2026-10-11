# -*- coding: utf-8 -*-
"""新闻 Sheet：财联社电报 + 市场快讯"""
from excel_monitor.logger import get_logger
from excel_monitor.sheets.base import BaseSheet
from excel_monitor.config_loader import AppConfig


class NewsSheet(BaseSheet):
    """新闻 Sheet Handler"""

    def __init__(self, name, excel_mgr, data_provider, config=None):
        super().__init__(name, excel_mgr, data_provider)
        self.config = config or AppConfig()
        self._logger = get_logger(self.__class__.__name__)

    def init(self):
        """新闻 Sheet 无需静态初始化"""
        self._logger.info("新闻 Sheet 初始化完成")

    def refresh(self):
        """刷新新闻数据

        每个数据块独立处理：数据源未刷到时保留上次数据不变。
        """
        self._logger.info("刷新新闻数据...")

        # 1. 财联社电报（从第1行开始）
        df_cls = self.data.get_news_cls()
        if not df_cls.empty:
            # 限制显示条数
            df_cls = df_cls.head(self.config.news_max_rows)
            self._write(df_cls, start_row=1, start_col=1)
            row_offset = len(df_cls) + 3
        else:
            self._logger.info("财联社电报未刷到，保留上次数据")
            row_offset = 1

        # 2. 市场快讯（金十数据）
        df_js = self.data.get_news_js()
        if not df_js.empty:
            df_js = df_js.head(self.config.news_max_rows)
            self._write(df_js, start_row=row_offset, start_col=1)
        else:
            self._logger.info("市场快讯未刷到，保留上次数据")
