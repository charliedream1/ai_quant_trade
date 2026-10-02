# -*- coding: utf-8 -*-
"""Unit tests for refactored egs_llm/a05_test project."""
import sys
from pathlib import Path


PROJ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJ))


def test_make_dirs_creates_nested_dirs(tmp_path):
    from src.tools.file_io.make_nd_clean_dirs import make_dirs
    target = tmp_path / 'a' / 'b' / 'c'
    make_dirs(str(target))
    assert target.exists()
    make_dirs(str(target))  # idempotent


def test_clean_dirs_removes_dir(tmp_path):
    from src.tools.file_io.make_nd_clean_dirs import clean_dirs, make_dirs
    target = tmp_path / 'to_clean'
    make_dirs(str(target))
    (target / 'inner.txt').write_text('hi', encoding='utf-8')
    clean_dirs(str(target))
    assert not target.exists()


def test_batch_test_transformers_imports_cleanly():
    """Importing the entry script verifies all rewrite path is correct.

    The real model call is skipped because we don't load any LLM weights here.
    """
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        'batch_test_transformers',
        str(PROJ / 'batch_test_transformers.py'),
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert hasattr(mod, 'Evaluator')
    assert hasattr(mod, 'main')


def test_simple_test_transformers_imports_cleanly():
    # simple_test_transformers.py tries to load an LLM at module level
    # (``/mnt/mdl/...``). That path does not exist in the test
    # environment, so the module can't be executed. We only verify the
    # file parses cleanly as Python source.
    import ast
    src = (PROJ / 'simple_test_transformers.py').read_text(encoding='utf-8')
    ast.parse(src)
