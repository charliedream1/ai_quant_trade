# 1. 简介
Qlib是由微软推出的一款量化交易平台，是一个非常体系化、流程化且非常优秀的基于机器学习的量化研究框架。
它将量化研究与机器学习非常系统化的结合在一起。

- 论文: [Qlib : An AI-oriented Quantitative Investment Platform](https://arxiv.org/pdf/2009.11189.pdf)   
- Github:  [qlib](https://github.com/microsoft/qlib)
- [**在线文档**](https://qlib.readthedocs.io/en/latest/index.html)     

## 1.1 核心功能
- 微软开发的AI量化投资平台，当前唯一且最完善的开源平台。
- 不仅提供了高速存储(快于MySQL, MongoDb等)，还提供了详细的全流程一站式服务，从数据下架、模型训练到回测评估。
- 几乎包含了量化投资全流程：alpha因子搜索(不用人工设计因子)、风控模型、最大化投资组合和交易执行。
- 包含机器学习(boosting类算法)、深度学习(LSTM->Transfomre)、强化学习、元学习和动态学习等前沿算法。
- 集成了MLFLOW(生命周期管理)和Optuna(自动超参数搜索)

## 1.2 缺点
- 每个样例中requirements.txt里的torch版本都不同，且比较老
- 不支持多GPU训练

# 2. 文档及教程
* 官方文档：https://qlib.readthedocs.io/en/latest/index.html
* QuantWorld2022教程: https://github.com/QuantWorld2022/qlib_tutorial