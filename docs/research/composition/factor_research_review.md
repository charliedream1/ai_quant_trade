# 因子研究能力取舍

2026-10-24。上游源码核查不等于上游运行验收，本文记录本项目独立实现的依据。

[PandaQuantFlow](https://github.com/PandaAI-Tech/panda_quantflow/tree/688b90e74a738b84567efe622a2d9c1e5ce10e00) 拆分特征工程、因子分析、模型与合成节点；[PandaFactor](https://github.com/PandaAI-Tech/panda_factor) 提供因子、算子、分析和调度思路。借鉴重点是研究与执行的衔接。本项目继续使用已实现的 Portfolio、Risk、账本、Agent 和 Gradio 工坊。

本批独立实现因子集、逐日预处理、已到期标签研究、去重、等权/ICIR合成、命名模型特征和数值缓存。因子监控已有研究指标，抽取统计函数复用，避免两套口径。

## 不照搬的部分

- 上游[加权节点](https://github.com/PandaAI-Tech/panda_quantflow/blob/688b90e74a738b84567efe622a2d9c1e5ce10e00/src/panda_plugins/internal/factor_weight_adjust_node.py) 对输入表整体计算标准化统计量；若包含未来日期会泄漏。本项目逐日期处理。
- [研报示例策略](https://github.com/PandaAI-Tech/panda_quantflow/blob/688b90e74a738b84567efe622a2d9c1e5ce10e00/src/panda_backtest/strategy/research_report_strategy.py) 用价格、成交量和振幅代理价值、成长、质量，不能当成真实财务因子。本批明确只有价量研究。
- [重要性相关合成](https://github.com/PandaAI-Tech/panda_quantflow/blob/688b90e74a738b84567efe622a2d9c1e5ce10e00/src/panda_ml/importance_spearman_factor_combiner.py) 与本项目滚动 ICIR 不是同一算法，不能把重要性视为盈利概率。
- [相关性依赖缺失反馈](https://github.com/PandaAI-Tech/panda_quantflow/issues/7) 表明节点名称不等于依赖完整；新增能力需要独立运行验收。

多任务网络和因子搜索留作后续。当前 240 根日线与固定母池不足以充分覆盖不同市场阶段，应先补长历史、历史可得成分和财务数据。

遵循用户要求，不复制、翻写或移入 Panda 源码、配置和模板，不安装其包；业务依赖未增加。真实行情、首次失败和修复后证据分别保存于项目 `docs/audit/factor_research_2026-10-24/`，方法及使用分别归入原理文档与使用文档。
