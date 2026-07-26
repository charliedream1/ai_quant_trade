# -*- coding: utf-8 -*-
"""资金情绪 Sheet：北向资金 + 微博舆情 + 新闻情绪 + 股吧热门

新增 Sheet（V2 增强）：
    1. 北向资金每日净流入（akshare 数据源）
    2. 微博舆情报告（akshare 数据源，反映散户情绪）
    3. 新闻情绪指数（akshare 数据源，反映媒体情绪）
    4. 股吧热门帖子（eastmoney 数据源，反映散户热度）

每个数据块互相独立，单个失败不影响其他写入。
"""
from excel_monitor.logger import get_logger
from excel_monitor.sheets.base import BaseSheet
from excel_monitor.config_loader import AppConfig


class SentimentSheet(BaseSheet):
    """资金情绪 Sheet Handler"""

    def __init__(self, name, excel_mgr, data_provider, config=None):
        super().__init__(name, excel_mgr, data_provider)
        self.config = config or AppConfig()
        self._logger = get_logger(self.__class__.__name__)

    def init(self):
        """资金情绪 Sheet 无需静态初始化"""
        self._logger.info("资金情绪 Sheet 初始化完成")

    def refresh(self):
        """刷新资金情绪数据

        每个数据块独立处理：数据源未刷到时保留上次数据不变。
        """
        self._logger.info("刷新资金情绪数据...")

        # 1. 北向资金（从第 1 行开始）
        df_north = self.data.get_north_money()
        if not df_north.empty:
            df_north = df_north.head(self.config.sentiment_max_rows)
            self._write(df_north, start_row=1, start_col=1)
            row_offset = len(df_north) + 3
        else:
            self._logger.info("北向资金未刷到，保留上次数据")
            row_offset = 1

        # 2. 微博舆情报告
        df_weibo = self.data.get_weibo_sentiment()
        if not df_weibo.empty:
            df_weibo = df_weibo.head(self.config.sentiment_max_rows)
            self._write(df_weibo, start_row=row_offset, start_col=1)
            row_offset += len(df_weibo) + 2
        else:
            self._logger.info("微博舆情未刷到，保留上次数据")
            row_offset += 2

        # 3. 新闻情绪指数
        df_news_sent = self.data.get_news_sentiment()
        if not df_news_sent.empty:
            df_news_sent = df_news_sent.head(self.config.sentiment_max_rows)
            self._write(df_news_sent, start_row=row_offset, start_col=1)
            row_offset += len(df_news_sent) + 2
        else:
            self._logger.info("新闻情绪未刷到，保留上次数据")
            row_offset += 2

        # 4. 股吧热门帖子
        df_guba = self.data.get_guba_hot_posts(
            page_size=self.config.guba_hot_max_rows
        )
        if not df_guba.empty:
            self._write(df_guba, start_row=row_offset, start_col=1)
        else:
            self._logger.info("股吧热门未刷到，保留上次数据")

        self._logger.info(
            f"资金情绪刷新完成: 北向={len(df_north)} 微博={len(df_weibo)} "
            f"新闻情绪={len(df_news_sent)} 股吧={len(df_guba)}"
        )
