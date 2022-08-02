# -*- coding: utf-8 -*-
# @Author   : Yi Li (liyi_best@foxmail.com)
# @Time     : 2022/7/27 22:51
# @File     : capital_allocation.py
# @Project  : ai_quant_trade
# Copyright (c) Personal 2022 Yi Li
# Function Description: Methods of how to allocate funds
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

from quant_brain.back_test.account_info import Account
from tools.log.log_util import addlog, log


@addlog(name='equal_allocation')
def equal_allocation(account_info: Account,
                     select_num: int,
                     ) -> float:
    """
    :param account_info: available cash in account
    :param select_num: number of stock to buy
    :return: allocate capital to buy stock
    """
    pos_num = len(account_info.pos_dict.keys())
    if pos_num < select_num:
        num = select_num - pos_num
        cash = account_info.cash / num
    else:
        cash = 0
    return cash


class FundsAllocator:
    def __init__(self):
        pass

