# 机构Alpha挖掘与体制研究方法

核查日期：2026-10-27。用于本项目23号设计的工作方法参考。用户确认后已接入A/B/C；本项目实际验证见[使用指南](../../usage/alpha_mining.md)及23号当前边界，不把公开机构方法、用户提供研究摘要和本项目实现混为机构原版系统。

## 公开证据与边界

| 主题 | 本轮证据 | 本项目采用方式 |
| --- | --- | --- |
| Man Group AlphaGPT | 官方文章和搜索可见的官方材料介绍Idea Person、Implementer、Evaluator及编排器、相同评估标准、人工监督；2026年合作公告继续提及AlphaGPT | 借鉴角色/研究纪律，独立实现；没有取得其私有代码、数据库、完整提示词和门槛参数 |
| JPMorgan QUEST/IndexGPT | 官方Markets搜索可见的访谈摘要说明，用LLM精炼主题—公司的检索关键词；官方DataQuery介绍新闻驱动的QUEST主题分数 | 主题关联及证据层，后续买卖和权重由确定性研究/组合规则负责 |
| JPMorgan四体制/八配置，2026年7月 | 用户提供摘要；本轮检索未取得可直接核验的官方原研究报告。公开二次报道的数字不升级为官方已核实事实 | 四体制、滞后、匿名与固定配置按用户需求独立设计；不声称复刻模型名单、权重或收益 |

Man Group把机构积累和研究流程视为重要能力，不宜把三个角色名称本身当作可持续收益来源。公开说明不能证明任何复刻流程都能发现可部署Alpha。[Man Group：What AI Can (and Can't Yet) Do for Alpha](https://www.man.com/insights/what-ai-can-do-for-alpha)、[2026年合作公告](https://www.man.com/news-centre/man-group-anthropic-partnership)。

JPMorgan主题产品的公开说明支持“关联精炼”的定位，不支持直接把LLM回答当收益预测。旧IndexGPT介绍页本轮返回403；Markets主页的完整访谈正文未稳定复现，研究记录保留搜索可见的官方摘要身份。用户提到Maharaj对随机性的具体警告本轮未核实完整原句，因此不作为直接引文。[官方Markets页面](https://www.jpmorgan.com/markets?source=megamenu)、[官方Portfolio Solutions访谈](https://emea-markets.jpmorgan.com/portfolio-solutions)、[官方DataQuery产品说明](https://www.jpmorgan.com/markets/dataquery)。

用户摘要中的“八个Agent全部战胜60/40”不能直接用作本项目成功标准；是否八种独立配置、推理强度对照或协作集成，必须看到原方法才可归因。首版将八个槽位独立记录，另加投票时作为本项目额外试验。

## 三条流程不能混成一个买卖Agent

Alpha挖掘产生可证伪因子假设、实现和统计证据；主题精炼产生文本关联及可复核股票池；体制分类产生状态，固定配置表负责资产权重。三者共用时点数据、费用后回测、风险及审计，但职责和评价对象不同。

已有多Agent回测复核是在回测完成后阅读证据；本次Alpha研究需管理从构想到试验和冻结的全过程，因此不能把旧四角色复核改名成AlphaGPT即视为完成。[现有流程](../agents/financial_multi_agent.md)。

## 研究纪律的具体含义

防p-hacking需要登记所有候选、参数和失败，冻结研究家族、数据切分及预算；对人工与AI采用同一政策。Holm等多重比较方法建立在明确研究家族和适用检验之上，不能自动修复无限次读取同一验证集后自适应调参。本文将其转化为本项目的预登记、验证反馈隔离和留出访问约束。[Harvey与Liu作者公开论文](https://people.duke.edu/~charvey/Research/Published_Papers/P116_Evaluating_trading_strategies.pdf)。

净收益、Sharpe和回撤之外，需要披露试验选择与分布假设。DSR论文讨论选择偏差和非正态；本设计先实现可独立验证的区块检验与家族校正，DSR作为后续独立校准项，不能只显示一个名称就宣称消除过拟合。[Bailey与López de Prado作者论文](https://www.davidhbailey.com/dhbpapers/deflated-sharpe.pdf)。

技术门槛的判断依据应是独立计算、因果不变量、真实成本与风险约束；经济逻辑应在看到验证成绩前登记。人工评审与Agent意见分别保留，不把模型生成的“已审查”当成真实测试或投委会决议。

## 防泄露需要哪些资料

宏观观察期和发布/修订时间不同。FRED默认实时区间是今天，ALFRED能按历史实时区间取当时已知资料，因此简单对今日修订值加滞后并不构成历史PIT数据。[圣路易斯联储实时区间文档](https://fred.stlouisfed.org/docs/api/fred/realtime_period.html)。

本项目设计分离观察日期、发布、可得、版本和入库时间，决策时点只选择当时可用版本；相对日期匿名时还要排除新闻标题、文件名、工具元数据、当前知识和未来研究记忆中的事件线索。

匿名化仍不能让模型忘记训练中过去事件的结局。即使输入因果检查通过，也需把历史回放与冻结后前向模拟分开报告。缺少历史版本、真实模型或足够样本时保持不可用或证据不足，不能通过补造日期或合成数据变成真实结论。

## 实施落点

统一入口建议放“策略构建 → Alpha研究”，AI工作台工作流中心提供同任务跳转；现有图形工坊接入经审核的研究产物，组合与Risk继续管理资金和约束。生成Python先采用受控因子定义编译并提供审阅源码，不让未知生成代码自动进入服务主进程。

详细范围、接口、阶段与验收见[23号设计](../../../doc/agents/alpha_mining_research_design.md)。实现仅复用现有项目研究接口；真实模型能输出错误字段，系统必须独立核对并保留拒绝证据，不能将调用成功等同研究通过。
