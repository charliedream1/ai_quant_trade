# -*- coding: utf-8 -*-
# @Author   : Yi Li (liyi_best@foxmail.com)
# @Time     : 2022/7/28 7:31
# @File     : trading_ctrl.py
# @Project  : ai_quant_trade
# Copyright (c) Personal 2022 Yi Li
# Function Description: Simulate Trading to calculate funds changing
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

from typing import Tuple
from typeguard import check_argument_types
import pandas as pd

from quant_brain.back_test.account_info import Account
from quant_brain.back_test.cal_fee import calculate_fee
from tools.log.log_util import addlog, log


@addlog(name='order_value')
def order_value(account: Account,
                stock_id: str,
                price_dict: pd.Series,
                trade_type: str,
                order_funds: float,
                order_cost: dict,
                ) -> Tuple[str, int, str]:
    """
    :param account: account info class
    :param stock_id: stock id to process
    :param price_dict: include high, low close of the day
    :param trade_type: buy or sell
    :param order_funds: funds to buy
    :param order_cost: values to calculate trading fees
    :return:
        order_type: actual order type
        pos: position number
        message: trading detailed message
    """
    # NOTICE: account will be used as a reference,
    #   value will be changed in this func will be effect at global level
    assert check_argument_types()

    hold = True if stock_id in account.pos_dict.keys() else False
    price = price_dict['close']
    funds_chg = 0
    order_type = ''
    pos = 0
    trade_lim = order_cost['trade_lim']

    # todo: stock have chance to reach limit,
    #  and the trade might have chance of fail
    if trade_type == 'buy' and not hold:
        # calculate purchase number, 1 buy = 100 shares
        # minimum subscribe for 100 shares, multiple 100 is to 1 buy
        pos = int(order_funds / price / trade_lim) * trade_lim

        # extra fee calculation
        fee = calculate_fee(price_dict, pos, order_cost, trade_type)

        # rest capital
        rest = order_funds - pos * price - fee
        if rest >= 0:
            # change account info
            account.cash = account.cash - order_funds + rest
            account.pos_dict[stock_id] = {'pos_num': pos,
                                          'price': price}
            funds_chg = -fee
            order_type = 'buy'
            hold = True
    elif trade_type == 'sell' and hold:
        pos = account.pos_dict[stock_id]['pos_num']

        # extra fee calculation
        fee = calculate_fee(price_dict, pos, order_cost, trade_type)

        # calculate capital of closing a position
        funds_chg = pos * price - fee
        account.cash += funds_chg

        account.pos_dict.pop(stock_id)
        order_type = 'sell'
        hold = False

    # update current stock market value if hold the stock
    if hold and not len(trade_type):
        account.pos_dict[stock_id]['price'] = price

    # output log
    message = ''
    if len(order_type):
        message = 'stock_id: ' + stock_id + ', ' + trade_type.upper() + \
                  ' with price: ' + str(price) + \
                  ', account cash ' + str(round(account.cash, 2))
        log.info(message)

    return order_type, pos, message
