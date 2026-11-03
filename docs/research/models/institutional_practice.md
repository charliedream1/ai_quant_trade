# 模型策略的机构应用与项目选型

调研日期：2026-10-19。依据机构官网与项目官方文档；模型名称不是投资效果保证。

## 机构应用证据

| 来源 | 公开内容 | 可以得出的结论 | 不能据此断言 |
| --- | --- | --- | --- |
| BlackRock，2025 年 AIM 白皮书 | 框架支持正则化线性模型、梯度提升集成与神经网络，并把预测接入成本和组合约束 | 成熟模型类别仍被纳入机构投资框架 | 具体基金使用哪个开源库，或公开案例等同实盘收益 |
| Robeco，2025-07-17 | 量化策略已加入多种机器学习信号；解释神经网络与梯度提升树 | 机器学习进入实际投资流程，不只停留在教材 | 所有策略均使用 LightGBM，或模型架构完全公开 |
| Robeco，2026-03-03 | 发布机器学习驱动的 NextGen Global Small Cap ETF | 有实际产品层面的机器学习应用 | 其底层模型就是本项目的小型示例 |
| Man Numeric，技术文章 | 展示 XGBoost 与 SHAP 的组合归因案例 | 树模型可用于收益归因与解释 | 该案例已经证明 XGBoost 选股的实盘成绩 |

“模型老”不意味着没有应用价值。要对照数据可用时点、预测目标、组合构建、换手和交易成本评价；机构公开材料不足以认定随机森林、LSTM、GRU 都是当前主力模型。上一轮六算法清单因此收敛为以下三套研究策略。

## 本项目首批实现

| 策略 | 目标 | 实现边界 |
| --- | --- | --- |
| LightGBM 截面选股 | 学习量价特征与后续相对收益，预测后选前列标的 | 浅树、滚动重训、按日期验证、下一交易日开盘执行 |
| XGBoost 截面选股 | 在一致特征和交易口径下比较另一种梯度提升实现 | 与 LightGBM 使用同一时间契约，支持成本和归因查询 |
| 小型 MLP 多因子融合 | 两隐藏层网络融合因子，平均多个种子的预测 | 标准化只拟合训练段，CPU 训练，预测与验证隔离 |

当前特征仅来自 OHLCV，包括滞后收益、动量、波动率、均线偏离、振幅与量比。本轮没有完整行业分类、历史成分股、时点财报或长期数据仓库，不能称为机构策略复现。行业中性、容量估计和完整组合优化仍需后续数据支持。

## 验证口径

- 只有实际拟合与样本外预测次数大于零才算模型链路通过；仅预热成功不算训练成功。
- 按日期切分训练与验证，训练标签到期日早于验证特征起始日；预测只读取执行日前的数据。
- 回测只接受开盘价订单，使用上一交易日形成的排名；股票池日期未对齐时拒绝执行。
- 合成样本只验证因果顺序、边界和撮合；真实行情验证另记来源、有效日期、成交、成本和耗时。
- 当前历史接口最多 240 根日线，属于小样本集成验收，无法据此证明长期超额收益。

## 官方来源

1. [BlackRock：Augmented Investment Management](https://www.blackrock.com/gls-download/literature/whitepaper/augmented-investment-management.pdf)，2025，机构框架说明。
2. [Robeco：From black box to glass box](https://www.robeco.com/en-sg/insights/2025/07/from-black-box-to-glass-box-understanding-and-attributing-machine-learning-models)，2025-07-17，机构应用与解释说明。
3. [Robeco：NextGen Global Small Cap ETF 发布](https://www.robeco.com/en-int/media/press-release/robeco-launches-innovative-ai-driven-nextgen-global-small-cap-etf)，2026-03-03，产品应用。
4. [Man Numeric：Shining Light into the Machine Learning Black Box](https://www.man.com/insights/shining-light-machine-learning)，组合归因技术案例，网页未明确发布日期。
5. [Qlib 模型基准](https://github.com/microsoft/qlib/blob/main/examples/benchmarks/README.md)，开源研究基准。
6. [FreqAI 模型配置](https://www.freqtrade.io/en/stable/freqai-configuration/)，开源工程参考。
7. [FinRL-Trading 机器学习选股](https://github.com/AI4Finance-Foundation/FinRL-Trading/blob/master/ML_STOCK_SELECTION.md)，开源选股实现参考。
