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
import sys
import pandas as pd
from tqdm import tqdm
from loguru import logger
from transformers import AutoModelForCausalLM, AutoTokenizer

path = os.getcwd()
sys.path.append(os.path.abspath(path + ('/..' * 3)))

from src.tools.file_io.make_nd_clean_dirs import make_dirs, clean_dirs


class Evaluator:
    def __init__(self, mdl_path):
        # load the tokenizer and the model
        self.tokenizer = AutoTokenizer.from_pretrained(mdl_path)
        self.model = AutoModelForCausalLM.from_pretrained(
            mdl_path,
            torch_dtype="auto",
            device_map="auto"
        )

    def mdl_infer(self, messages_batch):
        # 1. 预处理
        texts = self.tokenizer.apply_chat_template(
            messages_batch,
            tokenize = False,
            add_generation_prompt = True, # Must add for generation
            enable_thinking = True, # Disable thinking
        )

        # 2. 编码并生成 attention_mask
        self.tokenizer.padding_side = "left"
        inputs = self.tokenizer(
            texts,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=32768,
            add_special_tokens=True
        ).to("cuda")

        # 记录每条 prompt 的真实长度（非 pad 部分），用于后面分割生成结果
        #    attention_mask 为 1 的位置就是实际输入
        attention_mask = inputs.attention_mask  # (batch_size, seq_len)
        orig_lengths = attention_mask.sum(dim=1).tolist()  # list of ints, length=batch_size

        # 3. 批量生成（显式传递 attention_mask）
        output_ids = self.model.generate(
            input_ids=inputs["input_ids"],
            attention_mask=inputs["attention_mask"],
            eos_token_id=self.tokenizer.eos_token_id,
            pad_token_id=self.tokenizer.pad_token_id,
            max_new_tokens=3500,
            temperature=0.7,
            top_p=0.8,
            top_k=20,
            early_stopping=True,
        )

        # 4. 解码
        # 4.1 先把每条输出剪出新增的 token id 列表，放入一个 list
        seq_len = inputs["input_ids"].shape[1]

        gen_id_lists = [
            output_ids[seq_len:].tolist()  # 从原输入的末尾开始截，新生成的都在后面
            for output_ids in output_ids
        ]

        # 4.2 一次性 batch_decode
        #    skip_special_tokens=True 会把 eos、pad 之类的 token 都过滤掉
        decoded_texts = self.tokenizer.batch_decode(
            gen_id_lists,
            skip_special_tokens=True,
            clean_up_tokenization_spaces=True
        )

        # 4.3 如果还想 strip 掉首尾空白：
        decoded_texts = [t.strip() for t in decoded_texts]

        # 5. parse result
        judge_outputs = []
        for out in decoded_texts:
            if '</think>' in out:
                ret_process = out.split('</think>')[-1].strip()
            else:
                ret_process = out.split()[-1]
            if '上涨' in ret_process:
                final_ret = '[上涨]'
            elif '下跌' in ret_process:
                final_ret = '[下跌]'
            else:
                final_ret = ''
                logger.info(f'Unknown Ret: {out}')
            judge_outputs.append(final_ret)
        return decoded_texts, judge_outputs

    def evaluate(self, test_set_path, save_file_path, batch_size, test_num):
        df = pd.read_csv(test_set_path)
        if test_num > 0:
            logger.info(f"Randomly sampling {test_num} examples.")
            df = df.sample(test_num, random_state=3407)
            df = df.reset_index(drop=True)

        # 增加一列 predict
        df['predict'] = ''
        df['predict_ori'] = ''
        df['correct'] = 0
        unknown_cnt = 0

        batch, batch_meta = [], []
        deepseek_correct_num = 0
        processed = 0
        tot_num = len(df)
        pbar = tqdm(total=tot_num, desc=f"Computing Accuracy")
        for idx, row in df.iterrows():
            instruction = row['instruction']
            inputs = row['input']
            output = row['output']
            deepseek_out = row['deepseek_r1_answers']
            if output in deepseek_out:
                deepseek_correct_num += 1

            dialog = [
                {"role": "user", "content": '###新闻###\n' + inputs +
                                            '\n\n###任务###\n' + instruction},
            ]
            batch.append(dialog)
            batch_meta.append({'original_idx': idx, 'ref': output})

            if len(batch) == batch_size or idx == tot_num - 1:
                # 1. mdl_infer
                outputs, judge_outputs = self.mdl_infer(batch)
                # 2. parse result
                for i, sub_out, sub_judge_out in zip(range(len(outputs)), outputs, judge_outputs):
                    if sub_judge_out == '':
                        unknown_cnt += 1
                    processed += 1

                    original_idx = batch_meta[i]['original_idx']
                    ori_ref = batch_meta[i]['ref']

                    df.at[original_idx, 'predict_ori'] = sub_out
                    df.at[original_idx, 'predict'] = sub_judge_out
                    if ori_ref in sub_judge_out:
                        df.at[original_idx, 'correct'] = 1

                # 3. 统计准确率
                avg = df['correct'].sum() / processed
                pbar.set_postfix({f"avg_acc": f"{avg:.2%}"})
                pbar.update(len(batch))

                batch = []
                batch_meta = []

        pbar.close()

        # 统计准确率
        deepseek_accuracy = deepseek_correct_num / processed
        logger.info(f"Deepseek Total: {processed}, Deepseek Correct: {deepseek_correct_num}, "
                    f"Deepseek Accuracy: {deepseek_accuracy:.2%}")

        correct = df['correct'].sum()
        accuracy = correct / processed
        logger.info(f"Total: {processed}, Correct: {correct}, Accuracy: {accuracy:.2%}")
        logger.info(f"Unknown Count: {unknown_cnt}")
        # 保存结果
        df.to_csv(save_file_path, index=False, encoding='utf-8')
        logger.info(f"Results saved to {save_file_path}")


def main():
    # mdl_path = '/mnt/mdl/mdl_zoo/unsloth/Qwen3-0.6B-unsloth-bnb-4bit'
    mdl_path = '/mnt/mdl/mdl_zoo/unsloth/Qwen3-8B-unsloth-bnb-4bit'
    # mdl_path = '/mnt/mdl/out/unsloth/Qwen3-0.6B-unsloth-bnb-4bit-merged'
    # mdl_path = '/mnt/mdl/out/unsloth/Qwen3-8B-unsloth-bnb-16bit-merged'

    work_path = '/mnt'
    test_data_path = os.path.join(work_path, 'data/Finance-R1-Reasoning', 'test.csv')

    save_dir = os.path.join(work_path, 'evaluate', 'finance_r1_reasoning')
    make_dirs(save_dir)
    out_file_path = os.path.join(save_dir, 'test_result.csv')
    batch_size = 4  # 0.6B: 8, 8B: 4
    test_num = 500  # -1 means all

    evaluator = Evaluator(mdl_path)
    evaluator.evaluate(test_data_path, out_file_path, batch_size, test_num)


if __name__ == '__main__':
    main()
