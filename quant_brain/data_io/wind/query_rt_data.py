# -*- coding: utf-8 -*-
# @Author   : liyi
# @Time     : 2022/11/2 8:12
# @File     : query_rt_data.py
# @Project  : ai_quant_trade
# Copyright (c) Personal 2022 liyi
# Function Description: interface for actual/simulation bidding or back-test
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
from typing import Tuple

from tools.file_io.load_csv import get_self_select_stock_lst
from quant_brain.data_io.wind.utils import parse_val
from tools.log.log_util import addlog, log


# ============ 1. Account Related ==============
def get_funds(log_id: str) -> Tuple[float, float]:
    account_ret = w.tquery('Capital', 'LogonID=%d' % log_id)
    if account_ret.ErrorCode != 0:
        log.info("Error Code:", account_ret.ErrorCode)

    ret_dict = parse_val(account_ret, ['AvailableFund', 'TotalAsset'])
    ava_funds = ret_dict['AvailableFund']
    total_asset = ret_dict['TotalAsset']
    return ava_funds, total_asset


def check_position(log_id: str, stock_code: str) -> float:
    pos_ret = w.tquery('Position', 'LogonID={};Windcode={}'.format(log_id, stock_code))
    if pos_ret.ErrorCode != 0:
        # fixme: it seems that if u are not holding a position, the query will return err
        #  thus, I'm not display it for now
        # log.info("Error Code:", pos_ret.ErrorCode)
        balance = 0.0
    else:
        ret_dict = parse_val(pos_ret, ['SecurityBalance'])
        balance = ret_dict['SecurityBalance']
    return balance


def check_account_info(log_id: str):
    log.info('1. 根据LogonID查询所有成交')
    tradings = w.tquery('Trade', 'LogonID={}'.format(log_id))
    if tradings.ErrorCode == 0:
        log.info(tradings.Fields)
        log.info(tradings.Data)

    log.info('2. 查询账户资金')
    capital = w.tquery('Capital', 'LogonID={}'.format(log_id))
    if capital.ErrorCode == 0:
        log.info(capital.Fields)
        log.info(capital.Data)

    log.info('3. 查询账户持仓')
    position = w.tquery('Position', 'LogonID={}'.format(log_id))
    if position.ErrorCode == 0:
        log.info('持仓数量：{}'.format(len(position.Data[0])))
        log.info(position.Fields)
        log.info(position.Data)
    pass


def log_out(account, log_id):
    check_account_info(log_id)

    log.info('退出登录')
    w.tlogout(account)


def cancel_request(log_id: str):
    w.cancelRequest(0)

    # 根据MarketType区分不同市场进行撤单
    w.tcancel('1', 'MarketType=SHSZ;LogonID={}'.format(log_id))


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


def get_rt_val(stock_code: str):
    # Subscribe market quotation data: rt_last(现价)，rt_ma_5d（5日均价）, rt_ma_20d（20日均价）
    # func默认为None, 此时以一次性快照方式获取数据，func=DemoWSQCallback时, 以订阅的方式实时返回行情数据, DemoWSQCallback的函数定义可参考API帮助中心的案例
    # wsq函数快照模式支持输出DataFrame数据格式，需要函数添加参数usedf=True，可以使用usedfdt=True来填充DataFrame输出NaT的日期
    # 函数订阅模式下只返回订阅品种行情有变化的订阅指标, 对没有变化的订阅指标不重复返回实时行情数据
    # wsq_ret = w.wsq("600000.SH", "rt_last,rt_ma_5d,rt_ma_20d", func=self.my_callback)
    # rt_ret = w.wsq(["600000.SH"], "rt_last,rt_ma_5d,rt_ma_20d")
    rt_ret = w.wsq(stock_code, "rt_last,rt_ma_5d,rt_ma_20d")
    if rt_ret.ErrorCode != 0:
        log.info("Error Code:", rt_ret.ErrorCode)
    ret_dict = parse_val(rt_ret, ['RT_LAST', 'RT_MA_5D', 'RT_MA_20D'])
    rt_last, rt_ma_5d, rt_ma_20d = ret_dict['RT_LAST'], ret_dict['RT_MA_5D'], ret_dict['RT_MA_20D']
    return rt_last, rt_ma_5d, rt_ma_20d
