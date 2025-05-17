# -*- coding: utf-8 -*-
# @Author   : liyi
# @Time     : 2025/1/1 14:36
# @File     : s1_get_data.py
# @Project  : personal_resources_gitee
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

import os
from loguru import logger
from tqdm import tqdm
from dataclasses import dataclass

from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain.prompts import PromptTemplate
from langchain_community.tools.tavily_search import TavilySearchResults


def make_dirs(*dirs):
    for i in dirs:
        if not os.path.exists(i):
            os.makedirs(i)


def clean_dirs(path: str):
    if os.path.exists(path):
        for root, dirs, files in os.walk(path, topdown=False):
            # remove files first
            for name in files:
                os.remove(os.path.join(root, name))
            # remove folders
            for name in dirs:
                os.rmdir(os.path.join(root, name))
        os.rmdir(path)


@dataclass
class Args:
    llm_config: dict
    topic_lst: list
    travily_api_key_path: str
    search_top_k: int
    output_path: str


PROMPT = """###角色###
你是一名金融市场分析师，请基于检索到的信息分析，并生成行情分析报告。

###参考信息###
{doc}

###分析主题###
{topic}

###任务###
请基于参考信息对主题进行分析，并撰写报告。具体要求如下：
- 回答不要提及基于哪篇参考信息；
- 前面的参考信息可能有用，也可能没用，你需要从给出的参考信息中选出与问题最相关的那些，来为回答提供依据；
- 如果参考信息中均无相关信息或者参考信息无内容，则回复目前没有检索到相关资料，无法撰写；
- 回答一定要忠于原文，简洁但不丢信息；
- 回答一定要使用中文回复；
- 以markdown格式数据，注意添加合理的分段和标题；

###撰写段落内容###
- 一句话总结{topic}当前的市场行情；
- 第一段：总结主题相关的热点消息；
- 第二段：分析行情走势；
- 第三段：总结；
"""


class Reporter:
    def __init__(self, args: Args):
        self.args = args

        # 实现网络搜索工具
        with open(args.travily_api_key_path, 'r') as file:
            api_key = file.read().replace('\n', '')

        os.environ['TAVILY_API_KEY'] = api_key
        self.web_search_tool = TavilySearchResults(k=args.search_top_k)

        # 大模型初始化
        llm_config = args.llm_config
        llm = ChatOpenAI(
            model=llm_config['llm_mdl_name'],
            openai_api_key=llm_config['llm_api_key'],
            openai_api_base=llm_config['llm_server_url'],
            max_tokens=llm_config['llm_max_tokens'],
            temperature=llm_config['llm_temperature']
        )
        prompts_report = PromptTemplate(
            template=PROMPT,
            input_variables=["doc", "topic"],
        )
        self.writer_llm = prompts_report | llm | StrOutputParser()

    def generate_report(self):
        # 使用tqdm显示进度，并提示当前处理的主题
        tot_num = len(self.args.topic_lst)
        for topic in tqdm(self.args.topic_lst, total=tot_num):
            docs = self.web_search_tool.invoke({"query": topic})
            web_results = "\n---\n".join([d["content"] for d in docs])

            ret = self.writer_llm.invoke({'doc': web_results, 'topic': topic})

            # write to output
            out_file_path = os.path.join(self.args.output_path, f'{topic}_report.md')
            with open(out_file_path, 'w', encoding='utf-8') as f:
                f.write(ret)
        logger.info(f"Report generation finished! Output path: {self.args.output_path}")


def main():
    llm_config = {
        "llm_server_url": "http://localhost:8000/v1",
        "llm_mdl_name": "Qwen2-7B-Instruct",
        "llm_api_key": "EMPTY",
        "llm_max_tokens": 6500,  # for completion
        "llm_max_input_tokens": 24500,  # for input
        "llm_temperature": 0,
        "llm_batch_size": 26,
    }
    travily_api_key_file = '/home/api_key/TavilySearchApi.txt'
    search_top_k = 10
    output_path = '/data/output'
    make_dirs(output_path)

    topic_lst = ['低空经济', '人工智能']
    args = Args(llm_config=llm_config,
                topic_lst=topic_lst,
                travily_api_key_path=travily_api_key_file,
                search_top_k=search_top_k,
                output_path=output_path)
    reporter = Reporter(args)
    reporter.generate_report()


if __name__ == '__main__':
    main()
