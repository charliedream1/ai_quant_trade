# -*- coding: utf-8 -*-
# @Author   : liyi
# @Time     : 2022/11/2 8:14
# @File     : utils.py
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

from WindPy import w

from tools.log.log_util import addlog, log


def parse_val(in_data: w.WindData, query_fields_lst: list) -> dict:
    ret_dict = {}
    for item in query_fields_lst:
        ret_dict[item] = 0.0

    for k in range(0, len(in_data.Fields)):
        for item in query_fields_lst:
            if in_data.Fields[k] == item:
                ret_dict[item] = in_data.Data[k][0]
    return ret_dict


def my_callback(self, in_data: w.WindData):
    """Callback function for WSQ

    params
    ------
    indata: WindData, accepts the received market quotation data. WindData has the following fields:
              .ErrorCode: error code, if it is 0, the code runs successfully
              .StateCode: state code. No need to process it.
              .RequestID: save the request ID of WSQ request
              .Codes: wind code of the securities
              .Fields: fields for the received data
              .Times: local time rather than the corresponding time for the recieved data
              .Data: market quotation data
    """
    log.info(in_data)
    if in_data.ErrorCode != 0:
        log.info('error code:' + str(in_data.ErrorCode) + '\n')
        return ()

    # rt_last, rt_ma_5d, rt_ma_20d = self.parse_val(in_data)
    # string = str(rt_last) + ' ' + str(rt_ma_5d) + ' ' + str(rt_ma_20d)
    # log.info(string)
