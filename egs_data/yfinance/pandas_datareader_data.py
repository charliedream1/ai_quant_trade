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

# 注意：雅虎以关闭国内服务，该方法以无法访问，请查看yfinance或使用tushare
import pandas_datareader as web

print('web version', web.__version__)
start_date = '2020-01-01'
end_date = '2020-03-18'
data = web.data.DataReader('601318.ss', 'yahoo', start_date, end_date)
data.head()
