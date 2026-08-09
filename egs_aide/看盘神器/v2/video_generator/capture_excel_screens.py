# -*- coding: utf-8 -*-
"""截取 Excel 各 Sheet 真实显示效果"""
import os
import time

import win32com.client as win32
import win32gui
import win32con
from PIL import ImageGrab

# 使用相对路径（基于本脚本所在目录）
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
XLSX = os.path.join(_BASE_DIR, "看盘模板.xlsx")
OUT_DIR = os.path.join(_BASE_DIR, "video_generator", "excel_screenshots")
os.makedirs(OUT_DIR, exist_ok=True)


def main():
    print(f"启动 Excel 并打开: {XLSX}")
    xl = win32.DispatchEx("Excel.Application")
    xl.Visible = True
    xl.DisplayAlerts = False
    try:
        xl.WindowState = -4137  # xlMaximized
    except Exception:
        pass

    wb = xl.Workbooks.Open(XLSX)
    time.sleep(2)

    # 截取关键 sheet
    sheets = [
        ("详细行情", "detailed_quotes.png"),
        ("个性定制看盘", "custom_watch.png"),
        ("大盘", "market_overview.png"),
        ("新闻", "news.png"),
        ("资金情绪", "sentiment.png"),
        ("股票池", "stock_pool.png"),
    ]
    for name, fname in sheets:
        try:
            ws = wb.Sheets(name)
            ws.Activate()
            # 滚动到 A1
            xl.ActiveWindow.ScrollRow = 1
            xl.ActiveWindow.ScrollColumn = 1
            time.sleep(1.5)
            hwnd = xl.Hwnd
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            win32gui.BringWindowToTop(hwnd)
            time.sleep(1.0)
            rect = win32gui.GetWindowRect(hwnd)
            img = ImageGrab.grab(bbox=rect)
            out = os.path.join(OUT_DIR, fname)
            img.save(out)
            print(f"  [{name}] 截图: {out} ({img.size[0]}x{img.size[1]})")
        except Exception as e:
            print(f"  [{name}] 失败: {e}")

    try:
        wb.Save()
        xl.Quit()
    except Exception:
        pass


if __name__ == "__main__":
    main()
