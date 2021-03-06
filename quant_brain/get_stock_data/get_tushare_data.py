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
import datetime
import traceback

import tushare as ts
# replace below with your token and comment my import
# tushare_token = 'xxxx'
from data.private.tushare_token import tushare_token
from quant_brain.get_stock_data.api_stock_data import StockDataApi
from tools.date_time.date_format_check import validate
from tools.log.log_util import addlog, log


class TuShareData(StockDataApi, ABC):
    def __init__(self):
        super(TuShareData, self).__init__()

        # initialize api
        ts.set_token(tushare_token)
        self.ts_pro = ts.pro_api()

    @addlog(name='Acquire All data from Tushare')
    def get_df_data(self,
                    benchmark: str,
                    stock_id: str,
                    start_time: datetime.date,
                    end_time: datetime.date,
                    time_freq: str = 'daily',
                    skip_download: bool = True,
                    csv_dir: str = ''
                    ) -> dict:
        """
        :param benchmark: benchmark code for market index
        :param stock_id: stock id for query data
        :param start_time: query start time
        :param end_time: query end time
        :param time_freq: frequency of data, e.g. daily or minutes
        :param skip_download: if csv exist, it will skip download
        :param csv_dir: csv dir to save query data
        :return: query data with dataframe type
        """
        # check time format is YYYYMMDD
        validate(start_time)
        validate(end_time)

        # convert time format
        start_time = start_time.strftime('%Y%m%d')
        end_time = end_time.strftime('%Y%m%d')

        # get data
        data_dict = {}

        # fixme: without pay, index data can't be acquired
        # get benchmark index dataframe
        log.info('get benchmark index data')
        file_name = str(start_time) + '_' + str(end_time) + '_' + benchmark + '.csv'
        out_csv_file = os.path.join(csv_dir, file_name)
        df = self.query_data('index_daily', benchmark,
                             start_time, end_time, time_freq,
                             skip_download, out_csv_file)
        data_dict[benchmark] = df

        # get stock data dataframe
        log.info('get stock data dataframe')
        file_name = str(start_time) + '_' + str(end_time) + '_' + stock_id + '.csv'
        out_csv_file = os.path.join(csv_dir, file_name)
        df = self.query_data('fund_daily', stock_id,
                             start_time, end_time, time_freq,
                             skip_download, out_csv_file)
        data_dict[stock_id] = df

        return data_dict

    @addlog(name='Query Data')
    def query_data(self,
                   code_type: str,
                   code: str,
                   start_time: str,
                   end_time: str,
                   time_freq: str = 'daily',
                   skip_download: bool = True,
                   csv_dir: str = ''
                   ) -> pd.DataFrame:
        """
        :param code_type: index or stock
        :param code: id for query data
        :param start_time: query start time
        :param end_time: query end time
        :param time_freq: frequency of data, e.g. daily or minutes
        :param skip_download: if csv exist, it will skip download
        :param csv_dir: csv dir to save query data
        :return: query data with dataframe type
        """
        # loading data
        if os.path.exists(csv_dir) and skip_download:
            # load file if exist
            df = pd.read_csv(csv_dir, index_col=0)
        else:
            assert start_time < end_time

            try:
                # get stock data
                df = self.ts_pro.query(code_type, ts_code=code,
                                       start_date=start_time, end_date=end_time)
                df.to_csv(csv_dir)
            except Exception as e:
                df = pd.DataFrame()
                log.error('Caught exception in Tushare Data Acquisition')
                traceback.print_exc()

        return df
