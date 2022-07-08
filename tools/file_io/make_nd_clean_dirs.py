# -*- coding: utf-8 -*-
# @Author   : liyi (liyi_best@foxmail.com)
# @Time     : 2022/7/8 7:25
# @File     : prep_clean_dirs.py
# @Project  : ai_quant_trade
# Copyright (c) Personal 2022 liyi
# Function Description:
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os


def make_dirs(path: str):
    if not os.path.exists(path):
        os.makedirs(path)


def clean_dirs(path: str):
    if os.path.exists(path):
        for root, dirs, files in os.walk(path, topdown=False):
            # remove files first
            for name in files:
                os.remove(os.path.join(root, name))
            # remove folders
            for name in dirs:
                os.rmdir(os.path.join(root, name))
        os.rmdir(path)
