# 1. 资源
- 论文：
  - 上海同济大学
  - CFGPT: Chinese Financial Assistant with Large Language Model
    - https://arxiv.org/abs/2309.10654
      - 2023
  - RA-CFGPT: Chinese financial assistant with retrieval-augmented large language model
    - 2024
- Github (47 stars): https://github.com/TongjiFinLab/CFGPT1
- 开源模型 （基于intern-lm2开发）：CFGPT1 (7B)，pretrain, lora sft, sft
- 给出了比较详细的数据集类别和样例
- 包含详细案例分析
- 包含完整的训练、测试流程

- 模型参考：InternLM: https://github.com/InternLM/InternLM
- 训练框架参考：Firefly: https://github.com/yangjianxin1/Firefly
- 金融评测参考：FinGPT: https://github.com/AI4Finance-Foundation/FinGPT

# 2. 摘要

本论文介绍了一种名为CFGPT的中文金融生成预训练Transformer框架。该框架包括用于预训练和监督微调的数据集（CFData），用于处理金融文本的金融大语言模型（CFLLM），以及用于实际金融应用的部署框架（CFAPP）。CFData包括预训练数据集和监督微调数据集，其中预训练数据集汇集了中文金融数据和分析，以及总共584M个文档和141B个标记的一小部分通用文本；监督微调数据集针对六个不同的金融任务进行了定制，总共包含1.5M个指令对和1.5B个标记。CFLLM基于InternLM-7B进行训练，以平衡模型能力和大小，通过两个阶段的持续预训练和监督微调来训练。CFAPP以大型语言模型（LLMs）为核心，并通过附加模块增强了在实际应用中的多方面功能。论文代码已在https://github.com/TongjiFinLab/CFGPT1上发布。

![](.01_Chinese Financial Assistant with Large Language Model_images/训练流程.png)

![](.01_Chinese Financial Assistant with Large Language Model_images/训练流程_中文.png)

## 继续预训练

预训练数据集包括 5.91 亿份文档和 1930 亿个token，包括六个子数据集：

* CFData-CP（6.24%）：包括 3,900 份公司招股说明书，共计 130 亿个token；
* CFData-CA（12.28%）：包括 600 万份公司公告，共计 170 亿个token；
* CFData-RR（2.51%）：包括 39.2 万份研究报告，共计 30 亿个token；
* CFData-FN（18.70%）：包括 8,200 万份财经新闻，共计 260 亿个token；
* CFData-SM（60.15%）：包括 4.95 亿份社交媒体内容，共计 840 亿个token；
* CFData-Wiki（0.09%）：包括 25.5 万份维基百科内容，共计 1.37 亿个token。

我们从CFData-pt中抽取了一个财经文本子语料库，以便在InternLM-7B上进行进一步的预训练。该子语料库包含了来自大量中国财经数据和分析以及少量通用文本的共计约137亿个token，这些通用文本包括公告、研究报告、社交媒体内容、财经新闻文章和维基百科等，而这些数据主要由我们自行收集。

## 有监督微调

监督微调数据集包括160万条指令对和15亿个标记，其中包括六个金融任务：
* CFData-SA（5.69%）：12万个实例，8600万标记用于情感分析；
* CFData-RS（50.60%）：36.9万个实例，7.65亿标记用于报告摘要；
* CFData-ED（22.69%）：49万个实例，3.43亿标记用于事件检测；
* CFData-TD（12.37%）：36.9万个实例，1.87亿标记用于主题分解；
* CFData-QA（0.39%）：1.2万个实例，600万标记用于问答；
* CFData-SP（8.27%）：21.2万个实例，1.25亿标记用于股票价格预测。

我们利用高质量的领域特定数据，通过有监督的微调来实现金融领域的适应性。该数据集包括六个金融数据集，以反映金融分析和决策的不同方面，包括情感分析、事件检测、报告摘要、主题分解、问题回答和股票走势预测。

CFData-sft提供了大量金融领域的文本信息，使FinLLM能够从不同的信息源中学习。

考虑到实际需求，我们将这些金融有监督微调数据集重组成十个任务。

以下是详细信息：
| 任务 | 任务描述 | 数据集 | 大小 |
| - | - | - | - |
| Sentiment | 识别与财务文件相关的情感 | CFData-SA | 13K |
| Summary | 基于提供的财务文件生成内容摘要 | CFData-RS | 18K |
| Risk | 基于提供的财务文件生成风险警报 | CFData-RS | 20K |
| Suggestion | 基于提供的财务文件生成投资建议 | CFData-RS | 18K |
| Event | 识别与财务文件相关的事件类别 | CFData-ED | 12K |
| Industry | 识别与财务文件相关的行业类别 | CFData-ED | 14K |
| Company | 识别与财务文件相关的公司名称 | CFData-ED | 12K |
| Product | 识别与财务文件相关的产品名称 | CFData-ED | 21K |
| Exam | 回答与财务问题相关的是非问题 | CFData-QA | 16K |
| Stock | 预测股票未来走势 | CFData-SP | 15K |

更多关于CFData的信息，研究人员可以参考我们[CFData](./data)的一些示例数据