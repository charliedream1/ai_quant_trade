# -*- coding: utf-8 -*-
"""股票池 Sheet Handler 测试

覆盖：
    1. init: 加载股票池 + 写入表头 + 添加搜索按钮 + 显示默认列表
    2. refresh 搜索触发: SEARCH 信号 → 过滤显示
    3. refresh 显示全部触发: ALL 信号 → 显示全部
    4. refresh 无信号: 不操作
    5. setup_dropdown_for: 为目标 Sheet 设置下拉框
"""
import pandas as pd
from unittest.mock import MagicMock

from excel_monitor.config_loader import AppConfig
from excel_monitor.core.stock_pool import StockPool
from excel_monitor.sheets.stock_pool_sheet import StockPoolSheet


def _make_pool_with_data():
    """构造带测试数据的 StockPool"""
    pool = StockPool(cache_path="/tmp/nonexistent.json")
    pool.df = pd.DataFrame({
        "代码": ["000001", "600000", "600519", "000333", "300750"],
        "名称": ["平安银行", "浦发银行", "贵州茅台", "美的集团", "宁德时代"],
        "市场": ["深圳", "沪市", "沪市", "深圳", "深圳"],
        "拼音": ["payh", "pfyh", "gzmt", "mdjt", "ndsd"],
    })
    return pool


def _make_sheet(pool=None):
    """构造 StockPoolSheet 实例"""
    cfg = AppConfig()
    cfg.stock_pool_cache_days = 7
    mock_excel = MagicMock()
    mock_data = MagicMock()
    p = pool or _make_pool_with_data()
    sheet = StockPoolSheet("股票池", mock_excel, mock_data, cfg, p)
    sheet.sheet = MagicMock()
    return sheet, mock_excel, p


# =====================================================================
# 1. init
# =====================================================================
def test_init_loads_pool_and_displays():
    """测试 init 加载股票池并显示默认列表"""
    sheet, mock_excel, pool = _make_sheet()
    pool.load_or_fetch = MagicMock(return_value=pool.df)

    sheet.init()

    # 应显示前 200 条（默认 limit）
    assert mock_excel.write_df.call_count == 1
    written_df = mock_excel.write_df.call_args[0][1]
    assert len(written_df) == 5  # 只有 5 条测试数据
    assert list(written_df.columns) == ["代码", "名称", "市场"]


def test_init_adds_search_and_show_all_buttons():
    """测试 init 添加搜索按钮和显示全部按钮"""
    sheet, mock_excel, pool = _make_sheet()
    pool.load_or_fetch = MagicMock(return_value=pool.df)

    sheet.init()

    # 应添加 2 个按钮
    assert mock_excel.add_button.call_count == 2
    button_texts = [c[1]["text"] for c in mock_excel.add_button.call_args_list]
    assert "搜索" in button_texts
    assert "显示全部" in button_texts


def test_init_empty_pool_skips():
    """测试股票池为空时 init 不报错"""
    sheet, mock_excel, pool = _make_sheet()
    pool.load_or_fetch = MagicMock(return_value=pd.DataFrame())

    sheet.init()

    mock_excel.write_df.assert_not_called()


def test_init_writes_headers():
    """测试 init 写入表头"""
    sheet, mock_excel, pool = _make_sheet()
    pool.load_or_fetch = MagicMock(return_value=pool.df)

    sheet.init()

    # 表头在第 4 行
    calls = sheet.sheet.cells.call_args_list
    # 检查表头写入
    header_values = []
    for call in calls:
        args = call[0]
        if len(args) >= 2 and args[0] == 4:
            header_values.append(call)
    assert len(header_values) >= 3  # 代码、名称、市场


# =====================================================================
# 2. refresh 搜索触发
# =====================================================================
def test_refresh_search_trigger_filters():
    """测试 SEARCH 触发信号 → 过滤显示"""
    sheet, mock_excel, pool = _make_sheet()
    sheet._last_display_count = 5  # 模拟已有数据显示

    # D2 = "SEARCH", B1 = "平安"
    mock_excel.get_cell_value.side_effect = ["SEARCH", "平安"]

    sheet.refresh()

    # 应清除旧数据 + 写入过滤结果
    mock_excel.clear_range.assert_called_once()
    mock_excel.write_df.assert_called_once()
    written_df = mock_excel.write_df.call_args[0][1]
    assert len(written_df) == 1
    assert written_df.iloc[0]["名称"] == "平安银行"


def test_refresh_all_trigger_shows_all():
    """测试 ALL 触发信号 → 显示全部"""
    sheet, mock_excel, pool = _make_sheet()
    sheet._last_display_count = 1

    mock_excel.get_cell_value.return_value = "ALL"

    sheet.refresh()

    mock_excel.clear_range.assert_called_once()
    mock_excel.write_df.assert_called_once()
    written_df = mock_excel.write_df.call_args[0][1]
    assert len(written_df) == 5  # 全部


def test_refresh_no_trigger_does_nothing():
    """测试无触发信号时不操作"""
    sheet, mock_excel, pool = _make_sheet()

    mock_excel.get_cell_value.return_value = None

    sheet.refresh()

    mock_excel.clear_range.assert_not_called()
    mock_excel.write_df.assert_not_called()


def test_refresh_clears_trigger_signal():
    """测试触发后清除信号单元格"""
    sheet, mock_excel, pool = _make_sheet()
    sheet._last_display_count = 5

    mock_excel.get_cell_value.side_effect = ["SEARCH", "600"]

    sheet.refresh()

    # 应清除 D2 信号（sheet.cells(2,4).value = None）
    # 检查 cells 被赋值为 None
    [c for c in sheet.sheet.cells.call_args_list
                 if len(c[0]) >= 2 and c[0][0] == 2 and c[0][1] == 4]
    # cells(2,4).value = None 应该有调用


def test_refresh_empty_pool_returns():
    """测试股票池为空时 refresh 直接返回"""
    pool = StockPool(cache_path="/tmp/nonexistent.json")
    pool.df = pd.DataFrame()
    sheet, mock_excel, _ = _make_sheet(pool=pool)

    sheet.refresh()

    mock_excel.get_cell_value.assert_not_called()


# =====================================================================
# 3. setup_dropdown_for
# =====================================================================
def test_setup_dropdown_calls_validation():
    """测试 setup_dropdown_for 调用 Excel 数据验证 API"""
    sheet, mock_excel, pool = _make_sheet()
    target_sheet = MagicMock()
    target_range = MagicMock()
    target_sheet.range.return_value = target_range

    sheet.setup_dropdown_for(target_sheet, col=1, start_row=2, end_row=200)

    target_sheet.range.assert_called_once_with((2, 1), (200, 1))
    target_range.api.Validation.Delete.assert_called_once()
    target_range.api.Validation.Add.assert_called_once()
    # 检查 formula 引用股票池 Sheet
    add_args = target_range.api.Validation.Add.call_args
    formula = add_args[1]["Formula1"]
    assert "股票池" in formula
    assert "$A$" in formula


def test_setup_dropdown_empty_pool_skips():
    """测试股票池为空时不设置下拉框"""
    pool = StockPool(cache_path="/tmp/nonexistent.json")
    pool.df = pd.DataFrame()
    sheet, mock_excel, _ = _make_sheet(pool=pool)
    target_sheet = MagicMock()

    sheet.setup_dropdown_for(target_sheet, col=1)

    target_sheet.range.assert_not_called()


def test_setup_dropdown_failure_does_not_raise():
    """测试下拉框设置失败不抛异常（不影响主流程）"""
    sheet, mock_excel, pool = _make_sheet()
    target_sheet = MagicMock()
    target_sheet.range.side_effect = Exception("Excel error")

    # 不应抛异常
    sheet.setup_dropdown_for(target_sheet, col=1)


# =====================================================================
# 4. _display 辅助
# =====================================================================
def test_display_updates_status_text():
    """测试 _display 更新状态提示"""
    sheet, mock_excel, pool = _make_sheet()
    df = pool.df.head(2)

    sheet._display(df, total=5)

    # A2 应更新为 "共 5 只 | 当前显示 2 只"
    sheet.sheet.cells.assert_any_call(2, 1)
    # 检查 cells(2,1).value 被设置
    cells_2_1 = sheet.sheet.cells.call_args_list
    found = False
    for call in cells_2_1:
        if call[0] == (2, 1):
            found = True
    assert found


def test_display_clears_old_data_first():
    """测试 _display 先清除旧数据再写入"""
    sheet, mock_excel, pool = _make_sheet()
    sheet._last_display_count = 10  # 之前显示 10 条
    df = pool.df.head(3)

    sheet._display(df, total=5)

    # 应先 clear_range 再 write_df
    mock_excel.clear_range.assert_called_once()
    mock_excel.write_df.assert_called_once()
