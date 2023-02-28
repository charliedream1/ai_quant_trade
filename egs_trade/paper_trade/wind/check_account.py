# -*- coding: utf-8 -*-
# @Author   : liyi
# @Time     : 2022/11/7 22:58
# @File     : check_account.py
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
import sys

path = os.getcwd()
sys.path.append(os.path.abspath(path + ('/..' * 3)))

from quant_brain.data_io.wind.account_login import logon_wind, logon_account
from quant_brain.data_io.wind.query_rt_data import get_funds, check_account_info


def quick_check_account(account_file_path, market_type):
    logon_wind()
    account, log_id = logon_account(account_file_path, market_type)
    check_account_info(log_id)


def main():
    account_file_path = r''
    market_type = 'SHSZ'
    quick_check_account(account_file_path, market_type)


if __name__ == '__main__':
    main()
