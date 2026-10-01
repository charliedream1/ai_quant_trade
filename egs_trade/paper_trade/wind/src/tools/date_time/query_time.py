# -*- coding: utf-8 -*-
# @Author   : liyi
# @Time     : 2022/11/6 21:28
# @File     : query_time.py
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

import time


def split_hour_minutes(check_time: str):
    hour = int(check_time.split(':')[0])
    minutes = int(check_time.split(':')[1])
    return hour, minutes


def after_query_time(check_time: str) -> bool:
    ret = False
    cur_time = time.strftime('%H:%M', time.localtime())
    cur_hr, cur_minutes = split_hour_minutes(cur_time)
    check_hr, check_minutes = split_hour_minutes(check_time)
    if cur_hr > check_hr:
        ret = True
    if cur_hr == check_hr:
        if cur_minutes >= check_minutes:
            ret = True
    return ret
