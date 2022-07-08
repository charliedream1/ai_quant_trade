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
from tools.file_io.config import override_config
from tools.file_io.make_nd_clean_dirs import make_dirs, clean_dirs
from tools.log.log_util import addlog, log


class DoubleMa:
    def __init__(self, args):
        # 1. load yaml file
        with open(args.config, 'r') as fin:
            self.configs = yaml.load(fin, Loader=yaml.FullLoader)
        if len(args.override_config) > 0:
            self.configs = override_config(self.configs, args.override_config)

        self.test_conditions = self.configs['test_condition']
        self.order_cost = self.configs['order_cost']

        # 2. get stock data
        db = TuShareData()
        df = db.get_df_data(**args)
        df = df.reindex(index=df.index[::-1])  # reverse df

        # remove unused cols to make it fast to process
        used_cols = ['trade_date', 'close']
        df = df[used_cols]

        # 3. get moving average value
        df['ma_short'] = df['close'].rolling(window=self.configs['ma_short']).mean()
        df['ma_long'] = df['close'].rolling(window=self.configs['ma_long']).mean()
        self.df = df.dropna()

        # ======================================
        # ======== internal vars ===============
        self.pos_lst = []   # stocks holding list
        self.hold = False

    @addlog(name='before_market_open')
    def before_market_open(self):
        pass

    @addlog(name='market_open')
    def market_open(self):
        pass

    @addlog(name='after_market_close')
    def after_market_close(self):
        pass

    def back_test_ctrl(self):
        capital = self.test_conditions['capital']
        open_fee = self.order_cost['open_commission']

        # loop history data
        for i in range(len(self.df)):
            ma_short = self.df.loc[i, 'ma_short']
            ma_long = self.df.loc[i, 'ma_long']
            price = self.df.loc[i, 'close']

            # decision: buy or sell
            if ma_short >= ma_long and not self.hold:
                # calculate purchase number
                pos = int(capital / price / 100) * 100


def get_args():
    parser = argparse.ArgumentParser(description='double moving average strategy')
    parser.add_argument('--debug_off', action='store_true', help='config file')

    parser.add_argument('--config', help='config file')
    parser.add_argument('--data_dir', help='dir to store data')
    parser.add_argument('--exp_dir', help='export file dir')

    args = parser.parse_args()
    return args


def main():
    args = get_args()

    debug = True
    if args.debug_off:
        debug = False
    if debug:
        cur_dir = os.getcwd()
        args.config = os.path.join(cur_dir, 'conf', 'double_ma.yaml')
        args.data_dir = os.path.join(cur_dir, 'data')
        args.exp_dir = os.path.join(cur_dir, 'exp')

        make_dirs(args.data_dir)
        make_dirs(args.exp_dir)

    strategy = DoubleMa(args)
    strategy.back_test_ctrl()


if __name__ == '__main__':
    main()
