# -*- coding: utf-8 -*-
# @Author   : liyi
# @Time     : 2022/12/2 22:42
# @File     : fold_excel_rows.py
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

"""
Fold very long rows with more columns but shorter rows, easy for print out on paper

From
证券代码	证券简称
300001.SZ	特锐德
300002.SZ	神州泰岳

to
证券代码	证券简称       证券代码	证券简称      证券代码	证券简称
300001.SZ	特锐德    300002.SZ	神州泰岳       300002.SZ	神州泰岳

"""

import os
import pandas as pd
import math


def parse_files(in_file, out_file, row_num=48, col_num=3, sheet_name='Sheet1'):
    df = pd.read_excel(in_file, sheet_name=sheet_name)
    lines_lst = []
    line = ''
    file_cnt, row_cnt = 0, 0

    for tup in zip(df['证券代码'], df['证券简称']):
        if isinstance(tup[0], float) or isinstance(tup[1], float):
            continue

        row_cnt += 1
        line += tup[0] + ',' + tup[1] + ','
        if row_cnt > 0 and row_cnt % col_num == 0:
            lines_lst.append(line + '\n')
            line = ''

        # once reach row num, save to a new file
        act_row_cnt = row_cnt / col_num
        if (act_row_cnt % row_num == 0) and len(lines_lst):
            # df_out = pd.DataFrame(lines_lst)
            # df_out.to_excel(out_file, sheet_name=("Sheet" + str(file_cnt)))
            # new_out_name = os.path.splitext(out_file)[0] + '_' + str(file_cnt) + os.path.splitext(out_file)[1]
            new_out_name = os.path.splitext(out_file)[0] + '_' + str(file_cnt) + '.csv'
            with open(new_out_name, 'w') as fp:
                fp.writelines(lines_lst)
                lines_lst = []
            file_cnt += 1

    # put rest into file
    if len(line):
        lines_lst.append(line + '\n')

    if len(lines_lst):
        new_out_name = os.path.splitext(out_file)[0] + '_' + str(file_cnt) + '.csv'
        with open(new_out_name, 'w') as fp:
            fp.writelines(lines_lst)


def main():
    # todo: the style in saved file can't be edit in WPS or Excel, better to save with pandas
    #  or other excel processing tools
    work_path = r''
    in_dir = os.path.join(work_path, '111')
    out_dir = os.path.join(work_path, 'out')
    row_num = 48
    col_num = 3
    sheet_name = 'Sheet1'  # 输入原始excel需要读取的sheet的名称

    if not os.path.exists(out_dir):
        os.mkdir(out_dir)

    # loop files to process
    for file_path, dir_names, file_names in os.walk(in_dir):
        for filename in file_names:
            full_path = os.path.join(file_path, filename)
            out_file_path = os.path.join(out_dir, filename)
            print('Processing: ' + full_path)
            parse_files(full_path, out_file_path,
                        row_num=row_num, col_num=col_num, sheet_name=sheet_name)
    print('Complete')


if __name__ == '__main__':
    main()
