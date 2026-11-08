# 中文辩论与内部竞赛策略核查

2026-10-28，Codex。对象为用户指定的TradingAgents-CN与财跃星辰ContestTrade。本轮只调研与设计，没有安装、运行或迁入上游实现；下述本项目方案尚待人工确认。

## 版本与许可证

| 项目 | 本次核验版本 | 一手许可依据 | 本项目处理 |
| --- | --- | --- | --- |
| hsliuping/TradingAgents-CN | 默认分支v3.0，提交51060a7682cf51810b4bc3a704829438d18cd8dc | [分层LICENSE](https://github.com/hsliuping/TradingAgents-CN/blob/51060a7682cf51810b4bc3a704829438d18cd8dc/LICENSE)：tradingagents、cli、docs、tests、web及根配置属Apache-2.0；app、frontend、core为专有源码可见组件，列明分发与商业使用限制 | 从公开功能描述提炼需求，在本项目独立实现；不把整个仓库当Apache依赖，不迁入专有代码、提示词、界面资源 |
| TradingAgents-CN的main分支 | 74783e8817d6cf6de29867880631cc555153f36b | [main的LICENSE](https://github.com/hsliuping/TradingAgents-CN/blob/74783e8817d6cf6de29867880631cc555153f36b/LICENSE)同样区分Apache部分与app/frontend专有部分，范围与v3.0不同 | 固定到分支、提交及目录，不能拿旧fork的Apache徽标代表当前默认版本 |
| FinStep-AI/ContestTrade | main，提交22432f9bbba5f1d6862d3b6b5508d4d882b40b94 | [LICENSE](https://github.com/FinStep-AI/ContestTrade/blob/22432f9bbba5f1d6862d3b6b5508d4d882b40b94/LICENSE)为Apache-2.0 | 可按许可评估局部复用；首批仍以本项目既有执行器独立实现，避免整包依赖；若实际复制文件，逐文件记录来源、修改及版权/许可/适用NOTICE |

这两个指定版本不能笼统归为GPL项目。对GPL/AGPL、专有组件或授权不清的材料，遵循用户偏好，只参考公开方法，不复制实现。本轮没有取得商业授权，也不声称独立实现自动消除了所有数据、商标或专利问题。上游项目名称仅用于标明方法来源。

三份许可证的原始响应SHA256及HTTP核查记录保存在本轮[审计记录](../../audit/agent_strategy_design_2026-10-28.json)，没有把第三方业务源码复制进项目。后续开发若要复用Apache文件，先按锁定提交核查具体文件与第三方来源，不能仅凭仓库顶层许可推断全部依赖。

## 哪些机制值得加入

TradingAgents-CN的公开README描述了面向A股的多角色研究、乐观/审慎观点交锋和研究助手；它适合把单股与少量候选的多维证据放在同一份解释中。[v3.0官方介绍](https://github.com/hsliuping/TradingAgents-CN/blob/51060a7682cf51810b4bc3a704829438d18cd8dc/README.md)。本项目拟形成“事实分析→多空论证→审慎决策”流程，角色、提示词和界面由本项目设计，硬风控沿用现有规则。

ContestTrade的README描述数据团队提炼文本因子、研究团队按不同交易信念提出方案，再分别竞赛与组合。[官方介绍](https://github.com/FinStep-AI/ContestTrade/blob/22432f9bbba5f1d6862d3b6b5508d4d882b40b94/README.md)。论文v5进一步明确历史成绩量化、效用预测与资源分配，评分应在市场结果可见后更新；研究观点需要真正进入下一期的信息选择或组合预算。[作者论文](https://arxiv.org/html/2508.00554v5)。

本项目采用以下需求，不照搬上游角色提示词或评分实现：

- 数据竞赛决定哪些证据进入受限上下文，保留来源、反例、去重和未选原因。
- 研究竞赛决定不同研究风格获得的组合预算，保留正效用门槛、分散约束与现金。
- 成绩只来自已经成熟的结果，决策时点之后的收益不能用于同一时点选赢家。
- 质量评审帮助识别无依据的推断，不能仅凭语言说服力替代实际收益与风险。

## 论文与公开代码存在的范围差异

当前仓库main提交时间为2025-12-22，论文v5日期为2026-08-20。两者不是同一个实现版本，不能宣称按main装包就复现了v5完整实验。

| 核查点 | 公开证据 | 集成决策 |
| --- | --- | --- |
| 数据团队的选取 | 固定提交的[DataContest](https://github.com/FinStep-AI/ContestTrade/blob/22432f9bbba5f1d6862d3b6b5508d4d882b40b94/contest_trade/contest/data_analyst/data_contest.py)记录simple_topk；论文描述带信息预算和冗余约束的选择 | 首批明确实现有预算、有去重的规则选择，不冒充复现论文优化算法 |
| 效用预测 | 公开[数据预测器](https://github.com/FinStep-AI/ContestTrade/blob/22432f9bbba5f1d6862d3b6b5508d4d882b40b94/contest_trade/contest/data_analyst/predictor.py)有模型加载与均值路径；[研究预测器](https://github.com/FinStep-AI/ContestTrade/blob/22432f9bbba5f1d6862d3b6b5508d4d882b40b94/contest_trade/contest/researcher/research_predictor.py)依赖历史收益、评审特征和模型文件 | 本地重建成绩序列；显式区分统计基线、训练过的LightGBM与证据不足，不静默用另一算法冒充成功 |
| 研究权重 | [权重优化器](https://github.com/FinStep-AI/ContestTrade/blob/22432f9bbba5f1d6862d3b6b5508d4d882b40b94/contest_trade/contest/researcher/research_weight_optimizer.py)只给正预测效用分配权重，无正值时为零 | 方法可独立实现；净额、现金、费用和硬风控交给本项目账本 |
| 模型产物 | 仓库包含joblib文件，但仅看到文件不能证明训练时间、母池及标签范围 | 不加载上游不明训练来源的序列化模型；使用本地训练与原生模型格式，记录输入、窗口和摘要 |
| 绩效 | 论文给出特定数据、模型和协议下的研究回测 | 不把论文收益搬到本项目页面；本项目AR/IC/回撤以自己的数据与账本计算 |

## 与现有功能怎样分工

| 已有功能 | 目前真实职责 | 本轮增加内容 |
| --- | --- | --- |
| ResearchTeam | 已完成回测后的四角色复核 | 保持旧语义，避免改名后假称已实现双团队竞赛 |
| DecisionTeam与AgentGateway | 有限候选的选取/拒绝/退出、事件、真实API或Codex与严格决定回放 | 扩展可选工作流，加入中文多空研究和可审计的竞赛预算 |
| Alpha研究 | 假设发现、实现、验证、研究纪律和导出 | 接收成熟的研究假设或因子，保留独立研究家族和最终留出；不让竞赛绕过统计门槛 |
| 图形工坊、Portfolio/Risk | 级联/并行、预算、同账本费用和风险 | 两类策略作为可配置方案及节点；旧模板与旧Agent流程不变 |
| 资料、主题、图谱与报告库 | 来源、可得时间、原文引用、主题池、HTML展示 | 扩展为决策前的冻结证据包、角色过程与胜出/弃权原因 |

推荐首批采用本项目独立实现的两类方案，维持Gradio和现有存储。整体移植Vue/FastAPI应用、MongoDB/Redis服务、专有页面以及自动外部交易不纳入此次实现。具体阶段、六套预置、数据时点、预算和验收见[24号正式设计](../../../doc/agents/agent_debate_contest_strategy_design.md)。

2026-10-28实施更新：已按确认A/B独立实现六套预置与四种图形节点，配套延迟影子记分、明确统计基线/本地LightGBM、现金及现有Portfolio/Risk、API/CLI和报告库。中文事件和竞赛事件已用用户指定E盘配置的实际Qwen服务完成一次小样本流程；非收益复现实验，没有额外做参数或模型效果调优。页面操作与真实/夹具证据分别登记，见[使用](../../usage/agent_strategies.md)、[原理](../../principles/agent_strategies.md)和[验收](../../audit/agent_strategies_2026-10-28/README.md)。
