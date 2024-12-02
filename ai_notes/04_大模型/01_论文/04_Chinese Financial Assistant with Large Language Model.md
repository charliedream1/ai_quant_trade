- CFGPT: Chinese Financial Assistant with Large Language Model
- https://arxiv.org/abs/2309.10654

摘要

本论文介绍了一种名为CFGPT的中文金融生成预训练Transformer框架。该框架包括用于预训练和监督微调的数据集（CFData），用于处理金融文本的金融大语言模型（CFLLM），以及用于实际金融应用的部署框架（CFAPP）。CFData包括预训练数据集和监督微调数据集，其中预训练数据集汇集了中文金融数据和分析，以及总共584M个文档和141B个标记的一小部分通用文本；监督微调数据集针对六个不同的金融任务进行了定制，总共包含1.5M个指令对和1.5B个标记。CFLLM基于InternLM-7B进行训练，以平衡模型能力和大小，通过两个阶段的持续预训练和监督微调来训练。CFAPP以大型语言模型（LLMs）为核心，并通过附加模块增强了在实际应用中的多方面功能。论文代码已在https://github.com/TongjiFinLab/CFGPT1上发布。
