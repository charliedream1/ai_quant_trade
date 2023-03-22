# -*- coding: utf-8 -*-
# @Author   : liyi
# @Time     : 2023/3/20 21:45
# @File     : combine_data.py
# @Project  : ai_quant_trade
# Copyright (c) Personal 2022 liyi
# Function Description: Merge two csv into one
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


# due to the original github not provide full dataset csv and there's downloading
#   problem in China with 1_Data.ipynb, I combine the train_data.csv and
#   trade_data.csv into this full_data.csv to be used in 3_Backtest.ipynb
def concat_csv(train_csv, trade_csv, out_csv):
    with open(train_csv, 'r') as fp:
        train_text_lst = fp.readlines()
        last_line = train_text_lst[-1]
        lst_idx = int(last_line.split(',', 1)[0])

    with open(trade_csv, 'r') as fp:
        trade_text_lst = fp.readlines()
        for i in range(1, len(trade_text_lst)):
            idx = int(trade_text_lst[i].split(',', 1)[0])
            line = trade_text_lst[i].split(',', 1)[1]
            new_line = str(lst_idx + idx + 1) + ',' + line
            train_text_lst.append(new_line)

    with open(out_csv, 'w') as fp:
        fp.writelines(train_text_lst)


def main():
    train_csv = os.path.join(os.getcwd(), 'train_data.csv')
    trade_csv = os.path.join(os.getcwd(), 'trade_data.csv')
    out_csv = os.path.join(os.getcwd(), 'full_data.csv')
    concat_csv(train_csv, trade_csv, out_csv)


if __name__ == '__main__':
    main()
