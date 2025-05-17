# 1. 资源

- Unsloth Github (38.3k stars): https://github.com/unslothai/unsloth
- 文档：https://docs.unsloth.ai/
- Notebook: https://docs.unsloth.ai/get-started/unsloth-notebooks
- 所有经过dynamic量化版本模型：https://docs.unsloth.ai/get-started/all-our-models

# 2. 训练支持

支持LLM/VLLM/TTS

# 3. 安装

版本要求：pytorch-cuda=11.8,12.1 for CUDA 11.8 or CUDA 12.1. We support python=3.10,3.11,3.12

个人测试，CUDA 11.8无法工作，必须大于12，
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

# 4. SFT显存占用

Llama 3.1 (8B) 

4bit QLoRA on all linear layers (Q, K, V, O, gate, up and down) with rank = 32 with a batch size of 1

| GPU VRAM | 🦥Unsloth Context Length | Hugging Face + FA2 |
|----------|--------------------------|---------------------|
| 8 GB     | 2,972                    | OOM                 |
| 12 GB    | 21,848                   | 932                 |
| 16 GB    | 40,724                   | 2,551               |
| 24 GB    | 78,475                   | 5,789               |
| 40 GB    | 153,977                  | 12,264              |
| 48 GB    | 191,728                  | 15,502              |
| 80 GB    | 342,733                  | 28,454              |

Llama 3.3 (70B) 

4bit QLoRA on all linear layers (Q, K, V, O, gate, up and down) with rank = 32 with a batch size of 1

| GPU VRAM | 🦥Unsloth Context Length | Hugging Face + FA2 |
|----------|--------------------------|---------------------|
| 48 GB    | 12,106                   | OOM                 |
| 80 GB    | 89,389                   | 6,916               |

不同模型大小显存占用

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

# 5. 强化学习GRPO

## 5.1 显存优化
相比flash attention2, 做了很多优化，GRPO降低90%显存。
- Qlora 4 bit微调显存需求和模型参数大小一样
- loara 16 bit需要4倍显存

使用vLLM，vLLM和unsloth可只加载一份模型，节约显存

```python
# pip install unsloth vllm
from unsloth import FastLanguageModel
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name = "unsloth/Llama-3.2-3B-Instruct",
    fast_inference = True,
)
model.fast_generate(["Hello!"])
```

| Metrics                                      | Unsloth         | Standard + FA2 |
|----------------------------------------------|------------------|----------------|
| Training Memory Cost (GB)                    | 42 GB            | 414 GB         |
| GRPO Memory Cost (GB)                        | 9.8 GB           | 78.3 GB        |
| Inference Cost (GB)                          | 0 GB             | 16 GB          |
| Inference KV Cache for 20K context length    | 2.5 GB           | 2.5 GB         |
| Total Memory Usage                           | 54.33 GB (90% less) | 510.8 GB     |

# 6. 使用说明

训练过程如果仅保存lora权重，则在保存目录的`adapter_config.json`目录下会记录基础模型的路径，
因此，在使用unsloth加载模型时，仅指定lora路径也可以加载模型。如果基础模型路径变了，记得变更。

如下的代码保存，会报错，必须使用`merged_4bit_forced`，但按4bit加载时又会出错。

```bash
model.save_pretrained_merged("model", tokenizer, save_method = "merged_4bit",)
```

# 7. 问答效果

原版模型：

```text
<think>
好的，我现在需要根据提供的过去五个交易日的新闻，预测下一个交易日东方盛虹（000301.SZ）的涨跌情况。首先，我需要仔细阅读用户提供的新闻内容，提取关键信息，然后分析这些信息可能的影响因素，最后综合判断。

首先，用户给出的新闻包括从11月3日到11月9日的五个日期，每个日期都有不同的新闻。我需要先整理这些新闻，确保没有遗漏。例如，新闻11月3日有油价下跌，导致无水氢氟酸、除草剂等价格上涨；新闻11月4日提到2021年1-10月累计新增借款占2020年末净资产的比例为144.19%，这可能影响公司财务状况；新闻11月5日提到26股获北向资金加仓超亿元，这可能意味着市场对该公司有积极反应；新闻11月6日和11月7日提到宁德时代和万科A的项目，这可能与市场对新能源或房地产的积极预期有关；新闻11月8日和11月9日涉及炼化和化纤板块，这可能反映行业前景良好。

接下来，我需要分析这些信息如何影响东方盛虹。首先，油价下跌可能影响其基础化工产品，比如无水氢氟酸等，这可能导致价格上涨，从而可能影响公司的盈利能力。但新闻中提到的是“价格上涨”，这可能意味着公司产品价格上升，但需要看是否有其他因素。另外，新增借款比例高可能意味着公司财务状况良好，但需要结合其他因素。北向资金加仓可能表明市场对该公司有信心，可能上涨。另外，宁德时代和万科A的项目可能带动相关行业，但东方盛虹是否与这些项目相关？可能需要进一步确认。例如，新闻中提到26股获北向资金加仓，这可能意味着市场对该公司有积极反应，因此可能上涨。

现在需要综合这些因素。例如，如果北向资金加仓是积极的，而油价下跌可能影响基础化工产品，但公司可能有大额借贷担保，这可能意味着公司有财务优势。同时，市场对新能源和房地产的预期可能推动相关板块，但东方盛虹是否与这些板块相关？可能需要考虑。例如，新闻中提到“石化配置创近八年新高”，这可能意味着石油石化板块有好的前景，但东方盛虹是否属于这些板块？可能需要进一步分析。

另外，新闻中提到26股获北向资金加仓，这可能意味着市场对该公司有积极预期，因此预测上涨。而如果其他因素如财务状况良好、北向资金增持等，都可能支持上涨。因此，综合判断，可能预测下一个交易日该股票会涨。
</think>

[上涨]
```

训练过的模型：

```text
<think>
嗯，用户让我根据过去五个交易日的新闻来判断东方盛虹下一个交易日的股价涨跌。首先，我需要仔细分析每条新闻的内容，看看哪些可能对股价有正面或负面的影响。

首先看2021-11-03的新闻。NEWS1提到油价下跌，导致无水氢氟酸、除草剂、丁基橡胶等价格上涨。这可能对化工行业整体有利，因为这些产品可能被下游企业需求增加，但东方盛虹属于基础化工，可能受益。不过新闻中没有明确提到他们本身的情况，可能影响不大。

接下来是2021-11-04，有两个新闻。NEWS1和NEWS2都是关于新增借款占净资产比例的问题，这可能涉及财务状况，但具体影响不大，除非有特别大的债务问题，但新闻中没有提到。NEWS3和NEWS4都是关于北向资金加仓和化工行业点评，可能暗示市场对化工板块的看好，尤其是宁德时代和万科A的分拆上市，可能带动相关股票上涨，但东方盛虹是否受影响还不清楚。

11月5日的新闻更多关于基金转让和产品性能差异，这些可能属于内部业务调整，对股价影响有限。NEWS4提到26.51亿元受让连云港盛虹的财产份额，这可能增加盛虹的资产，但东方盛虹本身可能不会直接受益，除非有其他关联。NEWS7提到北向资金加仓，这通常被视为积极信号，可能带动股价。

11月8日的新闻提到炼化板块业绩提升，但宁德时代和万科A的分拆上市可能对整个行业有利，但东方盛虹可能没有直接关联。NEWS28是北向加仓，同样可能有利。

11月9日的新闻提到石油加工行业炼化板块需求恢复，这可能对整个行业有利，但具体到东方盛虹的业务是否受影响还不明确。综合来看，虽然市场有加仓和行业利好，但新闻中没有明确提到东方盛虹的直接利好消息。另外，新增借款比例的问题可能引发财务担忧，如果市场认为这会影响公司估值，可能引发担忧，导致股价下跌。不过，新闻中没有直接的负面因素，可能市场预期财务状况良好，从而维持上涨。因此，综合考虑，可能判断下一个交易日股价上涨。
</think>

上涨
```