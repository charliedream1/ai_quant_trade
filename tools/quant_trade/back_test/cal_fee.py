# -*- coding: utf-8 -*-
# @Author   : liyi (liyi_best@foxmail.com)
# @Time     : 2022/7/8 22:19
# @File     : cal_fee.py
# @Project  : ai_quant_trade
# Copyright (c) Personal 2022 liyi
# Function Description: calculation of fee during sell or buy
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

from random import choice


def calculate_fee(price: float, pos_num: int,
                  order_cost: dict, trade_type: str) -> float:
    """
    :param price: price of stock during the trading time
    :param pos_num: stock hold number
    :param order_cost: dict of every type of cost
    :param trade_type: buy or sell
    :return: trading fee
    """
    if trade_type == 'buy':
        com_fee = order_cost['open_commission'] * pos_num
        if com_fee < order_cost['min_commission']:
            com_fee = order_cost['min_commission']
        tax_fee = 0.0
    else:
        com_fee = order_cost['close_commission'] * pos_num
        tax_fee = order_cost['close_tax'] * price * pos_num

        if com_fee < order_cost['min_commission']:
            com_fee = order_cost['min_commission']

    # fixme: according to book and internet,
    #  buy slippage fee = price * (slippage rate)
    #  sell slippage fee = price * (-slippage rate)
    #  however, I think the sign of pos and neg could be random
    # options = [-1, 1]
    # choice_sign = choice(options)
    # slippage_fee = choice_sign * order_cost['slippage_fee'] * price * pos_num
    slippage_fee = 0.0

    total_fee = slippage_fee + com_fee + tax_fee
    return total_fee
