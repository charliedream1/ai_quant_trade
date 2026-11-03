"""A captured real font-group ordering must not break Chinese PDF phrase search."""

import subprocess


def test_pdf_search_reconstructs_visual_word_order():
    result = subprocess.run(
        [
            "node",
            "--input-type=module",
            "-e",
            "import {readFileSync} from 'node:fs'; import assert from 'node:assert/strict';"
            "import {searchableText} from './src/frontend/assets/file_viewer/pdf_reader.js';"
            "const value=JSON.parse(readFileSync('tests/fixtures/file_preview/search_items.json','utf8'));"
            "assert.equal(searchableText(value.items,0.35),value.expected.normalize('NFKC').toLocaleLowerCase());",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=20,
    )
    assert result.returncode == 0, result.stderr
