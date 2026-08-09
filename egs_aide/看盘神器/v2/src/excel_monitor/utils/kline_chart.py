# -*- coding: utf-8 -*-
"""K 线图绘制模块：使用 mplfinance 绘制 K 线并保存为图片"""
import os
import tempfile

import pandas as pd

from excel_monitor.logger import get_logger


def _get_mpf():
    """延迟导入 mplfinance"""
    import mplfinance as mpf
    return mpf


class KLineChart:
    """K 线图绘制器"""

    def __init__(self):
        self._logger = get_logger(self.__class__.__name__)

    @staticmethod
    def validate_data(df: pd.DataFrame) -> bool:
        """检查 DataFrame 是否包含 K 线所需的列

        所需列: Open, High, Low, Close, Volume
        """
        required = ["Open", "High", "Low", "Close"]
        return all(col in df.columns for col in required)

    def draw(self, df: pd.DataFrame, stock_name: str = "",
             output_path: str = None, chart_type: str = "candle",
             mav: tuple = (5, 10, 20)) -> str:
        """绘制 K 线图并保存为 PNG

        Args:
            df: K 线数据，需包含 Open/High/Low/Close/Volume 列，索引为日期
            stock_name: 股票名称（用于标题）
            output_path: 输出路径，None 则用临时文件
            chart_type: 图表类型 'candle'=蜡烛图, 'ohlc'=OHLC图
            mav: 均线周期

        Returns:
            图片文件路径，失败返回空字符串
        """
        if not self.validate_data(df):
            self._logger.error("K 线数据缺少必要列")
            return ""

        if df.empty:
            self._logger.warning("K 线数据为空")
            return ""

        # 确保索引是日期
        if not isinstance(df.index, pd.DatetimeIndex):
            try:
                df.index = pd.to_datetime(df.index)
            except Exception as e:
                self._logger.error(f"日期索引转换失败: {e}")
                return ""

        # 排序（K 线需要按时间正序）
        df = df.sort_index()

        # 输出路径
        if output_path is None:
            tmp = tempfile.NamedTemporaryFile(
                suffix=".png", delete=False, prefix="kline_"
            )
            output_path = tmp.name
            tmp.close()

        try:
            mpf = _get_mpf()
            # 自定义样式
            kwargs = {
                "type": chart_type,
                "title": f"\n{stock_name} K线图" if stock_name else "\nK线图",
                "volume": "Volume" in df.columns,
                "style": "charles",
                "figsize": (12, 7),
                "savefig": output_path,
            }
            # 均线（数据量足够时才加）
            if mav and len(df) >= max(mav):
                kwargs["mav"] = mav

            mpf.plot(df, **kwargs)
            self._logger.info(f"K 线图已保存: {output_path}")
            return output_path
        except Exception as e:
            self._logger.error(f"绘制 K 线失败: {e}")
            import traceback
            self._logger.debug(traceback.format_exc())
            return ""
