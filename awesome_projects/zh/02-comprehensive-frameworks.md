# 综合框架

[English](../en/02-comprehensive-frameworks.md) | [中文](../zh/02-comprehensive-frameworks.md) | [分类目录](README.md) | [语言入口](../README.md)

- **[Qlib](https://github.com/microsoft/qlib)** — 微软面向 AI 的量化投资平台，涵盖数据、模型训练、回测、工作流管理和研究自动化扩展接口。
  - 元数据： 语言： Python · 星标数： 49,218 · 许可证： MIT · 维护状态： 活跃 (最近推送 2026-10-08)
  - 文档／主页： https://qlib.readthedocs.io/en/latest/
  - 使用点评：适合作为面向机器学习的股票研究流程的优先候选。

- **[WonderTrader](https://github.com/wondertrader/wondertrader)** — 基于 C++ 核心的一站式量化投研与交易框架，涵盖数据清洗、回测、实盘和调度，支持 CTA/SEL/HFT/UFT 引擎与多市场品种。
  - 元数据： 语言： C++ · 星标数： 5,801 · 许可证： MIT · 维护状态： 近期维护 (最近推送 2025-09-30)
  - 文档／主页： -
  - 使用点评：选择端到端研究、回测与执行架构时值得评估。

- **[OpenBB](https://github.com/openbq-org/OpenBB)** — 面向分析师、量化研究人员与 AI 智能体的开放数据和分析平台。
  - 元数据： 语言： Python · 星标数： 74,092 · 许可证： 其他／自定义 · 维护状态： 活跃 (最近推送 2026-10-02)
  - 文档／主页： https://openbb.co
  - 使用点评：适合需要广泛数据与分析能力、而不只是回测引擎的研究工作流。

- **[PandaAI QuantFlow](https://github.com/PandaAI-Tech/panda_quantflow)** — 集成量化交易与机器学习工作流的平台，提供节点式可视化工作流设计、内置机器学习模型（XGBoost、LightGBM、随机森林、SVM、神经网络）、因子分析、股票与期货事件驱动回测，以及支持多用户工作流管理和 Docker 部署的 FastAPI 服务。
  - 元数据： 语言： JavaScript · 星标数： 1,053 · 许可证： GPL-3.0 · 维护状态： 近期维护 (最近推送 2025-08-14)
  - 文档／主页： -
  - 使用点评：适合作为端到端低代码量化投研与交易工作台的候选；生产采用前应核验随附 MongoDB 行情数据的授权，以及规划中的 CTP/QMT 实盘连接器。

## 金融工程工具库

- **[TF Quant Finance](https://github.com/google/tf-quant-finance)** — Google 基于 TensorFlow 开发的量化金融工具库。
  - 元数据： 语言： Python · 星标数： 5,519 · 许可证： APACHE-2.0 · 维护状态： 活跃 (最近推送 2026-08-07)
  - 文档／主页： -
  - 使用点评：可作为机器学习层的候选资源；生产采用前需验证适配性。

- **[QuantLib](https://github.com/lballabio/QuantLib)** — 用于期权和固定收益产品定价的 C++ 工具库。
  - 元数据： 语言： C++ · 星标数： 7,656 · 许可证： 其他／自定义 · 维护状态： 活跃 (最近推送 2026-10-03)
  - 文档／主页： http://quantlib.org
  - 使用点评：可作为量化分析与评估层的候选资源；生产采用前需验证适配性。

- **[pyql](https://github.com/enthought/pyql)** — QuantLib 的 Cython 封装。
  - 元数据： 语言： Cython · 星标数： 1,344 · 许可证： 其他／自定义 · 维护状态： 活跃 (最近推送 2026-07-18)
  - 文档／主页： -
  - 使用点评：可作为量化分析与评估层的候选资源；生产采用前需验证适配性。
