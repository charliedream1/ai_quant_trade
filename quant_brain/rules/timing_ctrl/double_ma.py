# -*- coding: utf-8 -*-
# @Author   : liyi (liyi_best@foxmail.com)
# @Time     : 2022/7/4 23:32
# @File     : double_ma.py
# @Project  : ai_quant_trade
# Copyright (c) Personal 2022 liyi
# Function Description: double moving average stratege
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

import pandas as pd
import numpy as np
import copy

from quant_brain.back_test.cal_fee import calculate_fee
from tools.log.log_util import addlog, log


class DoubleMa:
    def __init__(self, args):
        self.args = args

        # ma related value
        self.ma_short_dur = args['ma_short']
        self.ma_long_dur = args['ma_long']
        self.ma_short_val = -1
        self.ma_long_val = -1

        # stock related
        self.pos_stock_dict = {}
        self.hold = False

        self.capital = args['capital']
        self.pos = 0  # holding position number
        self.rest = 0  # rest capital

        # trading log
        self.df_trade = pd.DataFrame()
        self.trade_cnt = 0  # total trading times

        # ================
        # internal vars
        self._que = []
        self.capital_list = []

    @addlog(name='before_market_open')
    def before_market_open(self, close_val: list):
        # if system keeps alive, transfer data of each day one by one
        #  to this function, we this branch
        # this can be used for real or simulate real trading
        if len(close_val):
            assert len(close_val) == 1
            self._que.append(close_val)
            if len(self._que) > self.ma_long_dur:
                self._que = self._que[-self.ma_long_dur:]
            self.ma_short_val = np.mean(self._que[-self.ma_short_dur:])
            self.ma_long_val = np.mean(self._que[-self.ma_long_dur:])

    @addlog(name='market_open')
    def market_open(self, time_index: int, df_price: pd.Series()):
        price = df_price['close']
        trade_type = ''

        # decision: buy or sell
        if self.ma_short_val >= self.ma_long_val and not self.hold:
            # calculate purchase number, 1 buy = 100 shares
            # minimum subscribe for 100 shares, multiple 100 is to 1 buy
            self.pos = int(self.capital / price / 100) * 100

            # extra fee calculation
            fee = calculate_fee(price, self.pos, self.args, 'buy')

            # rest capital
            self.rest = self.capital - self.pos * price - fee
            assert self.rest >= 0

            # set holding flag to True
            self.hold = True
            trade_type = 'buy'
            self.trade_cnt += 1

            # output log
            message = 'Buy with price: ' + str(price) + \
                      ', capital ' + str(self.capital)
            log.info(message)
        elif self.ma_short_val < self.ma_long_val and self.hold:
            # extra fee calculation
            fee = calculate_fee(price, self.pos, self.args, 'sell')

            # calculate capital of closing a position
            self.capital = self.pos * price - fee + self.rest

            # clear holding position to 0
            self.pos = 0

            # set holding position to False
            self.hold = False
            trade_type = 'sell'
            self.trade_cnt += 1

            # output log
            message = 'Sell with price: ' + str(price) + \
                      ', capital ' + str(self.capital)
            log.info(message)

        # calculate capital of each day???????????????????????????
        if self.hold:
            # if holding position, record current market capitalization
            capital = self.rest + self.pos * price
            self.capital_list.append(capital)
        else:
            # if not holding, record current capital
            capital = self.capital
            self.capital_list.append(self.capital)

        # make trading record
        if len(trade_type):
            df_info = copy.deepcopy(df_price)
            df_info['time_index'] = time_index
            df_info['trade_type'] = trade_type
            df_info['capital'] = capital
            df_info['pos'] = self.pos
            self.df_trade = self.df_trade.append(df_info, ignore_index=True)
        pass

    @addlog(name='after_market_close')
    def after_market_close(self):
        pass

