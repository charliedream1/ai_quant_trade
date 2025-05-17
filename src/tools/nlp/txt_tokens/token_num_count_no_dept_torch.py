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
from loguru import logger
from typing import Optional, List, Tuple, Any
from tokenizers import Tokenizer

TOKEN_MDL_PATH = os.path.join(os.path.dirname(__file__), 'tokenizer.json')


class TokenCounter:
    def __init__(self):
        self.tokenizer =  Tokenizer.from_file(TOKEN_MDL_PATH)
        self.token_model_name = os.path.basename(TOKEN_MDL_PATH)
        pass

    def token_num_count(self, text: str):
        encoding = self.tokenizer.encode(text, add_special_tokens=True)
        return len(encoding.ids)

    def text_to_tokens_and_back(self, text, max_length):
        # 将文本转换为 tokens
        tokens = self.tokenizer.encode(text, add_special_tokens=True)
        token_num = len(tokens.ids)

        # 截断 tokens 如果超过最大长度
        if token_num > max_length:
            logger.warning(f'Input token exceed max input: {token_num} > {max_length}')
            token_ids = tokens.ids[:max_length]
            # 将 tokens 转换回文本
            decoded_text = self.tokenizer.decode(token_ids, skip_special_tokens=True)
        else:
            decoded_text = text
        return token_num, decoded_text


def main():
    token_counter = TokenCounter()
    text = "This is an example of a very long text that might need to be truncated if it exceeds the maximum length."
    token_num = token_counter.token_num_count(text)
    print('Token Num: ', token_num)

    tokens, decoded_text = token_counter.text_to_tokens_and_back(text, max_length=5)
    print("Tokens:", tokens)
    print("Decoded Text:", decoded_text)


if __name__ == "__main__":
    main()
