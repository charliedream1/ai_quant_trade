# -*- coding: utf-8 -*-
"""股票池 Sheet：全量股票列表 + 模糊搜索 + 下拉框数据源

新增 Sheet（V2 增强）：
    - 顶部搜索框 + 搜索按钮 + 显示全部按钮
    - 下方展示股票列表（代码、名称、市场）
    - 用户输入关键字 → 点搜索 → 过滤显示匹配项
    - 从结果复制到"个性定制看盘"Sheet

布局：
    A1: 搜索关键字    B1: [输入框]    C1: [搜索按钮]    D1: [显示全部]
    A2: 共 N 只 | 匹配 M 只
    A4: 代码    B4: 名称    C4: 市场    (表头)
    A5+: 数据行
"""
import pandas as pd

from excel_monitor.logger import get_logger
from excel_monitor.sheets.base import BaseSheet
from excel_monitor.config_loader import AppConfig
from excel_monitor.core.stock_pool import StockPool


class StockPoolSheet(BaseSheet):
    """股票池 Sheet Handler

    Attributes:
        pool: StockPool 实例（共享自 main.py）
        _search_cell: 搜索关键字所在单元格 (row, col)
        _trigger_cell: 搜索触发信号单元格
    """

    def __init__(self, name, excel_mgr, data_provider, config=None,
                 stock_pool: StockPool = None):
        super().__init__(name, excel_mgr, data_provider)
        self.config = config or AppConfig()
        self._logger = get_logger(self.__class__.__name__)
        self.pool = stock_pool or StockPool(
            cache_path=self.config.stock_pool_cache_path,
            cache_days=self.config.stock_pool_cache_days,
        )
        # 搜索框位置：B1
        self._search_cell = (1, 2)
        # 触发信号位置：D2（搜索按钮写入 "SEARCH"，显示全部按钮写入 "ALL"）
        self._trigger_cell = (2, 4)
        # 数据起始行（表头在第 4 行，数据从第 5 行）
        self._data_start_row = 5
        # 上次显示的条数（用于清除旧数据）
        self._last_display_count = 0
        # 默认显示条数（首次或显示全部时）
        self._default_limit = 200

    def init(self):
        """初始化：加载股票池 + 写入表头 + 添加搜索按钮"""
        self._logger.info("股票池 Sheet 初始化...")

        # 1. 加载股票池（缓存优先）
        df = self.pool.load_or_fetch()
        if df.empty:
            self._logger.warning("股票池为空，请检查网络或 akshare 安装")
            return

        # 2. 写入搜索区域
        self._setup_search_area()

        # 3. 默认显示前 N 只
        self._display(df.head(self._default_limit), total=len(df))

        self._logger.info(f"股票池初始化完成: {len(df)} 只股票")

    def _setup_search_area(self):
        """设置搜索区域：标题、输入框提示、按钮"""
        if self.sheet is None:
            return
        try:
            # A1: 标题
            self.sheet.cells(1, 1).value = "搜索关键字:"
            # B1: 输入框（用户在此输入）
            self.sheet.cells(1, 2).value = ""
            # C1: 搜索按钮
            self.excel_mgr.add_button(
                self.sheet, row=1, col=3,
                text="搜索", macro="SearchStockMacro",
                width=60, height=28
            )
            # D1: 显示全部按钮
            self.excel_mgr.add_button(
                self.sheet, row=1, col=4,
                text="显示全部", macro="ShowAllStockMacro",
                width=70, height=28
            )
            # A2: 状态提示（运行时更新）
            self.sheet.cells(2, 1).value = ""
            # D2: 触发信号单元格（按钮宏写入这里）
            self.sheet.cells(2, 4).value = None

            # 表头（第 4 行）
            headers = ["代码", "名称", "市场"]
            for i, h in enumerate(headers, 1):
                self.sheet.cells(4, i).value = h
        except Exception as e:
            self._logger.warning(f"设置搜索区域失败: {e}")

    def _display(self, df: pd.DataFrame, total: int = None):
        """显示股票列表到 Sheet"""
        if self.sheet is None:
            return
        total = total if total is not None else len(df)

        # 清除旧数据（从第 5 行开始）
        if self._last_display_count > 0:
            end_row = self._data_start_row + self._last_display_count - 1
            self.excel_mgr.clear_range(
                self.sheet, start_row=self._data_start_row, start_col=1,
                end_row=end_row + 5, end_col=3
            )

        # 写入新数据
        if not df.empty:
            self.excel_mgr.write_df(
                self.sheet, df[["代码", "名称", "市场"]],
                start_row=self._data_start_row, start_col=1
            )

        # 更新状态提示
        self.sheet.cells(2, 1).value = (
            f"共 {total} 只 | 当前显示 {len(df)} 只"
        )
        self._last_display_count = len(df)

    def refresh(self):
        """刷新：检查搜索触发信号"""
        if self.sheet is None or self.pool.df.empty:
            return

        # 检查触发信号
        try:
            trigger = self.excel_mgr.get_cell_value(
                self.sheet, self._trigger_cell[0], self._trigger_cell[1]
            )
        except Exception:
            return

        if not trigger:
            return

        trigger = str(trigger).strip().upper()
        # 清除触发信号
        try:
            self.sheet.cells(self._trigger_cell[0],
                             self._trigger_cell[1]).value = None
        except Exception:
            pass

        if trigger == "SEARCH":
            # 读取搜索关键字
            keyword = self.excel_mgr.get_cell_value(
                self.sheet, self._search_cell[0], self._search_cell[1]
            )
            keyword = str(keyword).strip() if keyword else ""
            self._logger.info(f"搜索股票: '{keyword}'")
            result = self.pool.search(keyword, limit=self._default_limit)
            self._display(result, total=len(self.pool.df))
        elif trigger == "ALL":
            self._logger.info("显示全部股票")
            self._display(
                self.pool.df.head(self._default_limit),
                total=len(self.pool.df)
            )

    def setup_dropdown_for(self, target_sheet, col: int = 1,
                           start_row: int = 2, end_row: int = 200):
        """为指定 Sheet 的代码列设置下拉框数据验证

        引用本 Sheet 的代码列作为下拉选项。

        Args:
            target_sheet: 目标 Sheet 对象
            col: 代码列号（从1开始）
            start_row, end_row: 应用下拉框的行范围
        """
        if self.sheet is None or self.pool.df.empty:
            self._logger.warning("股票池为空，无法设置下拉框")
            return
        try:
            # 数据验证公式：引用股票池 Sheet 的代码列
            # 格式: =股票池!$A$5:$A$N
            n = min(len(self.pool.df), 5000)  # Excel 数据验证有长度限制
            formula = f"={self.name}!$A${self._data_start_row}:$A${self._data_start_row + n - 1}"
            rng = target_sheet.range((start_row, col), (end_row, col))
            # xlwings 设置数据验证
            rng.api.Validation.Delete()
            rng.api.Validation.Add(
                Type=3,  # xlValidateList
                AlertStyle=2,  # xlValidAlertWarning（警告但不阻止）
                Formula1=formula
            )
            self._logger.info(f"下拉框已设置: {target_sheet.name} 列{col}")
        except Exception as e:
            self._logger.warning(f"设置下拉框失败: {e}（不影响手动输入）")
