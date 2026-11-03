# 轻量模型策略新增方案

2026-10-19 更新，Codex。状态：用户已确认，首批按三套完整模型策略与一个多 Agent 复核流程实施。机构调研归档见 `docs/research/`。

## 目标与选型

在现有规则策略之外，增加可从预制策略入口导入、实际训练、预测并回测的轻量模型策略。首批面向 CPU 小样本验收，不以回测盈利作为功能通过条件。

| 模型 | 类型 | 拟定的小模型规模 | 用途 |
| --- | --- | --- | --- |
| LightGBM 截面选股 | 梯度提升回归 | 60 棵树、15 个叶节点 | 学习后续相对收益并选择排名靠前标的 |
| XGBoost 截面选股 | 梯度提升回归 | 60 棵树、最大深度 3 | 同口径的树模型对照策略 |
| 小型 MLP 多因子融合 | 深度学习集成 | 32/16 两隐藏层、两个种子 | 平均多网络预测后进行截面选股 |

以上规模为初始建议，训练窗口、树数、隐藏单元、迭代轮数、随机种子、线程数和信号阈值均写入 YAML，最终报告记录实际配置与参数量。模型名称用于区分算法，不表示复现外部项目的完整基准绩效。

选型依据包括开源模型基准和机构应用，完整来源与证据边界见 `docs/research/models/institutional_practice.md`。首批聚焦以上三套完整流程；随机森林、LSTM、GRU 留作后续对比，不把开源库支持误当作机构当前主力模型的证明。

实际测试环境为项目内 `.venv-models`，复用既有 py311 的基础包，并在本项目隔离安装 LightGBM 4.6.0；scikit-learn 1.8.0、XGBoost 3.1.3、PyTorch 2.9.1+cpu、NumPy 2.4.6 均实际运行。版本见 `requirements-models.txt`，未修改 conda 环境包。

## 与现有系统衔接

- 源码在 src 下按特征构造、训练/预测、模型后端、策略适配分类；egs 下提供三个薄策略入口及 YAML 配置，复用现有预制策略介绍和导入流程。
- 复用统一策略端口、安全校验、dry-run、策略启用、回测和归因查询。导入预检只验证依赖与端口，不在单根样例行情上训练。
- 模型依赖作为可选依赖记录实际测试版本；仅执行模型策略时加载后端。缺少依赖或样本不足时明确报告原因，禁止退回伪模型、随机预测或技术指标替代模型。
- 保留前轮尚未提交的回测报告改动；本轮不清理未获删除授权的历史测试目录，不修改项目外文件和 conda 环境包。

## 特征、标签与执行时间

- 统一使用有明确历史时点的 OHLCV 衍生特征：滞后收益、动量、波动率、均线偏离、日内振幅、量比。只使用预测时点已知的数据。
- 标签使用指定预测周期的后续收益，按当日股票池去均值形成相对收益；训练只能使用已经到期的标签，周期和选股阈值在 YAML 配置。
- 神经网络的归一化仅拟合训练段，验证和测试段仅变换；树模型保留一致的特征列顺序。
- 按交易日期顺序切分训练、验证与样本外测试，标签跨期处保留隔离间距。多标的切分按日期进行，禁止同日未来数据混入训练。
- 收盘后形成的预测缓存到下一根可交易行情才发出委托，默认按下一交易日开盘执行；不得将当天收盘信息按当天开盘价成交。
- 前期历史用于预热，满足最小训练量后才预测；采用配置的滚动训练间隔，避免每根行情重复训练。

## 数据与能力边界

当前回测加载器和真实 K 线接口最多读取 240 根；mock 数据最多 120 根且基本单边上涨，可能只有单一标签类别。第一轮验收在实际可取得的历史长度内设置训练窗口与测试段，明确报告真实日期、有效样本量、类别分布和预热长度，不宣称长期有效性。

mock 测试用于接口与边界；离线涨跌样本用于训练和时序契约测试；真实行情另行执行三个模型的小样本训练、预测和回测。真实源不可访问或有效日期不足时，应保留失败证据并标记未通过，不把 mock 结果计为真实行情验收。当前采用回归目标，不要求分类标签必须有两类。

## 结果说明

参数选择与留档现由统一策略参数流程管理：模型默认 YAML、已保存默认值、所选方案和运行覆盖逐层合并。预览只读配置，不触发训练；回测保存完整配置、种子、验证比例、策略与模型源码摘要及实际数据证据。规则与页面说明见 `10_strategy_parameter_design.md`。

训练摘要记录模型名称、训练/验证日期、标签到期日、样本数、训练次数、耗时、种子、树规模或网络配置、样本外预测与信号次数；当前记录验证与样本外 MSE，不以分类准确率或 AUC 评价回归策略。

组合评价复用收益、风险、交易、成本和回撤报告。零交易可作为合法策略结果，但必须证明模型实际完成训练和预测；不能把仅完成预热的任务计为模型验证通过。行业轮动和原有规则策略继续保留自身定位。

## 验收计划

1. 依次验证三个示例的依赖、AST 校验、导入、默认 YAML 参数、启用和端口执行。
2. 检查真实拟合次数大于零、权重或树结构有效、预测数值有限、输出维度正确。
3. 测试改动未来数据不改变历史预测、标准化不读取测试段、标签成熟与信号延迟均符合时间契约。
4. 执行三个模型的样本外小样本回测，核对日期、资产、持仓、成交、佣金、净值和归因；记录真实行情与合成样本的来源区别。
5. 实际操作预制策略导入和回测页面，检查训练等待状态、错误提示、结果可读性和耗时；训练不得发生在首屏加载期间。
6. Review 后运行相关单测、集成测试和全量回归，以及 mypy、Ruff、pip-audit、Semgrep、Bandit；缺工具或环境问题单独记录，不修改 conda 包来掩盖问题。
7. 更新 README、策略端口设计、帮助和当周 changelog；检查 UTF-8 中文与 Windows/Linux 路径兼容；停止本轮服务。测试临时文件按用户逐项删除确认规则清理。

## 多 Agent 复核

ETF 策略与 ETF 专用复核流程见 `doc/11_etf_strategy_design.md`。ETF 轮动和趋势策略复用统一端口、参数方案和回测快照；多 Agent 只复核 ETF 池、基准、费用、流动性、换手和跟踪误差，不开放委托权限。

新增模型分析、风控审查、独立复核与投研汇总四阶段，每阶段实际调用普通文本模型，通过文本 ReAct 读取已完成的回测和前序角色结果；JSON 使用 json_repair 后再进行字段与证据引用校验。生成研究复核报告，不开放委托能力。角色状态、工具轨迹和输出会持久保存；接口未配置或调用失败时明确失败，不把 mock 回复计为真实 Agent 验证。机构案例与本项目边界见 `docs/research/agents/financial_multi_agent.md`。

## 官方参考

- [Qlib 模型基准](https://github.com/microsoft/qlib/blob/main/examples/benchmarks/README.md)
- [FreqAI 模型配置](https://www.freqtrade.io/en/stable/freqai-configuration/)
- [FinRL-Trading 机器学习选股](https://github.com/AI4Finance-Foundation/FinRL-Trading/blob/master/ML_STOCK_SELECTION.md)
- [LightGBM 参数与训练速度](https://lightgbm.readthedocs.io/en/stable/Parameters-Tuning.html)
- [scikit-learn RandomForestClassifier](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.RandomForestClassifier.html)
- [XGBoost Python API](https://xgboost.readthedocs.io/en/stable/python/python_api.html)
- [scikit-learn TimeSeriesSplit](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html)
- [scikit-learn 数据泄漏与预处理](https://scikit-learn.org/stable/common_pitfalls.html)
- [PyTorch GRU](https://docs.pytorch.org/docs/main/generated/torch.nn.GRU.html)
- [PyTorch LSTM](https://docs.pytorch.org/docs/main/generated/torch.nn.LSTM.html)
