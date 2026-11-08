"""Bounded, lossless file parsing and row diagnostics shared by every client."""

from __future__ import annotations

import csv
import hashlib
import math
import re
from functools import lru_cache
from io import BytesIO, StringIO
from pathlib import Path
from typing import Any
from zipfile import BadZipFile, ZipFile

import openpyxl
import yaml

from src.core.config import PROJECT_ROOT
from src.core.repository import Repository


@lru_cache(maxsize=1)
def import_config() -> dict[str, Any]:
    return yaml.safe_load((PROJECT_ROOT / "egs/config/data/resource_import.yaml").read_text(encoding="utf-8"))


def template_path(kind: str) -> Path:
    if kind not in import_config()["templates"]:
        raise ValueError("模板格式只支持 csv / xlsx")
    return PROJECT_ROOT / import_config()["templates"][kind]


def _matrix(filename: str, content: bytes) -> list[list[Any]]:
    cfg = import_config()
    if not content or len(content) > cfg["limits"]["file_bytes"]:
        raise ValueError("文件为空或超过资源池上传大小限制")
    suffix = Path(filename).suffix.lower()
    if suffix not in cfg["formats"]:
        raise ValueError("仅支持 CSV/XLSX；旧 XLS 请先转换为 XLSX")
    if suffix == ".csv":
        for encoding in cfg["encodings"]:
            try:
                text = content.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        else:
            raise ValueError("CSV 编码须为 UTF-8 或 GB18030")
        if "\x00" in text:
            raise ValueError("CSV 包含非法空字符")
        iterator = csv.reader(StringIO(text), strict=True)
        rows = []
        try:
            for row in iterator:
                rows.append(row)
                if len(rows) > cfg["limits"]["rows"] + 1:
                    raise ValueError("导入行数超过限制")
        except csv.Error as exc:
            raise ValueError("CSV结构损坏，请检查引号和分隔符") from exc
        return rows
    return _excel(content, cfg["limits"])


def _excel(content: bytes, limits: dict[str, int]) -> list[list[Any]]:
    try:
        with ZipFile(BytesIO(content)) as archive:
            if sum(item.file_size for item in archive.infolist()) > limits["expanded_bytes"]:
                raise ValueError("Excel 解压后体积超过限制")
            if any("vbaproject" in item.filename.lower() for item in archive.infolist()):
                raise ValueError("模板不允许宏")
        workbook = openpyxl.load_workbook(BytesIO(content), read_only=True, data_only=False, keep_links=False)
        try:
            sheet = workbook.worksheets[0]
            if (sheet.max_column or 0) > limits["columns"] or (sheet.max_row or 0) > limits["rows"] + 1:
                raise ValueError("Excel 行列数超过限制")
            rows = []
            for number, row in enumerate(sheet.iter_rows(), 1):
                if number > limits["rows"] + 1 or len(row) > limits["columns"]:
                    raise ValueError("Excel 行列数超过限制")
                if any(cell.data_type == "f" for cell in row):
                    raise ValueError("导入文件不允许公式，请粘贴为值")
                rows.append([cell.value for cell in row])
            return rows
        finally:
            workbook.close()
    except (BadZipFile, KeyError, OSError) as exc:
        raise ValueError("Excel 文件损坏或实际格式不是 XLSX") from exc


def _headers(row: list[Any]) -> tuple[dict[str, int], list[str]]:
    cfg = import_config()
    if len(row) > cfg["limits"]["columns"]:
        raise ValueError("导入列数超过限制")
    aliases = {alias.lower(): field for field, names in cfg["fields"].items() for alias in names}
    headers: dict[str, int] = {}
    unknown = []
    seen = set()
    for index, value in enumerate(row):
        text = str(value or "").strip().lower()
        if text in seen:
            raise ValueError(f"重复表头：{text}")
        seen.add(text)
        field = aliases.get(text)
        if not field:
            unknown.append(text)
        elif field in headers:
            raise ValueError(f"多个表头映射到同一字段：{field}")
        else:
            headers[field] = index
    if "symbol" not in headers:
        raise ValueError("缺少证券代码列 symbol/证券代码，不能猜测第一列")
    return headers, unknown


def _identity(row: dict[str, Any], repo: Repository, default_market: str) -> tuple[dict[str, Any], str]:
    market = str(row.get("market") or default_market).strip().upper()
    if market not in {"CN", "US"}:
        raise ValueError("市场仅支持 CN/US")
    symbol = str(row.get("symbol") or "").strip().upper()
    if market == "CN":
        symbol = re.sub(r"^(SH|SZ|BJ)", "", symbol)
        symbol = re.sub(r"\.(SH|SZ|BJ)$", "", symbol)
        if not re.fullmatch(r"\d{6}", symbol):
            raise ValueError("A股/ETF代码须为六位文本，请保留前导零")
    elif not re.fullmatch(r"[A-Z][A-Z0-9.-]{0,9}", symbol):
        raise ValueError("美股代码格式不合法")
    known = repo.db.query_one("SELECT * FROM security_master WHERE market = ? AND symbol = ?", (market, symbol))
    name = str(row.get("name") or "").strip()
    warning = ""
    if known:
        names = {known["name"], *re.split(r"[,，;；|]", str(known.get("aliases") or ""))}
        if name and name not in names:
            raise ValueError(f"代码与名称不一致，主数据名称：{known['name']}")
        name = known["name"]
    else:
        warning = "主数据未收录，仅通过格式校验"
    return {**row, "market": market, "symbol": symbol, "name": name or symbol}, warning


def parse_import(filename: str, content: bytes, repo: Repository, market: str) -> dict[str, Any]:
    """Preview is read-only; invalid records retain original row numbers and values."""
    matrix = _matrix(filename, content)
    if not matrix:
        raise ValueError("导入文件没有表头")
    headers, unknown = _headers(matrix[0])
    result: dict[str, Any] = {
        "file_name": Path(filename).name,
        "sha256": hashlib.sha256(content).hexdigest(),
        "schema_version": import_config()["version"],
        "rows": [],
        "errors": [],
        "warnings": [f"忽略未知列：{name}" for name in unknown],
    }
    seen: set[tuple[str, str]] = set()
    for number, values in enumerate(matrix[1:], 2):
        if not any(value is not None and str(value).strip() for value in values):
            continue
        row = {
            key: str(values[i] if i < len(values) and values[i] is not None else "").strip()
            for key, i in headers.items()
        }
        try:
            normalized = _validated_row(row, repo, market)
            identity = (normalized["market"], normalized["symbol"])
            if identity in seen:
                raise ValueError("文件内证券重复，请先合并或移除重复行")
            seen.add(identity)
            result["rows"].append({**normalized, "row": number})
        except ValueError as exc:
            result["errors"].append({"row": number, "field": "record", "value": str(values), "message": str(exc)})
    if not result["rows"] and not result["errors"]:
        result["errors"].append({"row": 2, "field": "symbol", "value": "", "message": "文件没有有效标的"})
    markets = {row["market"] for row in result["rows"]}
    if len(markets) > 1 or markets and markets != {market}:
        result["errors"].append(
            {"row": 0, "field": "market", "value": str(sorted(markets)), "message": "请切换到对应市场并分市场导入"}
        )
    result["valid"] = not result["errors"]
    return result


def _validated_row(row: dict[str, Any], repo: Repository, market: str) -> dict[str, Any]:
    cfg = import_config()["limits"]
    if any(len(str(value)) > cfg["text_length"] for value in row.values()):
        raise ValueError("字段文本超过长度限制")
    normalized, warning = _identity(row, repo, market)
    try:
        weight = float(row.get("weight") or 1.0)
    except (ValueError, TypeError) as exc:
        raise ValueError("权重必须为有限数，空值才使用默认值1") from exc
    if not math.isfinite(weight) or not 0 <= weight <= cfg["weight_max"]:
        raise ValueError("权重必须为非负有限数且不超过配置上限")
    return {**normalized, "weight": weight, "source": "import", "warning": warning}
