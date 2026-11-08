"""Lossless import, stale previews and atomic failure behavior."""

from io import BytesIO
from pathlib import Path

import openpyxl
import pytest

from src.engine.market.resource_pool import ResourcePoolService
from src.engine.market.resource_transfer import ResourceImportService


def test_import_preserves_codes_and_preview_does_not_create_pool(client):
    service = ResourcePoolService()
    transfer = ResourceImportService(service.repo)
    content = b"symbol,weight\n000001,0\n000002,1\n"
    report = transfer.preview(None, "codes.csv", content)
    assert report["valid"]
    assert [row["symbol"] for row in report["rows"]] == ["000001", "000002"]
    assert not service.list_pools()
    result = transfer.commit(None, "codes.csv", content, preview_hash=report["preview_hash"])
    rows = {row["symbol"]: row for row in service.list_items(result["pool_id"])}
    assert rows["000001"]["weight"] == 0


@pytest.mark.parametrize("weight", ["garbage", "NaN", "Infinity", "-0.5"])
def test_bad_weights_block_whole_batch(client, weight):
    service = ResourcePoolService()
    transfer = ResourceImportService(service.repo)
    content = f"symbol,weight\n600519,1\n000001,{weight}\n".encode()
    report = transfer.preview(None, "bad.csv", content)
    assert report["errors"][0]["row"] == 3
    with pytest.raises(ValueError, match="校验未通过"):
        transfer.commit(None, "bad.csv", content)
    assert not service.list_pools()


def test_stale_preview_and_duplicate_records_are_rejected(client):
    service = ResourcePoolService()
    pool = service.create_pool("stable")
    transfer = ResourceImportService(service.repo)
    content = b"symbol\n600519\n"
    report = transfer.preview(pool["id"], "pool.csv", content)
    service.repo.update("resource_pools", pool["id"], {"description": "changed"})
    with pytest.raises(ValueError, match="重新校验"):
        transfer.commit(pool["id"], "pool.csv", content, preview_hash=report["preview_hash"])
    assert not service.list_items(pool["id"])
    assert not transfer.preview(pool["id"], "dup.csv", b"symbol\n600519\n600519\n")["valid"]


def test_transaction_rolls_back_mid_batch_failure(client, monkeypatch):
    service = ResourcePoolService()
    transfer = ResourceImportService(service.repo)
    original = transfer._write

    def fail_second(pool_id, row):
        if row["symbol"] == "000001":
            raise RuntimeError("injected storage failure")
        original(pool_id, row)

    monkeypatch.setattr(transfer, "_write", fail_second)
    with pytest.raises(RuntimeError, match="storage failure"):
        transfer.commit(None, "pool.csv", b"symbol\n600519\n000001\n")
    assert not service.list_pools()
    assert service.repo.db.scalar("SELECT COUNT(*) FROM resource_pool_items") == 0


def test_excel_formulas_and_unknown_headers_are_rejected(client):
    transfer = ResourceImportService(ResourcePoolService().repo)
    with pytest.raises(ValueError, match="缺少证券代码"):
        transfer.preview(None, "wrong.csv", b"whatever\n600519\n")
    # Test input is intentionally generated in memory; the shipped template is authored separately.
    workbook = openpyxl.Workbook()
    workbook.active.append(["symbol", "weight"])
    workbook.active.append(["000001", "=1+1"])
    stream = BytesIO()
    workbook.save(stream)
    with pytest.raises(ValueError, match="不允许公式"):
        transfer.preview(None, "formula.xlsx", stream.getvalue())


def test_shipped_excel_template_without_declared_dimensions_imports(client):
    path = Path(__file__).resolve().parents[2] / "egs/examples/resource_pool_templates/universe.xlsx"
    service = ResourcePoolService()
    transfer = ResourceImportService(service.repo)
    report = transfer.preview(None, path.name, path.read_bytes())
    assert report["valid"]
    assert report["rows"][0]["symbol"] == "000001"
    result = transfer.commit(None, path.name, path.read_bytes(), preview_hash=report["preview_hash"])
    assert result["added"] == 2
