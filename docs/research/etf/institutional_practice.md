# ETF 真实应用与项目边界

调研日期：2026-10-20。结论区分 ETF 载体、量化/因子产品、AI/机器学习产品和本项目可验证能力。

## 公开证据

| 证据 | 公开内容 | 结论 |
| --- | --- | --- |
| ICI 2025 统计 | 美国 ETF 年末资产约 13.4 万亿美元，占投资公司资产约 30% | ETF 已是主流投资载体 |
| SEC 主动 ETF 研究 | 主动 ETF 资产占比仍较小，但数量和资产近年持续增长 | 主动/量化 ETF 已产品化，但不是 ETF 市场主体 |
| BlackRock 2025 Form 10-K | iShares ETF AUM 约 5.5 万亿美元，2025 年 ETF 净流入约 5270 亿美元 | ETF 被机构和零售组合广泛使用 |
| J.P. Morgan 2026 | 主动 ETF AUM 超过 2000 亿美元 | 主动 ETF 有真实资金规模 |
| Robeco 2026 | 推出机器学习驱动的全球小盘主动 ETF，组合经理仍负责模型假设与极端环境判断 | AI/ML ETF 已有真实产品，但采用“模型 + 人工治理” |

## 对本项目的含义

ETF 轮动和趋势配置适合作为真实资产池研究功能；必须配套基准、调仓、价差、费用、成交额、换手、容量和数据时点。当前 `etf_universes.yaml` 只保存研究池和公开元数据，不能代替基金公告或完整基金数据库。

多 Agent 适合作为 ETF 研究复核和报告协作层，角色可检查池构成、数据源、费用、流动性、换手、回撤和跟踪误差。它不是收益策略本身，也不应绕过回测、风控和人工审批直接下单。

## 来源

- [ICI ETF FAQs](https://www.ici.org/faqs/faqs_etfs_other_invest)
- [SEC：The Fast-Growing Market of Active ETFs](https://www.sec.gov/file/dera-fast-growing-mrkt-2602pdf)
- [BlackRock 2025 Form 10-K](https://www.sec.gov/Archives/edgar/data/2012383/000130817926000264/blk015204-arsa.pdf)
- [J.P. Morgan：largest active ETF provider](https://am.jpmorgan.com/hk/en/asset-management/per/insights/etf-insights/largest-active-etf-provider/)
- [Robeco：AI-driven NextGen Global Small Cap ETF](https://www.robeco.com/en-int/media/press-release/robeco-launches-innovative-ai-driven-nextgen-global-small-cap-etf)
