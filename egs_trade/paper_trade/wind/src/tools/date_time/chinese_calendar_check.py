# -*- coding: utf-8 -*-
# @Author   : liyi
# @Time     : 2022/11/4 8:30
# @File     : chinese_calendar_check.py
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

import datetime

import chinese_calendar as calendar
from chinese_calendar import is_workday, is_holiday


def is_workdays(date):
    request_date = datetime.date(date.year, date.month, date.day)
    return is_workday(request_date)


def is_holidays(date):
    request_date = datetime.date(date.year, date.month, date.day)
    return is_holiday(request_date)


def is_festival(date):
    request_date = datetime.date(date.year, date.month, date.day)
    on_holiday, holiday_name = calendar.get_holiday_detail(request_date)
    return on_holiday, holiday_name


if __name__ == "__main__":
    today = datetime.datetime.now()
    week = is_workdays(today)
    holiday = is_holidays(today)
    festival = is_festival(today)
    print("week-{}".format(week))
    print("holiday-{}".format(holiday))
    print("festival-{}-{}".format(festival[0], festival[1]))
