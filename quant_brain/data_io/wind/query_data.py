# -*- coding: utf-8 -*-
# @Author   : liyi
# @Time     : 2022/11/2 8:12
# @File     : query_data.py
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

from WindPy import w
from datetime import datetime

from tools.file_io.load_csv import get_self_select_stock_lst
from quant_brain.data_io.wind.utils import parse_val
from tools.log.log_util import addlog, log


# ============ 1. Account Related ==============
def get_ava_funds(log_id: str) -> float:
    account_ret = w.tquery('Capital', 'LogonID=%d' % log_id)
    if account_ret.ErrorCode != 0:
        log.info("Error Code:", account_ret.ErrorCode)

    ret_dict = parse_val(account_ret, ['AvailableFund'])
    ava_funds = ret_dict['AvailableFund']
    return ava_funds


def check_account_info():
    log.info('1. 根据LogonID查询所有成交')
    tradings = w.tquery('Trade', 'LogonID=1')
    if tradings.ErrorCode != 0:
        log.info(tradings.Data)

    log.info('2. 查询账户资金')
    capital = w.tquery('Capital', 'LogonID=1')
    if capital.ErrorCode != 0:
        log.info(capital.Data)

    log.info('3. 查询账户持仓')
    position = w.tquery('Position', 'LogonID=1')
    if position.ErrorCode != 0:
        log.info(position.Data)


# ============ 2. Data Related ==============
def get_stock_pool(self_sel_stock_path: str, market_code: str) -> list:
    # 4. get stock pool list
    if self_sel_stock_path is not None and self_sel_stock_path != '':
        stock_lst = get_self_select_stock_lst(self_sel_stock_path)
    else:
        # 1. get the latest constituents of HS300 index
        query_date = datetime.today().strftime('%Y-%m-%d')
        error_code, stock_codes = w.wset("sectorconstituent",
                                         "date={};windcode={};field=wind_code,sec_name".
                                         format(query_date, market_code),
                                         usedf=True)
        if error_code != 0:
            log.error("Error Code:" + error_code)
            log.error("Error Message:" + stock_codes.iloc[0, 0])
            stock_lst = []
        else:
            stock_lst = list(stock_codes['wind_code'])

    return stock_lst

