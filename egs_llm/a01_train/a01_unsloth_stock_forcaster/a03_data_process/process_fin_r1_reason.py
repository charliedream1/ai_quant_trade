# -*- coding: utf-8 -*-
# @Author   : liyi
# @Time     : 2025/5/12 23:05
# @File     : edit_active_excel.py
# @Project  : main
# Copyright (c) Personal 2025 liyi
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
import json
import pandas as pd
from tqdm import tqdm
from loguru import logger


def convert_format(in_file_path, out_file_path):
    data_lst = []
    df = pd.read_csv(in_file_path)
    for idx, row in tqdm(df.iterrows(), total=len(df)):
        instruction = row['instruction']
        inputs = row['input']
        thinks = row['thinks']
        output = row['output']
        dialog = [
                {"role": "user", "content": '###新闻###\n' + inputs +
                                            '\n\n###任务###\n' + instruction},
                {"role": "assistant", "content": '<think>\n' + thinks + '\n</think>\n\n' + output},
        ]
        data_lst.append(dialog)
    logger.info(f"Total {len(data_lst)} records converted.")

    conv = {"conversations": data_lst}
    with open(out_file_path, 'w', encoding='utf-8') as f:
        json.dump(conv, f, ensure_ascii=False, indent=4)  # indent参数用于美化格式
    logger.info(f"Converted data saved to {out_file_path}")


def main():
    work_path = '/mnt/data/Finance-R1-Reasoning'
    file_path = os.path.join(work_path, 'train.csv')
    out_file_path = os.path.join(work_path, 'train_unsloth_formatted.json')
    convert_format(file_path, out_file_path)


if __name__ == '__main__':
    main()
