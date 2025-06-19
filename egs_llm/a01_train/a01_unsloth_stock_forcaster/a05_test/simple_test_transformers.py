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

from transformers import AutoModelForCausalLM, AutoTokenizer


model_name = '/mnt/mdl/out/unsloth/Qwen3-0.6B-unsloth-bnb-4bit-merged'

# load the tokenizer and the model
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(
    model_name,
    torch_dtype="auto",
    device_map="auto"
)

# prepare the model input
prompt = """###新闻###
Date:2021-09-30, Stock:中银证券,过去五日的新闻为:
2021-09-23: nan
2021-09-24: nan
2021-09-27: NEWS1: 非银金融行业研究周报：债券“南向通”运行 央行明确虚拟货币属性.NEWS2: 中材国际：长江证券、中银证券等6家机构于9月23日调研我司.NEWS3: 券商积极备战北交所 优质项目“争夺战”悄然打响.
2021-09-28: NEWS1: 中银证券：原材料价格上涨的影响持续存在.
2021-09-29: NEWS1: 万顺新材：天风证券股份有限公司、中银国际证券股份有限公司等7家机构于9月28日调研我司.

###任务###
请根据过去五个交易日内关于该股票的新闻，预测下一个交易日该股票的涨跌，如果预测下一个交易日该股票会涨，请输出[上涨],如果预测下一个交易日该股票会跌，请输出[下跌]"""

messages = [
    {"role": "user", "content": prompt}
]
text = tokenizer.apply_chat_template(
    messages,
    tokenize=False,
    add_generation_prompt=True,
    enable_thinking=True # Switches between thinking and non-thinking modes. Default is True.
)
model_inputs = tokenizer([text], return_tensors="pt").to(model.device)

# conduct text completion
generated_ids = model.generate(
    **model_inputs,
    max_new_tokens=3500
)
output_ids = generated_ids[0][len(model_inputs.input_ids[0]):].tolist()

# parsing thinking content
try:
    # rindex finding 151668 (</think>)
    index = len(output_ids) - output_ids[::-1].index(151668)
except ValueError:
    index = 0

thinking_content = tokenizer.decode(output_ids[:index], skip_special_tokens=True).strip("\n")
content = tokenizer.decode(output_ids[index:], skip_special_tokens=True).strip("\n")

print("thinking content:", thinking_content)
print("content:", content)