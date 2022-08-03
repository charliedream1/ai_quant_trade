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

import os
import ffn
import pandas as pd

from tools.log.log_util import addlog, log


@addlog(name='cal_risk_indicator')
def cal_risk_indicator(capital: float,
                       base_rise: float,
                       capital_list: list,
                       df_trade: pd.DataFrame(),
                       df_index: pd.DataFrame(),
                       metrics_save_path: str):
    """
    :param capital: initial money you have for stock trading
    :param base_rise: e.g. Bank Deposit Rate, risk-free interest rate
    :param capital_list: capital changing list during trading period
    :param df_trade: detailed trading info dataframe
    :param df_index: benchmark of market index
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
    indicator_dict['total_returns'] = total_returns
    log.info('Total Return Rate: %.5f' % total_returns)

    # 2. Total Annal Return
    # ((1+P)^(250/n) - 1) * 100%, P is capital returns
    # different from annual return if trading time less than a year
    # due to its not the real annual return, it's a converted value
    # 250 is the trading days in one year
    annal_returns = ffn.annualize(total_returns,
                                  len(capital_list), one_year=250)
    indicator_dict['annal_returns'] = annal_returns
    log.info('Annual Return Rate: %.5f' % annal_returns)

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
    # todo: due to index data not available from tushare api without pay
    if len(df_index):
        strategy_pct_chg = capital_series.pct_change()
        strategy_pct_chg.fillna(0)
        cov = strategy_pct_chg.cov(df_index['pct_chg'])
        sigma = strategy_pct_chg.cov(df_index['pct_chg'])
        # Another Solution: np.cov(s1, s2))[0][1]/np.var(s2)
        beta = cov / sigma
        indicator_dict['beta'] = beta
        log.info('Beta Value: %.5f' % beta)

        df_index.loc[:, 'pct_chg'] /= 100
        df_index.loc[:, 'pct_chg'] += 1
        strategy_pct_chg /= 100
        strategy_pct_chg += 1
        sign_rise = df_index['pct_chg'].prod(axis=0) - 1
        rise = strategy_pct_chg.prod(axis=0) - 1

    # 4. Alpha
    # alpha is non-system risk. It represents returns which has no
    #  relationship with market fluctuation. E.g., if strategy return
    #  is 20%, benchmark return is 10%, the alpha is 10%.
    #  Alpha = Rp - [Rf + Beta * (Rm - Rf)]
    #  Rp: strategy annual returns, Rm benchmark returns,
    #  Beta: bata ratio is the one calculated above in 3
    #  Rf is risk-free interest rate, can be easily thought as
    #    Bank Deposit Rate, usually set as 0.04
    # todo: due to index data not available from tushare api without pay
    if len(df_index):
        alpha = rise - (base_rise + beta * (sign_rise - base_rise))
        indicator_dict['alpha'] = alpha
        log.info('Alpha Value: %.5f' % alpha)

    # 5. calculate sharp rate
    # used to evaluate every one risk u take, the non-risk returns
    # the larger value is, the more returns while more risk u take, vice versa
    # usually, the larger value is, the better
    # Sharp Ratio = (Rp - Rf) / Op
    # Rp: annual return, Rf: no-risk interest rate, Op: changing rate of the strategy
    sharp_ratio = ffn.calc_sharpe(capital_returns)
    indicator_dict['sharp_ratio'] = sharp_ratio
    log.info('Sharp Rate: %.5f' % sharp_ratio)

    # 6. calculate max withdraw
    # evaluate max loss of the strategy, the smaller the value the better
    # max_draw_down = (Px-Py)/Px, (Px, PY: max value during a time)
    max_withdraw = ffn.calc_max_drawdown(capital_series)
    indicator_dict['max_withdraw'] = max_withdraw
    log.info('Max Withdraw: %.5f' % max_withdraw)

    # 7. Sortino Ratio
    # evaluate strategy loss, the larger value the better
    # Sharp Ratio = (Rp - Rf) / Od
    # Rp: annual return, Rf: no-risk interest rate, Od: strategy downward volatility
    sortino_ratio = ffn.calc_sortino_ratio(capital_returns)
    indicator_dict['sortino_ratio'] = sortino_ratio
    log.info('Sortino Rate: %.5f' % sortino_ratio)

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
    indicator_dict['win_rate'] = win_rate
    log.info('Win Rate: %.5f' % win_rate)

    # 9. profit-loss ratio
    # during a time period of trading, if profit is 12000,
    # loss is 8000, then the ratio is 1.5
    # loop through each trade and neglect first trade
    # type1: sum of profit / sum of loss
    # type2: max of profit / max of loss
    # todo: need to confirm it's correct (I implemented type2)
    # fixme: repeat calculation with step 8
    #   to make it clear, I split to write
    max_profit, max_loss = 0, 1.0e-10  # 1.0e-10 to avoid divide by zero
    # neglect 1st trade, due to no win or loss for 1st buy
    for i in range(1, total_trades):
        if df_trade['capital'].iloc[i] >= capital:
            max_profit = max(max_profit, df_trade['capital'].iloc[i] - capital)
        else:
            max_loss = max(max_loss, capital - df_trade['capital'].iloc[i])
    profit_loss_ratio = max_profit / max_loss
    indicator_dict['profit_loss_ratio'] = profit_loss_ratio
    log.info('Profit-Loss Ratio: %.5f' % profit_loss_ratio)

    # 10. Max Consecutive Losses (todo)
    max_con_losses, cur_con_losses, pre_loss = 0, 0, 0
    pre_flag = False
    # neglect 1st trade, due to no win or loss for 1st buy
    for i in range(1, total_trades):
        if df_trade['capital'].iloc[i] < capital:
            if df_trade['capital'].iloc[i] < df_trade['capital'].iloc[i-1]:
                loss = capital - df_trade['capital'].iloc[i]
                if pre_flag:
                    cur_con_losses += loss + pre_loss
                    max_con_losses = max(max_con_losses, cur_con_losses)
                    pre_loss = 0
                else:
                    max_con_losses = max(max_con_losses, loss)
                    cur_con_losses = 0
                    pre_loss = loss

                pre_flag = True
                continue

        pre_flag = False
        cur_con_losses = 0
        pre_loss = 0

    indicator_dict['max_con_losses'] = max_con_losses
    log.info('Max Consecutive Losses: %.5f' % max_con_losses)

    # === save to the file ===
    # 1. save risk indicator
    df_result = pd.DataFrame(data=indicator_dict.values(),
                             index=indicator_dict.keys())
    save_path = os.path.join(metrics_save_path, 'risk_indicator.csv')
    df_result.to_csv(save_path)

    # 2. save trading info
    save_path = os.path.join(metrics_save_path, 'trading_info.csv')
    df_trade.to_csv(save_path)
