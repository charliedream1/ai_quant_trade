# -*- coding: utf-8 -*-
"""pytest 配置：将 src 目录加入 Python 路径"""
import os
import sys

_SRC_DIR = os.path.join(os.path.dirname(__file__), "..", "src")
_SRC_DIR = os.path.abspath(_SRC_DIR)
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)
