# -*- coding: utf-8 -*-
# @Author   : Yi Li (liyi_best@foxmail.com)
# @Time     : 2022/7/14 22:59
# @File     : trades_on_k_line.py
# @Project  : ai_quant_trade
# Copyright (c) Personal 2022 Yi Li
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

import talib
import pandas as pd
import mplfinance as mpl
# use old api
from mplfinance.original_flavor import candlestick2_ohlc, volume_overlay
import matplotlib
import matplotlib.pyplot as plt

# Use Qt5Agg for plot show, otherwise, no plot shown
matplotlib.use('Qt5Agg')

from tools.log.log_util import addlog, log


@addlog(name='plot_trades_on_capital')
def plot_trades_on_capital(stock_id: str,
                           capital_list: list,
                           df_trade: pd.DataFrame(),
                           save_plt_path: str):
    """
    :param stock_id: stock id
    :param capital_list: account capital changing list
    :param df_trade: trading info Dataframe
    :param save_plt_path: save path for the plots
    :return: None
    """
    # todo: add draw of base capital, base return
    # create figure object
    fig = plt.figure()
    ax1 = fig.add_subplot(111)

    # 1. plot trades on capital line
    # create title
    ax1.set_title(str(stock_id) + 'Trading Details with Capital Changing')
    # make plot of capital changing
    ax1.plot(range(len(capital_list)), capital_list)

    # make annotation of buying and selling
    for i in range(len(df_trade)):
        # offset the annotate from data point on line
        # adjust to a proper value
        offset_val = 2000 if i % 2 else - 2000
        # 1st arg: text for annotation
        # 2nd arg: xy axis of the point
        # 3rd arg: xy axis for text on plot
        # 4th arg: arrow type
        #  -  no arrow
        #  -> single track arrow
        #  <- reverse arrow
        #  <-> bidirectional arrow
        # -|> triangle arrow
        # <|- reversed triangle arrow
        ax1.annotate(text=df_trade['trade_type'].iloc[i],
                     xy=(df_trade['time_index'].iloc[i],
                         df_trade['capital'].iloc[i]),
                     xytext=(df_trade['time_index'].iloc[i],
                             df_trade['capital'].iloc[i] + offset_val),
                     arrowprops={'arrowstyle': '->'})

    ax1.grid(True, axis='both')  # enable grids

    if len(save_plt_path):
        # save as a vector graph to prevent of blur effect
        # ax1.savefig(save_plt_path, dpi=300)
        # above gives all of warnings:
        #   The PostScript backend does not support transparency;
        #   partially transparent artists will be rendered opaque.
        fig.savefig(save_plt_path, format="svg", transparent=True)


@addlog(name='plot_trades_on_k_line')
def plot_trades_on_k_line(stock_id: str,
                          df_stock: pd.DataFrame(),
                          df_trade: pd.DataFrame(),
                          save_plt_path: str):
    """
    :param stock_id: stock_id
    :param df_stock: stock info dataframe
    :param df_trade: trading info dataframe
    :param save_plt_path: plot saving path
    :return:
    """
    # create figure object
    fig = plt.figure()

    # add subplot
    ax1 = fig.add_subplot(211)
    ax2 = fig.add_subplot(212)

    # 1. draw k line
    candlestick2_ohlc(ax1, df_stock['open'], df_stock['high'],
                      df_stock['low'], df_stock['close'],
                      colordown='green', colorup='red', width=0.6)
    # 2. draw volume
    volume_overlay(ax2, df_stock['open'], df_stock['close'],
                   df_stock['vol'],
                   colordown='green', colorup='red', width=1)

    # 3. calculate moving average value
    # ma5_df = talib.MA(df_stock['close'], timeperiod=5)
    # ma10_df = talib.MA(df_stock['close'], timeperiod=10)
    # ma20_df = talib.MA(df_stock['close'], timeperiod=20)
    #
    # ax1.plot(ma5_df, label='ma5')
    # ax1.plot(ma10_df, label='ma10')
    # ax1.plot(ma20_df, label='ma10')

    ax1.plot(df_stock['ma_short'], label='ma_short')
    ax1.plot(df_stock['ma_long'], label='ma_long')
    ax1.legend()

    # make annotation of buying and selling on k line
    for i in range(len(df_trade)):
        # offset the annotate from data point on line
        # adjust to a proper value
        offset_val = 2 if i % 2 else -2
        # 1st arg: text for annotation
        # 2nd arg: xy axis of the point
        # 3rd arg: xy axis for text on plot
        # 4th arg: arrow type
        #  -  no arrow
        #  -> single track arrow
        #  <- reverse arrow
        #  <-> bidirectional arrow
        # -|> triangle arrow
        # <|- reversed triangle arrow
        # make annotation on k line close value
        ax1.annotate(text=df_trade['trade_type'].iloc[i],
                     xy=(df_trade['time_index'].iloc[i],
                         df_trade['close'].iloc[i]),
                     xytext=(df_trade['time_index'].iloc[i],
                             df_trade['close'].iloc[i] + offset_val),
                     arrowprops={'arrowstyle': '->'})

    # set properties of each figure
    ax1.grid(True, axis='both')  # enable grids
    ax2.grid(True, axis='both')  # enable grids
    ax1.set_title(str(stock_id) + 'K Line')
    ax2.set_title('Volume Changing')

    # plt.grid(True, axis='both')  # enable grids
    plt.tight_layout()

    if len(save_plt_path):
        # save as a vector graph to prevent of blur effect
        # fig.savefig(save_plt_path, dpi=300)
        # above gives all of warnings:
        #   The PostScript backend does not support transparency;
        #   partially transparent artists will be rendered opaque.
        fig.savefig(save_plt_path, format="svg", transparent=True)


def show_plt():
    # make block true to solve conflicts, otherwise, plot not response
    plt.show(block=True)
    # plt.close()
