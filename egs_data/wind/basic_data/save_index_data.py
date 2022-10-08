# -*- coding: utf-8 -*-
# @Author   : liyi
# @Time     : 2022/10/3 22:32
# @File     : save_index_data.py
# @Project  : ai_quant_trade
# Copyright (c) Personal 2022 liyi
# Function Description: save index data
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
from tqdm import tqdm

path = os.getcwd()
sys.path.append(os.path.abspath(path + ('/..' * 3)))

from quant_brain.data_io.wind.dump_data import WindDataLoader

from tools.log.log_util import addlog, log
from tools.file_io.config import override_config
from tools.file_io.make_nd_clean_dirs import make_dirs, clean_dirs
from tools.file_io.load_csv import get_self_select_stock_lst


def get_args():
    parser = argparse.ArgumentParser(description='Handle Wind Data')
    parser.add_argument('--debug_off', action='store_true', help='config file')

    parser.add_argument('--start_stage', default=1, type=int, help='config file')
    parser.add_argument('--stop_stage', default=100, type=int, help='config file')

    parser.add_argument('--self_sel_stock_path', default=None, type=str,
                        help='xls path for self selected stock list')
    parser.add_argument('--market_code', default='000300.SH', type=str,
                        help='market code to acquire corresponding stock list')
    parser.add_argument('--cols_name',
                        default='amount,open,high,low,close,factor,vwap,volume',
                        type=str,
                        help='columns name for data frame')
    parser.add_argument('--wsd_fields',
                        default='amt,open,high,low,close,adjfactor,vwap,volume',
                        type=str,
                        help='wind data filed name')

    parser.add_argument('--adjust_type', default='B',
                        choices=['F', 'B', 'N'],
                        help='price adjust type, pre-adjust:F, post-adjust:B, NO adjust: N')
    parser.add_argument('--freq', type=str, default='1d', help='frequency of data')
    parser.add_argument('--start_time', type=str, help='dir to store data')
    parser.add_argument('--end_time', type=str, help='dir to store data')

    parser.add_argument('--exp_dir', type=str, help='export file dir')
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
        args.start_stage = 1
        args.stop_stage = 100

        # 沪深300：000300.SH'， 上证：000001.SH
        args.market_code = '000001.SH'  # ['000300.SH', '000001.SH']

        args.start_time = '2008-01-01'
        args.end_time = '2022-09-26'

        # price adjust type, pre-adjust:F, post-adjust:B, NO adjust: N
        args.adjust_type = 'B'

        out_dir = r'E:\Data\wind\cn_data\index_data'
        out_folder_name = args.freq + '_' + \
                          args.start_time.replace('-', '').replace(' ', '').replace(':', '') + '_' + \
                          args.end_time.replace('-', '').replace(' ', '').replace(':', '') + '_' + args.adjust_type
        args.exp_dir = os.path.join(out_dir, out_folder_name)

        make_dirs(args.exp_dir)

    wind_loader = WindDataLoader()

    file_name = 'trade_calendar_' + args.start_time.replace('-', '') + '_' + \
                args.end_time.replace('-', '') + '.csv'
    out_csv_path = os.path.join(args.exp_dir, file_name)

    if os.path.exists(out_csv_path):
        df_trade_calendar = pd.read_csv(out_csv_path, index_col=0)
    else:
        df_trade_calendar = wind_loader.dump_trade_calendar(args)

    trade_calendar_lst = list(df_trade_calendar.index)

    if type(args.market_code) == list:
        market_code = args.market_code
        for item in market_code:
            args.market_code = item
            wind_loader.dump_index_data(args, trade_calendar_lst)
    else:
        wind_loader.dump_index_data(args, trade_calendar_lst)


if __name__ == '__main__':
    main()
