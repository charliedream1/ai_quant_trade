# -*- coding: utf-8 -*-
# @Author   : liyi
# @Time     : 2022/10/8 23:17
# @File     : double_ma.py
# @Project  : ai_quant_trade
# Copyright (c) Personal 2022 liyi
# Function Description: Real bid simualation
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
import sys
import argparse
import pandas as pd
from datetime import datetime
import time
import schedule
from tqdm import tqdm

from WindPy import w

path = os.getcwd()
sys.path.append(os.path.abspath(path + ('/..' * 3)))

from quant_brain.data_io.wind.account_login import logon_wind, logon_account
from quant_brain.data_io.wind.query_rt_data import get_funds, check_account_info, \
    get_stock_pool, check_position, log_out, get_rt_val
from quant_brain.data_io.wind.utils import parse_val, my_callback

from quant_brain.rules.timing_ctrl.moving_average import double_ma_timing

from tools.date_time.chinese_calendar_check import is_workdays
from tools.date_time.query_time import after_query_time
from tools.log.log_util import addlog, log


class BidSimulator:
    def __init__(self, args):
        self.args = args

        # ==== internal variables ====
        # calculate purchase number, 1 buy = 100 shares
        # minimum subscribe for 100 shares, multiple 100 is to 1 buy
        self._trade_lim = 100
        # OrderType, LMT限价委托， FOK市价委托
        self._order_type = 'LMT'
        #       账户的市场类型，SHSZ：深圳上海A，CZC：郑商所，SHF：上期所，DCE：大商所，CFE：中金所，
        #       SHO：上证期权，HK：港股
        market_type = 'SHSZ'
        self._hold_num = 200  # number of stock to hold
        self.task_time = '9:30'  # timed task start time of each day

        # 1. logon account
        logon_wind()
        self.account, self.log_id = logon_account(args.account_file_path, market_type)

        # 2. get stock pool list
        self.stock_lst = get_stock_pool(args.self_sel_stock_path, args.market_code)
        log.info('Stock Pool Num: {}'.format(len(self.stock_lst)))

        self._stock_pool_num = len(self.stock_lst)
        if self._hold_num > self._stock_pool_num:
            self._hold_num = self._stock_pool_num

    @addlog(name='Simulate Real Trading')
    def trade(self):
        log.info('Start with Trading...')
        # use avg for each stock
        ava_funds, total_asset = get_funds(self.log_id)
        avg_funds = total_asset / self._hold_num
        # todo: this cnt might be inaccurate, consider to query from API though
        #  it might slows down the processing time
        # pos_cnt: stock holding number
        cnt, buy_cnt, sell_cnt, pos_cnt, err_cnt = 0, 0, 0, 0, 0
        p_bar = tqdm(self._stock_pool_num)

        for stock_code in self.stock_lst:
            # todo: consider make parallel, currently, 181 stocks takes 5.45 min to complete
            p_bar.update(1)
            p_bar.set_description("Processing %s: (%d / %d)" % (stock_code, cnt, self._stock_pool_num))

            # exceed max hold num, stop it
            if pos_cnt >= self._hold_num:
                break

            # 1. Subscribe real time market quotation data
            rt_last, rt_ma_5d, rt_ma_20d = get_rt_val(stock_code)

            # 2. check holding position
            # 根据Windcode查询指定证券持仓
            hold_pos = False
            balance = check_position(self.log_id, stock_code)
            if balance > 0:
                hold_pos = True

            # 3. call strategy
            trade_type = double_ma_timing(rt_ma_5d, rt_ma_20d, hold_pos)

            # 4. trading
            # # Wind code, trading direction, order price, amount
            # # 输入委托下单的交易方向, Buy '1' #买入开仓、证券买入, Sell '4' #卖出平仓、证券卖出
            # OrderType, LMT限价委托， FOK市价委托
            if trade_type == 'buy':
                # todo: 当日委托过不再重复委托，用于存在失败，重新运行时
                # get order fund value
                ava_funds, total_asset = get_funds(self.log_id)
                if ava_funds > avg_funds:
                    order_funds = avg_funds
                else:
                    order_funds = ava_funds

                # check if enough money to buy, minimum purchase 100 hands
                if order_funds > rt_last * self._trade_lim:
                    # calculate purchase number, 1 buy = 100 shares
                    # minimum subscribe for 100 shares, multiple 100 is to 1 buy
                    pos = int(order_funds / rt_last / self._trade_lim) * self._trade_lim
                    order_ret = w.torder(stock_code, 'Buy', rt_last, pos,
                                         'OrderType={};LogonID={}'.
                                         format(self._order_type, self.log_id))
                    if order_ret.ErrorCode != 0:
                        log.info("Error Code:", order_ret.ErrorCode)
                        err_cnt += 1
                    else:
                        # todo: print out stock Chinese name
                        log.info('Buy: {}, Price: {}, Order_Nm: {}'.format(stock_code, rt_last, pos))
                        buy_cnt += 1
                        pos_cnt += 1
            elif trade_type == 'sell':
                order_ret = w.torder(stock_code, 'Sell', rt_last, balance,
                                     'OrderType={};LogonID={}'.format(self._order_type, self.log_id))
                if order_ret.ErrorCode != 0:
                    log.info("Error Code:", order_ret.ErrorCode)
                    err_cnt += 1
                else:
                    log.info('Sell: {}, Price: {}, Sell Num: {}'.format(stock_code, rt_last, balance))
                    pos_cnt -= 1
                    sell_cnt += 1
            else:
                if hold_pos:
                    pos_cnt += 1

        log.info('Total Holding Position: {}'.format(pos_cnt))
        log.info('Today Buy Cnt: {}'.format(buy_cnt))
        log.info('Today Sell Cnt: {}'.format(sell_cnt))

        p_bar.close()
        log.info('Err Num: ({} / {})'.format(err_cnt, self._stock_pool_num))

    # ============================================
    def timed_task(self):
        # self.trade()  # for debug only
        pre_date = None

        while True:
            today = datetime.now()
            week = is_workdays(today)

            # === for debug only ===
            # cur_date = datetime.today().strftime('%Y-%m-%d')
            #
            # if cur_date != pre_date and after_query_time('9:30'):
            #     # todo: if trading err, consider to try running another 2 times
            #     # self.trade()
            #     pre_date = cur_date
            # === for debug ===

            if week:
                cur_date = datetime.today().strftime('%Y-%m-%d')

                if cur_date != pre_date and after_query_time('9:30'):
                    # todo: if trading err, consider to try running another 2 times
                    self.trade()
                    pre_date = cur_date

            time.sleep(200)  # seconds


def get_args():
    parser = argparse.ArgumentParser(description='Handle Wind Data')
    parser.add_argument('--debug_off', action='store_true', help='config file')

    parser.add_argument('--account_file_path', default=None, type=str, help='account_file_path')
    parser.add_argument('--self_sel_stock_path', default=None, type=str,
                        help='xls path for self selected stock list')
    parser.add_argument('--market_code', default='000300.SH', type=str,
                        help='market code to acquire corresponding stock list')

    args = parser.parse_args()
    return args


def main():
    args = get_args()

    debug = True
    if args.debug_off:
        debug = False
    if debug:
        args.account_file_path = r''
        args.self_sel_stock_path = ''
        args.market_code = '000300.SH'  # 沪深300：000300.SH'， 上证：000001.SH

    sim = BidSimulator(args)
    sim.timed_task()
    log_out(sim.account, sim.log_id)


if __name__ == '__main__':
    main()
