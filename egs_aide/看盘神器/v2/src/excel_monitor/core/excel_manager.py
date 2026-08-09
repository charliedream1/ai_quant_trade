# -*- coding: utf-8 -*-
"""Excel 管理器：封装 xlwings 工作簿操作"""
import os
from typing import Optional, Tuple

import xlwings as xw
import pandas as pd

from excel_monitor.logger import get_logger


class ExcelManager:
    """管理 Excel 工作簿的打开、读写"""

    def __init__(self, xlsx_path: str):
        self._logger = get_logger(self.__class__.__name__)
        self._xlsx_path = xlsx_path

        if not os.path.exists(xlsx_path):
            raise FileNotFoundError(f"Excel 文件不存在: {xlsx_path}")

        self.wb = xw.Book(xlsx_path)
        # 确保 Excel 应用可见（避免后台模式导致 save 异常）
        try:
            self.wb.app.visible = True
        except Exception:
            pass
        self._logger.info(f"已打开 Excel: {xlsx_path}")

    def get_sheet_by_name(self, name: str) -> Optional[xw.Sheet]:
        """按名称获取 Sheet"""
        try:
            return self.wb.sheets[name]
        except Exception:
            self._logger.warning(f"Sheet 不存在: {name}")
            return None

    def add_sheet(self, name: str, after: Optional[str] = None) -> xw.Sheet:
        """新增 Sheet，若已存在则直接返回

        Args:
            name: Sheet 名称
            after: 在该 Sheet 之后插入；为 None 时追加到末尾
        """
        existing = self.get_sheet_by_name(name)
        if existing is not None:
            return existing
        try:
            if after is not None:
                after_sheet = self.get_sheet_by_name(after)
                if after_sheet is not None:
                    sheet = self.wb.sheets.add(name, after=after_sheet)
                else:
                    sheet = self.wb.sheets.add(name)
            else:
                sheet = self.wb.sheets.add(name)
            self._logger.info(f"已新增 Sheet: {name}")
            return sheet
        except Exception as e:
            self._logger.error(f"新增 Sheet '{name}' 失败: {e}")
            raise

    def sheet_to_df(self, sheet: xw.Sheet) -> Tuple[pd.DataFrame, int, int]:
        """将 Sheet 转为 DataFrame，返回 (df, row_num, col_num)"""
        row_num = sheet.api.UsedRange.Rows.Count
        col_num = sheet.api.UsedRange.Columns.Count

        if row_num <= 1 and col_num <= 1:
            val = sheet.range((1, 1)).value
            if val is None:
                return pd.DataFrame(), 0, 0

        df = sheet.range(
            (1, 1), (row_num, col_num)
        ).options(pd.DataFrame, headers=True, index=False).value

        if df is None:
            return pd.DataFrame(), 0, 0

        return df, row_num, col_num

    def write_df(self, sheet: xw.Sheet, df: pd.DataFrame,
                 start_row: int = 1, start_col: int = 1):
        """将 DataFrame 写入 Sheet（含列名）

        使用 xlwings 单点赋值方式，确保列名和数据都被正确写入。
        """
        if df is None or df.empty:
            self._logger.debug(f"写入空数据，跳过: {sheet.name}")
            return

        # 检测 Excel 进程是否存活，避免 COM 调用卡死
        if not self.is_alive():
            self._logger.warning(f"Excel 进程已退出，跳过写入 {sheet.name}")
            return

        try:
            # 重置 index，避免 DataFrame 的索引被写入造成错位
            df_write = df.reset_index(drop=True)
            n_rows = df_write.shape[0]
            n_cols = df_write.shape[1]

            # 将 NaN 替换为 None，避免 xlwings 写入 nan 字符串
            df_write = df_write.where(pd.notnull(df_write), None)

            # 构造含列名的二维列表（第一行为列名，后续为数据）
            data = [df_write.columns.tolist()]
            for row in df_write.itertuples(index=False, name=None):
                data.append([str(v) if isinstance(v, pd.Timestamp) else v for v in row])

            # 使用单点起始写入，让 xlwings 自动扩展范围
            # 这样可以避免范围大小不匹配的问题
            target_range = sheet.range((start_row, start_col))
            target_range.value = data

            # 验证写入结果
            verify = sheet.range(
                (start_row, start_col),
                (start_row + n_rows, start_col + n_cols - 1)
            ).value
            verify_rows = len(verify) if verify else 0
            self._logger.info(
                f"已写入 {sheet.name}: {n_rows} 行 × {n_cols} 列 "
                f"(起始行{start_row}列{start_col}), 验证读取 {verify_rows} 行"
            )
        except Exception as e:
            self._logger.error(f"写入 {sheet.name} 失败: {e}")
            import traceback
            self._logger.debug(traceback.format_exc())

    def clear_range(self, sheet: xw.Sheet, start_row: int = 1,
                    start_col: int = 1, end_row: int = 200, end_col: int = 50):
        """清除指定区域内容"""
        sheet.range((start_row, start_col), (end_row, end_col)).clear_contents()

    def highlight_row(self, sheet: xw.Sheet, row: int,
                      start_col: int = 1, end_col: int = 20,
                      color: tuple = (255, 200, 200)):
        """高亮整行（默认浅红色背景）"""
        rng = sheet.range((row, start_col), (row, end_col))
        rng.color = color

    def clear_highlight(self, sheet: xw.Sheet, start_row: int = 1,
                        end_row: int = 200, start_col: int = 1, end_col: int = 20):
        """清除高亮格式"""
        rng = sheet.range((start_row, start_col), (end_row, end_col))
        rng.color = None

    def add_button(self, sheet: xw.Sheet, row: int, col: int,
                   text: str, macro: str, width: int = 100, height: int = 30):
        """在 Sheet 中添加表单按钮并绑定宏

        使用 Excel COM API 直接添加 Form Control 按钮（xlwings 0.36
        未提供 shapes.add_button 接口）。

        Args:
            sheet: 目标 Sheet
            row, col: 按钮左上角位置（行、列，从1开始）
            text: 按钮显示文字
            macro: 绑定的宏名称（VBA 函数名）
            width: 按钮宽度（像素）
            height: 按钮高度（像素）
        """
        try:
            cell = sheet.cells(row, col)
            left = cell.left
            top = cell.top
            # 使用 Excel COM API 添加 Form Control 按钮
            # Buttons().Add(Left, Top, Width, Height) 单位为 points
            api = sheet.api
            button = api.Buttons().Add(left, top, width, height)
            button.Caption = text
            button.OnAction = macro
            button.Name = f"Btn_{macro}"
            self._logger.info(f"按钮已添加: {text} -> {macro}")
            return button
        except Exception as e:
            self._logger.error(f"添加按钮失败: {e}")
            return None

    def insert_image(self, sheet: xw.Sheet, image_path: str,
                     row: int = 1, col: int = 1,
                     width: int = 600, height: int = 350):
        """在 Sheet 中插入图片

        Args:
            sheet: 目标 Sheet
            image_path: 图片文件路径
            row, col: 插入位置（行、列，从1开始）
            width: 图片宽度（像素）
            height: 图片高度（像素）
        """
        try:
            # 先清除该位置已有的图片（避免叠加）
            self.clear_images_in_range(sheet, row, col, row + 20, col + 10)

            anchor = sheet.cells(row, col)
            pic = sheet.pictures.add(
                image_path, left=anchor.left, top=anchor.top,
                width=width, height=height
            )
            self._logger.info(f"图片已插入: {image_path} -> 行{row}列{col}")
            return pic
        except Exception as e:
            self._logger.error(f"插入图片失败: {e}")
            return None

    def clear_images_in_range(self, sheet: xw.Sheet,
                              start_row: int, start_col: int,
                              end_row: int, end_col: int):
        """清除指定区域内的图片"""
        try:
            left = sheet.cells(start_row, start_col).left
            top = sheet.cells(start_row, start_col).top
            right = sheet.cells(end_row, end_col).left
            bottom = sheet.cells(end_row, end_col).top

            for pic in list(sheet.pictures):
                if (pic.left >= left and pic.top >= top and
                        pic.left < right and pic.top < bottom):
                    pic.delete()
                    self._logger.debug(f"已删除图片: {pic.name}")
        except Exception as e:
            self._logger.debug(f"清除图片时: {e}")

    def get_cell_value(self, sheet: xw.Sheet, row: int, col: int):
        """获取单元格值"""
        return sheet.cells(row, col).value

    def close(self):
        """关闭工作簿（先保存再关闭）"""
        try:
            self.wb.save()
            self._logger.info(f"Excel 已保存: {self._xlsx_path}")
            self.wb.close()
        except Exception as e:
            self._logger.error(f"关闭 Excel 失败: {e}")

    def is_alive(self) -> bool:
        """检测 Excel 应用是否仍然存活"""
        try:
            _ = self.wb.app.pid
            return True
        except Exception:
            return False

    def save(self):
        """保存工作簿（不关闭）

        使用显式路径调用 Save，确保数据写入磁盘。
        若 Excel 进程已退出，跳过保存以避免主线程卡死。
        """
        # 先检测 Excel 进程是否存活，避免 COM 调用卡死
        if not self.is_alive():
            self._logger.warning("Excel 进程已退出，跳过本次保存")
            return
        try:
            # 使用 COM API 直接调用 Save，确保磁盘写入
            self.wb.api.Save()
            self._logger.info(f"Excel 已保存: {self._xlsx_path}")
        except Exception as e:
            self._logger.error(f"保存 Excel 失败: {e}")
            # 降级：尝试 xlwings 原生 save
            try:
                if not self.is_alive():
                    return
                self.wb.save(self._xlsx_path)
                self._logger.info(f"Excel 已保存(降级): {self._xlsx_path}")
            except Exception as e2:
                self._logger.error(f"降级保存也失败: {e2}")
