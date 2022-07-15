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
def cal_risk_indicator(capital_list: list, metrics_save_path: str):
    capital_series = pd.Series(capital_list)
    # calculate simple rate of return
    capital_returns = ffn.to_returns(capital_series)
    # calculate total rate of return
    log.info('Total Return Rate: %.2f' % ffn.calc_total_return(capital_series))
    # calculate max withdraw
    log.info('Max Withdraw: %.2f' % ffn.calc_max_drawdown(capital_series))
    # calculate sharp rate
    log.info('Sharp Rate: %.2f' % ffn.calc_sharpe(capital_returns))

    # todo: save to the file
