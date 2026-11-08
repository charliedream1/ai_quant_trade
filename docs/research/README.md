# 量化与平台能力调研

- [因子研究能力取舍](composition/factor_research_review.md)：Panda 功能思路、独立实现范围及不直接复用的原因。

2026-10-28 更新。这里按研究主题保存机构公开应用、开源实现和平台选型依据；正式设计在 `doc/`，实际测试证据在 `docs/audit/`。

| 分类 | 文档 | 内容 |
| --- | --- | --- |
| Agent策略方案 | [中文辩论与内部竞赛](agents/tradingagents_cn_contesttrade_review.md) | TradingAgents-CN混合授权、ContestTrade Apache及论文/代码差异；24号A/B已独立实施，真实小样本只验证流程 |
| Alpha研究 | [机构挖掘与体制研究方法](alpha_mining/institutional_workflows.md) | Man三角色、QUEST主题精炼、四体制与证据分级；23号已接入，真实模型/样本边界见验收 |
| 文件与应用集成 | [网页文件预览与外部软件](platform/document_preview_feasibility.md) | 只读预览/Markdown编辑已按22号接入；完整Office编辑与远程浏览器仍为调研候选 |
| 模型策略 | [机构应用与模型选型](models/institutional_practice.md) | 树模型、神经网络的公开证据、证据边界与本项目三套策略 |
| 模型安全 | [Torch 告警核查](models/torch_security_review_2026-10-21.md) | 当前代码触发路径、官方修复记录、2.14.1 候选扫描与未验证边界 |
| 因子监控 | [股票池边界与通用方案](factors/universe_monitoring_review.md) | 默认小池、现有四因子原理、日期与覆盖问题，以及 Alphalens/Qlib 的通用监控方法；建议尚未实施 |
| 平台改进 | [监控、图表、图谱与导入设计](../../doc/data/monitor_graph_resource_design.md) | 2026-10-25接入通用监控/Qlib信号分析、解释、图谱证据与导入校验；真实验收范围见报告 |
| 多 Agent | [金融多 Agent 应用](agents/financial_multi_agent.md) | Man Group、TradingAgents 的应用层级和本项目复核流程 |
| ETF | [ETF 研究](etf/README.md) | ETF 载体、主动/AI ETF 应用证据和项目研究边界 |
| 策略编排 | [组合与风险组件参考](composition/framework_comparison.md) | LEAN/Qlib 分层、HRP/CVaR 与时点隔离；14号设计的A/B已接入，C独立扩展 |
| 图形编排 | [PandaQuantFlow核查](composition/panda_quantflow_review.md) | 官方节点/连线/运行证据、公开前端边界及继续使用Gradio的方案 |

机构公布某一模型类别，不等于公开某个产品的完整实现。文档分别标注机构自述应用、技术研究、开源框架与本项目设计，避免把案例回测、营销表述和实际资金绩效混在一起。
