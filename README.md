<div align="center">

<img src=".README_images/LOGO_NEW.png" width="260" height="270" alt="AI Quantitative Trading Bot" />

# 🤖 AI Quantitative Trading Bot

**One-Stop AI Quantitative Trading Platform · From Learning & Simulation to Live Trading**

[**中文版**](README_ZH.md) | [**日本語版**](README_JA.md)

[![License](https://img.shields.io/badge/License-Apache%202.0-brightgreen.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python-Version](https://img.shields.io/badge/Python-3.8+-brightgreen)](https://github.com/charliedream1/ai_quant_trade)
[![Stars](https://img.shields.io/github/stars/charliedream1/ai_quant_trade?style=social)](https://github.com/charliedream1/ai_quant_trade)

<p>
  <sub>👇 Follow the WeChat account · Join the Knowledge Planet for more hands-on content and video tutorials</sub>
</p>

<a href="https://t.zsxq.com/dHt9l" title="AI智投星球">
  <img src=".README_images/quant_qrcode.jpg" width="150" alt="AI智投星球" />
</a>
&nbsp;&nbsp;&nbsp;&nbsp;
<img src=".README_images/公众号链接.png" width="150" alt="WeChat Official Account" />

</div>

---

<p align="center">
  <a href="#-new-features">🔥 New Features</a> •
  <a href="#-introduction">📖 Introduction</a> •
  <a href="#-quick-start">🚀 Quick Start</a> •
  <a href="#-local-quant-strategies">📊 Quant Strategies</a> •
  <a href="#-llm-applications">🤖 LLMs</a> •
  <a href="#-alpha-mining">⛏️ Alpha Mining</a> •
  <a href="#-data-processing">💾 Data</a> •
  <a href="#-trading-assistant-tools">🛠️ Tools</a> •
  <a href="#-companion-resources">🎁 Resources</a>
</p>

---

## ✨ Core Highlights

| 🎯 Positioning | 📌 Description |
|:---:|:---|
| 🏦 **One-Stop Platform** | Full-process coverage from learning and simulation to live trading |
| 📈 **Diverse Strategies** | LLMs, alpha mining, traditional strategies, ML, DL, RL, GNN, high-frequency trading |
| 📚 **Resource Aggregation** | Curated online resources, real-world case studies, paper interpretations, code implementations |
| 🛠️ **Assistant Tools** | Practical trading helpers such as stock monitoring and stock recommendations |
| 🌍 **Multi-Market Coverage** | Stocks, funds, cryptocurrencies, and other markets |
| 🚀 **Live Deployment** | Supports multiple deployment methods including Python/C++/CPU/GPU |

---

## 🔥 New Features

| **Date** | **Feature** |
|:---|:---|
| 2026.07.25 | 🆕 [**"Stealth Stock Trading" Tool V2: Modular Monitoring System + Alert Monitoring + K-Line Charts + Multi-Source Fallback**](egs_aide/看盘神器/v2) |
| 2025.08.09 | 🆕 [**Reasoning Stock Price Forecasting LLM Training Tutorial (20% accuracy boost, interpretable)**](egs_courses/01_推理型股价预测大模型训练教程.md) |
| 2025.05.17 | 🆕 [**Unsloth Reasoning Stock Forecasting LLM (code in this repo, detailed guide & model on the Planet)**](egs_llm/a01_train/a01_unsloth_stock_forcaster) |
| 2025.01.03 | [**LLM-based Financial Market Analysis (video tutorial on the Planet or WeChat account)**](egs_llm/b01_app/a01_hot_topic_report/v1_proto_internet) |

<details>
<summary>📂 <b>2023 Updates</b></summary>

| **Date** | **Feature** |
|:---|:---|
| 2023.04.09 | [**StructBERT Market Sentiment Analysis**](https://github.com/charliedream1/ai_quant_trade/tree/master/egs_fin_nlp/emotion_analysis/01_StructBert_Binary_Class) |
| 2023.03.28 | [**RL Multi-Stock Trading: 53% Annualized Return**](https://github.com/charliedream1/ai_quant_trade/tree/master/egs_trade/rl/a002_finRL_tutorial/a01_Stock_NeurIPS2018) |
| 2023.02.28 | [**ML Auto-Mining 5,000 Alphas & Stock Trend Prediction**](https://github.com/charliedream1/ai_quant_trade/tree/master/egs_alpha/auto_alpha/tsfresh) |
| 2023.02.05 | [**Stock Monitoring with Excel**](https://github.com/charliedream1/ai_quant_trade/tree/master/egs_aide/%E7%9C%8B%E7%9B%98%E7%A5%9E%E5%99%A8/v1) |
| 2023.01.01 | [**Local Deep RL Strategy**](https://github.com/charliedream1/ai_quant_trade/tree/master/egs_trade/rl/a001_proto_sb3) |

</details>

<details>
<summary>📂 <b>2022 Updates</b></summary>

| **Date** | **Feature** |
|:---|:---|
| 2022.11.07 | [**Wind Local Live Trading Simulation**](https://github.com/charliedream1/ai_quant_trade/tree/master/egs_trade/real_bid_simulate/wind) |
| 2022.08.03 | [**Basic Backtest Framework + Double Moving Average Strategy**](https://github.com/charliedream1/ai_quant_trade/tree/master/egs_trade/vanilla/double_ma) |

</details>

---

## 📖 Introduction

### Target Audience

- 🏢 **Institutional Investors**
- 👨‍💻 **Retail Traders (with programming background)**
- 🌱 **Retail Traders (no programming background)**

### Project Structure

```
ai_quant_trade
├── ai_notes ........... Financial quantitative trading knowledge (Markdown / Jupyter Notebook knowledge system)
│   ├── 资源 ........... Continuously collected excellent resources from across the web
│   ├── 实战 ........... Hands-on usage, frameworks, libraries, and pitfalls
│   └── 热点 ........... Financial market hot topics, tech hot topics, paper interpretations
├── docs ............... Usage documentation for this repo
├── egs_aide ........... Trading assistant tools (monitoring tools, etc.)
├── egs_alpha .......... Alpha library & alpha mining
├── egs_data ........... Data acquisition & processing (Wind / open-source tools)
├── egs_fin_nlp ........ Text analysis (sentiment analysis, etc.)
├── egs_llm ............ LLM applications (stock prediction / financial analysis)
├── egs_online_platform  Online research platform strategies (JoinQuant / Uqer)
├── egs_trade .......... Local quantitative stock trading strategies
│   ├── paper_trade .... Live trading simulation (Wind)
│   ├── rl ............. Reinforcement learning for trading
│   ├── ms_qlib ........ Microsoft Qlib framework
│   └── vanilla ........ Traditional rule-based strategies
├── quant_brain ........ Core algorithm library
├── runtime ............ Model deployment and real-world usage
├── tools .............. Auxiliary tools
├── requirements.txt
└── README.md
```

---

## 🚀 Quick Start

This repository is not packaged as a Python package yet. Please clone the entire project, then navigate to each `egs` directory for detailed **usage instructions** and **principle explanations**.

```bash
# 1. Clone the repo
git clone https://github.com/charliedream1/ai_quant_trade.git

# 2. Install dependencies
pip install -r requirements.txt

# 3. Enter the corresponding example directory and check the README to get started
cd egs_trade/rl/a002_finRL_tutorial/a01_Stock_NeurIPS2018
```

---

## 📊 Local Quantitative Strategies

> 📁 **Code Directory**: [egs_trade](egs_trade)
>
> 🎯 Each example comes with a comprehensive tutorial — from principles and usage to code walkthrough.

You can build an independent quantitative trading system locally, covering the following strategy types:

| Category | Strategy | Status |
|:---:|:---|:---:|
| 🤖 AI Strategies | Reinforcement learning, GNN, DL, ML, HFT, alpha mining, LLMs | ✅ / 🔨 |
| 📐 Traditional Strategies | Rule-based strategies (double MA, portfolio management, etc.) | ✅ |

### 🧠 Reinforcement Learning Strategies

> 📁 **Code Directory**: `egs_trade/rl`

Since the AlphaGo vs. Ke Jie match in 2017, deep reinforcement learning has taken off.

Compared with ML and DL, RL is **goal-oriented** (uses interaction as the objective), while many other methods consider isolated sub-problems (such as "stock price prediction", "market prediction", "trading decision", etc.) and cannot directly obtain interactive actions. RL is directly oriented to "completing the commander's task" and can produce a sequence of actions.

**Strategy List:**

| **No.** | **Strategy** | **Paper** |
|:---:|:---|:---|
| 1 | [Prototype](egs_trade/rl/a001_proto_sb3) | — |
| 2 | [FinRL Tutorial 0 - NeurIPS2018](egs_trade/rl/a002_finRL_tutorial/a01_Stock_NeurIPS2018) | [Practical Deep Reinforcement Learning Approach for Stock Trading](https://arxiv.org/abs/1811.07522) |

**Backtest Results:**

| **No.** | **Strategy** | **Market** | **Annualized Return** | **Max Drawdown** | **Sharpe Ratio** |
|:---:|:---|:---|:---:|:---:|:---:|
| 1 | [Prototype](egs_trade/rl/a001_proto_sb3) | China A-Shares | — | — | — |
| 2 | [FinRL Tutorial 0 - NeurIPS2018](egs_trade/rl/a002_finRL_tutorial/a01_Stock_NeurIPS2018) | US Dow Jones 30 | 53.1% | -10.4% | 2.17 |

### 📐 Traditional Strategies

> Although traditional strategies may seem outdated, they are more operable and still have some practical value. DL and ML often need to be combined with rules to work effectively.

1. **[Double Moving Average Strategy + Simple Handwritten Backtest Framework](egs_trade/vanilla/double_ma)**
   - [Detailed Tutorial](egs_trade/vanilla/double_ma/文档教程)
   - Includes strategy code + self-built pure handwritten backtest framework
   - Includes nice plotting indicating buy/sell points
   - 🎯 Goal: Through this example, understand how to build a complete quantitative trading framework

2. **[Portfolio Management 7-Lesson Course](egs_trade/vanilla/portfolio_optimization)**

---

## 💰 Live Trading

> 📁 **Code Directory**: [egs_trade](egs_trade)

### Live Trading Simulation

1. **[Wind Local Live Trading Simulation: Double MA Strategy](egs_trade/paper_trade/wind)**
   - Live trading simulation implemented with Wind software
   - Wind is often the data source of choice for major financial institutions; due to its high price, it's more suitable for institutions
   - 🏢 Target Users: Institutions

---

## 🛠️ Trading Assistant Tools

> 📁 **Code Directory**: [egs_aide](egs_aide)

1. **[Stock Monitoring with Excel V1](egs_aide/看盘神器/v1)**
   - 👀 Hard to be spotted while monitoring stocks
   - 📋 Customizable stock watchlist
   - ⚡ Use Excel for fast calculation and data processing

2. **["Stealth Stock Trading" Tool V2: Modular Monitoring System](egs_aide/看盘神器/v2)** 🆕

   ![Monitoring Tool V2 Demo](egs_aide/看盘神器/v2/看盘神器V2演示.gif)

   - 🏗️ **Architecture Refactor**: Upgraded from a single file to a modular `excel_monitor` package with Sheet Handler pattern; each Sheet refresh is isolated
   - 🔔 **Alert Monitoring**: Customizable upper/lower price/change limits; triggered rows turn red + popup reminders
   - 📈 **K-Line Charts**: Draw K-line charts with a button click in Excel (mplfinance candlestick + MA lines), no need to switch software
   - 💰 **Capital Sentiment**: New Sheet aggregating northbound capital + Weibo sentiment + news sentiment + Guba hot posts
   - 🔍 **Stock Pool Selection**: Built-in all A-shares; fuzzy search by code/name/pinyin initial + dropdown selection, no need to look up codes
   - 🔄 **Multi-Source Fallback**: qstock main source + akshare/Eastmoney/Tencent/NetEase/efinance backups; auto-switch when one fails
   - ⚙️ **Hot Config Reload**: YAML + Excel "Config" Sheet; watchlist/refresh interval can be hot-applied in Excel without restart
   - 🧪 **Out-of-the-Box**: One command auto-generates the Excel template (7 Sheets), no need to prepare stock lists in advance
   - ✅ **Unit Tests**: pytest covers core logic (156 items), stable for long-running sessions

3. **[Streamlit Real-Time Market Monitor](egs_tools/a02_market_monitor_via_streamlit)**
   - 🌐 Web-based real-time market dashboard

---

## ⛏️ Alpha Mining

> 📁 **Code Directory**: [egs_alpha](egs_alpha)

### Alpha Mining Strategies

| **No.** | **Strategy** | **Paper** |
|:---:|:---|:---|
| 1 | [ML Auto-Mining 5,000 Alphas & Stock Trend Prediction](egs_alpha/auto_alpha/tsfresh) | — |

### Alpha Library

| **No.** | **Alpha Library** |
|:---:|:---|
| 1 | [alpha101](egs_alpha/alpha_libs/alpha101) |
| 2 | [stockstats](egs_alpha/alpha_libs/stockstats) |
| 3 | [ta_lib](egs_alpha/alpha_libs/ta_lib) |

---

## 💾 Data Processing

> 📁 **Code Directory**: [egs_data](egs_data)

- Detailed usage of various common data sources
- Unified data source interface

![Data Sources Diagram](.README_images/数据源.png)

---

## 📝 Text Analysis

> 📁 **Code Directory**: [egs_fin_nlp](egs_fin_nlp)

| **No.** | **Tool** |
|:---:|:---|
| 1 | [**StructBERT Market Sentiment Analysis**](egs_fin_nlp/emotion_analysis/01_StructBert_Binary_Class) |

---

## 🤖 LLM Applications

> 📁 **Code Directory**: [egs_llm](egs_llm)

| **No.** | **Tool** |
|:---:|:---|
| 1 | [**LLM-based Financial Market Analysis (video tutorial on the Planet or WeChat account)**](egs_llm/b01_app/a01_hot_topic_report/v1_proto_internet) |
| 2 | [**Unsloth Reasoning Stock Forecasting Model Training (open-source code; detailed guide & model on the Planet)**](egs_llm/a01_train/a01_unsloth_stock_forcaster) |

---

## 🌟 a_Best Resources on the Web (Highly Recommended)

> 📁 **Directory**: [a_全网优秀资源](a_全网优秀资源)
>
> ⭐ **The Highlight Section of This Repo**: Curated, organized, and reviewed top-quality quantitative resources from across the entire web, all in one place!

### 🎯 What Is This?

This is the most essential "resource treasure trove" of this repo — **we spent tremendous effort curating, organizing and reviewing tens of thousands of materials from across the web**, classified by the full quantitative trading workflow so that you can quickly find the tools and materials you need, avoiding detours.

**Differences from Other Sections of This Repo:**

| Section | Positioning | Features |
|:---|:---|:---|
| `a_全网优秀资源` ⭐ | Hands-on Resource Aggregation | Curated excellent projects from across the web, with reviews and comparisons |
| `egs_trade` | Complete Strategy Practice | Step-by-step strategy implementation tutorials |
| `egs_llm` | LLM Applications | LLM practices in finance |
| `ai_notes` | Knowledge Notes | Theory, concepts, pitfalls |

### ✨ Four Major Features

- 🔍 **Best of the Best**: Selected from the vast sea of resources across the web to avoid repeated pitfalls
- 📂 **Clear Categorization**: Classified by the full quant workflow (data → strategy → backtest → trading), easy to find what you need
- 📝 **With Reviews**: Not just links, but also pros/cons analysis and getting-started guides
- 🔄 **Continuously Updated**: Keeping up with technology development, continuously adding new resources

### 📚 Resource Category Overview

| No. | Category | Core Content |
|:---:|:---|:---|
| 📚 `00_基础知识` | Beginner Learning | Stock learning guides, introductory tutorials |
| 🎓 `00_学习资源` | Resource Aggregation | GitHub quant resources, open-source project collection |
| 📊 `01_数据` | Data Acquisition | Data acquisition tools, news data, multimodal data |
| 🏗️ `02_综合框架` | Mainstream Quant Frameworks | Qlib, WonderTrader, etc. detailed explanations |
| 🔄 `03_回测框架` | Backtest Tools | Backtrader, PyAlgoTrade, Zipline, RQAlpha, QuantDigger, etc. |
| ⛏️ `04_因子` | Alpha Library | Alpha101, ta_lib, stockstats, alphalens, etc. |
| 💹 `05_交易策略` | Strategy Resources | Traditional / ML / DL / RL / GNN / research report reproduction / portfolio |
| 🛠️ `06_辅助工具` | Assistant Tools | K-line pattern recognition, financial modeling |
| 📊 `07_可视化` | Visualization Libraries | Quant charts and visualization |
| 🧠 `08_知识图谱` | Knowledge Graph | Traditional & LLM-based solutions |
| ⚡ `09_高频交易` | High-Frequency Trading | Crypto high-frequency trading |
| 🤖 `10_大模型` | LLM in Finance | FinGPT, FinRobot, TradingAgents, Agent, RAG, Skill packs, etc. |
| 🌐 `11_投研平台` | Online Platforms | Free quant platform collection |
| 💻 `12_交易平台` | Trading Interfaces | EasyTrader, VNPy, etc. |

### 🔥 Highlighted Recommendations

- 🤖 **LLM Applications in Finance**: Covers the latest research and practice including FinGPT, FinMem, Self-Reflective, Stock-chain, TradingAgents, FinRobot, etc.
- 🛠️ **Skill Pack Collection (60+)**: Includes Chan Theory, technical analysis, quant statistics, fundamental analysis, crypto, macro analysis, etc.
- 📊 **Backtest Framework Multi-dimensional Comparison**: Hands-on comparison of Backtrader, Zipline, RQAlpha, PyAlgoTrade, QuantDigger, etc.
- 🔬 **Research Report Reproduction**: Selected high-quality broker research reports with reproduction code
- 💹 **Complete Trading Strategies**: From traditional double MA to RL and GNN, covering all types of strategy resources

> 💡 **Usage Tip**: Browse the [a_全网优秀资源](a_全网优秀资源) directory as needed; if you're interested in a project, click to view the detailed introduction and review.

---

## 📚 Programming & AI Basics

For easier maintenance, the original `ai_wiki` directory content (system operations, programming basics, AI basics, AI practice, etc.) has been independently synchronized to the repo **AI LLM Pitfall Guide**.

It records a large number of problems and solutions encountered in actual development, and tracks cutting-edge technology developments in real-time. Welcome to follow and Star ⭐

> ✨ **AI LLM Pitfall Guide**
> - **Github**: https://github.com/charliedream1/ai_wiki
> - **Gitee (Domestic Mirror)**: https://gitee.com/charlie1/ai_wiki.git
> - **Introduction**: Share various practical cases, track cutting-edge technology developments, covering the full stack of AI knowledge — including LLMs, programming techniques, machine learning, deep learning, reinforcement learning, GNN, speech recognition, NLP, image recognition, etc.

---

## 🌐 Online Research Platforms

> 📁 **Code Directory**: [egs_online_platform](egs_online_platform)

Domestic quant platforms such as JoinQuant, Uqer, MiRuo, GuoRen, and BigQuant can be tried by interested readers.

Research platforms are cloud platforms tailored for quant enthusiasts (quants), providing free stock data acquisition, accurate backtesting, high-speed live trading interfaces, easy-to-use API documentation, and a strategy library from easy to difficult, making it convenient to quickly implement and validate strategies.

> ⚠️ **Note**: The following strategies are only valid for the backtest periods described and have not been carefully tuned or verified for full-period performance. No strategy can guarantee effectiveness across all periods, so please be cautious when using them in live trading.

### JoinQuant Platform

> 🔗 [JoinQuant Platform](https://www.joinquant.com/) · Welcome to follow me: **量客攻城狮**
>
> - For detailed strategy introductions and source code, please click the corresponding strategy link
> - JoinQuant Usage Introduction: [egs_online_platform/聚宽_JoinQuant](https://github.com/charliedream1/ai_quant_trade/tree/master/egs_online_platform/%E8%81%9A%E5%AE%BD_JoinQuant)
> - This part of the code can only run on [**JoinQuant Platform**](https://www.joinquant.com/)

**Stock Quant Strategies:**

| Strategy | Return | Max Drawdown |
|:---|:---:|:---:|
| [**ML - Dynamic Factor Selection Strategy**](https://www.joinquant.com/view/community/detail/f2a9d2ec6d4ad18882fa0a364fb9123d) | 12.3% | 38.93% |
| [**Small-Cap + Multi-MA Quantitative Trading**](https://www.joinquant.com/view/community/detail/c754d315a391f39f61858dfe3275f45f) | 58.4% | 46.61% |
| [**Dragon-Tiger List - Look Long Trade Short**](https://www.joinquant.com/view/community/detail/0986c3b92578952cc22c52f0a5ea4664) | 41.82% | 26.89% |
| [**Strong Stocks + Trend Line + Stop-Loss/Take-Profit**](https://www.joinquant.com/view/community/detail/c0390ceabdc1b3365df343490b7caf28) | 10.09% | 21.449% |

**Stock Analysis Research:**

- [Hands-on Tutorial on "ML - Dynamic Multi-Factor Stock Selection" (with nanny-level tutorial)](https://www.joinquant.com/view/community/detail/4fa769264b0bf6489b36351b43e37012)
- [Dragon-Tiger List Data Filtering](https://www.joinquant.com/view/community/detail/a3a95cc7e53092aaea510d93bab9cb96)
- [Concept Sector Data Acquisition and Stock Selection](https://www.joinquant.com/view/community/detail/d1bf674ad163654aa263dac859762c90)
- [Detailed Explanation: Stock Data Acquisition & Graphical Analysis (with detailed code)](https://www.joinquant.com/view/community/detail/8fe84d0d25dcf1a6da72e442460cdf36)

---

## 📖 Quant Resource Collection

> [(Our article with 26,000+ reads on Zhihu) The Ultimate Collection of AI Stock Quantitative Trading Tools and Open-Source Projects](https://zhuanlan.zhihu.com/p/562878605)

We have re-categorized and reviewed all tools, collected in the [ai_notes](ai_notes) folder for easy lookup.

🎯 **In Development:**
- Continuously reviewing all tools to facilitate selection
- Continuously documenting the pros and cons of each tool to form comparison tables for easy selection
- Continuously documenting usage: We don't make comprehensive tutorials, only list the most commonly used and practical features, so you can get started quickly

---

## 🎁 Companion Resources

This code repository adheres to the principle of **parallel paid and free** offerings.

### 💎 Paid Resources — Knowledge Planet

> Register on the official Knowledge Planet website for guaranteed user rights. [Planet Content Introduction](docs/03_星球使用和介绍)

<font face="逐浪立楷" color=#00bfff>
🔥 As low as 0.1 RMB/day | Exclusive Crash Course | Painless Learning | 📺 Video Tutorials | Q&A |
Open-Source Pitfall Guide | Self-Developed Tool Code | 3-Minute Video Paper Speed | Library |
One of the lowest-priced quant planets on the web | 3-day no-questions-asked refund
</font>

👇 Scan the QR code below or click the link to enter the Planet and view more detailed introductions 🎏

**Planet Video Introduction:**
- Planet Usage Guide: https://mp.weixin.qq.com/s/SGc49e0xf24q5aUbf3rO0g?token=2028063978&lang=zh_CN
- Learning Path & Group Resource Usage: https://mp.weixin.qq.com/s/3-U048mc0riVsdETrKr77g

**Planet Join Links:**
- [AI智投星球](https://t.zsxq.com/dHt9l): AI quantitative trading crash course, cutting-edge tech, real-world cases, resource library
- [AI速成营](https://t.zsxq.com/q42Js): In-depth supplements on programming, LLMs, AI basics, principles and finance practice & job-seeking cases, complementary to AI智投星球

**Planet Introduction:**
- [**Planet Content Introduction**](docs/03_星球使用和介绍/01_星球介绍.md)
- [**New User Guide**](docs/03_星球使用和介绍/02_新人使用指南.md)

👇 Scan the QR code for a more detailed introduction to the "Planet" (there are funny comics inside)!

<div align="center">
<img src=".README_images/知识星球_量化海报.png" width=245 height="520" alt="Knowledge Planet - Quant"/>
<img src=".README_images/知识星球_大模型海报.png" width=245 height="620" alt="Knowledge Planet - LLM"/>
</div>

> 🎯 This repo will continue to be updated, but some code will be privately maintained and only visible on the Planet. The corresponding features will be noted in the repo.

---


### 🆓 Free Resources

**WeChat Official Account**

🔥 Real-time updates on the latest news
🎁 <font color=orange>Follow and like any article, DM the admin to receive a free exquisite quant material package!</font>

<img src=".README_images/公众号链接.png" width="320" height="120" alt="WeChat Official Account" align=center />

---

- [Zhihu: 576 Followers](https://www.zhihu.com/people/yi-dui-ji-mu-zai-kuang-xiang)
- [JoinQuant: 599 Followers](https://www.joinquant.com/user/d7aafd0b8b767b735bfb6f3639c81a6c)

---

**Code Repository (Forever Free)**

> ✨ **AI Quantitative Trading Bot**
> - **Github**: https://github.com/charliedream1/ai_quant_trade
> - **Gitee (Domestic Mirror)**: https://gitee.com/charlie1/ai_quant_trade.git

**Companion Repo**

> ✨ **AI驯龙笔记 (AI Taming Notes)**
> - **Github**: https://github.com/charliedream1/ai_wiki
> - **Gitee (Domestic Mirror)**: https://gitee.com/charlie1/ai_wiki.git
> - **Introduction**: Share various practical cases, track cutting-edge technology developments, covering the full stack of AI knowledge — including LLMs, programming techniques, machine learning, deep learning, reinforcement learning, GNN, speech recognition, NLP, image recognition, etc.

---

## 💖 Support Me

Your support is the driving force for me to move forward. Even "0.1 RMB" makes me happy. Thank you for your support \(^o^)/

<div align="center">
<img src=".README_images/支付宝收款码_alma_new.jpg" width="300" height="390" alt="Alipay QR Code"/>
&nbsp;&nbsp;&nbsp;&nbsp;
<img src=".README_images/微信收款码_alma_new.jpg" width="300" height="390" alt="WeChat QR Code"/>
</div>

---

## 💬 Discussion

Feel free to start a discussion in [Github Discussions](https://github.com/charliedream1/ai_quant_trade/discussions).

## 🐛 Technical Support

- Feel free to submit issues at [Github Issues](https://github.com/charliedream1/ai_quant_trade/issues)
- Join the Knowledge Planet for more technical support
  - [AI智投星球](https://t.zsxq.com/dHt9l): Focused on AI quantitative trading knowledge sharing
  - [LLM Pitfall Guide](https://t.zsxq.com/q42Js): Focused on programming, LLMs, and AI application empowerment

## ❓ FAQ

Please see the documentation → [**FAQ**](docs/02_常见问题)

## 📄 Citation

```bibtex
@misc{ai_quant_trade,
  author={Yi Li},
  title={ai_quant_trade},
  year={2022},
  publisher = {GitHub},
  journal = {GitHub repository},
  howpublished = {\url{https://github.com/charliedream1/ai_quant_trade}},
}
```

---

<div align="center">

**If this project helps you, please give it a Star ⭐ to support!**

[![Stargazers over time](https://starchart.cc/charliedream1/ai_quant_trade.svg)](https://starchart.cc/charliedream1/ai_quant_trade)

</div>
