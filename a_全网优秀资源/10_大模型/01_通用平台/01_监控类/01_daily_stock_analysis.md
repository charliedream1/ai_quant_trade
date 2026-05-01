- Github (33k stars): [ZhuLinsen/daily\_stock\_analysis: LLM驱动的 A/H/美股智能分析器：多数据源行情 + 实时新闻 + LLM决策仪表盘 + 多渠道推送，零成本定时运行，纯白嫖. LLM-powered stock analysis system for A/H/US markets.](https://github.com/ZhuLinsen/daily_stock_analysis)

基于 AI 大模型的 A股/港股/美股自选股智能分析系统，每日自动分析并推送「决策仪表盘」到企业微信/飞书/Telegram/Discord/Slack/邮箱


## ✨ 功能特性

[](https://github.com/ZhuLinsen/daily_stock_analysis#-%E5%8A%9F%E8%83%BD%E7%89%B9%E6%80%A7)


| 模块       | 功能           | 说明                                                                     |
| ---------- | -------------- | ------------------------------------------------------------------------ |
| AI         | 决策仪表盘     | 一句话核心结论 + 评分 + 买卖点位 + 风险警报 + 操作检查清单               |
| 分析       | 多维度分析     | 技术面、实时行情、筹码分布、新闻舆情、公告、资金流与基本面聚合           |
| 市场       | 全球市场       | 支持 A股、港股、美股、美股指数及常见 ETF                                 |
| 策略       | 市场策略系统   | 内置 A股复盘、美股 Regime、均线、缠论、波浪、情绪周期等策略能力          |
| 复盘       | 大盘复盘       | 每日市场概览、指数表现、涨跌统计与板块强弱（支持 cn / hk / us / both）   |
| Web        | 双主题工作台   | 支持手动分析、配置管理、任务进度、历史报告、回测、持仓管理               |
| 导入       | 智能导入与补全 | 支持图片、CSV/Excel、剪贴板导入，自选股输入支持代码/名称/拼音/别名补全   |
| 历史       | 报告管理       | 支持历史报告查看、完整 Markdown 报告、重新分析与批量管理                 |
| 回测       | AI 回测验证    | 对历史分析进行事后验证，查看方向准确率和模拟收益                         |
| Agent 问股 | 策略对话       | 多轮策略问答，支持均线金叉/缠论/波浪等 11 种内置策略，Web/Bot/API 全链路 |
| 推送       | 多渠道通知     | 支持企业微信、飞书、Telegram、Discord、Slack、邮件等主流渠道             |
| 自动化     | 定时运行       | 支持 GitHub Actions、Docker、本地定时任务和 FastAPI 服务模式             |


### 技术栈与数据来源

[](https://github.com/ZhuLinsen/daily_stock_analysis#%E6%8A%80%E6%9C%AF%E6%A0%88%E4%B8%8E%E6%95%B0%E6%8D%AE%E6%9D%A5%E6%BA%90)


| 类型     | 支持                                                                                                                                                                                                                                                                                        |
| -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| AI 模型  | [AIHubMix](https://aihubmix.com/?aff=CfMq)、Gemini、OpenAI 兼容、DeepSeek、通义千问、Claude、Ollama 本地模型等                                                                                                                                                                              |
| 行情数据 | [TickFlow](https://tickflow.org/auth/register?ref=WDSGSPS5XC)、AkShare、Tushare、Pytdx、Baostock、YFinance、Longbridge                                                                                                                                                                      |
| 新闻搜索 | [Anspire](https://aisearch.anspire.cn/)、[SerpAPI](https://serpapi.com/baidu-search-api?utm_source=github_daily_stock_analysis)、[Tavily](https://tavily.com/)、[Bocha](https://open.bocha.cn/)、[Brave](https://brave.com/search/api/)、[MiniMax](https://platform.minimaxi.com/)、SearXNG |
| 社交舆情 | [Stock Sentiment API](https://api.adanos.org/docs)（Reddit / X / Polymarket，仅美股，可选）                                                                                                                                                                                                 |


**新闻源配置（推荐）**

新闻源会显著影响舆情、公告、事件和催化因素质量，建议至少配置一个搜索服务。


| Secret 名称         | 说明                                                                                                                       | 必填 |
| ------------------- | -------------------------------------------------------------------------------------------------------------------------- | :--: |
| `ANSPIRE_API_KEYS`  | [Anspire AI Search](https://aisearch.anspire.cn/)：中文内容特别优化，可增强 A 股分析效果                                   | 推荐 |
| `SERPAPI_API_KEYS`  | [SerpAPI](https://serpapi.com/baidu-search-api?utm_source=github_daily_stock_analysis)：搜索引擎结果补强，适合实时金融新闻 | 推荐 |
| `TAVILY_API_KEYS`   | [Tavily](https://tavily.com/)：通用新闻搜索 API                                                                            | 可选 |
| `BOCHA_API_KEYS`    | [博查搜索](https://open.bocha.cn/)：中文搜索优化，支持 AI 摘要                                                             | 可选 |
| `BRAVE_API_KEYS`    | [Brave Search](https://brave.com/search/api/)：隐私优先，美股资讯补强                                                      | 可选 |
| `MINIMAX_API_KEYS`  | [MiniMax](https://platform.minimaxi.com/)：结构化搜索结果                                                                  | 可选 |
| `SEARXNG_BASE_URLS` | SearXNG 自建实例：无配额兜底，适合私有部署                                                                                 | 可选 |
