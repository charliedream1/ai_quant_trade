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

from unsloth import FastLanguageModel
from transformers import TextStreamer

# mdl_path = '/mnt/mdl/mdl_zoo/unsloth/Qwen3-0.6B-unsloth-bnb-4bit'
# mdl_path = '/mnt/mdl/out/unsloth/Qwen3-0.6B-unsloth-bnb-4bit-lora'
# mdl_path = '/mnt/mdl/out/unsloth/Qwen3-8B-unsloth-bnb-4bit-lora'
mdl_path = '/mnt/mdl/out/unsloth/Qwen3-0.6B-unsloth-bnb-4bit-merged'
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name = mdl_path, # YOUR MODEL YOU USED FOR TRAINING
    max_seq_length = 8076,
    load_in_4bit = True,
)

messages = [
    {
        "role" : "user", "content" : """###新闻###
Date:2021-12-20, Stock:国泰君安,过去五日的新闻为:
2021-12-13: nan
2021-12-14: NEWS1: 旨在控制整体杠杆率，券商收益互换业务再迎监管规范，对保证金管理提出四项要求.NEWS2: 掌舵21年，阎峰卸任国君国际行政总裁，在港中资券商迎首位女总裁 董监高成员变化.NEWS3: 安信证券：“20国君G5”2021年第一次债券持有人会议通过相关议案.
2021-12-15: NEWS1: 国泰君安资管首只公募FOF基金12月15日发行.NEWS2: 开市以来26家公司获调研，知名机构频现身.
2021-12-16: NEWS1: 扎根地方助推当地资本市场繁荣 国泰君安金鸡湖论坛奉上思想“盛宴”.NEWS2: 上海证券总经理杨玉成确认离职，即将奔赴百联商投，本人回应表示：属集团工作调动.NEWS3: 黑色持仓日报：期螺涨2.44%，国泰君安增持1.1万手多单.NEWS4: 证券行业2022年投资策略：权益公募产业链利润十年十倍 分部重估优质券商.NEWS5: 业内人士：2022年全市场股权激励案例或超1000家.NEWS6: 业内人士：2022年全市场股权激励案例或超1000家.NEWS7: 国泰君安君弘APP跨年新版 三箭齐发助推数字化财富管理新模式.
2021-12-17: nan

###任务###
请根据过去五个交易日内关于该股票的新闻，预测下一个交易日该股票的涨跌，如果预测下一个交易日该股票会涨，请输出[上涨],如果预测下一个交易日该股票会跌，请输出[下跌]"""
     }
]
text = tokenizer.apply_chat_template(
    messages,
    tokenize = False,
    add_generation_prompt = True, # Must add for generation
    enable_thinking = True, # Disable thinking
)
# 2* faster
FastLanguageModel.for_inference(model)

# ===============流式########################
# 不使用print，也会自动打印
ret_ids = model.generate(
    **tokenizer(text, return_tensors = "pt").to("cuda"),
    max_new_tokens = 2256, # Increase for longer outputs!
    temperature = 0.7, top_p = 0.8, top_k = 20, # For non thinking
    streamer = TextStreamer(tokenizer, skip_prompt = True),
)
# ret_ids 是 Tensor，batch_size=1 时取第一个序列并解码
ret_text_stream = tokenizer.decode(ret_ids[0], skip_special_tokens=True)

# ===============非流式########################
# 不要传 streamer 参数
# ret_ids = model.generate(
#     **tokenizer(
#         text,
#         return_tensors="pt"
#     ).to("cuda"),
#     max_new_tokens=2256,
#     temperature=0.7,
#     top_p=0.8,
#     top_k=20,
# )
#
# # ret_ids 是 Tensor，batch_size=1 时取第一个序列并解码
# ret_text = tokenizer.decode(ret_ids[0], skip_special_tokens=True)
# print(ret_text)
