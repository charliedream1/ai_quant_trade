# -*- coding: utf-8 -*-
# @Author   : liyi
# @Time     : 2022/9/24 8:24
# @File     : dump_data.py
# @Project  : ai_quant_trade
# Copyright (c) Personal 2022 liyi
# Function Description: dump data to local from wind client
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

from WindPy import w

path = os.getcwd()
sys.path.append(os.path.abspath(path + ('/..' * 3)))

from tools.log.log_util import addlog, log
from tools.file_io.config import override_config
from tools.file_io.make_nd_clean_dirs import make_dirs, clean_dirs
from tools.file_io.load_csv import get_self_select_stock_lst


# fixme: some issue might occur for Data Dump Issue
#  1. Get stock list of each day, and loop each day to download
#     Problem: u need to merge data for each data, and stock list might be different for each day,
#             due to stock suspended or tapering, there would be more work
#  2. Get stock list of one day, and use this list to download for a period
#     Problem: some stock might in the early period due to it has not been appeared

class WindDataLoader:
    def __init__(self):
        self.start_ret = w.start()

        if self.start_ret.ErrorCode != 0:
            log.info("Start failed")
            log.info("Error Code:" + str(self.start_ret.ErrorCode))
            log.info("Error Message:" + self.start_ret.Data[0])
            raise LookupError

    @staticmethod
    @addlog(name='Dump trade calendar to CSV')
    def dump_trade_calendar(args) -> pd.DataFrame:
        """
        :param args: args class
        :return: Dataframe with one column of data time
        """
        error_code, data = w.tdays(args.start_time, args.end_time, "", usedf=True)
        if error_code != 0:
            log.error("Error Code:" + str(error_code))
            log.error("Error Message:" + data.iloc[0, 0])
            raise LookupError

        file_name = 'trade_calendar_' + args.start_time.replace('-', '') + '_' + \
                    args.end_time.replace('-', '') + '.csv'
        out_csv_path = os.path.join(args.exp_dir, file_name)
        # if not set header false, csv will have first row empty
        data.to_csv(out_csv_path, header=False)
        return data

    @staticmethod
    @addlog(name='Dump stock pool list to CSV')
    def get_stock_list(args, query_date: str = '') -> pd.DataFrame:
        """
        :param args: args class
        :param query_date: data to check, if empty, use today
        :return: Dataframe: wind_code, sec_name (stock name)
        """
        # 1. get the latest constituents of HS300 index
        if not len(query_date):
            query_date = datetime.today().strftime('%Y-%m-%d')

        error_code, stock_codes = w.wset("sectorconstituent",
                                         "date={};windcode={};field=wind_code,sec_name".
                                         format(query_date, args.market_code),
                                         usedf=True)
        if error_code != 0:
            log.error("Error Code:" + error_code)
            log.error("Error Message:" + stock_codes.iloc[0, 0])
            raise LookupError

        # file_name = 'stock_lst_' + args.market_code + '_' + query_date.replace('-', '') + '.csv'
        file_name = 'stock_lst_' + args.market_code + '.csv'
        out_csv_path = os.path.join(args.exp_dir, file_name)
        stock_codes.to_csv(out_csv_path, index=False)

        return stock_codes

    @staticmethod
    @addlog(name='Dump market data to CSV')
    def dump_market_data_simple(args, stock_codes: list):
        """
        Dump data with simple way without too much checks
        :param args: args class
        :param stock_codes: stock code list
        :return:
        """
        # fixme: some issue might occur for Data Dump Issue
        #  1. Get stock list of each day, and loop each day to download
        #     Problem: u need to merge data for each data, and stock list might be different for each day,
        #             due to stock suspended or tapering, there would be more work

        # loop through to download data of each stock and save in a csv file
        total_num = len(stock_codes)
        cnt = 0
        p_bar = tqdm(total_num)

        out_path = os.path.join(args.exp_dir, 'stocks_data')
        clean_dirs(out_path)
        make_dirs(out_path)

        for wind_code in stock_codes:
            p_bar.update(1)
            p_bar.set_description("Processing %s: (%d / %d)" % (wind_code, cnt, total_num))

            out_csv_path = os.path.join(out_path, wind_code + '.csv')
            # due to api has visit limitation, we will not repeat download
            if os.path.exists(out_csv_path):
                continue

            if args.freq == '1d':
                error_code, data = w.wsd(wind_code, args.wsd_fields,
                                         args.start_time, args.end_time,
                                         "unit=1;PriceAdj={}".format(args.adjust_type), usedf=True)
            elif args.freq == '1m':
                error_code, data = w.wsi(wind_code, args.wsd_fields, args.start_time, args.end_time,
                                         "PriceAdj={}".format(args.adjust_type), usedf=True)
            else:
                log.error('Wrong Param set for args.freq')
                raise ValueError

            if error_code != 0:
                log.error(wind_code + ":ErrorCode:" + str(error_code))
                log.error("Error Message:" + data.iloc[0, 0])
                continue

            data.index.name = 'DATE'
            # after save in csv, nan cell in dataframe will be empty
            data.to_csv(out_csv_path)
            cnt += 1

        p_bar.close()
        log.info('Total Processed: ({} / {})'.format(cnt, total_num))

    @staticmethod
    @addlog(name='Dump index data to CSV')
    def dump_index_data(args, trade_calendar_lst):
        df_index_val = pd.DataFrame(columns=['date', 'CLOSE'])
        total_num = len(trade_calendar_lst)
        cnt = 0
        p_bar = tqdm(total_num)

        for item in trade_calendar_lst:
            p_bar.update(1)
            p_bar.set_description("Processing %s: (%d / %d)" % (item, cnt, total_num))

            # 获取收盘价
            error_code, data = w.wss(args.market_code, "close",
                                     "tradeDate={};priceAdj={};cycle=D".format(item, args.adjust_type),
                                     usedf=True)
            df_index_val = df_index_val.append({'date': item, 'CLOSE': data['CLOSE'][0]},
                                               ignore_index=True)

            if error_code != 0:
                log.error(item + ":ErrorCode:" + str(error_code))
                log.error("Error Message:" + data.iloc[0, 0])
                continue

            cnt += 1

        file_name = args.market_code + '_' + trade_calendar_lst[0].replace('_', '') + \
            trade_calendar_lst[-1].replace('_', '')
        out_file_path = os.path.join(args.exp_dir, file_name)
        df_index_val.to_csv(out_file_path)

        p_bar.close()
        log.info('Total Processed: ({} / {})'.format(cnt, total_num))



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
        args.start_stage = 2
        args.stop_stage = 100

        args.self_sel_stock_path = r'E:\Data\stock_pool\证券.xls'
        args.market_code = '000300.SH'  # 沪深300：000300.SH'， 上证：000001.SH
        args.freq = '1m'   # 1d: daily, 1m: 1 minute

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
            args.end_time = '2022-09-26'
        else:
            # there is no too much limitation for minute data
            # for minute data
            args.wsd_fields = 'open,high,low,close,volume,amt,chg,pct_chg'
            args.start_time = '2022-01-29 10:00:00'
            args.end_time = '2022-05-05 10:05:00'

        # price adjust type, pre-adjust:F, post-adjust:B, NO adjust: N
        args.adjust_type = 'B'

        out_dir = r'E:\Data\wind\cn_data\lte_300_SH'
        out_folder_name = args.freq + '_' + \
                          args.start_time.replace('-', '').replace(' ', '').replace(':', '') + '_' + \
                          args.end_time.replace('-', '').replace(' ', '').replace(':', '')
        args.exp_dir = os.path.join(out_dir, out_folder_name)

        make_dirs(args.exp_dir)

    wind_loader = WindDataLoader()
    if args.start_stage <= 1 and args.stop_stage >= 1:
        df_trade_calendar = wind_loader.dump_trade_calendar(args)

    if args.start_stage <= 2 and args.stop_stage >= 2:
        if args.self_sel_stock_path is not None or args.self_sel_stock_path != '':
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
