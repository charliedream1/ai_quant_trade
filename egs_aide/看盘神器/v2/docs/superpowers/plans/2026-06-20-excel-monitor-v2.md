# Excel 盯盘工具 V2 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 `egs_aide/看盘神器/v2/` 下开发模块化、配置驱动的 Excel 实时盯盘工具，包含大盘、详细行情、新闻、个性定制看盘四个 Sheet。

**Architecture:** 采用策略模式——每个 Sheet 对应一个 Handler 类（继承 `BaseSheet`），由 `ExcelManager` 管理 xlwings 工作簿，`DataProvider` 封装 qstock 数据获取。`main.py` 负责组装和刷新循环。配置通过 `config.py` 集中管理，用户无需改代码即可定制自选股和显示列。

**Tech Stack:** Python 3.8+, xlwings, qstock, pandas, openpyxl（模板生成）, pytest

---

## 文件结构

```
egs_aide/看盘神器/v2/
├── main.py                  # 入口：组装组件 + 刷新循环
├── config.py                # 配置：刷新间隔、自选股、指数列表等
├── data_provider.py         # qstock 数据获取封装（含异常处理）
├── excel_manager.py         # xlwings 工作簿/Sheet 读写管理
├── sheets/
│   ├── __init__.py
│   ├── base.py              # BaseSheet 抽象基类
│   ├── market_overview.py   # 大盘 Sheet Handler
│   ├── detailed_quotes.py   # 详细行情 Sheet Handler
│   ├── news_sheet.py        # 新闻 Sheet Handler
│   └── custom_watch.py      # 个性定制看盘 Sheet Handler
├── create_template.py       # 生成 Excel 模板（openpyxl）
├── tests/
│   ├── __init__.py
│   ├── test_config.py       # 配置解析测试
│   ├── test_data_provider.py # 数据转换逻辑测试
│   └── test_sheets.py       # Sheet Handler 逻辑测试（mock 数据）
├── requirements.txt
└── 看盘模板.xlsx            # Excel 模板（由 create_template.py 生成）
```

**职责划分：**
- `config.py`：所有可配置项（刷新间隔、自选股列表、指数列表、Sheet 名称映射）
- `data_provider.py`：所有 qstock 调用，统一异常处理，返回 DataFrame
- `excel_manager.py`：xlwings 工作簿打开、Sheet→DataFrame 读取、DataFrame→Sheet 写入
- `sheets/base.py`：定义 `init()` 和 `refresh()` 接口
- `sheets/*.py`：各 Sheet 的数据获取 + 写入逻辑
- `create_template.py`：用 openpyxl 生成带格式的 Excel 模板
- `main.py`：组装所有组件，运行刷新循环

---

## Task 1: 项目初始化与依赖

**Files:**
- Create: `egs_aide/看盘神器/v2/requirements.txt`
- Create: `egs_aide/看盘神器/v2/sheets/__init__.py`
- Create: `egs_aide/看盘神器/v2/tests/__init__.py`

- [ ] **Step 1: 创建 requirements.txt**

```
xlwings
qstock
pandas
openpyxl
pytest
```

- [ ] **Step 2: 创建包初始化文件**

`egs_aide/看盘神器/v2/sheets/__init__.py`:
```python
# Sheet handlers package
```

`egs_aide/看盘神器/v2/tests/__init__.py`:
```python
# Tests package
```

- [ ] **Step 3: 安装依赖**

Run: `pip install xlwings qstock pandas openpyxl pytest`
Expected: 所有包安装成功

- [ ] **Step 4: Commit**

```bash
git add egs_aide/看盘神器/v2/requirements.txt egs_aide/看盘神器/v2/sheets/__init__.py egs_aide/看盘神器/v2/tests/__init__.py
git commit -m "feat(v2): init project structure and dependencies"
```

---

## Task 2: 配置模块 (config.py)

**Files:**
- Create: `egs_aide/看盘神器/v2/config.py`
- Create: `egs_aide/看盘神器/v2/tests/test_config.py`

- [ ] **Step 1: 编写配置测试**

`egs_aide/看盘神器/v2/tests/test_config.py`:
```python
from config import AppConfig, SheetConfig


def test_default_config():
    cfg = AppConfig()
    assert cfg.refresh_interval == 3
    assert cfg.excel_template == "看盘模板.xlsx"
    assert "上证指数" in cfg.market_indices
    assert len(cfg.watch_stocks) > 0


def test_sheet_names():
    cfg = AppConfig()
    assert cfg.sheets["market_overview"] == "大盘"
    assert cfg.sheets["detailed_quotes"] == "详细行情"
    assert cfg.sheets["news"] == "新闻"
    assert cfg.sheets["custom_watch"] == "个性定制看盘"


def test_custom_watch_columns():
    cfg = AppConfig()
    assert "代码" in cfg.custom_watch_columns
    assert "名称" in cfg.custom_watch_columns
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd egs_aide/看盘神器/v2 && python -m pytest tests/test_config.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'config'`

- [ ] **Step 3: 实现配置模块**

`egs_aide/看盘神器/v2/config.py`:
```python
# -*- coding: utf-8 -*-
"""盯盘工具 V2 配置模块"""
from dataclasses import dataclass, field
from typing import List, Dict


@dataclass
class SheetConfig:
    """Sheet 名称映射"""
    market_overview: str = "大盘"
    detailed_quotes: str = "详细行情"
    news: str = "新闻"
    custom_watch: str = "个性定制看盘"


@dataclass
class AppConfig:
    """全局配置"""
    # Excel 模板文件名
    excel_template: str = "看盘模板.xlsx"

    # 刷新间隔（秒）
    refresh_interval: int = 3

    # Sheet 名称映射
    sheets: Dict[str, str] = field(default_factory=lambda: {
        "market_overview": "大盘",
        "detailed_quotes": "详细行情",
        "news": "新闻",
        "custom_watch": "个性定制看盘",
    })

    # 大盘指数列表（qstock 简称）
    market_indices: List[str] = field(default_factory=lambda: [
        "上证指数", "深证成指", "创业板指", "沪深300",
        "上证50", "中证500", "科创50",
    ])

    # 自选股代码列表（用户可修改）
    watch_stocks: List[str] = field(default_factory=lambda: [
        "中国平安", "贵州茅台", "宁德时代", "比亚迪",
        "招商银行", "东方财富",
    ])

    # 个性定制看盘显示列
    custom_watch_columns: List[str] = field(default_factory=lambda: [
        "代码", "名称", "最新价", "涨跌幅", "涨跌额",
        "成交量", "成交额", "换手率", "最高", "最低",
        "开盘", "昨收", "刷新时间",
    ])

    # 新闻显示条数
    news_max_rows: int = 50
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd egs_aide/看盘神器/v2 && python -m pytest tests/test_config.py -v`
Expected: PASS — 3 passed

- [ ] **Step 5: Commit**

```bash
git add egs_aide/看盘神器/v2/config.py egs_aide/看盘神器/v2/tests/test_config.py
git commit -m "feat(v2): add config module with dataclass-based settings"
```

---

## Task 3: 数据提供者 (data_provider.py)

**Files:**
- Create: `egs_aide/看盘神器/v2/data_provider.py`
- Create: `egs_aide/看盘神器/v2/tests/test_data_provider.py`

- [ ] **Step 1: 编写数据转换测试**

`egs_aide/看盘神器/v2/tests/test_data_provider.py`:
```python
import pandas as pd
from data_provider import DataProvider


def test_clean_stock_code_removes_postfix():
    """测试去除代码后缀 (.SZ / .SH)"""
    dp = DataProvider()
    assert dp.clean_code("000001.SZ") == "000001"
    assert dp.clean_code("600000.SH") == "600000"
    assert dp.clean_code("300001") == "300001"


def test_filter_columns():
    """测试按指定列过滤 DataFrame"""
    dp = DataProvider()
    df = pd.DataFrame({
        "代码": ["000001"], "名称": ["平安银行"],
        "最新": [10.5], "涨幅": [2.3], "多余列": [0],
    })
    result = dp.filter_columns(df, ["代码", "名称", "最新", "涨幅"])
    assert list(result.columns) == ["代码", "名称", "最新", "涨幅"]
    assert "多余列" not in result.columns


def test_rename_columns():
    """测试列名重命名映射"""
    dp = DataProvider()
    df = pd.DataFrame({"最新": [10.5], "涨幅": [2.3]})
    result = dp.rename_columns(df, {"最新": "最新价", "涨幅": "涨跌幅"})
    assert "最新价" in result.columns
    assert "涨跌幅" in result.columns
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd egs_aide/看盘神器/v2 && python -m pytest tests/test_data_provider.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'data_provider'`

- [ ] **Step 3: 实现 DataProvider**

`egs_aide/看盘神器/v2/data_provider.py`:
```python
# -*- coding: utf-8 -*-
"""数据提供者：封装 qstock 数据获取，统一异常处理"""
import logging
import traceback
from typing import List, Dict, Optional

import pandas as pd
import qstock as qs


class DataProvider:
    """qstock 数据获取封装"""

    def __init__(self):
        self._logger = logging.getLogger(self.__class__.__name__)

    # ===== 纯逻辑方法（可测试） =====

    @staticmethod
    def clean_code(code: str) -> str:
        """去除代码后缀，如 000001.SZ -> 000001"""
        return code.split(".")[0]

    @staticmethod
    def filter_columns(df: pd.DataFrame, columns: List[str]) -> pd.DataFrame:
        """按指定列过滤 DataFrame，仅保留存在的列"""
        existing = [c for c in columns if c in df.columns]
        return df[existing].copy()

    @staticmethod
    def rename_columns(df: pd.DataFrame, mapping: Dict[str, str]) -> pd.DataFrame:
        """重命名列"""
        return df.rename(columns=mapping)

    # ===== 数据获取方法（调用 qstock） =====

    def get_index_realtime(self, code_list: List[str]) -> pd.DataFrame:
        """获取指数实时行情"""
        try:
            df = qs.realtime_data(code=code_list)
            return df if df is not None and not df.empty else pd.DataFrame()
        except Exception as e:
            self._logger.error(f"获取指数行情失败: {e}")
            traceback.print_exc()
            return pd.DataFrame()

    def get_stock_realtime(self, code_list: List[str]) -> pd.DataFrame:
        """获取个股实时行情"""
        try:
            clean_codes = [self.clean_code(c) for c in code_list]
            df = qs.realtime_data(code=clean_codes)
            return df if df is not None and not df.empty else pd.DataFrame()
        except Exception as e:
            self._logger.error(f"获取个股行情失败: {e}")
            traceback.print_exc()
            return pd.DataFrame()

    def get_industry_boards(self) -> pd.DataFrame:
        """获取行业板块行情"""
        try:
            df = qs.realtime_data("行业板块")
            return df if df is not None and not df.empty else pd.DataFrame()
        except Exception as e:
            self._logger.error(f"获取行业板块失败: {e}")
            traceback.print_exc()
            return pd.DataFrame()

    def get_concept_boards(self) -> pd.DataFrame:
        """获取概念板块行情"""
        try:
            df = qs.realtime_data("概念板块")
            return df if df is not None and not df.empty else pd.DataFrame()
        except Exception as e:
            self._logger.error(f"获取概念板块失败: {e}")
            traceback.print_exc()
            return pd.DataFrame()

    def get_limit_up_pool(self) -> pd.DataFrame:
        """获取涨停板"""
        try:
            df = qs.stock_zt_pool()
            return df if df is not None and not df.empty else pd.DataFrame()
        except Exception as e:
            self._logger.error(f"获取涨停板失败: {e}")
            traceback.print_exc()
            return pd.DataFrame()

    def get_billboard(self) -> pd.DataFrame:
        """获取龙虎榜"""
        try:
            df = qs.stock_billboard()
            return df if df is not None and not df.empty else pd.DataFrame()
        except Exception as e:
            self._logger.error(f"获取龙虎榜失败: {e}")
            traceback.print_exc()
            return pd.DataFrame()

    def get_realtime_change(self) -> pd.DataFrame:
        """获取盘口异动"""
        try:
            df = qs.realtime_change()
            return df if df is not None and not df.empty else pd.DataFrame()
        except Exception as e:
            self._logger.error(f"获取盘口异动失败: {e}")
            traceback.print_exc()
            return pd.DataFrame()

    def get_news_cls(self) -> pd.DataFrame:
        """获取财联社电报"""
        try:
            df = qs.news_data()
            if df is not None and not df.empty:
                df["发布时间"] = df["发布时间"].apply(str)
                df["发布日期"] = df["发布日期"].apply(str)
            return df if df is not None and not df.empty else pd.DataFrame()
        except Exception as e:
            self._logger.error(f"获取财联社新闻失败: {e}")
            traceback.print_exc()
            return pd.DataFrame()

    def get_news_js(self) -> pd.DataFrame:
        """获取市场快讯（金十数据）"""
        try:
            df = qs.news_data("js")
            return df if df is not None and not df.empty else pd.DataFrame()
        except Exception as e:
            self._logger.error(f"获取市场快讯失败: {e}")
            traceback.print_exc()
            return pd.DataFrame()

    def get_stock_news(self, code: str) -> pd.DataFrame:
        """获取个股新闻"""
        try:
            df = qs.stock_news(code)
            return df if df is not None and not df.empty else pd.DataFrame()
        except Exception as e:
            self._logger.error(f"获取个股新闻失败: {e}")
            traceback.print_exc()
            return pd.DataFrame()
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd egs_aide/看盘神器/v2 && python -m pytest tests/test_data_provider.py -v`
Expected: PASS — 3 passed

- [ ] **Step 5: Commit**

```bash
git add egs_aide/看盘神器/v2/data_provider.py egs_aide/看盘神器/v2/tests/test_data_provider.py
git commit -m "feat(v2): add DataProvider with qstock wrapper and error handling"
```

---

## Task 4: Excel 管理器 (excel_manager.py)

**Files:**
- Create: `egs_aide/看盘神器/v2/excel_manager.py`

- [ ] **Step 1: 实现 ExcelManager**

`egs_aide/看盘神器/v2/excel_manager.py`:
```python
# -*- coding: utf-8 -*-
"""Excel 管理器：封装 xlwings 工作簿操作"""
import os
import logging
from typing import Optional, Tuple

import xlwings as xw
import pandas as pd


class ExcelManager:
    """管理 Excel 工作簿的打开、读写"""

    def __init__(self, xlsx_path: str):
        self._logger = logging.getLogger(self.__class__.__name__)
        self._xlsx_path = xlsx_path

        if not os.path.exists(xlsx_path):
            raise FileNotFoundError(f"Excel 文件不存在: {xlsx_path}")

        self.wb = xw.Book(xlsx_path)
        self._logger.info(f"已打开 Excel: {xlsx_path}")

    def get_sheet_by_name(self, name: str) -> Optional[xw.Sheet]:
        """按名称获取 Sheet"""
        try:
            return self.wb.sheets[name]
        except Exception:
            self._logger.warning(f"Sheet 不存在: {name}")
            return None

    def sheet_to_df(self, sheet: xw.Sheet) -> Tuple[pd.DataFrame, int, int]:
        """将 Sheet 转为 DataFrame，返回 (df, row_num, col_num)"""
        row_num = sheet.api.UsedRange.Rows.count
        col_num = sheet.api.UsedRange.Columns.count

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
        """将 DataFrame 写入 Sheet"""
        if df is None or df.empty:
            self._logger.debug(f"写入空数据，跳过: {sheet.name}")
            return

        n_rows = df.shape[0]
        n_cols = df.shape[1]
        # 写入列名 + 数据（共 n_rows+1 行）
        sheet.range(
            (start_row, start_col),
            (start_row + n_rows, start_col + n_cols - 1)
        ).value = df

    def clear_range(self, sheet: xw.Sheet, start_row: int = 1,
                    start_col: int = 1, end_row: int = 200, end_col: int = 50):
        """清除指定区域内容"""
        sheet.range((start_row, start_col), (end_row, end_col)).clear_contents()

    def close(self):
        """关闭工作簿"""
        try:
            self.wb.close()
        except Exception as e:
            self._logger.error(f"关闭 Excel 失败: {e}")
```

- [ ] **Step 2: 验证语法**

Run: `cd egs_aide/看盘神器/v2 && python -c "import excel_manager; print('OK')"`
Expected: 输出 `OK`（xlwings 在无 Excel 环境下 import 不报错即可）

- [ ] **Step 3: Commit**

```bash
git add egs_aide/看盘神器/v2/excel_manager.py
git commit -m "feat(v2): add ExcelManager wrapping xlwings operations"
```

---

## Task 5: Sheet 基类 (sheets/base.py)

**Files:**
- Create: `egs_aide/看盘神器/v2/sheets/base.py`

- [ ] **Step 1: 实现 BaseSheet 抽象基类**

`egs_aide/看盘神器/v2/sheets/base.py`:
```python
# -*- coding: utf-8 -*-
"""Sheet Handler 抽象基类"""
from abc import ABC, abstractmethod

import pandas as pd
import xlwings as xw

from data_provider import DataProvider
from excel_manager import ExcelManager


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
        """写入数据到 Sheet"""
        if self.sheet is None:
            return
        # 先清除旧数据
        self.excel_mgr.clear_range(self.sheet, start_row=start_row,
                                   start_col=start_col)
        self.excel_mgr.write_df(self.sheet, df, start_row, start_col)
```

- [ ] **Step 2: 验证语法**

Run: `cd egs_aide/看盘神器/v2 && python -c "from sheets.base import BaseSheet; print('OK')"`
Expected: 输出 `OK`

- [ ] **Step 3: Commit**

```bash
git add egs_aide/看盘神器/v2/sheets/base.py
git commit -m "feat(v2): add BaseSheet abstract class for sheet handlers"
```

---

## Task 6: 大盘 Sheet (sheets/market_overview.py)

**Files:**
- Create: `egs_aide/看盘神器/v2/sheets/market_overview.py`
- Create: `egs_aide/看盘神器/v2/tests/test_sheets.py`

- [ ] **Step 1: 编写 Sheet Handler 测试（mock 数据）**

`egs_aide/看盘神器/v2/tests/test_sheets.py`:
```python
import pandas as pd
from unittest.mock import MagicMock, patch
from sheets.market_overview import MarketOverviewSheet


def test_market_overview_refresh_with_mock():
    """测试大盘 Sheet 刷新逻辑（mock 数据源）"""
    mock_excel = MagicMock()
    mock_data = MagicMock()

    # mock 返回数据
    mock_data.get_index_realtime.return_value = pd.DataFrame({
        "名称": ["上证指数", "深证成指"],
        "最新": [3200.0, 10500.0],
        "涨幅": [0.5, -0.3],
    })
    mock_data.get_industry_boards.return_value = pd.DataFrame({
        "名称": ["银行", "证券"], "涨幅": [1.2, -0.5],
    })
    mock_data.get_concept_boards.return_value = pd.DataFrame()
    mock_data.get_limit_up_pool.return_value = pd.DataFrame()

    sheet = MarketOverviewSheet("大盘", mock_excel, mock_data)
    sheet.sheet = MagicMock()

    # 不应抛异常
    sheet.refresh()

    # 验证数据源被调用
    mock_data.get_index_realtime.assert_called_once()
    mock_data.get_industry_boards.assert_called_once()
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd egs_aide/看盘神器/v2 && python -m pytest tests/test_sheets.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'sheets.market_overview'`

- [ ] **Step 3: 实现 MarketOverviewSheet**

`egs_aide/看盘神器/v2/sheets/market_overview.py`:
```python
# -*- coding: utf-8 -*-
"""大盘 Sheet：指数行情 + 行业板块 + 概念板块 + 涨停板"""
import logging

from sheets.base import BaseSheet
from config import AppConfig


class MarketOverviewSheet(BaseSheet):
    """大盘总览 Sheet Handler"""

    def __init__(self, name, excel_mgr, data_provider, config=None):
        super().__init__(name, excel_mgr, data_provider)
        self.config = config or AppConfig()
        self._logger = logging.getLogger(self.__class__.__name__)

    def init(self):
        """大盘 Sheet 无需静态初始化"""
        self._logger.info("大盘 Sheet 初始化完成")

    def refresh(self):
        """刷新大盘数据"""
        self._logger.info("刷新大盘数据...")

        # 1. 主要指数行情（从第1行开始）
        df_index = self.data.get_index_realtime(self.config.market_indices)
        if not df_index.empty:
            self._write(df_index, start_row=1, start_col=1)

        # 2. 行业板块涨幅榜（空2行后写入）
        row_offset = len(df_index) + 3 if not df_index.empty else 1
        df_industry = self.data.get_industry_boards()
        if not df_industry.empty:
            self._write(df_industry, start_row=row_offset, start_col=1)
            row_offset += len(df_industry) + 2

        # 3. 概念板块涨幅榜
        df_concept = self.data.get_concept_boards()
        if not df_concept.empty:
            self._write(df_concept, start_row=row_offset, start_col=1)
            row_offset += len(df_concept) + 2

        # 4. 涨停板
        df_zt = self.data.get_limit_up_pool()
        if not df_zt.empty:
            self._write(df_zt, start_row=row_offset, start_col=1)
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd egs_aide/看盘神器/v2 && python -m pytest tests/test_sheets.py -v`
Expected: PASS — 1 passed

- [ ] **Step 5: Commit**

```bash
git add egs_aide/看盘神器/v2/sheets/market_overview.py egs_aide/看盘神器/v2/tests/test_sheets.py
git commit -m "feat(v2): add MarketOverviewSheet with indices, boards, limit-up"
```

---

## Task 7: 详细行情 Sheet (sheets/detailed_quotes.py)

**Files:**
- Create: `egs_aide/看盘神器/v2/sheets/detailed_quotes.py`
- Modify: `egs_aide/看盘神器/v2/tests/test_sheets.py`

- [ ] **Step 1: 添加详细行情测试**

在 `tests/test_sheets.py` 末尾追加:
```python
from sheets.detailed_quotes import DetailedQuotesSheet


def test_detailed_quotes_refresh_with_mock():
    """测试详细行情 Sheet 刷新逻辑"""
    mock_excel = MagicMock()
    mock_data = MagicMock()

    # mock Sheet 已有自选股数据
    mock_excel.sheet_to_df.return_value = (
        pd.DataFrame({
            "代码": ["000001", "600000"],
            "名称": ["平安银行", "浦发银行"],
        }),
        3, 2,
    )
    mock_data.get_stock_realtime.return_value = pd.DataFrame({
        "代码": ["000001", "600000"],
        "名称": ["平安银行", "浦发银行"],
        "最新": [10.5, 8.3],
        "涨幅": [2.1, -0.5],
        "时间": ["10:30:00", "10:30:00"],
    })
    mock_data.get_billboard.return_value = pd.DataFrame()
    mock_data.get_realtime_change.return_value = pd.DataFrame()

    sheet = DetailedQuotesSheet("详细行情", mock_excel, mock_data)
    sheet.sheet = MagicMock()

    sheet.refresh()

    mock_data.get_stock_realtime.assert_called_once()
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd egs_aide/看盘神器/v2 && python -m pytest tests/test_sheets.py::test_detailed_quotes_refresh_with_mock -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: 实现 DetailedQuotesSheet**

`egs_aide/看盘神器/v2/sheets/detailed_quotes.py`:
```python
# -*- coding: utf-8 -*-
"""详细行情 Sheet：自选股实时行情 + 龙虎榜 + 盘口异动"""
import logging

import pandas as pd

from sheets.base import BaseSheet
from config import AppConfig


class DetailedQuotesSheet(BaseSheet):
    """详细行情 Sheet Handler"""

    def __init__(self, name, excel_mgr, data_provider, config=None):
        super().__init__(name, excel_mgr, data_provider)
        self.config = config or AppConfig()
        self._logger = logging.getLogger(self.__class__.__name__)
        self._stock_codes: list = []

    def init(self):
        """从 Excel Sheet 读取自选股代码"""
        df, _, _ = self.excel_mgr.sheet_to_df(self.sheet)
        if not df.empty and "代码" in df.columns:
            self._stock_codes = df["代码"].dropna().tolist()
            self._logger.info(f"自选股加载完成: {self._stock_codes}")
        else:
            # 如果 Excel 中没有自选股，使用配置默认值
            self._stock_codes = self.config.watch_stocks
            self._logger.info(f"使用默认自选股: {self._stock_codes}")

    def refresh(self):
        """刷新详细行情"""
        self._logger.info("刷新详细行情...")

        # 1. 自选股实时行情
        if self._stock_codes:
            df_rt = self.data.get_stock_realtime(self._stock_codes)
            if not df_rt.empty:
                self._write(df_rt, start_row=1, start_col=1)
                row_offset = len(df_rt) + 3
            else:
                row_offset = 1
        else:
            row_offset = 1

        # 2. 龙虎榜
        df_billboard = self.data.get_billboard()
        if not df_billboard.empty:
            self._write(df_billboard, start_row=row_offset, start_col=1)
            row_offset += len(df_billboard) + 2

        # 3. 盘口异动
        df_change = self.data.get_realtime_change()
        if not df_change.empty:
            self._write(df_change, start_row=row_offset, start_col=1)
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd egs_aide/看盘神器/v2 && python -m pytest tests/test_sheets.py -v`
Expected: PASS — 2 passed

- [ ] **Step 5: Commit**

```bash
git add egs_aide/看盘神器/v2/sheets/detailed_quotes.py egs_aide/看盘神器/v2/tests/test_sheets.py
git commit -m "feat(v2): add DetailedQuotesSheet with watchlist, billboard, changes"
```

---

## Task 8: 新闻 Sheet (sheets/news_sheet.py)

**Files:**
- Create: `egs_aide/看盘神器/v2/sheets/news_sheet.py`
- Modify: `egs_aide/看盘神器/v2/tests/test_sheets.py`

- [ ] **Step 1: 添加新闻 Sheet 测试**

在 `tests/test_sheets.py` 末尾追加:
```python
from sheets.news_sheet import NewsSheet


def test_news_sheet_refresh_with_mock():
    """测试新闻 Sheet 刷新逻辑"""
    mock_excel = MagicMock()
    mock_data = MagicMock()

    mock_data.get_news_cls.return_value = pd.DataFrame({
        "发布时间": ["10:30", "10:25"],
        "标题": ["央行降息", "GDP增长5%"],
    })
    mock_data.get_news_js.return_value = pd.DataFrame({
        "时间": ["10:28"],
        "内容": ["美国CPI数据公布"],
    })

    sheet = NewsSheet("新闻", mock_excel, mock_data)
    sheet.sheet = MagicMock()

    sheet.refresh()

    mock_data.get_news_cls.assert_called_once()
    mock_data.get_news_js.assert_called_once()
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd egs_aide/看盘神器/v2 && python -m pytest tests/test_sheets.py::test_news_sheet_refresh_with_mock -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: 实现 NewsSheet**

`egs_aide/看盘神器/v2/sheets/news_sheet.py`:
```python
# -*- coding: utf-8 -*-
"""新闻 Sheet：财联社电报 + 市场快讯"""
import logging

from sheets.base import BaseSheet
from config import AppConfig


class NewsSheet(BaseSheet):
    """新闻 Sheet Handler"""

    def __init__(self, name, excel_mgr, data_provider, config=None):
        super().__init__(name, excel_mgr, data_provider)
        self.config = config or AppConfig()
        self._logger = logging.getLogger(self.__class__.__name__)

    def init(self):
        """新闻 Sheet 无需静态初始化"""
        self._logger.info("新闻 Sheet 初始化完成")

    def refresh(self):
        """刷新新闻数据"""
        self._logger.info("刷新新闻数据...")

        # 1. 财联社电报（从第1行开始）
        df_cls = self.data.get_news_cls()
        if not df_cls.empty:
            # 限制显示条数
            df_cls = df_cls.head(self.config.news_max_rows)
            self._write(df_cls, start_row=1, start_col=1)
            row_offset = len(df_cls) + 3
        else:
            row_offset = 1

        # 2. 市场快讯（金十数据）
        df_js = self.data.get_news_js()
        if not df_js.empty:
            df_js = df_js.head(self.config.news_max_rows)
            self._write(df_js, start_row=row_offset, start_col=1)
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd egs_aide/看盘神器/v2 && python -m pytest tests/test_sheets.py -v`
Expected: PASS — 3 passed

- [ ] **Step 5: Commit**

```bash
git add egs_aide/看盘神器/v2/sheets/news_sheet.py egs_aide/看盘神器/v2/tests/test_sheets.py
git commit -m "feat(v2): add NewsSheet with CLS telegrams and JS market express"
```

---

## Task 9: 个性定制看盘 Sheet (sheets/custom_watch.py)

**Files:**
- Create: `egs_aide/看盘神器/v2/sheets/custom_watch.py`
- Modify: `egs_aide/看盘神器/v2/tests/test_sheets.py`

- [ ] **Step 1: 添加个性定制看盘测试**

在 `tests/test_sheets.py` 末尾追加:
```python
from sheets.custom_watch import CustomWatchSheet


def test_custom_watch_refresh_with_mock():
    """测试个性定制看盘 Sheet 刷新逻辑"""
    mock_excel = MagicMock()
    mock_data = MagicMock()

    # mock Sheet 中已有自选股
    mock_excel.sheet_to_df.return_value = (
        pd.DataFrame({
            "代码": ["中国平安", "贵州茅台"],
            "名称": ["中国平安", "贵州茅台"],
        }),
        3, 2,
    )
    mock_data.get_stock_realtime.return_value = pd.DataFrame({
        "代码": ["中国平安", "贵州茅台"],
        "名称": ["中国平安", "贵州茅台"],
        "最新": [45.0, 1800.0],
        "涨幅": [1.5, 0.8],
        "时间": ["10:30:00", "10:30:00"],
    })

    config = AppConfig()
    sheet = CustomWatchSheet("个性定制看盘", mock_excel, mock_data, config)
    sheet.sheet = MagicMock()

    sheet.init()
    sheet.refresh()

    mock_data.get_stock_realtime.assert_called_once()
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd egs_aide/看盘神器/v2 && python -m pytest tests/test_sheets.py::test_custom_watch_refresh_with_mock -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: 实现 CustomWatchSheet**

`egs_aide/看盘神器/v2/sheets/custom_watch.py`:
```python
# -*- coding: utf-8 -*-
"""个性定制看盘 Sheet：用户自选股 + 自定义显示列"""
import logging

import pandas as pd

from sheets.base import BaseSheet
from config import AppConfig


class CustomWatchSheet(BaseSheet):
    """个性定制看盘 Sheet Handler

    用户在 Excel 的"个性定制看盘" Sheet 中填写自选股代码，
    程序读取后获取实时行情并按 config.custom_watch_columns 过滤显示。
    """

    def __init__(self, name, excel_mgr, data_provider, config=None):
        super().__init__(name, excel_mgr, data_provider)
        self.config = config or AppConfig()
        self._logger = logging.getLogger(self.__class__.__name__)
        self._stock_codes: list = []

    def init(self):
        """从 Excel 读取用户自定义的自选股"""
        df, _, _ = self.excel_mgr.sheet_to_df(self.sheet)
        if not df.empty and "代码" in df.columns:
            self._stock_codes = df["代码"].dropna().tolist()
            self._logger.info(f"定制自选股加载: {self._stock_codes}")
        else:
            self._stock_codes = self.config.watch_stocks
            self._logger.info(f"使用默认自选股: {self._stock_codes}")

    def refresh(self):
        """刷新定制看盘数据"""
        self._logger.info("刷新个性定制看盘...")

        if not self._stock_codes:
            self._logger.warning("无自选股，跳过刷新")
            return

        # 获取实时行情
        df_rt = self.data.get_stock_realtime(self._stock_codes)
        if df_rt.empty:
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

        self._write(df_display, start_row=1, start_col=1)
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd egs_aide/看盘神器/v2 && python -m pytest tests/test_sheets.py -v`
Expected: PASS — 4 passed

- [ ] **Step 5: Commit**

```bash
git add egs_aide/看盘神器/v2/sheets/custom_watch.py egs_aide/看盘神器/v2/tests/test_sheets.py
git commit -m "feat(v2): add CustomWatchSheet with configurable columns"
```

---

## Task 10: Excel 模板生成器 (create_template.py)

**Files:**
- Create: `egs_aide/看盘神器/v2/create_template.py`

- [ ] **Step 1: 实现模板生成脚本**

`egs_aide/看盘神器/v2/create_template.py`:
```python
# -*- coding: utf-8 -*-
"""生成 Excel 看盘模板（使用 openpyxl）

运行: python create_template.py
生成: 看盘模板.xlsx（含4个 Sheet：大盘、详细行情、新闻、个性定制看盘）
"""
import os
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

from config import AppConfig


def _style_header(cell):
    """设置表头样式"""
    cell.font = Font(bold=True, size=11, color="FFFFFF")
    cell.fill = PatternFill(start_color="4472C4", end_color="4472C4",
                            fill_type="solid")
    cell.alignment = Alignment(horizontal="center", vertical="center")
    thin = Side(border_style="thin", color="CCCCCC")
    cell.border = Border(left=thin, right=thin, top=thin, bottom=thin)


def create_template(output_path: str = None):
    """生成 Excel 模板"""
    cfg = AppConfig()
    path = output_path or os.path.join(os.getcwd(), cfg.excel_template)

    wb = Workbook()

    # === Sheet 1: 大盘 ===
    ws1 = wb.active
    ws1.title = cfg.sheets["market_overview"]
    ws1["A1"] = "=== 大盘总览（自动刷新）==="
    ws1["A1"].font = Font(bold=True, size=14)

    # === Sheet 2: 详细行情 ===
    ws2 = wb.create_sheet(cfg.sheets["detailed_quotes"])
    ws2["A1"] = "代码"
    ws2["B1"] = "名称"
    _style_header(ws2["A1"])
    _style_header(ws2["B1"])
    # 示例自选股
    ws2["A2"] = "中国平安"
    ws2["B2"] = "中国平安"
    ws2["A3"] = "贵州茅台"
    ws2["B3"] = "贵州茅台"

    # === Sheet 3: 新闻 ===
    ws3 = wb.create_sheet(cfg.sheets["news"])
    ws3["A1"] = "=== 财经新闻（自动刷新）==="
    ws3["A1"].font = Font(bold=True, size=14)

    # === Sheet 4: 个性定制看盘 ===
    ws4 = wb.create_sheet(cfg.sheets["custom_watch"])
    # 写入表头
    headers = cfg.custom_watch_columns
    for col_idx, header in enumerate(headers, 1):
        cell = ws4.cell(row=1, column=col_idx, value=header)
        _style_header(cell)
    # 示例自选股
    ws4["A2"] = "中国平安"
    ws4["B2"] = "中国平安"
    ws4["A3"] = "贵州茅台"
    ws4["B3"] = "贵州茅台"

    # 设置列宽
    for ws in [ws1, ws2, ws3, ws4]:
        for col in ws.columns:
            ws.column_dimensions[col[0].column_letter].width = 15

    wb.save(path)
    print(f"模板已生成: {path}")
    return path


if __name__ == "__main__":
    create_template()
```

- [ ] **Step 2: 运行生成模板**

Run: `cd egs_aide/看盘神器/v2 && python create_template.py`
Expected: 输出 `模板已生成: .../看盘模板.xlsx`

- [ ] **Step 3: 验证模板文件存在**

Run: `ls -la egs_aide/看盘神器/v2/看盘模板.xlsx`
Expected: 文件存在

- [ ] **Step 4: Commit**

```bash
git add egs_aide/看盘神器/v2/create_template.py egs_aide/看盘神器/v2/看盘模板.xlsx
git commit -m "feat(v2): add Excel template generator with 4 formatted sheets"
```

---

## Task 11: 主入口 (main.py)

**Files:**
- Create: `egs_aide/看盘神器/v2/main.py`

- [ ] **Step 1: 实现 main.py**

`egs_aide/看盘神器/v2/main.py`:
```python
# -*- coding: utf-8 -*-
"""Excel 盯盘工具 V2 主入口

使用方法:
    1. python create_template.py   # 生成 Excel 模板（首次运行）
    2. python main.py               # 启动盯盘

在 Excel 模板的"详细行情"和"个性定制看盘" Sheet 中填入自选股代码即可。
"""
import os
import sys
import time
import logging

from config import AppConfig
from data_provider import DataProvider
from excel_manager import ExcelManager
from sheets.market_overview import MarketOverviewSheet
from sheets.detailed_quotes import DetailedQuotesSheet
from sheets.news_sheet import NewsSheet
from sheets.custom_watch import CustomWatchSheet


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def main():
    setup_logging()
    logger = logging.getLogger("main")
    cfg = AppConfig()

    # 1. 检查模板是否存在，不存在则生成
    template_path = os.path.join(os.getcwd(), cfg.excel_template)
    if not os.path.exists(template_path):
        logger.info("模板不存在，自动生成...")
        from create_template import create_template
        create_template(template_path)

    # 2. 初始化组件
    excel_mgr = ExcelManager(template_path)
    data_provider = DataProvider()

    # 3. 创建 Sheet Handlers
    handlers = [
        MarketOverviewSheet(cfg.sheets["market_overview"],
                            excel_mgr, data_provider, cfg),
        DetailedQuotesSheet(cfg.sheets["detailed_quotes"],
                            excel_mgr, data_provider, cfg),
        NewsSheet(cfg.sheets["news"],
                  excel_mgr, data_provider, cfg),
        CustomWatchSheet(cfg.sheets["custom_watch"],
                         excel_mgr, data_provider, cfg),
    ]

    # 4. 初始化每个 Sheet
    for handler in handlers:
        try:
            handler.setup()
            handler.init()
        except Exception as e:
            logger.error(f"Sheet '{handler.name}' 初始化失败: {e}")

    # 5. 刷新循环
    logger.info(f"开始实时刷新，间隔 {cfg.refresh_interval} 秒...")
    try:
        while True:
            for handler in handlers:
                try:
                    handler.refresh()
                except Exception as e:
                    logger.error(f"Sheet '{handler.name}' 刷新失败: {e}")
            time.sleep(cfg.refresh_interval)
    except KeyboardInterrupt:
        logger.info("用户中断，退出...")
    finally:
        excel_mgr.close()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 验证语法**

Run: `cd egs_aide/看盘神器/v2 && python -c "import main; print('OK')"`
Expected: 输出 `OK`

- [ ] **Step 3: Commit**

```bash
git add egs_aide/看盘神器/v2/main.py
git commit -m "feat(v2): add main entry point with refresh loop"
```

---

## Task 12: 全量测试与集成验证

- [ ] **Step 1: 运行全部测试**

Run: `cd egs_aide/看盘神器/v2 && python -m pytest tests/ -v`
Expected: 所有测试通过（4+ tests）

- [ ] **Step 2: 验证模板生成**

Run: `cd egs_aide/看盘神器/v2 && python create_template.py`
Expected: 生成 `看盘模板.xlsx`，含4个 Sheet

- [ ] **Step 3: 验证 import 链完整**

Run: `cd egs_aide/看盘神器/v2 && python -c "from main import main; print('import OK')"`
Expected: 输出 `import OK`

- [ ] **Step 4: 更新 egs_aide/README.md**

在 `egs_aide/README.md` 表格中添加 v2 行:
```markdown
| 2 | 模块化盯盘工具V2 | egs_aide/看盘神器/v2 |
```

- [ ] **Step 5: Commit**

```bash
git add egs_aide/README.md
git commit -m "docs(v2): update README with v2 entry"
```

---

## 架构说明

### 数据流

```
用户编辑 Excel 模板（填入自选股）
        ↓
main.py 启动
    ├── ExcelManager 打开 .xlsx
    ├── DataProvider 初始化（qstock）
    ├── 创建 4 个 Sheet Handler
    │       ├── MarketOverviewSheet  → 大盘
    │       ├── DetailedQuotesSheet  → 详细行情
    │       ├── NewsSheet            → 新闻
    │       └── CustomWatchSheet     → 个性定制看盘
    ├── init(): 各 Handler 加载静态数据（自选股列表）
    └── while True:
            ├── handler.refresh()  → 获取实时数据 → 写入 Excel
            └── sleep(refresh_interval)
```

### V1 → V2 改进

| 方面 | V1 | V2 |
|------|----|----|
| 架构 | 单文件单类 | 模块化，策略模式 |
| 配置 | 硬编码 | `config.py` 集中管理 |
| Sheet 匹配 | 字符串 `in sheet.name` | 名称映射字典 |
| pandas | `df.append()`（已废弃） | `pd.concat()` / 直接赋值 |
| 异常处理 | 各处 try-except | DataProvider 统一封装 |
| 扩展性 | 改代码 | 新增 Handler 类即可 |
| 测试 | 无 | pytest + mock |

### 各 Sheet 内容

| Sheet | 内容 | 数据源 |
|-------|------|--------|
| 大盘 | 主要指数 + 行业板块 + 概念板块 + 涨停板 | `qs.realtime_data()`, `qs.stock_zt_pool()` |
| 详细行情 | 自选股实时行情 + 龙虎榜 + 盘口异动 | `qs.realtime_data()`, `qs.stock_billboard()`, `qs.realtime_change()` |
| 新闻 | 财联社电报 + 市场快讯 | `qs.news_data()`, `qs.news_data('js')` |
| 个性定制看盘 | 用户自选股 + 自定义显示列 | `qs.realtime_data()` + 列过滤 |

### 用户使用流程

1. `pip install -r requirements.txt`
2. `python create_template.py` — 生成 Excel 模板
3. 打开 `看盘模板.xlsx`，在"详细行情"和"个性定制看盘" Sheet 中填入自选股代码
4. `python main.py` — 启动实时刷新
5. 修改 `config.py` 可自定义：刷新间隔、指数列表、自选股、显示列
