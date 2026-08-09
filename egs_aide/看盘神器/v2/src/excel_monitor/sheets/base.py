# -*- coding: utf-8 -*-
"""Sheet Handler 抽象基类"""
from abc import ABC, abstractmethod

import pandas as pd
import xlwings as xw

from excel_monitor.core.data_provider import DataProvider
from excel_monitor.core.excel_manager import ExcelManager


class BaseSheet(ABC):
    """每个 Sheet 的 Handler 继承此类，实现 init() 和 refresh()"""

    def __init__(self, name: str, excel_mgr: ExcelManager,
                 data_provider: DataProvider):
        self.name = name
        self.excel_mgr = excel_mgr
        self.data = data_provider
        self.sheet: xw.Sheet = None

    def setup(self):
        """获取 Sheet 对象，子类可 override 扩展初始化"""
        self.sheet = self.excel_mgr.get_sheet_by_name(self.name)
        if self.sheet is None:
            raise ValueError(f"Sheet '{self.name}' 不存在于工作簿中")

    @abstractmethod
    def init(self):
        """初始化加载（仅执行一次，加载静态数据）"""
        pass

    @abstractmethod
    def refresh(self):
        """刷新数据（每次循环调用）"""
        pass

    def _write(self, df: pd.DataFrame, start_row: int = 1, start_col: int = 1):
        """写入数据到 Sheet

        重要：若 df 为空（数据源未刷到），直接返回，不清除旧数据，
        保持上一次成功刷新的内容不变。
        """
        if self.sheet is None:
            return
        if df is None or df.empty:
            # 数据源未刷到，保持原数据不变
            return
        # 只清除数据实际占用的范围（+2行余量），避免清除过大范围导致 Excel 卡顿
        n_rows = df.shape[0] + 2
        n_cols = df.shape[1] + 2
        self.excel_mgr.clear_range(
            self.sheet, start_row=start_row, start_col=start_col,
            end_row=start_row + n_rows, end_col=start_col + n_cols - 1
        )
        self.excel_mgr.write_df(self.sheet, df, start_row, start_col)
        # 写入后立即保存，避免因后续操作卡住导致数据丢失
        self.excel_mgr.save()
