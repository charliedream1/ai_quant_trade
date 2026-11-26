"""Regression coverage for the broker research PDF parser."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from pdf_parser import parse_pdf  # noqa: E402


def test_plain_text_with_pdf_extension_fails(tmp_path):
    document = tmp_path / "invalid.pdf"
    document.write_text("This is plain text.", encoding="utf-8")

    result = parse_pdf(document, extract_imgs=False)

    assert not result.parse_success
    assert not result.full_text
    assert result.error
