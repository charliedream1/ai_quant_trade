# -*- coding: utf-8 -*-
# @Author   : liyi
# @Time     : 2022/10/8 22:53
# @File     : save_market_data.py
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

import os
import sys
import argparse
import pandas as pd

path = os.getcwd()
sys.path.append(os.path.abspath(path + ('/..' * 3)))

from quant_brain.data_io.wind.dump_data import WindDataLoader

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
    # PriceAdj: 复权，前复权-F，后复权-B，无复权则不写这个参数
    # 查询字段：
    # 指标名称    字段
    # 开盘价      open
    # 最高价      high
    # 最低价      low
    # 收盘价      close
    # 成交量      volume
    # 涨跌        chg
    # 成交额      amt
    # 均价        vwap
    # 前收盘价    pre_close
    # 复权因子    adjfactor
    # 换手率      turn
    # 交易状态    trade_status
    # 停牌原因    susp_reason
    # 涨跌停状态  maxupordown
    # 涨停价      maxup
    # 跌停价      maxdown
    # 开盘集合竞价成交价   open_auction_price
    # 开盘集合竞价成交量   open_auction_volume  股（张）
    # 开盘集合竞价成交额   open_auction_amount  元

    args = get_args()

    debug = True
    if args.debug_off:
        debug = False
    if debug:
        args.start_stage = 1
        args.stop_stage = 100

        args.self_sel_stock_path = ''
        args.market_code = '000300.SH'  # 沪深300：000300.SH'， 上证：000001.SH
        args.freq = '1d'   # 1d: daily, 1m: 1 minute

        # columns name for data frame
        args.cols_name = 'amount,open,high,low,close,factor,vwap,volume'

        if args.freq == '1d':
            # wind data filed name, check meaning above
            #  for daily data
            args.wsd_fields = 'amt,open,high,low,close,adjfactor,vwap,volume,' \
                              'chg,turn,trade_status,maxupordown,maxup,maxdown'
            # args.wsd_fields = "open,high,low,close,volume,chg,amt,pre_close,adjfactor," + \
            #                   "turn,trade_status,susp_reason,maxupordown,maxup,maxdown,open_auction_price," + \
            #                   "open_auction_volume,open_auction_amount"
            args.start_time = '2008-01-01'
            args.end_time = '2022-09-30'
        else:
            # there is no too much limitation for minute data
            # for minute data
            args.wsd_fields = 'open,high,low,close,volume,amt,chg,pct_chg'
            args.start_time = '2022-01-29 10:00:00'
            args.end_time = '2022-05-05 10:05:00'

        # price adjust type, pre-adjust:F, post-adjust:B, NO adjust: N
        args.adjust_type = 'B'

        out_dir = r''
        out_folder_name = args.freq + '_' + \
                          args.start_time.replace('-', '').replace(' ', '').replace(':', '') + '_' + \
                          args.end_time.replace('-', '').replace(' ', '').replace(':', '')
        args.exp_dir = os.path.join(out_dir, out_folder_name)

        make_dirs(args.exp_dir)

    wind_loader = WindDataLoader()
    if args.start_stage <= 1 and args.stop_stage >= 1:
        df_trade_calendar = wind_loader.dump_trade_calendar(args)

    if args.start_stage <= 2 and args.stop_stage >= 2:
        if args.self_sel_stock_path is not None and args.self_sel_stock_path != '':
            stock_lst = get_self_select_stock_lst(args.self_sel_stock_path)
        else:
            file_name = 'stock_lst_' + args.market_code + '.csv'
            out_csv_path = os.path.join(args.exp_dir, file_name)

            if os.path.exists(out_csv_path):
                df_stock_list = pd.read_csv(out_csv_path)
            else:
                # if query_date empty, use today
                df_stock_list = wind_loader.get_stock_list(args, query_date=args.end_time)
            stock_lst = df_stock_list['wind_code']
        wind_loader.dump_market_data_simple(args, stock_lst)


if __name__ == '__main__':
    main()
