# -*- coding: utf-8 -*-
# @Author   : liyi (liyi_best@foxmail.com)
# @Time     : 2022/7/8 22:34
# @File     : back_tester.py
# @Project  : ai_quant_trade
# Copyright (c) Personal 2022 liyi
# Function Description: back test for the strategy
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
from tools.quant_trade.back_test.risk_indicator import cal_risk_indicator
from tools.plots.trades_on_k_line import plot_trades_on_capital, plot_trades_on_k_line, show_plt
from tools.quant_trade.back_test.cal_fee import calculate_fee
from tools.file_io.config import override_config
from tools.file_io.make_nd_clean_dirs import make_dirs, clean_dirs
from tools.log.log_util import addlog, log


class BackTester:
    @addlog(name='Back Test Initialization')
    def __init__(self, args):
        self.args = args

        # 1. load yaml file
        with open(args.config, 'r', encoding='utf8') as fin:
            self.configs = yaml.load(fin, Loader=yaml.FullLoader)
        if len(args.override_config) > 0:
            self.configs = override_config(self.configs, args.override_config)

        self.data_condition = self.configs['data_condition']
        self.test_conditions = self.configs['test_condition']
        self.data_condition['csv_dir'] = self.args.data_dir
        self.order_cost = self.configs['order_cost']

        # 2. get stock data
        db = TuShareData()
        df = db.get_df_data(**self.data_condition)
        # reverse df, make start from history to current
        df = df.reindex(index=df.index[::-1])
        df = df.reset_index(drop=True)  # reset index

        # remove unused cols to make it fast to process
        # used_cols = ['trade_date', 'close']
        # df = df[used_cols]

        # 3. get moving average value
        df['ma_short'] = df['close'].rolling(window=self.test_conditions['ma_short']).mean()
        df['ma_long'] = df['close'].rolling(window=self.test_conditions['ma_long']).mean()
        # the beginning of mean duration will be empty, drop it
        self.df = df.dropna()

        # 4. initialize strategy
        from egs_local_strategies.rules.double_ma.double_ma import DoubleMa
        strategy_config = self.configs['order_cost']
        strategy_config['capital'] = self.test_conditions['capital']
        strategy_config['stock_id'] = self.data_condition['stock_id']
        strategy_config['ma_short'] = self.test_conditions['ma_short']
        strategy_config['ma_long'] = self.test_conditions['ma_long']
        self.strategy = DoubleMa(strategy_config)

        # ======================================
        # ======== internal vars ===============
        self.pos_lst = []  # stocks holding list
        self.hold = False

    @addlog(name='start offline back test')
    def offline_back_test_ctrl(self):
        # loop history data, start from 1 is to avoid see the future
        for i in range(1, len(self.df)):
            self.strategy.ma_short_val = self.df['ma_short'].iloc[i - 1]
            self.strategy.ma_long_val = self.df['ma_long'].iloc[i - 1]
            # price = self.df['close'].iloc[i]
            # not use i-1 is because to use today's current price to order
            self.strategy.market_open(i, self.df.iloc[i])

        # calculate risk indicator
        log.info('*** Total Trading Times: %d' % self.strategy.trade_cnt)
        cal_risk_indicator(self.test_conditions['capital'],
                           self.strategy.capital_list,
                           self.strategy.df_trade,
                           self.args.exp_dir)

        # make plots
        plot_trades_on_capital(self.strategy.capital_list, self.strategy.df_trade, self.args.exp_dir)
        plot_trades_on_k_line(self.df.iloc[1:, :], self.strategy.df_trade, self.args.exp_dir)
        show_plt()

    @addlog(name='offline_trade_simulation_ctrl')
    def offline_trade_simulation_ctrl(self):
        pass


def get_args():
    parser = argparse.ArgumentParser(description='double moving average strategy')
    parser.add_argument('--debug_off', action='store_true', help='config file')

    parser.add_argument('--config', help='config file')
    parser.add_argument('--data_dir', help='dir to store data')
    parser.add_argument('--exp_dir', help='export file dir')

    parser.add_argument('--override_config',
                        action='append',
                        default=[],
                        help="override yaml config")

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

    slu = BackTester(args)
    slu.offline_back_test_ctrl()


if __name__ == '__main__':
    main()
