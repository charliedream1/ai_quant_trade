# -*- coding: utf-8 -*-
# @Author   : Yi Li (liyi_best@foxmail.com)
# @Time     : 2022/7/27 23:13
# @File     : moving_average.py
# @Project  : ai_quant_trade
# Copyright (c) Personal 2022 Yi Li
# Function Description: Moving Average Line Strategies for Time Ctrl of buying or selling
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

from typeguard import check_argument_types


def double_ma_timing(ma_short: float,
                     ma_long: float,
                     hold: bool) -> str:
    """
    :param ma_short: short moving average value
    :param ma_long: long moving average value
    :param hold: whether hold a position
    :return: trading type
    """
    assert check_argument_types()
    trade_type = ''
    if ma_short >= ma_long and not hold:
        trade_type = 'buy'
    elif ma_short < ma_long and hold:
        trade_type = 'sell'
    return trade_type
