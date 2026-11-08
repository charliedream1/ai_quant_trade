"""Stock-list spreadsheet formatting with explicit portable file encoding."""

import csv
from pathlib import Path

import pandas as pd
import yaml

from src.core.config import PROJECT_ROOT


def spreadsheet_policy():
    return yaml.safe_load((PROJECT_ROOT / "egs/config/platform/legacy_utilities.yaml").read_text(encoding="utf-8"))[
        "spreadsheet"
    ]


def get_self_select_stock_lst(file_path):
    return list(pd.read_excel(file_path)[spreadsheet_policy()["code_column"]])


def parse_files(in_file, out_file, row_num=None, col_num=None, sheet_name=None):
    cfg = spreadsheet_policy()
    row_num, col_num = row_num or cfg["rows_per_page"], col_num or cfg["columns_per_row"]
    if row_num < 1 or col_num < 1:
        raise ValueError("Page and column counts must be positive")
    frame = pd.read_excel(in_file, sheet_name=sheet_name or cfg["sheet_name"])
    records = frame[[cfg["code_column"], cfg["name_column"]]].dropna().values.tolist()
    page_size = row_num * col_num
    output = Path(out_file)
    output.parent.mkdir(parents=True, exist_ok=True)
    for page, start in enumerate(range(0, len(records), page_size)):
        items = records[start : start + page_size]
        with output.with_name(output.stem + f"_{page}.csv").open("w", newline="", encoding="utf-8-sig") as stream:
            writer = csv.writer(stream)
            for offset in range(0, len(items), col_num):
                writer.writerow([value for record in items[offset : offset + col_num] for value in record])
