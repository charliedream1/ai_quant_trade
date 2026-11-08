# ETF 策略与多 Agent 投研设计

2026-11-04 extension: cross-asset and sector ETF recipes, dated research inputs, total-return/cash accounting and benchmark-relative methods are specified in [Strategy Extensions and Evidence Design](strategy_extensions_implementation_design.md). Exact methods and public references are maintained in [Strategy Methods](../../docs/principles/strategy_methods.md). The original scope below describes the initial ETF release.

2026-10-20，Codex。用户已确认，按生产研究边界补充 ETF 策略与 ETF 多 Agent 复核。

## 能力定位

ETF 是交易工具和资产池载体，策略仍由轮动、趋势、风险预算或因子组合定义。本项目首期支持配置化 ETF 池、相对强弱轮动和趋势配置。ETF 数据缺失时保留缺失状态，不把缺失字段当作零值；多 Agent 只生成研究报告，不取得委托权限。

## ETF 池与元数据

`egs/config/strategies/etf_universes.yaml` 维护 ETF 池、市场、标签、跟踪基准、类别、费率和调仓频率。`src/data/etf.py:ETFUniverseService` 读取配置并调用现有数据源生成快照，快照记录最新价格、涨跌幅、历史点数、平均成交额、数据源和状态。规模、费率或成交额缺失时返回空值或 unavailable，禁止用模拟数值伪造。

当前提供 A 股核心宽基和行业/主题 ETF 池。配置用于研究筛选和回测解释，不能替代基金公告、实时申赎信息、跟踪误差报告或容量评估。

## 策略与执行

`ETFMomentumRotationStrategy` 使用已经形成的历史相对收益，在调仓日选择排名靠前的 ETF，下一可交易日开盘执行；`ETFTrendAllocationStrategy` 使用延迟移动均线趋势差过滤 ETF，按调仓周期形成买卖信号。两者复用统一策略端口、参数方案、组合约束、成本和回测快照。

策略参数包括池标识、回看窗口、Top-N、调仓周期、趋势阈值和数量。ETF 回测指标额外记录资产类型、ETF 池、换手、相对标的池收益和跟踪误差；跟踪误差是策略净值相对回测标的池等权基准的日收益差年化波动，不代表基金对正式指数的跟踪误差。

## ETF 多 Agent 复核

现有四角色流程增加 `etf_review` 工作流：ETF 池与策略分析员、流动性与费用审查员、ETF 独立复核员、ETF 投研汇总员。角色必须读取 ETF 快照、指标、任务参数和前序意见；证据不足、数据不可用、换手/跟踪误差缺失会形成系统风险提示。协议仍使用普通文本 ReAct、`json_repair`、只读证据和角色留档。

ETF 复核与普通模型复核共用运行报告结构，但记录 workflow 类型和 ETF 证据。任何结论都不等于批准交易，`can_trade` 固定为 false；真实交易仍需确定性回测、流动性和人工风控审批。

## 数据与验证边界

本轮真实验证使用 510300、510500、159915、512100 四只 ETF 的 240 个共同交易日，2025-10-23 至 2026-10-20，Tencent 日 K 复权行情。两套策略各完成一次回测，训练不涉及大模型，输出交易、换手、跟踪误差和参数快照。小样本验证只证明数据、策略端口、调仓延迟、成本和报告链路，不证明长期收益、基金容量或对正式指数的跟踪效果。

后续可增加基金份额、申赎、折溢价、ETF 做市价差、历史成分和正式基准指数数据；这些字段必须取得稳定来源后再纳入实盘约束。
