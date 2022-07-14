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

import argparse
import os

import yaml
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import ffn

from tools.quant_trade.get_stock_data.get_tushare_data import TuShareData
from tools.quant_trade.back_test.cal_fee import calculate_fee
from tools.file_io.config import override_config
from tools.file_io.make_nd_clean_dirs import make_dirs, clean_dirs
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
    def market_open(self, df_price):
        price = df_price['close']

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
            # set holding positon to False
            self.hold = False
            message = 'Sell with price: ' + str(price) + \
                      ', capital ' + str(self.capital)
            log.info(message)

        # calculate capital of each day计算每日的资金数目
        if self.hold:
            # if holding position, record current market capitalization
            self.capital_list.append(self.rest + self.pos * price)
        else:
            # if not holding, record current capital
            self.capital_list.append(self.capital)

    @addlog(name='after_market_close')
    def after_market_close(self):
        pass

