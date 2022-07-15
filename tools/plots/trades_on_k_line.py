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

import pandas as pd
import matplotlib
import matplotlib.pyplot as plt

# Use Qt5Agg for plot show, otherwise, no plot shown
matplotlib.use('Qt5Agg')

from tools.log.log_util import addlog, log


@addlog(name='plot_trades')
def plot_trades(capital_list: list,
                df_trade: pd.DataFrame(),
                save_plt_path: str):
    """
    :param capital_list: account capital changing list
    :param df_trade: trading info Dataframe
    :param save_plt_path: save path for the plots
    :return: None
    """
    # 1. plot trades on capital line
    # create title
    plt.title('Trading Details')
    # make plot of capital changing
    plt.plot(range(len(capital_list)), capital_list)

    # make annotation of buying and selling
    for i in range(len(df_trade)):
        # offset the annotate from data point on line
        # adjust to a proper value
        offset_val = 2000 if i % 2 else -2000
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
        plt.annotate(text=df_trade['trade_type'].iloc[i],
                     xy=(df_trade['time_index'].iloc[i],
                         df_trade['capital'].iloc[i]),
                     xytext=(df_trade['time_index'].iloc[i],
                             df_trade['capital'].iloc[i] + offset_val),
                     arrowprops={'arrowstyle': '->'})

    plt.grid(True, axis='both')  # enable grids
    # make block true to solve conflicts, otherwise, plot not response
    plt.show(block=True)
