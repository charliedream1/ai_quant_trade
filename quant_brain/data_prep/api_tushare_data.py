# -*- coding: utf-8 -*-
# @Author   : liyi
# @Time     : 2022/7/5 8:13
# @File     : api_tushare_data.py
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
from quant_brain.data_prep.api_stock_data import StockDataApi
from tools.date_time.date_format_check import validate
from tools.log.log_util import addlog, log


class TuShareData(StockDataApi, ABC):
    def __init__(self):
        super(TuShareData, self).__init__()

        # initialize api
        ts.set_token(tushare_token)
        self.ts_pro = ts.pro_api()

    # todo: will be moved to external functions
    @addlog(name='Acquire All data from Tushare')
    def get_df_data(self,
                    benchmark: str,
                    stock_lst: list,
                    start_time: datetime.date,
                    end_time: datetime.date,
                    time_freq: str = 'daily',
                    skip_download: bool = True,
                    csv_dir: str = ''
                    ) -> dict:
        """
        :param benchmark: benchmark code for market index
        :param stock_lst: stock id for query data
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

        # fixme: without purchase VIP, index data can't be acquired
        # get benchmark index dataframe
        log.info('get benchmark index data')
        file_name = benchmark + '_' + str(start_time) + '_' + str(end_time) + '.csv'
        out_csv_file = os.path.join(csv_dir, file_name)
        if benchmark != 'None':
            df = self.query_data('index_daily', benchmark,
                                 start_time, end_time, time_freq,
                                 skip_download, out_csv_file)
        else:
            df = pd.DataFrame()
        data_dict[benchmark] = df

        # get stock data dataframe
        for code in stock_lst:
            log.info('get stock data %s' % code)
            file_name = code + '_' + str(start_time) + '_' + str(end_time) + '.csv'
            out_csv_file = os.path.join(csv_dir, file_name)
            df = self.query_data('fund_daily', code,
                                 start_time, end_time, time_freq,
                                 skip_download, out_csv_file)
            data_dict[code] = df

        return data_dict
    
    # todo: u might consider to use parallel to accelerate
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
        assert code_type in ['fund_daily', 'index_daily']

        # loading data
        if os.path.exists(csv_dir) and skip_download:
            # load file if exist
            df = pd.read_csv(csv_dir, index_col=0)
        else:
            assert start_time < end_time
            df = pd.DataFrame()

            try:
                if code_type == 'fund_daily':
                    # get stock data
                    df = self.ts_pro.query(time_freq, ts_code=code,
                                           start_date=start_time, end_date=end_time)
                elif code_type == 'index_daily':
                    # get index data
                    df = self.ts_pro.index_daily(ts_code=code,
                                                 start_date=start_time, end_date=end_time)
                elif code_type == 'stk_factor':
                    df = self.ts_pro.stk_factor(ts_code=code,
                                                 start_date=start_time, end_date=end_time)
            except Exception as e:
                log.error('Caught exception in Tushare Data Acquisition %s' % e)
                traceback.print_exc()

            if len(df):
                # reverse df, make start from history to current
                df = df.reindex(index=df.index[::-1])
                df = df.reset_index(drop=True)  # reset index
                df.to_csv(csv_dir)

        return df

    @addlog(name='get stock list and basic info')
    def get_stk_basic(self, exchange: str) -> list:
        """
        :param exchange: 交易所 SSE上交所 SZSE深交所 BSE北交所
        :return: stock list
        """
        # #查询当前所有正常上市交易的股票列表
        # （注册后修改个人信息）即可免费调取
        # list_status: 上市状态 L上市 D退市 P暂停上市，默认是L
        # exchange: 交易所 SSE上交所 SZSE深交所 BSE北交所
        # market: 市场类别 （主板/创业板/科创板/CDR/北交所）
        # df = self.ts_pro.query('stock_basic', exchange='SSE',
        #                        list_status='L',
        #                        fields='ts_code,symbol,name,area,industry,market,list_date')
        df = self.ts_pro.query('stock_basic', exchange=exchange,
                               list_status='L',
                               fields='ts_code')

        return df.to_list()
