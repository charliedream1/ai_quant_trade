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

import pandas as pd
from tqdm import tqdm
from loguru import logger


def convert_format(in_file_path):
    data_lst = []
    df = pd.read_parquet(in_file_path, engine="pyarrow")
    for idx, row in tqdm(df.iterrows(), total=len(df)):
        prompt = row['prompt']
        sys_msg, instruction = prompt.split('<</SYS>>')
        sys_msg = sys_msg.replace('[INST]<<SYS>>', '').strip()
        instruction = instruction.replace('[/INST]', '').strip()
        answer = row['answer']
        label = row['label']
        dialog = {
            "conversations": [
                {"role": "system", "content": sys_msg},
                {"role": "user", "content": instruction},
                {"role": "assistant", "content": answer},
            ]
        }
        data_lst.append(dialog)

    output_filepath = in_file_path.replace('.parquet', '_converted.jsonl')
    df_out = pd.DataFrame(data_lst)
    df_out.to_json(output_filepath, orient='records', lines=True, force_ascii=False)
    logger.info(f"Converted data saved to {output_filepath}")


def main():
    file_path = '/mnt/data/fingpt-forecaster-sz50-20230201-20240101/data/train-00000-of-00001-a2aad981aad5c8d4.parquet'
    # file_path = '/mnt/data/fingpt-forecaster-dow30-202305-202405/data/train-00000-of-00001-7c4c80aa07272d4c.parquet'
    convert_format(file_path)


if __name__ == '__main__':
    main()
