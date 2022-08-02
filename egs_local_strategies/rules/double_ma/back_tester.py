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

import pandas as pd
import yaml
import copy

from quant_brain.back_test.account_info import Account
from quant_brain.back_test.trading_ctrl import order_value
from quant_brain.rules.timing_ctrl.moving_average import double_ma_timing
from quant_brain.portfolio.capital_allocation import equal_allocation
from quant_brain.fetch_data.get_tushare_data import TuShareData
from quant_brain.back_test.risk_indicator import cal_risk_indicator

from tools.plots.trades_on_k_line import plot_trades_on_capital, plot_trades_on_k_line, show_plt
from tools.file_io.config import override_config
from tools.file_io.make_nd_clean_dirs import make_dirs
from tools.log.log_util import addlog, log


class BackTester:
    @addlog(name='Back Test Initialization')
    def __init__(self, args):
        self._args = args

        # == internal vars =====
        self._trade_cnt = 0  # times of trades made
        self._data_len = 0  # queried data len

        # 1. load yaml file
        with open(args.config, 'r', encoding='utf8') as fin:
            self.configs = yaml.load(fin, Loader=yaml.FullLoader)
        if len(args.override_config) > 0:
            self.configs = override_config(self.configs, args.override_config)

        self.data_condition = self.configs['data_condition']
        self.data_condition['csv_dir'] = args.data_dir

        self.test_conditions = self.configs['test_condition']
        self.order_cost = self.configs['order_cost']

        # 2. load data
        self.stock_num = len(self.data_condition['stock_lst'])
        self._df_dict = self.prepare_data()  # dict with each stock data
        self._account = Account(self.test_conditions['capital'])

    # ==================== Sub Functions ======================
    @addlog(name='start offline back test')
    def prepare_data(self):
        db = TuShareData()
        df_dict = db.get_df_data(**self.data_condition)
        benchmark_id = self.data_condition['benchmark']
        self._df_benchmark = df_dict[benchmark_id]

        df_stock_dict = {}
        for key, df in df_dict.items():
            if key == benchmark_id:
                continue

            # remove unused cols to make it fast to process
            # used_cols = ['trade_date', 'close']
            # df = df[used_cols]

            # 3. get moving average value
            df['ma_short'] = df['close'].rolling(window=self.test_conditions['ma_short']).mean()
            df['ma_long'] = df['close'].rolling(window=self.test_conditions['ma_long']).mean()

            # the beginning of mean duration will be empty, drop it
            org_num = len(df)
            df = df.dropna()
            cur_num = len(df)
            drop_num = org_num - cur_num
            message = key + ' Dropped Null Data Num: ' + str(drop_num)
            log.info(message)
            assert cur_num != 0

            df_stock_dict[key] = df

        # (todo: maybe u need consider of handle unequal data)
        # check data len equal
        self._data_len = len(list(df_stock_dict.values())[0])
        log.info('Data Len: %d' % self._data_len)

        for key, val in df_stock_dict.items():
            if self._data_len != len(val):
                log.error('ERR: each stock data length not equal!!!')
                raise ValueError

        return df_stock_dict

    @addlog(name='single trading process')
    def trading_ctrl(self, index):
        trade_sign = False
        trade_message = ''

        for stock_id in self._df_dict.keys():
            # get available cash to buy stock
            order_funds = equal_allocation(self._account, self.stock_num)

            if order_funds > 0:
                # timing control, -1 to avoid future
                ma_short_val = self._df_dict[stock_id]['ma_short'].iloc[index - 1]
                ma_long_val = self._df_dict[stock_id]['ma_long'].iloc[index - 1]
                hold = True if stock_id in self._account.pos_dict.keys() else False
                trade_type = double_ma_timing(ma_short_val, ma_long_val, hold)

                # make order
                order_type, pos, trade_message = order_value(self._account,
                                                             stock_id,
                                                             self._df_dict[stock_id].iloc[index],
                                                             trade_type,
                                                             order_funds,
                                                             self.order_cost)

                # log trading info into account for historical check
                if len(order_type):
                    trade_sign = True
                    self._account.daily_trading_lst. \
                        append(str(self._df_dict[stock_id].iloc[index]['trade_date']) + '\n')

                    df_info = copy.deepcopy(self._df_dict[stock_id].iloc[index])
                    df_info['time_index'] = index
                    df_info['trade_type'] = order_type
                    df_info['pos'] = pos

                    if stock_id not in self._account.trade_dict.keys():
                        self._account.trade_dict[stock_id] = pd.DataFrame()

                    self._account.trade_dict[stock_id] = \
                        self._account.trade_dict[stock_id].append(df_info, ignore_index=True)

                    self._account.daily_trading_lst.append(trade_message + '\n')

                    message = '\n' + '===' * 30 + '\n'
                    self._account.daily_trading_lst.append(message)

        # check total capital in account
        total_capital = self._account.get_total_capital()
        self._account.funds_chg_lst.append(total_capital)

        # add trading record
        for stock_id in self._account.trade_dict.keys():
            self._account.trade_dict[stock_id]['total_capital'] = total_capital

        if trade_sign:
            message = 'Account Total Capital: %.2f' % total_capital
            self._account.daily_trading_lst.append(message + '\n')
            log.info(message)

            if not len(trade_message):
                trade_message = 'None'
            tmp_dict = {'capital': total_capital, 'trading detail': trade_message}
            df_info = pd.DataFrame([tmp_dict.values()], columns=tmp_dict.keys())
            self._account.pd_gather_trades = self._account.pd_gather_trades.append(df_info, ignore_index=True)

            message = '\n' + '===' * 30 + '\n'
            self._account.daily_trading_lst.append(message)

    # ==================== Main Process Control ======================
    @addlog(name='start offline back test')
    def offline_back_test_ctrl(self):
        # loop history data, start from 1 is to avoid see the future
        # todo: check whether each stock might have different len due to drop nan
        for i in range(1, self._data_len):
            self.trading_ctrl(i)

        log.info('*** Total Trading Times: %d' % self._trade_cnt)

        # calculate risk indicator
        # cal_risk_indicator(self.test_conditions['capital'],
        #                    self.test_conditions['base_rate'],
        #                    self._account.funds_chg_lst,
        #                    self._account.pd_gather_trades,
        #                    self._df_benchmark,
        #                    self._args.exp_dir)
        #
        # # make plots
        # save_path = os.path.join(self._args.exp_dir, 'plot_trades_on_capital.jpg')
        # plot_trades_on_capital(self._account.funds_chg_lst,
        #                        self._account.pd_gather_trades,
        #                        save_path)
        #
        # for stock_id in self._account.trade_dict.keys():
        #     save_path = os.path.join(self._args.exp_dir, str(stock_id) + 'plot_trades_on_k_line.jpg')
        #     plot_trades_on_k_line(self._account.trade_dict[stock_id][1:, :],
        #                           self._account.trade_dict[stock_id],
        #                           save_path)
        # show_plt()

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
