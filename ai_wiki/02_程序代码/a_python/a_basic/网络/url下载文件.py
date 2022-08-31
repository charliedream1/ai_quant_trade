# -*- coding: utf-8 -*-
# @Author   : Yi Li (liyi_best@foxmail.com)
# @Time     : 2022/8/23 13:27
# @File     : url下载文件.py
# @Project  : ai_quant_trade
# Copyright (c) Personal 2022 Yi Li
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

from pathlib import Path

# download get_data.py script
scripts_dir = Path("~/tmp/qlib_code/scripts").expanduser().resolve()
scripts_dir.mkdir(parents=True, exist_ok=True)
import requests

with requests.get("https://raw.githubusercontent.com/microsoft/qlib/main/scripts/get_data.py") as resp:
    with open(scripts_dir.joinpath("get_data.py"), "wb") as fp:
        fp.write(resp.content)
