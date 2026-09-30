# AI 量化交易操盘手

<p align="center">
  <img src="https://raw.githubusercontent.com/charliedream1/ai_quant_trade/master/.README_images/LOGO_NEW.png" width="200" alt="logo" />
</p>

> **一站式 AI 量化交易平台 · 从学习、模拟到实盘**

本站收录项目实战教程、文档与社区入口。代码与各项目说明托管在
[GitHub 仓库](https://github.com/charliedream1/ai_quant_trade)，本文档由
[MkDocs Material](https://squidfunk.github.io/mkdocs-material/) 驱动。

---

## 项目集

<div class="grid cards" markdown>

-   :material-chart-line: __交易策略（8 个项目）__

    ---

    - [双均线策略](egs_trade/vanilla/double_ma/README.md) — 经典入门回测
    - [动量轮动](egs_trade/vanilla/momentum_rotation/README.md)
    - [组合优化](egs_trade/vanilla/portfolio_optimization/README.md)
    - [PPO 强化学习](egs_trade/rl/a001_proto_sb3/README.md)
    - [finRL NeurIPS 复现](egs_trade/rl/a002_finRL_tutorial/a01_Stock_NeurIPS2018/README.md)
    - [Qlib 多股票](egs_trade/ms_qlib/README.md)
    - [Wind 实盘](egs_trade/paper_trade/wind/README.md)
    - [双均线文档教程](egs_trade/vanilla/double_ma/文档教程/README.md)

-   :material-database: __数据源（24 个数据源）__

    ---

    - [Tushare](egs_data/股票/tushare/README.md) · [Wind](egs_data/股票/wind/README.md) · [AKShare](egs_data/股票/akshare/README.md)
    - [Baostock](egs_data/股票/baostock/README.md) · [巨潮资讯](egs_data/股票/cninfo/README.md) · [东方财富](egs_data/股票/eastmoney/README.md)
    - [EFinance](egs_data/股票/efinance/README.md) · [网易](egs_data/股票/netease/README.md) · [Qlib 数据](egs_data/股票/qlib/README.md)
    - [QStock](egs_data/股票/qstock/README.md) · [腾讯](egs_data/股票/tencent/README.md) · [Web API](egs_data/股票/web_api/README.md)
    - [YFinance](egs_data/股票/yfinance/README.md)
    - [基金](egs_data/基金/fund/README.md) · [期货](egs_data/期货/futures/README.md)
    - [加密货币 CCXT](egs_data/电子币/ccxt/README.md) · [CryptoCompare](egs_data/电子币/cryptocompare/README.md)
    - [宏观经济 FRED](egs_data/宏观经济/fred/README.md) · [世界银行](egs_data/宏观经济/world_bank/README.md)
    - [雪球](egs_data/新闻/xueqiu/README.md) · [Finnhub](egs_data/新闻/finnhub/README.md) · [GDELT](egs_data/新闻/gdelt/README.md) · [NewsAPI](egs_data/新闻/news_api/README.md)

-   :material-flask: __因子挖掘（5 个项目）__

    ---

    - [Alpha101 因子库](egs_alpha/alpha_libs/alpha101/README.md)
    - [Stockstats](egs_alpha/alpha_libs/stockstats/README.md)
    - [TA-Lib](egs_alpha/alpha_libs/ta_lib/README.md)
    - [auto_alpha](egs_alpha/auto_alpha/README.md)
    - [tsfresh](egs_alpha/auto_alpha/tsfresh/README.md)

-   :material-robot: __大模型与 Skill（5 个项目）__

    ---

    - [Unsloth 股票预测训练](egs_llm/a01_train/a01_unsloth_stock_forcaster/README.md)
    - [模型下载](egs_llm/a01_train/a01_unsloth_stock_forcaster/a01_download_mdl/README.md)
    - [模型训练](egs_llm/a01_train/a01_unsloth_stock_forcaster/a04_train/README.md)
    - [热点报告生成](egs_llm/b01_app/a01_hot_topic_report/v1_proto_internet/README.md)
    - [券商研报 Skill](egs_skill/broker-research-analyst/README.md)

-   :material-message-text: __金融 NLP 与在线平台__

    ---

    - [情感分析](egs_fin_nlp/emotion_analysis/01_StructBert_Binary_Class/README.md)
    - [聚宽说明](egs_online_platform/聚宽_JoinQuant/说明.md)
    - [优矿说明](egs_online_platform/优矿_Uqer/说明.md)

-   :material-tools: __辅助工具__

    ---

    - [看盘神器 v1](egs_aide/看盘神器/v1/README.md)
    - [看盘神器 v2](egs_aide/看盘神器/v2/README.md)

</div>

---

## 站点导航

<div class="grid cards" markdown>

-   :material-book-open-page-variant: __学习笔记__

    ---

    收录 `ai_notes/` 下的精选理论、论文与坑点笔记。

    [论文笔记 →](ai_notes/03_论文/README.md) ·
    [论文导航 →](ai_notes/03_论文/01_papers_with_code.md) ·
    [GPT 金融分析 →](ai_notes/03_论文/01_大模型/01_通用金融/01_GPT金融分析.md)

-   :material-help-circle: __教程与 FAQ__

    ---

    各项目的使用说明、FAQ、研究文档。

    [Unsloth FAQ →](egs_llm/a01_train/a01_unsloth_stock_forcaster/a00_FAQ/01_FAQ.md) ·
    [Skill 文档 →](egs_skill/broker-research-analyst/SKILL.md) ·
    [PDF 解析研究 →](egs_skill/PDF_PARSER_RESEARCH.md) ·
    [更多 →](教程FAQ.md)

-   :material-cog: __进阶__

    ---

    环境配置、常见问题、部署运维。

    [GPU 环境配置 →](01_环境配置/01_GPU环境配置/01_Win下GPU配置.md) ·
    [Conda 安装 →](01_环境配置/02_python环境配置/01_conda安装.md) ·
    [GitHub 问题 →](02_常见问题/02_Github问题.md)

-   :material-rocket-launch: __部署运维__

    ---

    文档站发布到 GitHub Pages / Cloudflare Pages。

    [发布操作指南 →](04_website_deployment/发布操作指南.md) ·
    [Cloudflare 部署 →](04_website_deployment/Cloudflare_Pages_部署指南.md)

-   :material-account-group: __社区__

    ---

    知识星球介绍与新人指南。

    [星球介绍 →](03_星球使用和介绍/01_星球介绍.md) ·
    [新人指南 →](03_星球使用和介绍/02_新人使用指南.md)

</div>

---

## 核心亮点

| 维度 | 说明 |
|:---:|:---|
| 一站式平台 | 从学习、模拟到实盘，全流程覆盖 |
| 多元策略 | 大模型、因子挖掘、传统策略、机器学习、深度学习、强化学习、图网络 |
| 24+ 数据源 | 股票 / 基金 / 期货 / 加密货币 / 宏观 / 新闻 |
| 资源汇总 | 全网资源、实战案例、论文解读、代码实现 |
| 辅助工具 | 辅助盯盘、股票推荐等实用操盘工具 |

---

## 贡献与社区

- 提交 PR：请参考仓库根目录 [CONTRIBUTING.md](https://github.com/charliedream1/ai_quant_trade/blob/master/CONTRIBUTING.md)
- 加入 [知识星球](03_星球使用和介绍/01_星球介绍.md) 获取实战答疑

---

## License

[Apache-2.0](https://github.com/charliedream1/ai_quant_trade/blob/master/LICENSE) · Copyright © 2026 charliedream1
