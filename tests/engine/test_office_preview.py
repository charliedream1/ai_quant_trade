"""Actual LibreOffice conversions, read-only enforcement, deduplication and real timeout."""

import io
from threading import Event
from time import monotonic

import pytest
from pypdf import PdfReader

from src.documents.config import preview_config
from src.documents.conversion import executable
from src.documents.store import PreviewStore
from tests.engine.preview_fixture_builder import build


@pytest.fixture(scope="module")
def office_samples(tmp_path_factory):
    executable()
    return build(tmp_path_factory.mktemp("office-fixtures"))


def wait_for_pdf(client, identifier):
    started = monotonic()
    while monotonic() - started < 60:
        response = client.post(f"/api/v1/file-previews/{identifier}/conversion").json()
        assert response["code"] == 0, response
        value = response["data"]
        if value["status"] not in {"running", "queued"}:
            return value
        Event().wait(0.05)
    raise AssertionError("Office preview did not reach terminal state")


@pytest.mark.parametrize("format", ["docx", "xlsx", "pptx", "doc", "xls", "ppt", "odt", "ods", "odp"])
def test_actual_office_formats_convert_with_chinese_text_and_stay_readonly(client, office_samples, format):
    path = office_samples[format]
    content = path.read_bytes()
    uploaded = client.post("/api/v1/file-previews/uploads", files={"file": (path.name, content)}).json()
    assert uploaded["code"] == 0, uploaded
    row = uploaded["data"]
    assert not row["editable"] and row["kind"] == "office"
    value = wait_for_pdf(client, row["id"])
    assert value["status"] == "completed", value
    pdf = client.get(f"/api/v1/file-previews/{row['id']}/pdf")
    assert pdf.headers["content-type"] == "application/pdf"
    reader = PdfReader(io.BytesIO(pdf.content))
    assert reader.pages and "量化" in "".join(page.extract_text() for page in reader.pages)
    if format in {"doc", "docx", "odt", "ppt", "pptx", "odp"}:
        assert len(reader.pages) >= 2
    again = client.post(f"/api/v1/file-previews/{row['id']}/conversion").json()["data"]
    assert again["cached"] and again["cache_key"] == value["cache_key"]
    denied = client.put(
        f"/api/v1/file-previews/{row['id']}/markdown", json={"revision": row["revision"], "content": "forbidden"}
    ).json()
    assert denied["code"] == 1002
    assert client.get(f"/api/v1/file-previews/{row['id']}/raw").content == content


def test_duplicate_content_shares_one_conversion(client, office_samples):
    path = office_samples["docx"]
    records = [
        client.post("/api/v1/file-previews/uploads", files={"file": (path.name, path.read_bytes())}).json()["data"]
        for _ in range(2)
    ]
    first = client.post(f"/api/v1/file-previews/{records[0]['id']}/conversion").json()["data"]
    second = client.post(f"/api/v1/file-previews/{records[1]['id']}/conversion").json()["data"]
    assert first["cache_key"] == second["cache_key"]
    assert wait_for_pdf(client, records[0]["id"])["status"] == "completed"
    assert len(list((PreviewStore().root / "converted").iterdir())) == 1


def test_actual_timeout_is_failed_and_original_is_preserved(client, office_samples, monkeypatch):
    path = office_samples["docx"]
    row = client.post("/api/v1/file-previews/uploads", files={"file": (path.name, path.read_bytes())}).json()["data"]
    monkeypatch.setitem(preview_config()["limits"], "conversion_timeout_seconds", 0.001)
    result = wait_for_pdf(client, row["id"])
    assert result["status"] == "failed" and "超时" in result["error"]
    assert client.get(f"/api/v1/file-previews/{row['id']}/raw").content == path.read_bytes()
