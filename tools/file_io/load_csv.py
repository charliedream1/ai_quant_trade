# -*- coding: utf-8 -*-
# @Author   : liyi
# @Time     : 2022/10/1 22:19
# @File     : load_csv.py
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
import pandas as pd


def get_self_select_stock_lst(file_path: str) -> list:
    df_data = pd.read_excel(file_path)
    return list(df_data['证券代码'])
