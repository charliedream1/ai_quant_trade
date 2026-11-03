# 原理文档

2026-10-30新增[安全边界、任务与模块组织](security_concurrency.md)，说明访问控制、经复核源码工作进程、SQLite租约、取消/背压、模块拆分与尚未消除的风险。

首次学习量化可从[量化基础课程](quant_basics/README.md)开始，十二章覆盖数据、统计、因子、回测、组合与样本外检验；应用中对应独立“学习空间”。

新增：[因子面板、研究与评分](factor_research.md)，说明时点、缺失、IC/ICIR、权重、模型特征与缓存一致性。

本目录解释数据、策略、指标与 AI 怎样工作，以及结论能证明什么。具体点击步骤见[使用文档](../usage/README.md)；原理正文不重复操作教程。

| 文件 | 内容 |
|------|------|
| [知识库文件检索](knowledge_retrieval.md) | 命名库、标题切分、模型关键词、多轮检索与引用 |
| [辩论与双团队竞赛](agent_strategies.md) | 角色边界、原文引用、成熟成绩、效用预测、预算与影子账本 |
| [Alpha研究纪律](alpha_mining.md) | 试验家族、时点隔离、统计与账本、三角色和主题/体制边界 |
| [文件预览与版本保存](file_preview.md) | 原件、RAG文本、Office转换、Markdown版本冲突与隔离阅读 |
| [系统架构](architecture.md) | 页面、API、CLI、领域服务和闭环 |
| [数据与缓存](data_pipeline.md) | 来源、市场、时间边界和冷暖加载 |
| [策略标准端口](strategy_port_principles.md) | 加载、适配、接口校验与回测的区别 |
| [策略编排与组合](strategy_composition.md) | 级联、并行、Agent、Risk、Portfolio 与批次账本 |
| [图形工坊](strategy_graph.md) | Gradio画布、布局和计算分离、子策略路径与真实事件 |
| [参数与复现](parameters.md) | 继承、覆盖、快照和证据 |
| [回测与指标](backtest_metrics.md) | 撮合、成本、基准、收益风险及归因 |
| [执行成本与快照](execution_costs.md) | 外部订单计费、现金勾稽、历史状态与独立执行实验 |
| [模型与 ETF](model_etf.md) | 时点隔离、轮动、流动性和跟踪误差 |
| [AI 与多 Agent](ai_agents.md) | ReAct、会话、事件流和只读复核 |
| [CLI 协议](cli_protocol.md) | 请求、输出、退出状态和同步超时 |
| [存储分工](storage.md) | SQLite、文件、Parquet 和 DuckDB |
| [关系图谱](relation_graph_principles.md) | 关系类型、来源和解释 |
| [通用因子监控](factor_monitoring.md) | 股票池版本、日期标签、覆盖率与内置/Qlib信号分析 |
| [Gradio 交互](gradio_ui_principles.md) | 延迟挂载、页面组织和视觉验证 |
| [运行隔离与入口整合](runtime_navigation.md) | 实际版本、来源、锁文件和唯一编辑入口 |
| [验证原则](testing_principles.md) | 单元、集成、浏览器和真实证据边界 |

正式架构与接口设计保留在项目 `doc/`；13 号设计为本地 Skill 洞察，14 号为策略编排、Risk 与 Portfolio，A/B 已接入、C 待扩展。机构应用调研在 `docs/research/`，外部参考在 `docs/reference/`，历史验收在 `docs/audit/`。它们是资料档案，不混入日常操作目录，也不随帮助站点复制历史附件。
