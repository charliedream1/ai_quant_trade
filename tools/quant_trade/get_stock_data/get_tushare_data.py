# -*- coding: utf-8 -*-
# @Author   : liyi
# @Time     : 2022/7/5 8:13
# @File     : get_tushare_data.py
# @Project  : ai_quant_trade
# Copyright (c) Personal 2022 liyi
# Function Description: get stock data from tushare api
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

# # 1. 安装和简介
# Tushare网址: [**https://tushare.pro/**](https://tushare.pro/)
# api website: https://tushare.pro/document/2?doc_id=27
# 安装
# ``` sh
# pip install tushare
# ```
# **注：如果大量调用，或需要获取更详细的信息，需要付费**
# - 旧版本接口将不再维护，建议使用新接口Tushare Pro (需要注册获取token)
# - 注册后在右上角用户头像--》个人主页--》获取token
# - 如果没有缴费加入会员，很多接口都无法调用(每个接口调用需要的积分数，请查看接口文档)

import os
from abc import ABC
import pandas as pd

import tushare as ts
# replace below with your token and comment my import
# tushare_token = 'xxxx'
from data.private.tushare_token import tushare_token
from tools.quant_trade.get_stock_data.api_stock_data import StockDataApi


class TuShareData(StockDataApi, ABC):

    def get_df_data(self,
                    stock_id: str,
                    start_time: str,
                    end_time: str,
                    csv_dir: str,
                    skip_download: bool = True
                    ) -> pd.DataFrame:
        # output path
        file_name = stock_id + '_' + start_time + '_' + end_time
        out_csv_file = os.path.join(csv_dir, file_name)

        if os.path.exists(out_csv_file):
            # load file if exist
            df = pd.read_csv(out_csv_file)
        else:
            # initialize api
            ts.set_token(tushare_token)
            ts_pro = ts.pro_api()

            # get stock data
            df = ts_pro.query('daily', ts_code=stock_id,
                              start_date=start_time, end_date=end_time)
            df.to_csv(out_csv_file)
        return df
