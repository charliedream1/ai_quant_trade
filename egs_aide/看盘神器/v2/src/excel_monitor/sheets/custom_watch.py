# -*- coding: utf-8 -*-
"""个性定制看盘 Sheet：用户自选股 + 自定义显示列 + 预警监控

用户在 Excel 的"个性定制看盘" Sheet 中：
  - A-M 列：填写自选股代码（程序自动刷新行情数据）
  - N-Q 列：填写预警条件（涨跌幅下限/上限、价格下限/上限）

达到预警条件时：整行变红 + 弹窗提醒
"""
from typing import List, Optional

import pandas as pd

from excel_monitor.logger import get_logger
from excel_monitor.sheets.base import BaseSheet
from excel_monitor.config_loader import AppConfig
from excel_monitor.core.alert_checker import (
    AlertCondition, AlertChecker
)
from excel_monitor.utils.kline_chart import KLineChart

# qstock 返回的列名可能不统一，这里做兼容映射
_PRICE_COLS = ["最新", "最新价", "当前价", "现价"]
_CHANGE_COLS = ["涨跌幅", "涨幅", "涨跌幅%"]


class CustomWatchSheet(BaseSheet):
    """个性定制看盘 Sheet Handler"""

    def __init__(self, name, excel_mgr, data_provider, config=None):
        super().__init__(name, excel_mgr, data_provider)
        self.config = config or AppConfig()
        self._logger = get_logger(self.__class__.__name__)
        self._stock_codes: list = []
        self._alert_conditions: List[AlertCondition] = []
        # 数据列数（用于写入时只清除数据区域，保留预警条件列）
        self._data_col_count = len(self.config.custom_watch_columns)
        # 刷新计数器（用于定时重载配置）
        self._refresh_count = 0
        # K 线图绘制器
        self._kline_chart = KLineChart()
        # K 线按钮行号（B21 单元格存储用户选择的行号）
        self._kline_row_cell = (21, 2)  # (row, col) = B21

    def init(self):
        """从 Excel 读取自选股代码和预警条件（首次加载）"""
        self._reload_from_excel()
        # 添加"画K线"按钮
        self._add_kline_button()

    def _add_kline_button(self):
        """在 Excel 中添加'画K线'按钮"""
        if self.sheet is None:
            return
        # 清除 D21 占位文字
        try:
            self.sheet.cells(21, 4).value = None
        except Exception:
            pass
        # 添加按钮（位于 D21 位置）
        self.excel_mgr.add_button(
            self.sheet, row=21, col=4,
            text="画K线", macro="DrawKLineMacro",
            width=80, height=30
        )
        # 尝试注入 VBA 宏
        self._setup_vba_macro()

    def _setup_vba_macro(self):
        """注入 VBA 宏，使按钮点击时写入触发信号

        VBA 宏点击后向 D21 写入 "DRAW"，由 refresh() 轮询检测。
        若 VBA 注入失败（权限/格式限制），降级为手动输入模式。
        """
        vba_code = (
            'Sub DrawKLineMacro()\n'
            '    Range("D21").Value = "DRAW"\n'
            'End Sub'
        )
        try:
            wb = self.sheet.book
            vb_project = wb.api.VBProject
            module_name = "KLineModule"
            # 移除旧模块（如果存在）
            try:
                old = vb_project.VBComponents.Item(module_name)
                vb_project.VBComponents.Remove(old)
            except Exception:
                pass
            # 添加新模块（1 = vbext_ct_StdModule）
            vb_module = vb_project.VBComponents.Add(1)
            vb_module.Name = module_name
            vb_module.CodeModule.AddFromString(vba_code)
            self._logger.info("VBA 宏注入成功，点击按钮即可画K线")
        except Exception as e:
            self._logger.warning(
                f"VBA 宏注入失败: {e}。"
                f"如需启用按钮，请在 Excel → 文件 → 选项 → 信任中心 → "
                f"信任中心设置 → 宏设置 中勾选"
                f"'信任对 VBA 工程对象模型的访问' 后重启程序。"
            )
            self._logger.info(
                "降级为轮询模式：在 D21 单元格输入 DRAW，"
                "下次刷新时自动画K线"
            )

    def _check_kline_trigger(self):
        """检查是否有画K线触发信号（轮询模式）"""
        if self.sheet is None:
            return
        try:
            trigger = self.excel_mgr.get_cell_value(self.sheet, 21, 4)
        except Exception:
            return
        if trigger and str(trigger).strip().upper() == "DRAW":
            # 清除触发信号
            try:
                self.sheet.cells(21, 4).value = None
            except Exception:
                pass
            # 触发画K线
            self.draw_kline()

    def draw_kline(self):
        """画K线图：读取选中行号 → 获取股票代码 → 获取K线数据 → 绘图 → 插入图片"""
        if self.sheet is None:
            self._logger.warning("Sheet 未初始化，无法画K线")
            return

        # 1. 读取 B21 单元格的行号
        row_num = self.excel_mgr.get_cell_value(self.sheet, 21, 2)
        if row_num is None:
            self._logger.warning("请在 B21 输入要画K线的股票行号")
            return
        try:
            row_num = int(row_num)
        except (ValueError, TypeError):
            self._logger.warning(f"B21 行号无效: {row_num}，请输入数字")
            return
        if row_num < 2:
            self._logger.warning(f"行号 {row_num} 无效，应 >= 2")
            return

        # 2. 获取该行的股票代码（A 列）
        code = self.excel_mgr.get_cell_value(self.sheet, row_num, 1)
        if not code:
            self._logger.warning(f"第 {row_num} 行无股票代码")
            return
        code = str(code).strip()

        # 3. 获取股票名称（B 列）
        name = self.excel_mgr.get_cell_value(self.sheet, row_num, 2)
        name = str(name).strip() if name else code

        self._logger.info(f"开始画K线: 行{row_num} 代码={code} 名称={name}")

        # 4. 获取 K 线数据
        df = self.data.get_kline_data(
            code, count=self.config.kline_count, freq=self.config.kline_freq
        )
        if df.empty:
            self._logger.warning(f"获取K线数据失败: {code}")
            return

        # 5. 绘制 K 线图
        image_path = self._kline_chart.draw(
            df, stock_name=name,
            chart_type=self.config.kline_chart_type,
            mav=self.config.kline_mav
        )
        if not image_path:
            self._logger.error("K线图绘制失败")
            return

        # 6. 插入图片到 Excel
        self.excel_mgr.insert_image(
            self.sheet, image_path,
            row=self.config.kline_display_row,
            col=self.config.kline_display_col,
            width=self.config.kline_image_width,
            height=self.config.kline_image_height
        )
        self._logger.info(f"K线图已插入: {code} ({name})")

    def _reload_from_excel(self):
        """从 Excel 重新读取自选股代码和预警条件"""
        df, _, _ = self.excel_mgr.sheet_to_df(self.sheet)

        if not df.empty and "代码" in df.columns:
            self._stock_codes = df["代码"].dropna().tolist()
            self._logger.info(f"定制自选股加载: {self._stock_codes}")
        else:
            self._stock_codes = self.config.watch_stocks
            self._logger.info(f"使用默认自选股: {self._stock_codes}")

        # 读取预警条件
        self._alert_conditions = self._parse_alert_conditions(df)
        if self._alert_conditions:
            self._logger.info(
                f"预警条件加载: {len(self._alert_conditions)} 只股票"
            )

    def _parse_alert_conditions(self, df: pd.DataFrame) -> List[AlertCondition]:
        """从 DataFrame 解析预警条件"""
        conditions = []
        if df.empty:
            return conditions

        # 获取预警列名
        alert_cols = self.config.alert_columns
        # 找到各预警列在 df 中的位置
        col_map = {}
        for ac in alert_cols:
            if ac in df.columns:
                col_map[ac] = df.columns.get_loc(ac)

        if not col_map:
            return conditions

        for _, row in df.iterrows():
            code = str(row.get("代码", "")).strip()
            if not code or code == "nan":
                continue
            name = str(row.get("名称", code)).strip()

            def _get_val(col_name):
                """安全获取数值，空值返回 None"""
                if col_name not in col_map:
                    return None
                val = row.iloc[col_map[col_name]]
                if pd.isna(val) or val is None:
                    return None
                try:
                    return float(val)
                except (ValueError, TypeError):
                    return None

            cond = AlertCondition(
                code=code,
                name=name,
                change_pct_min=_get_val("涨跌幅下限"),
                change_pct_max=_get_val("涨跌幅上限"),
                price_min=_get_val("价格下限"),
                price_max=_get_val("价格上限"),
            )
            # 至少有一个条件才加入
            if any([cond.change_pct_min, cond.change_pct_max,
                    cond.price_min, cond.price_max]):
                conditions.append(cond)

        return conditions

    @staticmethod
    def _find_value(row, possible_cols: List[str]) -> Optional[float]:
        """从多个可能的列名中找到数值"""
        for col in possible_cols:
            if col in row.index:
                val = row[col]
                if pd.notna(val) and val is not None:
                    try:
                        return float(val)
                    except (ValueError, TypeError):
                        pass
        return None

    def refresh(self):
        """刷新定制看盘数据 + 检查预警"""
        self._logger.info("刷新个性定制看盘...")

        # 检查画K线触发信号（轮询模式）
        self._check_kline_trigger()

        # 每隔 N 次刷新，重新从 Excel 读取股票代码和预警条件（支持实时修改）
        self._refresh_count += 1
        reload_interval = self.config.config_reload_interval
        if reload_interval > 0 and self._refresh_count % reload_interval == 0:
            self._logger.info(f"第 {self._refresh_count} 次刷新，重载 Excel 配置...")
            self._reload_from_excel()

        if not self._stock_codes:
            self._logger.warning("无自选股，跳过刷新")
            return

        # 获取实时行情
        df_rt = self.data.get_stock_realtime(self._stock_codes)
        if df_rt.empty:
            self._logger.info("自选股行情未刷到，保留上次数据")
            return

        # 按配置列过滤
        df_display = self.data.filter_columns(
            df_rt, self.config.custom_watch_columns
        )

        # 补充刷新时间
        if "刷新时间" in self.config.custom_watch_columns \
                and "刷新时间" not in df_display.columns:
            if "时间" in df_rt.columns:
                df_display["刷新时间"] = df_rt["时间"]

        # 写入数据（只清除数据列区域，保留预警条件列）
        self._write_data(df_display)

        # 检查预警并高亮
        triggered_rows = self._check_and_highlight(df_display, df_rt)

        # 弹窗提醒
        if triggered_rows and self.config.alert_popup_enabled:
            self._show_popup(triggered_rows)

    def _write_data(self, df: pd.DataFrame):
        """写入数据到 Sheet（只清除数据列，不触碰预警条件列）

        重要：用户在 Excel 中可能填入中文名称（如"中国平安"）作为"代码"列，
        此时 df 中代码列也会是中文。为避免后续刷新时按中文匹配失败，
        在写入前用行情数据返回的标准代码替换中文代码列。
        """
        if self.sheet is None:
            return

        # 用行情数据返回的代码列替换原 df 的代码列
        # 这样下次刷新时 _reload_from_excel 读到的就是标准代码
        if not df.empty and "代码" in df.columns:
            # 同时更新内存中的 _stock_codes，避免下次刷新再次传中文
            new_codes = df["代码"].astype(str).tolist()
            if new_codes:
                self._stock_codes = new_codes

        # 只清除数据列区域（列 1 到 data_col_count）
        self.excel_mgr.clear_range(
            self.sheet, start_row=1, start_col=1,
            end_row=200, end_col=self._data_col_count
        )
        self.excel_mgr.write_df(self.sheet, df, start_row=1, start_col=1)

    def _check_and_highlight(self, df_display: pd.DataFrame,
                             df_rt: pd.DataFrame) -> List:
        """检查预警条件，高亮触发的行，返回触发的 AlertResult 列表"""
        if not self._alert_conditions:
            return []

        # 清除之前的高亮
        total_cols = self._data_col_count + len(self.config.alert_columns)
        self.excel_mgr.clear_highlight(
            self.sheet, start_row=2, end_row=200,
            start_col=1, end_col=total_cols
        )

        # 构建 code -> price / change_pct 映射
        price_map = {}
        change_map = {}
        for _, row in df_rt.iterrows():
            code = str(row.get("代码", "")).strip()
            if not code:
                continue
            price = self._find_value(row, _PRICE_COLS)
            change = self._find_value(row, _CHANGE_COLS)
            if price is not None:
                price_map[code] = price
            if change is not None:
                change_map[code] = change

        # 批量检查预警
        all_results = AlertChecker.check_batch(
            self._alert_conditions, price_map, change_map
        )

        if not all_results:
            return []

        # 找出触发的股票代码
        triggered_codes = {r.code for r in all_results}

        # 高亮触发的行（Excel 行号 = 数据行 + 1（表头）+ 1（从1开始））
        for idx, row in df_display.iterrows():
            code = str(row.get("代码", "")).strip()
            if code in triggered_codes:
                excel_row = idx + 2  # df 索引 0 = Excel 第 2 行
                self.excel_mgr.highlight_row(
                    self.sheet, row=excel_row,
                    start_col=1, end_col=total_cols,
                    color=(255, 200, 200)
                )
                self._logger.warning(
                    f"预警触发: {code} 行 {excel_row} 已高亮"
                )

        return all_results

    def _show_popup(self, results: List):
        """弹出预警提醒窗口"""
        message = AlertChecker.format_alert_message(results)
        self._logger.warning(f"预警弹窗:\n{message}")

        try:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            messagebox.showwarning("盯盘预警", message)
            root.destroy()
        except Exception as e:
            # 无 GUI 环境（如 CI/服务器），降级为日志输出
            self._logger.info(f"无 GUI 环境，预警仅记录日志: {e}")
