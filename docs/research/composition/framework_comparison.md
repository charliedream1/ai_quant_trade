# 可组合量化策略的开源机制参考

2026-10-22 核查。本文调研组件机制，为项目 14 号设计提供依据；不统计机构使用率，不将开源功能或历史论文结果作为本项目收益证明。

| 官方来源 | 核查到的机制 | 本项目采用或保留的边界 |
| --- | --- | --- |
| [LEAN Alpha](https://www.quantconnect.com/docs/v2/writing-algorithms/algorithm-framework/alpha/key-concepts) | 一个算法可以接收多个有来源的 Alpha 信号，交给组合层处理 | 组件唯一命名，信号融合与资金分配分离；逻辑多模型不等于线程并行 |
| [LEAN Portfolio](https://www.quantconnect.com/docs/v2/writing-algorithms/algorithm-framework/portfolio-construction/key-concepts) | 预测集合转成持仓目标，之后进入风险管理 | 增加独立目标组合契约，不让多个评分分支各自下单 |
| [LEAN Risk](https://www.quantconnect.com/docs/v2/writing-algorithms/algorithm-framework/risk-management/key-concepts) | 多个风险组件可以依次调整目标；清仓信号需要处理以免重新入场 | 保存顺序、冷却与实际执行状态，合并账户硬限额，不由投票解除 |
| [Qlib Portfolio Strategy](https://qlib.readthedocs.io/en/latest/component/strategy.html) | 组合可从预测分数生成，提供目标权重及 TopkDropout 等接口 | 复用职责分离；现有 Qlib 外部 Workflow 不直接视为新组合引擎已支持 |
| [PyPortfolioOpt HRP](https://pyportfolioopt.readthedocs.io/en/latest/OtherOptimizers.html) | 根据资产相关性进行层次配置，提供可替换优化接口 | HRP 与等权/逆波动率做同口径对照，不声称普遍更优 |
| [PyPortfolioOpt CVaR](https://pyportfolioopt.readthedocs.io/en/latest/GeneralEfficientFrontier.html) | 支持基于收益情景的尾部风险优化及可行性约束 | 需要足量数据和求解诊断；240 根日线不足以证明稳健尾部控制 |
| [scikit-learn TimeSeriesSplit](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html) | 按时间顺序划分样本，并可留 gap | 截面按日期一起切分，另按金融标签覆盖时间检查跨界；不只按行随机分割 |

## 项目选择

第一批采用轻量注册表、类型化无环图、冻结参数和既有模型后端，建立可验证的规则级联、并行评分、目标组合与持续风控。先补齐时间轴和账本，再增加高级分配器。

本轮不安装 LEAN、PyPortfolioOpt 或 Riskfolio。直接迁入完整框架会改变数据、策略接口和执行语义；是否引入可选优化库需在实施阶段核验所需功能、许可证、依赖安全及实际可用版本。基础能力优先复用项目已有数值/模型环境。

Agent 定位为研究终审。候选来源、数据时点、可用工具和后续确定性风控均由平台控制；旧回测复核可提供方法，但其事后证据不适合作为历史当期交易输入。关于当前金融多 Agent 应用证据，继续参见[已有调研](../agents/financial_multi_agent.md)。

正式设计见项目 `doc/strategies/strategy_composition_risk_portfolio_design.md`，帮助站点的概要见[组合原理（设计）](../../principles/strategy_composition.md)。

2026-10-23补充：[PandaQuantFlow图形编排核查](panda_quantflow_review.md)提供节点式界面与Gradio组件方案，正式交互设计见项目 `doc/strategies/gradio_visual_strategy_editor_design.md`。该增强尚未实施，不与14号已交付编排混为一谈。
