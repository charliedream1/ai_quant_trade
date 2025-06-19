# 1. 资源

- 代码：✨AI股票操盘手（2.8k星）: 
  - https://github.com/charliedream1/ai_quant_trade
  - （国内镜像）https://gitee.com/charlie1/ai_quant_trade.git 
- 模型/数据/详细使用/答疑：https://t.zsxq.com/dHt9l

**声明**

本文主要以教学和知识分享为目的，方案本不能作为投资建议，投资有风险，入市需谨慎。

# 2. 核心功能简介

**核心原理**
给定新闻信息，模型给出推理性分析解释，并给出股价预测：
- 推理数据由DeepSeek-R1蒸馏得来
- 模型训练采用Unsloth-Qwen3-0.6B-bnb-4bit，通过4-bit LoRA微调得到
- 单卡8分钟完成训练

**效果**
在500个测试集上
- lora微调: 49%
- 原版Qwen3-0.6B: 47.4%
- DeepSeek-R1: 45.6%

# 3. 使用

## 3.1 目录结构

文件夹分为5个：
- a01_download_mdl: 模型下载
- a02_download_data: 数据下载
- a03_data_process: 数据处理，主要用于转化数据格式
- a04_train: 模型训练
- a05_test: 模型测试

如何使用：
- 按顺序执行每个目录中的文件
- 在每个文件夹下有对应的requirements.txt文件，安装对应的依赖包

## 3.2 数据介绍

- 数据为：IDEA-FinAI/Finance-R1-Reasoning
- 1000条训练集和1000条测试集

对话样例如下：

输入：

```text
###新闻###
新闻：Date:2021-06-28, Stock:药明康德,过去五日的新闻为:
2021-06-21: NEWS1: 药明康德(02359)：参股公司Ambrx于纽交所上市.NEWS2: 药明康德(02359)拟6000万美元认购基金SEA Fund.NEWS3: 【招商策略】美元走强美债收益率走弱，市场表现如何？——金融市场流动性与监管动态周报（0621）.NEWS4: 连年增速下滑 CRO巨头泰格掏空“家底”.NEWS5: 连年增速下滑，泰格掏空“家底”，“豪赌”投资换订单.NEWS6: 沪股通净卖出17.56亿元.NEWS7: 晚间公告｜6月21日这些公告有看头.NEWS8: 北向资金净卖出20.09亿元 药明康德净卖出4.69亿元.NEWS9: 北上资金净卖出20.1亿元药明康德遭净卖出4.69亿元.NEWS10: 北向资金连续2日净卖出，继续抛售医药生物和白酒股.NEWS11: 【港股通】药明康德(02359)参投公司Ambrx Biopharma于美国上市.NEWS12: 药明康德(603259.SH)：参股公司Ambrx登陆纽交所.NEWS13: 药明康德：参股公司Ambrx在纽约证券交易所挂牌上市.NEWS14: 药明康德：参股公司Ambrx在纽交所挂牌上市公司持有11.1%股份.NEWS15: 药明康德：参股公司Ambrx Biopharma在美国纽约证券交易所挂牌上市.NEWS16: 富国中证医药50ETF一季报：股票仓位为97.60%，重仓迈瑞医疗、药明康德等.NEWS17: 【重磅】粤开医药|2021年中期策略及下半年展望：长坡厚雪，后发先至.NEWS18: A股收盘综述：军工、科技热度不减，权重股继续低迷.NEWS19: 金融监管政策周报（6.15-6.20）：进一步明确IPO股东穿透核查要求.NEWS20: 突然反转！外资大举减仓超50亿，终止连续9周抢筹！.NEWS21: 【开源医药】行业周报：持续看好康复行业和创新药产业链.NEWS22: 医药生物行业周报：医疗服务会是下半年医药最强音么？强调重视康复医疗赛道.NEWS23: 新冠疫苗成功了，mRNA疫苗的未来会是？.NEWS24: 明日下午3点！从原子水平看清细节，蛋白质晶体学如何助力新药研发.NEWS25: 一封得罪 14 万股民的道歉信.NEWS26: 上市公司股东偷偷减持该罚 减持股份.
2021-06-22: NEWS1: 上海瀛翊违规减持29亿背后：尚有三大谜团待解！新证券法背景下该怎么罚怎么赔？ 减持股份.NEWS2: 中药龙头比茅台多涨16倍！看A股优质稀缺龙头30强.NEWS3: 药明康德(02359)根据可转换债券发行164.77万股H股.NEWS4: 《2020年度药品审评报告》解读：药品审评审批“速”“质”提升 全面利好医药行业发展.NEWS5: 医药板块持续反弹，资金盯上这些股，疫苗等细分赛道值得关注.NEWS6: 【首发】Insilico Medicine获2.55亿美元C轮融资，将用于推进项目进展并进一步强化研发能力.NEWS7: 药明康德现1笔大宗交易 共成交1,882.49万元.NEWS8: 药明康德参股公司Ambrx在纽交所挂牌上市 已被复兴、厚朴投资收购.NEWS9: 市场流动性跟踪周报：北向资金近两月首现净流出.NEWS10: 药明康德今日大宗交易成交12.78万股，成交价147.3元折价3.0%.NEWS11: 北向资金近两月首现净流出【流动性跟踪第18期】.NEWS12: 北向资金连续3日净卖出，贵州茅台遭净卖出近8亿元.NEWS13: 国盛策略：上周北上资金转为流出 电子、机械设备和计算机行业获集中加仓.NEWS14: 【国盛策略｜陆股通周监控】外围波动抬升，北上转为流出*第88期.NEWS15: 金融市场流动性与监管动态周报：美元走强美债收益率走弱 市场表现如何？.NEWS16: 医药行业2021年半年报业绩前瞻：CXO、生物制品、创新器械、医疗服务有望持续高增长.NEWS17: 药明康德6000万美元认购基金 专注东南亚医疗投资.NEWS18: 医药行业周报：关注国产色谱填料领军企业纳微科技.NEWS19: 上海瀛翊违规减持29亿背后：疑曾被列入经营异常名单，GP江苏瑞联副总担任药明康德旗下私募执行董事 减持股份.NEWS20: 科技股受宠！北向资金增持软件服务，大幅加仓这只苹果概念股.NEWS21: 上海瀛翊违规减持药明康德三大“谜团”待解：真实违规动机究竟为何？幕后操盘者是谁？和药明康德有无关联？ 减持股份.NEWS22: 北向资金动向盘点：有一种坚定看好叫做小幅净卖出.NEWS23: 速递 | RNAi治疗痛风，7亿美元合作开发创新治疗模式.NEWS24: 用数字技术让违规减持成为不可能.
2021-06-23: NEWS1: 新牛股诞生！纳微科技上市首日涨12倍，中一签能赚超5万.NEWS2: 基因细胞治疗CDMO：新兴赛道 蓬勃发展.NEWS3: 晚间重要公告2021年6月23日星期三.NEWS4: “中考”要交卷了！百亿基金业绩大曝光.NEWS5: 数据复盘｜电子、汽车等7个行业获主力资金青睐 北向资金抢筹药明康德等股.NEWS6: 北向资金 | 合计净流入81.99亿元，药明康德、美的集团、韦尔股份净买入居前.NEWS7: 最牛新股纳微科技首日暴涨1400%：有何来头？高瓴、红杉嗨翻了.NEWS8: 北向资金今日净流入81.99亿元，加仓药明康德近8亿元.NEWS9: 北上资金大幅净买入81.98亿元药明康德获净买入7.95亿元.NEWS10: 北向资金近82亿资金大幅加码A股，药明康德净买入近8亿元.NEWS11: 科创板最牛新股诞生，纳微科技上市首日暴涨1274%，机构纷纷看好.NEWS12: 药明康德(603259.SH)：参股公司纳微科技登陆科创板.NEWS13: 药明康德(603259.SH)参股公司纳微科技于6月23日上交所科创板挂牌上市.NEWS14: 药明康德：参股公司纳微科技在科创板挂牌上市.NEWS15: 上市首日暴涨1400%，这只科创板新股"封神"，有何来头？高瓴、红杉赚嗨了，打破国外垄断？.NEWS16: 最强新股一天涨14倍！李佳琦、薇娅公司也要上市？回应来了.NEWS17: 啥情况？千亿白马跌超10%！外资加仓，半导体又火了.NEWS18: 纳微科技暴涨1127%！科创板史上最牛新股诞生.NEWS19: 暴涨1127%！科创板史上最牛新股诞生，打破“卡脖子”困局，高瓴、红杉和4000亿巨头赚翻了.NEWS20: AI药物研发公司InsilicoMedicine获2.55亿美元C轮融资.NEWS21: 医药股在香港集体爆发 行业多重利好催化审评审批效率提速.NEWS22: 【行情】港股生物技术板块普涨，金斯瑞生物涨超5%，药明康德涨近3%，再鼎医药涨近2%.NEWS23: 2021年医药行业政策系列：MAH(药品上市许可持有人)制度红利释放 引燃医药产业创新热情.NEWS24: 药明康德6月22日现1笔大宗交易.NEWS25: 中泰证券：药品审评审批“速”“质”提升，全面利好医药行业发展.NEWS26: 速递 | mRNA疫苗预防季节性流感，1期临床试验已经启动.NEWS27: 速递 | 一线治疗宫颈癌，Keytruda组合疗法显着延长患者总生存期.NEWS28: 对上市公司重要股东违规减持都应依法查处.NEWS29: CXO行业成医药基金宠儿.NEWS30: 谁在幕后操盘？上海瀛翊违规减持药明康德 三大谜团待解 其他违规处罚.
2021-06-24: NEWS1: 北向资金今日再度净买入30.97亿元，新能源概念股受资金抢筹.NEWS2: 6月24日六家公司公告出现利好：药明康德参股纳微科技、复星医药产品获批.NEWS3: 医药行业2021年下半年投资策略：疫后重归长逻辑.NEWS4: 【国金晨讯】CXO高景气，当下哪些公司值得重点关注？高景气度下铜产业格局变化及其投资机会.NEWS5: 北向资金动向盘点：重手加仓“电子”.NEWS6: 一日 10 倍股！N 纳微涨成科创板首日涨幅新王！财富盛宴后，暗藏“九死一生”的对赌协议.NEWS7: 速递 | 蛋白降解疗法+ADC，新锐获8400万美元开发创新抗癌疗法.NEWS8: 速递 | 全球首批！“first-in-class”糖尿病口服疗法在日本获批.NEWS9: 纳微科技一日10倍背后 暗藏“九死一生”的对赌协议.
2021-06-25: NEWS1: 药明康德(02359)调整2018年A股激励计划授予的限制性A股股票回购数量和回购价格.NEWS2: 药明康德：约826万股限售股解禁，占比0.28% 解禁.NEWS3: 药明康德(603259.SH)826万股限制性股票将于7月1日上市流通.NEWS4: 药明康德(603259.SH)：826.004万股限制性股票将于7月1日上市流通.NEWS5: 北向资金本周爆买A股超200亿，连续加码金融股.NEWS6: 北上资金本周200亿扫货，顺周期王者归来，A股稳了？.NEWS7: 医疗板块逆势拉升，国际医学、通策医疗涨超5%.NEWS8: 南向资金高比例持有港股名单.NEWS9: 北向资金动向盘点：个股增减持“神经分裂”.NEWS10: 光伏板块大爆发，北向资金大幅加仓光伏龙头，甩卖白酒股与医药股.NEWS11: 速递 | 百时美施贵宝布局阿尔茨海默病，合作开发创新Tau蛋白抗体.NEWS12: 速递 | 艾伯维收购BCMA双特异性抗体疗法，治疗多发性骨髓瘤.NEWS13: 继续针对β淀粉样蛋白，两款阿尔茨海默病疗法获突破性疗法认定.NEWS14: 速递 | KRAS抑制剂获FDA突破性疗法认定，再鼎拥有大中华区开发权益.

###任务###
请根据过去五个交易日内关于该股票的新闻，预测下一个交易日该股票的涨跌，如果预测下一个交易日该股票会涨，请输出[上涨],如果预测下一个交易日该股票会跌，请输出[下跌]
```

输出：

```text
<think>
好的，我需要根据过去五天的新闻来判断药明康德下一个交易日的股价涨跌。首先，我要仔细分析每天的新闻内容，看看哪些是利好消息，哪些是利空消息，然后综合评估这些信息对股价的影响。

首先看6月21日的新闻。药明康德的参股公司Ambrx在纽交所上市，这可能是一个利好，因为参股公司上市可能带来投资收益和品牌效应。但同时，当天北向资金净卖出药明康德4.69亿元，连续两天净卖出，这可能显示外资在减持，属于利空。此外，关于CRO巨头泰格增速下滑的新闻可能对行业情绪有负面影响，但药明康德本身未被直接提及，影响可能有限。另外，医药行业周报提到看好创新药产业链，这对药明康德作为CXO龙头企业是利好。

6月22日的新闻中，药明康德认购基金SEA Fund，可能显示公司积极投资，拓展业务，属于中性或略偏利好。但当天出现大宗交易折价3%，且北向资金继续净流出，减持药明康德，这可能对股价造成压力。同时，关于上海瀛翊违规减持的新闻涉及药明康德，可能引发市场对公司治理的担忧，属于利空。

6月23日，药明康德的参股公司纳微科技在科创板上市首日暴涨，这可能带来投资收益，利好股价。当天北向资金转为大幅净流入，药明康德获净买入近8亿元，显示外资重新加仓，这是明显的利好信号。此外，行业新闻继续看好CXO高景气度，支持药明康德的业务前景。

6月24日，北向资金继续净买入，新能源概念受捧，但药明康德相关的新闻较少，主要是纳微科技的后续报道，可能维持正面情绪。行业策略报告提到疫后长逻辑，对医药行业整体有利。

6月25日，药明康德有826万股限售股解禁，解禁可能带来抛压，属于利空。但当天北向资金整体净买入，且金融股被加码，市场情绪可能较好。医疗板块逆势拉升，显示资金流入医药股，可能抵消部分解禁压力。

综合来看，虽然存在解禁和违规减持的利空，但参股公司上市带来的利好、北向资金的大幅流入以及行业整体的积极前景可能占据主导。尤其是23日北向资金大举买入，显示机构信心增强。因此，综合判断下一个交易日股价可能上涨。
</think>

上涨
```

处理脚本：

```python
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
```

## 3.3 安装

在`a04_train`目录下

版本要求：pytorch-cuda=11.8,12.1 for CUDA 11.8 or CUDA 12.1. We support python=3.10,3.11,3.12

测试CUDA 11.8无法工作，必须大于12

```bash
pip install -r requirements.txt
```

更新
```bash
pip install --upgrade --force-reinstall --no-cache-dir unsloth unsloth_zoo
```

测试采用的版本：2.7.4.post1

```bash
# flash attention 2 
pip3 install flash-attn --no-build-isolation
```

检查xfomers是否安装成功
```bash
python -m xformers.info
```

查看bitsandbytes是否安装成功
```bash
python -m bitsandbytes
```

## 3.4 训练

训练采用Unsloth 4bit Lora，显存消耗如下：

| Model Parameters | QLoRA (4-bit) VRAM | LoRA (16-bit) VRAM |
|------------------|--------------------|---------------------|
| 3B               | 3.5 GB             | 8 GB                |
| 7B               | 5 GB               | 19 GB               |
| 8B               | 6 GB               | 22 GB               |
| 9B               | 6.5 GB             | 24 GB               |
| 11B              | 7.5 GB             | 29 GB               |
| 14B              | 8.5 GB             | 33 GB               |
| 27B              | 22 GB              | 64 GB               |
| 32B              | 26 GB              | 76 GB               |
| 40B              | 30 GB              | 96 GB               |
| 70B              | 41 GB              | 164 GB              |
| 81B              | 48 GB              | 192 GB              |
| 90B              | 53 GB              | 212 GB              |
| 405B             | 237 GB             | 950 GB              |


```python
def generate_conversation(examples):
    instructions = examples['instruction']
    inputs = examples['input']
    thinks = examples['thinks']
    outputs = examples['output']

    conversations = []
    for instruct, in_query, think, output  in zip(instructions, inputs, thinks, outputs):
        conversations.append([
            {"role": "user", "content": '###新闻###\n' + in_query +
                                        '\n\n###任务###\n' + instruct},
            {"role": "assistant", "content": '<think>\n' + think + '\n</think>\n\n' + output},
        ])
    return { "conversations": conversations, }

model, tokenizer = FastLanguageModel.from_pretrained(
    model_name = mdl_path,
    max_seq_length = 32768,   # Context length - can be longer, but uses more memory
    load_in_4bit = True,     # 4bit uses much less memory
    load_in_8bit = False,    # A bit more accurate, uses 2x memory
    full_finetuning = False, # We have full finetuning now!
    # token = "hf_...",      # use one if using gated models
)

model = FastLanguageModel.get_peft_model(
    model,
    r = 32,           # Choose any number > 0! Suggested 8, 16, 32, 64, 128
    target_modules = ["q_proj", "k_proj", "v_proj", "o_proj",
                      "gate_proj", "up_proj", "down_proj",],
    lora_alpha = 32,  # Best to choose alpha = rank or rank*2
    lora_dropout = 0, # Supports any, but = 0 is optimized
    bias = "none",    # Supports any, but = "none" is optimized
    # [NEW] "unsloth" uses 30% less VRAM, fits 2x larger batch sizes!
    use_gradient_checkpointing = "unsloth", # True or "unsloth" for very long context
    random_state = 3407,
    use_rslora = True,   # We support rank stabilized LoRA
    loftq_config = None,  # And LoftQ
)

reasoning_conversations = tokenizer.apply_chat_template(
    reasoning_dataset.map(generate_conversation, batched = True)["conversations"],
    tokenize = False,
)

data = pd.concat([
    pd.Series(reasoning_conversations),
])
if data_random_sample > 0:
    print(f"Randomly sampling {data_random_sample} examples.")
    data = data.sample(data_random_sample, random_state = 3407)
    data = data.reset_index(drop = True)

data.name = "text"
combined_dataset = Dataset.from_pandas(pd.DataFrame(data))
combined_dataset = combined_dataset.shuffle(seed = 3407)

# 2. train model
trainer = SFTTrainer(
    model = model,
    tokenizer = tokenizer,
    train_dataset = combined_dataset,
    eval_dataset = None, # Can set up evaluation!
    args = SFTConfig(
        dataset_text_field = "text",
        per_device_train_batch_size = 2,
        gradient_accumulation_steps = 4, # Use GA to mimic batch size!
        warmup_steps = 5,
        num_train_epochs = 1, # Set this for 1 full training run.
        # max_steps = 20,
        learning_rate = 2e-5, # Reduce to 2e-5 for long training runs
        logging_steps = 1,
        optim = "adamw_8bit",
        weight_decay = 0.01,
        lr_scheduler_type = "linear",
        seed = 3407,
        report_to = "none", # Use this for WandB etc
    ),
)
```

# 4. 测试

从1000个测试集，抽样500进行测试，测评通过提取结果中的[上涨]或[下跌]标签，评判准确率
- deepseek-R1: 45.6%
- 0.6B lora 1k样本: 49%
- 0.6B原版unsloth-bnb-4bit: 47.4%
  - 出现部分不符合预期的输出，或者重复输出停不下来

1000样本全量测试：
- deepseek-R1: 44.3%
- 0.6B lora 1k样本: 49.9%

# 5. Ollama部署

**1.安装**
```bash
apt-get update
apt-get install pciutils -y
curl -fsSL https://ollama.com/install.sh | sh
```

默认启动地址：127.0.0.1:11434

**2.运行**

如果无法启动，则新开一个窗口，或者查阅`ollama使用说明`

```bash
ollama run hf.co/unsloth/Qwen3-8B-GGUF:Q4_K_XL
```

**3.问答**
如果不思考，可以改system提示词，或者直接使用下面的命令：
```bash
>>> Write your prompt here /nothink
```

# 6. 未来改进

数据优化：
- 排查发现当前有少量数据，存在新闻为空，也给出预测，需要剔除
- 加入对应新闻日期的股价数据
- 由于不是每个公司每天都有新闻，可以考虑总结一周、或一个月的新闻，进行预测

训练优化：
- 加入强化学习
- 实验更大的模型

测试：
- 加入回测框架
