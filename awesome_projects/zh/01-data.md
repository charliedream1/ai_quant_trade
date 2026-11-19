# 数据

[English](../en/01-data.md) | [中文](../zh/01-data.md) | [分类目录](README.md) | [语言入口](../README.md)

## 推荐数据源

- **[baostock](http://www.baostock.com)** — 免费、免注册的 A 股数据源，Qlib 也使用该数据源。
  - 元数据： 星标数： 不适用（非 GitHub 项目） · 许可证： 参见官网 · 维护状态： 需查阅官网
  - 文档／主页： http://www.baostock.com
  - 使用点评：适合构建 A 股历史数据原型的免费数据源；生产使用前应验证覆盖面与延迟。
- **Wind** — 业内权威的付费数据供应商。
  - 元数据： 星标数： 不适用（商业供应商） · 许可证： 商业许可 · 维护状态： 由供应商维护
  - 文档／主页： https://www.wind.com.cn
  - 使用点评：机构级付费数据源，适用于更重视合规、覆盖面和服务支持的场景。

## 开源数据工具库

- **[qlib](https://github.com/microsoft/qlib)** — 微软 AI 量化框架，提供基于 Yahoo Finance 的数据能力，覆盖中国与美国市场。
  - 元数据： 语言： Python · 星标数： 49,218 · 许可证： MIT · 维护状态： 活跃 (最近推送 2026-10-08)
  - 文档／主页： https://qlib.readthedocs.io/en/latest/
  - 使用点评：可用于评估数据层的覆盖面、时效性与集成成本。
- **[akshare](https://github.com/akfamily/akshare)** — 覆盖面较广、基于爬虫的数据工具库。
  - 元数据： 语言： Python · 星标数： 22,851 · 许可证： MIT · 维护状态： 活跃 (最近推送 2026-10-07)
  - 文档／主页： https://akshare.akfamily.xyz
  - 使用点评：可用于评估数据层的覆盖面、时效性与集成成本。
- **[efinance](https://github.com/Micro-sheep/efinance)** — 基于爬虫的数据工具库，不提供市场指数接口。
  - 元数据： 语言： Python · 星标数： 4,078 · 许可证： MIT · 维护状态： 活跃 (最近推送 2026-07-17)
  - 文档／主页： -
  - 使用点评：可用于评估数据层的覆盖面、时效性与集成成本。
- **[adata](https://github.com/1nchaos/adata)** — A 股数据工具库。
  - 元数据： 语言： Python · 星标数： 5,209 · 许可证： APACHE-2.0 · 维护状态： 近期维护 (最近推送 2025-12-26)
  - 文档／主页： https://adata.30006124.xyz
  - 使用点评：可用于评估数据层的覆盖面、时效性与集成成本。
- **[mootdx](https://github.com/mootdx/mootdx)** — 通达信行情数据。
  - 元数据： 语言： Python · 星标数： 2,293 · 许可证： MIT · 维护状态： 近期维护 (最近推送 2024-07-16)
  - 文档／主页： -
  - 使用点评：可用于评估数据层的覆盖面、时效性与集成成本。
- **[easyquotation](https://github.com/shidenggui/easyquotation)** — 新浪与腾讯的实时行情。
  - 元数据： 语言： Python · 星标数： 5,326 · 许可证： MIT · 维护状态： 活跃 (最近推送 2026-02-28)
  - 文档／主页： -
  - 使用点评：可用于评估数据层的覆盖面、时效性与集成成本。
- **[stock-api](https://github.com/zhangxiangliang/stock-api)** — 股票数据 API。
  - 元数据： 语言： TypeScript · 星标数： 1,963 · 许可证： MIT · 维护状态： 活跃 (最近推送 2026-10-11)
  - 文档／主页： https://zhangxiangliang.github.io/stock-api/
  - 使用点评：可用于评估数据层的覆盖面、时效性与集成成本。
- **[OpenBB](https://github.com/openbq-org/OpenBB)** — 面向分析师、量化研究人员和 AI 智能体的开放数据平台，适用于数据访问、看板和智能体工作流需要共享金融接口的场景。
  - 元数据： 语言： Python · 星标数： 74,092 · 许可证： 其他／自定义 · 维护状态： 活跃 (最近推送 2026-10-02)
  - 文档／主页： https://openbb.co
  - 使用点评：适合作为统一金融数据与分析层的候选方案；商业使用前需审查许可证。

## 多模态与开放数据集

- **[stocknet-dataset](https://github.com/yumoxu/stocknet-dataset)** — 包含 88 只股票两年内的价格变化与推文，数据来自 Twitter 和 Yahoo Finance；对应爱丁堡大学 2018 年论文《基于推文与历史价格的股票走势预测》。
  - 元数据： 语言： 未知 · 星标数： 681 · 许可证： MIT · 维护状态： 不活跃 (最近推送 2019-03-06)
  - 文档／主页： -
  - 使用点评：可用于评估数据层的覆盖面、时效性与集成成本。

## 新闻数据

- **[Horizon](https://github.com/Thysrael/Horizon)** — 开源 AI 新闻雷达：从 Hacker News、RSS、Reddit、Telegram、Twitter/X、GitHub、OpenBB 等多源采集，支持 AI 评分、去重和中英文 Markdown 日报。
  - 元数据： 语言： Python · 星标数： 9,550 · 许可证： MIT · 维护状态： 活跃 (最近推送 2026-10-04)
  - 文档／主页： https://www.horizon1123.top
  - 使用点评：可用于评估数据层的覆盖面、时效性与集成成本。
- **[Listed-company-news-crawl-and-text-analysis](https://github.com/DemonDamon/FinnewsHunter)** — 爬取上市公司新闻并开展文本分析与分类，使用 SVM、随机森林等算法。
  - 元数据： 语言： Python · 星标数： 1,495 · 许可证： APACHE-2.0 · 维护状态： 活跃 (最近推送 2026-10-01)
  - 文档／主页： -
  - 使用点评：可用于评估数据层的覆盖面、时效性与集成成本。
- **[FinnewsHunter](https://github.com/DemonDamon/FinnewsHunter)** — 爬取新浪、Meijin、金融界、中国证券网、证券时报网等财经新闻，用于文本分析与分类。
  - 元数据： 语言： Python · 星标数： 1,495 · 许可证： APACHE-2.0 · 维护状态： 活跃 (最近推送 2026-10-01)
  - 文档／主页： -
  - 使用点评：可用于评估数据层的覆盖面、时效性与集成成本。

## 金融数据源

- **[FinRL-Meta](https://github.com/AI4Finance-Foundation/FinRL-Meta)** — 面向金融深度强化学习的元宇宙平台，提供股票、加密货币、外汇、模拟与实盘交易等动态市场环境。
  - 元数据： 语言： Python · 星标数： 1,946 · 许可证： MIT · 维护状态： 活跃 (最近推送 2026-10-06)
  - 文档／主页： https://ai4finance.org
  - 使用点评：可作为数据源层的候选资源；生产采用前需验证适配性。

- **[Tushare Python SDK](https://github.com/waditu/tushare)** — 中国股票历史数据采集工具。
  - 元数据： 语言： Python · 星标数： 15,421 · 许可证： BSD-3-CLAUSE · 维护状态： 近期维护 (最近推送 2024-03-13)
  - 文档／主页： https://tushare.pro/
  - 使用点评：适合作为 Tushare 数据的 Python 接入层；生产使用前需核验令牌配额与数据授权。

- **[Tushare Pro](https://tushare.pro/)** — 提供高质量 A 股数据的服务，包含付费档位。
  - 元数据： 星标数： 不适用（商业数据服务） · 许可证： 平台使用条款 · 维护状态： 由供应商维护
  - 文档／主页： https://tushare.pro/
  - 使用点评：可作为付费 A 股数据选项；需核验配额、授权与实际运行需求。

- **[yfinance](https://github.com/ranaroussi/yfinance)** — 提供市场历史数据，接入和使用较方便。
  - 元数据： 语言： Python · 星标数： 25,485 · 许可证： APACHE-2.0 · 维护状态： 活跃 (最近推送 2026-10-06)
  - 文档／主页： https://ranaroussi.github.io/yfinance
  - 使用点评：可作为数据源层的候选资源；生产采用前需验证适配性。

- **[WRDS](https://github.com/wharton/wrds)** — 面向学术研究的 Python 数据访问库。
  - 元数据： 语言： Python · 星标数： 160 · 许可证： BSD-3-CLAUSE · 维护状态： 活跃 (最近推送 2026-02-11)
  - 文档／主页： http://wrds.wharton.upenn.edu/
  - 使用点评：可作为数据源层的候选资源；生产采用前需验证适配性。

- **[FinanceDatabase](https://github.com/JerBouma/FinanceDatabase)** — 跨资产证券代码数据库，涵盖股票、ETF、基金、指数、货币、加密货币与货币市场。
  - 元数据： 语言： Python · 星标数： 9,455 · 许可证： MIT · 维护状态： 活跃 (最近推送 2026-10-11)
  - 文档／主页： https://www.jeroenbouma.com/projects/financedatabase
  - 使用点评：可用于维护跨资产代码集合；采用前需验证覆盖面与更新频率。

- **[jqdatasdk](https://github.com/JoinQuant/jqdatasdk)** — 聚宽数据接口，提供 3 个月免费试用，数据质量适合实盘应用。
  - 元数据： 语言： Python · 星标数： 1,208 · 许可证： MIT · 维护状态： 活跃 (最近推送 2026-01-29)
  - 文档／主页： https://www.joinquant.com/
  - 使用点评：可作为数据层的候选资源；生产采用前需验证适配性。

## 时序数据库

- **[qlib-server](https://github.com/microsoft/qlib-server)** — Qlib 数据服务系统，支持在线模式与共享数据服务。
  - 元数据： 语言： Python · 星标数： 394 · 许可证： MIT · 维护状态： 近期维护 (最近推送 2025-12-18)
  - 文档／主页： -
  - 使用点评：可作为数据层的候选资源；生产采用前需验证适配性。

- **[arctic](https://github.com/man-group/arctic)** — 基于 MongoDB 和 Python 的高性能时序与逐笔数据存储。
  - 元数据： 语言： Python · 星标数： 3,087 · 许可证： LGPL-2.1 · 维护状态： 近期维护 (最近推送 2024-04-09)
  - 文档／主页： https://arctic.readthedocs.io/en/latest/
  - 使用点评：可作为数据层的候选资源；生产采用前需验证适配性。

- **[kairosdb](https://github.com/kairosdb/kairosdb)** — 基于 Cassandra 的时序数据库。
  - 元数据： 语言： Java · 星标数： 1,761 · 许可证： APACHE-2.0 · 维护状态： 活跃 (最近推送 2026-03-06)
  - 文档／主页： -
  - 使用点评：可作为数据层的候选资源；生产采用前需验证适配性。

- **[opentsdb](https://github.com/OpenTSDB/opentsdb)** — 基于 HBase 的时序数据库。
  - 元数据： 语言： Java · 星标数： 5,064 · 许可证： LGPL-2.1 · 维护状态： 近期维护 (最近推送 2024-12-13)
  - 文档／主页： http://opentsdb.net
  - 使用点评：可作为数据层的候选资源；生产采用前需验证适配性。
