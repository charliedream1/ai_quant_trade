# -*- coding: utf-8 -*-
# @Author   : ly
# @Time     : 2022/6/23 23:08
# @File     : pandas_datareader_data.py
# @Project  : ai_quant_trade
# Copyright (c)
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

# 注意：雅虎已关闭国内服务，yahoo 源已不可用；stooq 源 URL 也已失效
# 改用 FRED（美联储经济数据）源，免费、无需 API Key、国内可直连
import pandas_datareader as web
import pandas as pd

print('web version', web.__version__)
start_date = '2020-01-01'
end_date = '2024-12-31'

# FRED 源：获取美国 GDP 数据（季度）
data = web.data.DataReader('GDP', 'fred', start_date, end_date)
print(data.tail())
print(f"共获取 {len(data)} 条数据")
