# -*- coding: utf-8 -*-
# @Author   : Yi Li (liyi_best@foxmail.com)
# @Time     : 2022/7/27 8:49
# @File     : account_info.py
# @Project  : ai_quant_trade
# Copyright (c) Personal 2022 Yi Li
# Function Description: Account Info Tracking
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

from tools.log.log_util import addlog, log


class Account:
    def __init__(self, capital: int):
        # 1. dynamic changing info
        self.cash = capital  # available cash for trading
        self.total_capital = capital
        # stock id: {pos_num, price}, price for current price
        self.pos_dict = {}

        # 2. trading history log
        # historical trading of each stock
        # stock id: dataframe (detailed trading info)
        self.trade_dict = {}
        # each day's trading history (only log trading really happens)
        self.daily_trading_lst = []
        # overall trading info, make each day's trading as one
        self.pd_gather_trades = pd.DataFrame()
        # log total funds changing of each day even no trades happened on the day
        self.funds_chg_lst = []

    # total capital is the sum of position current cap with account cash
    @addlog(name='get_total_capital')
    def get_total_capital(self):
        self.total_capital = 0

        # calculate pos stock market cap
        for val in self.pos_dict.values():
            self.total_capital += val['pos_num'] * val['price']

        self.total_capital += self.cash

        return self.total_capital
