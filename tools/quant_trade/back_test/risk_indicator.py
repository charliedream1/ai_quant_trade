# -*- coding: utf-8 -*-
# @Author   : liyi (liyi_best@foxmail.com)
# @Time     : 2022/7/8 8:19
# @File     : risk_indicator.py
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

import ffn
import pandas as pd

from tools.log.log_util import addlog, log


@addlog(name='cal_risk_indicator')
def cal_risk_indicator(capital: float,
                       capital_list: list,
                       df_trade: pd.DataFrame(),
                       metrics_save_path: str):
    """
    :param capital: initial money you have for stock trading
    :param capital_list: capital changing list during trading period
    :param df_trade: detailed trading info dataframe
    :param metrics_save_path: path to save risk indicator
    :return:
    """
    indicator_dict = {}
    capital_series = pd.Series(capital_list)

    # 1. calculate simple rate of return
    # represent capital changing (Pend - Pstart) / Pstart * 100%
    capital_returns = ffn.to_returns(capital_series)
    # calculate total rate of return
    total_returns = ffn.calc_total_return(capital_series)
    log.info('Total Return Rate: %.2f' % total_returns)

    # 2. Total Annal Return
    # ((1+P)^(250/n) - 1) * 100%, P is capital returns
    # different from annual return if trading time less than a year
    # due to its not the real annual return, it's a converted value
    # 250 is the trading days in one year
    annal_returns = ffn.annualize(total_returns,
                                  len(capital_list), one_year=250)
    log.info('Annual Return Rate: %.2f' % annal_returns)

    # 3. Beta
    # Use to evaluate correlation between returns of strategy and benchmark returns
    #  we usually use Shanghai securities composite index as benchmark
    #  if benchmark return raise 1%, and strategy return raise 1.5%,
    #  and beta is 1.5, vice versa -1.5
    #  if market place is good, the larger value the better
    #  if not good, the smaller the better
    #  it is usually explained as system risk
    #  Beta = Cov(Dp, Dm) / Var(Dm)
    #  Cov: covariance, Var: variance of benchmark return
    # Beta > 1: strategy changing larger than benchmark one, vice versa
    # todo

    # 4. Alpha (todo)

    # 5. calculate sharp rate
    # used to evaluate every one risk u take, the non-risk returns
    # the larger value is, the more returns while more risk u take, vice versa
    # usually, the larger value is, the better
    # Sharp Ratio = (Rp - Rf) / Op
    # Rp: annual return, Rf: no-risk interest rate, Op: changing rate of the strategy
    sharp_ratio = ffn.calc_sharpe(capital_returns)
    log.info('Sharp Rate: %.2f' % sharp_ratio)

    # 6. calculate max withdraw
    # evaluate max loss of the strategy, the smaller the value the better
    # max_draw_down = (Px-Py)/Px, (Px, PY: max value during a time)
    max_withdraw = ffn.calc_max_drawdown(capital_series)
    log.info('Max Withdraw: %.2f' % max_withdraw)

    # 7. Sortino Ratio
    # evaluate strategy loss, the larger value the better
    # Sharp Ratio = (Rp - Rf) / Od
    # Rp: annual return, Rf: no-risk interest rate, Od: strategy downward volatility
    sortino_ratio = ffn.calc_sortino_ratio(capital_returns)
    log.info('Sortino Rate: %.2f' % sortino_ratio)

    # 8. win rate
    # e.g. 8 wins in 10 trades, then win rate is 80%
    # loop through each trade and neglect first trade
    #  (? whether include first trade)
    # type1: Capital Now > Capital Pre, count 1 win
    # type2: Capital Now > Original Capital, count 1 win
    # type3: type 1 and 2 all satisfied
    # todo: need to confirm it's correct (I implemented type3)
    total_trades = len(df_trade)  # todo: whether to remove 1 ?
    win_cnt = 0
    # neglect 1st trade, due to no win or loss for 1st buy
    for i in range(1, total_trades):
        if df_trade['capital'].iloc[i] > df_trade['capital'].iloc[i - 1]:
            if df_trade['capital'].iloc[i] > capital:
                win_cnt += 1
    win_rate = win_cnt / total_trades
    log.info('Win Rate: %.2f' % win_rate)

    # 9. profit-loss ratio
    # during a time period of trading, if profit is 12000,
    # loss is 8000, then the ratio is 1.5
    # loop through each trade and neglect first trade
    # type1: sum of profit / sum of loss
    # type2: max of profit / max of loss
    # todo: need to confirm it's correct (I implemented type2)
    # fixme: repeat calculation with step 8
    #   to make it clear, I split to write
    max_profit, max_loss = 0, 0
    # neglect 1st trade, due to no win or loss for 1st buy
    for i in range(1, total_trades):
        if df_trade['capital'].iloc[i] >= capital:
            max_profit = max(max_profit, df_trade['capital'].iloc[i] - capital)
        else:
            max_loss = max(max_profit, capital - df_trade['capital'].iloc[i])
    profit_loss_ratio = max_profit / max_loss
    log.info('Profit-Loss Ratio: %.2f' % profit_loss_ratio)

    # 10. Max Consecutive Losses (todo)

    # todo: save to the file
