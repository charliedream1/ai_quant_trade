# -*- coding: utf-8 -*-
# @Author   : liyi
# @Time     : 2022/11/2 8:26
# @File     : account_login.py
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
from WindPy import w

from tools.log.log_util import addlog, log


def logon_wind():
    start_ret = w.start()

    if start_ret.ErrorCode != 0:
        log.info("Start failed")
        log.info("Error Code:" + str(start_ret.ErrorCode))
        log.info("Error Message:" + start_ret.Data[0])


def logon_account(account_file_path: str, market_type: str):
    # 1. get simulation account
    if not os.path.exists(account_file_path):
        log.error('Error: account file path not exist!!!')
        raise FileNotFoundError

    with open(account_file_path, 'r') as fp:
        account = fp.readline()
        if not len(account):
            log.error('Error: account file without contents !!!')
            raise LookupError
        account = account.strip()

    # 2. logon wind simulation account
    # 参数： BrokerID (模拟用户设000)，DepartmentID（模拟用户设0），LogonAccount（开户账号），
    #       Password（模拟交易为任意值），AccountType
    #       账户的市场类型，SHSZ：深圳上海A，CZC：郑商所，SHF：上期所，DCE：大商所，CFE：中金所，
    #       SHO：上证期权，HK：港股
    wind_login = w.tlogon('0000', '0', account, '*', market_type)
    if wind_login.ErrorCode != 0:
        log.info("Simulation Account Login failed")
        log.info("Error Code:" + str(wind_login.ErrorCode))
    log_id = wind_login.Data[0][0]  # 2nd 0 is to get first account id

    return log_id
