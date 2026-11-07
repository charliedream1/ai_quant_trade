<div align="center">

<img src=".README_images/LOGO_NEW.png" width="260" height="270" alt="AI量化交易操盘手" />

# 🤖 AI量化交易操盘手

**一站式AI量化交易平台 · 从学习、模拟到实盘**

[**ENGLISH VERSION**](README.md) | [**日本語版**](README_JA.md)

[![License](https://img.shields.io/badge/License-Apache%202.0-brightgreen.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python-Version](https://img.shields.io/badge/Python-3.11%2B%20Workspace-brightgreen)](https://github.com/charliedream1/ai_quant_trade)
[![Stars](https://img.shields.io/github/stars/charliedream1/ai_quant_trade?style=social)](https://github.com/charliedream1/ai_quant_trade)

<p>
  <sub>👇 关注公众号 · 加入知识星球，获取更多实战内容与视频教程</sub>
</p>

<a href="https://t.zsxq.com/dHt9l" title="AI智投星球">
  <img src=".README_images/quant_qrcode.jpg" width="200" alt="AI智投星球" />
</a>
&nbsp;&nbsp;&nbsp;&nbsp;
<img src=".README_images/公众号链接.png" width="200" alt="微信公众号" />

</div>

---

**Economic research · 2026-11-03:** Chinese macroeconomic trends and A-share financial statements, accounting metrics, peer comparisons and optional evidence-backed model reports. See the [economic analysis guide](docs/usage/economic_analysis.md).

**模型接口 · 2026-11-03：**新增OpenAI/LiteLLM SDK选择与共享RPM、并发和重试控制，详见[模型接口指南](docs/usage/model_interfaces.md)。

**知识库更新 · 2026-11-02：**新增按库隔离的文件入库、Markdown标题切分、zvec-grep多轮关键词问答、会话附件、引用预览与研报论文下载入库。详见[知识库指南](docs/usage/knowledge.md)。

**最近更新 · 2026-11-01：** [一体化量化工作台](#integrated-workspace)串起行情、图形策略、回测、AI会话和带引用的知识问答；从[工作台使用指南](docs/usage/workspace.md)开始。

## 📑 目录

- [1. ✨ 核心亮点](#1--核心亮点)
- [2. 🔥 新特性](#2--新特性)
- [3. 🧩 一体化量化工作台（`src`）](#integrated-workspace)
- [4. 📖 简介](#4--简介)
- [5. 🌟 awesome_projects（重点推荐）](#5--awesome_projects重点推荐)
- [6. 🚀 快速开始](#6--快速开始)
- [7. 📊 本地量化策略](#7--本地量化策略)
- [8. 💰 实盘交易](#8--实盘交易)
- [9. 🛠️ 辅助操盘工具](#9--辅助操盘工具)
- [10. ⛏️ 因子挖掘](#10--因子挖掘)
- [11. 💾 数据处理](#11--数据处理)
- [12. 📝 文本分析](#12--文本分析)
- [13. 🤖 大模型应用](#13--大模型应用)
- [14. 📚 编程及AI基础知识](#14--编程及ai基础知识)
- [15. 🌐 在线投研平台](#15--在线投研平台)
- [16. 📖 量化资源集合](#16--量化资源集合)
- [17. 🎁 配套资源](#17--配套资源)
- [18. 💖 打赏我](#18--打赏我)
- [19. 💬 讨论](#19--讨论)
- [20. 🐛 技术支持](#20--技术支持)
- [21. ❓ 常见问题](#21--常见问题)
- [22. 📄 引用](#22--引用)

---

## 1. ✨ 核心亮点

| 🎯 定位 | 📌 说明 |
|:---:|:---|
| 🏦 **一站式平台** | 从学习、模拟到实盘，全流程覆盖 |
| 📈 **多元策略** | 大模型、因子挖掘、传统策略、机器学习、深度学习、强化学习、图网络、高频交易 |
| 📚 **资源汇总** | 全网资源汇总、实战案例、论文解读、代码实现 |
| 🛠️ **辅助工具** | 辅助盯盘、股票推荐等实用操盘工具 |
| 🌍 **多市场覆盖** | 覆盖股票、基金、加密货币等多个市场 |
| 🚀 **实盘部署** | 支持 Python/C++/CPU/GPU 等多种部署方式 |

---

## 2. 🔥 新特性

| **时间** | **特性** |
|:---|:---|
| 2026.11.06 | [**SAG knowledge and document Q&A**](docs/usage/sag_knowledge_qa.md): optional SAG retrieval, isolated single-document questions, JEV/vector/standard rerank alternatives and explicit fallback traces. |
| 2026.11.01 | 🆕 [**一体化量化研究工作台**](docs/usage/workspace.md)：在同一Gradio应用内完成账户总览、行情研究、图形策略、含成本回测、AI项目会话和带引用的知识问答。 |
| 2026.10.31 | [**执行管理与研究证据**](docs/usage/access_and_execution.md)：自定义源码复核、冻结参数快照、后端过程状态、RAG引用及文件阅读/Markdown编辑。 |
| 2026.10.29 | [**Agent API/CLI后端与十类原生研究Skill**](docs/usage/agent_cli_skills.md)，展示实际过程并核验可用性。 |
| 2026.10.28 | [**多空辩论、双团队竞赛**](docs/usage/agent_strategies.md)，以及[Alpha挖掘、主题与体制研究](docs/usage/alpha_mining.md)。 |
| 2026.10.24 | [**图形策略工坊**](docs/usage/strategy_composition.md)：级联、并行评分、因子/模型组件及Portfolio/Risk组合。 |
| 2026.07.25 | 🆕 [**上班"摸鱼炒股"神器 V2：模块化盯盘系统 + 预警监控 + K线图 + 多源 fallback**](egs_aide/excel_stock_monitor/v2) |

<details>
<summary>📂 <b>2025 年更新</b></summary>

| **时间** | **特性** |
|:---|:---|
| 2025.08.09 | 🆕 [**推理型股价预测大模型训练教程（预测准确率提升20%，且可解析）**](egs_courses/01_推理型股价预测大模型训练教程.md) |
| 2025.05.17 | 🆕 [**Unsloth推理型股价预测大模型（代码见本仓库、详细指南+模型见星球）**](egs_llm/a01_train/a01_unsloth_stock_forcaster) |
| 2025.01.03 | [**大模型金融市场分析（视频教程见星球或公众号）**](egs_llm/b01_app/a01_hot_topic_report/v1_proto_internet) |

</details>

<details>
<summary>📂 <b>2023 年更新</b></summary>

| **时间** | **特性** |
|:---|:---|
| 2023.04.09 | [**StructBERT市场情绪分析**](https://github.com/charliedream1/ai_quant_trade/tree/master/egs_fin_nlp/emotion_analysis/01_StructBert_Binary_Class) |
| 2023.03.28 | [**强化学习多股票交易：年化收益53%**](https://github.com/charliedream1/ai_quant_trade/tree/master/egs_trade/rl/a002_finRL_tutorial/a01_Stock_NeurIPS2018) |
| 2023.02.28 | [**机器学习自动挖掘5000个因子及股票趋势预测**](https://github.com/charliedream1/ai_quant_trade/tree/master/egs_alpha/auto_alpha/tsfresh) |
| 2023.02.05 | [**利用EXCEL看盘**](https://github.com/charliedream1/ai_quant_trade/tree/master/egs_aide/%E7%9C%8B%E7%9B%98%E7%A5%9E%E5%99%A8/v1) |
| 2023.01.01 | [**本地深度强化学习策略**](https://github.com/charliedream1/ai_quant_trade/tree/master/egs_trade/rl/a001_proto_sb3) |

</details>

<details>
<summary>📂 <b>2022 年更新</b></summary>

| **时间** | **特性** |
|:---|:---|
| 2022.11.07 | [**Wind本地实盘模拟**](https://github.com/charliedream1/ai_quant_trade/tree/master/egs_trade/real_bid_simulate/wind) |
| 2022.08.03 | [**基础回测框架 + 双均线策略**](https://github.com/charliedream1/ai_quant_trade/tree/master/egs_trade/vanilla/double_ma) |

</details>

---

<a id="integrated-workspace"></a>

## 3. 🧩 一体化量化工作台（`src`）

新的[`src/`](src)是一套可直接运行的研究工作台：以模块化**Gradio网页**、共用**REST API与CLI**串起行情、策略、回测、AI会话和本地知识。历史`egs_*/`示例项目继续保留，可独立使用。

[**平台说明入口**](docs/platform/index.md) · [**工作台使用指南**](docs/usage/workspace.md) · [**快速上手**](docs/usage/quick_start.md) · [**原理文档**](docs/principles/README.md) · [**命令行指南**](docs/usage/cli.md)

| 能力 | 可以完成的操作 |
| --- | --- |
| 总览与市场研究 | 查看净值、资金配置、持仓统计、新闻、板块和个股；运行因子监控，核对图谱关系证据。 |
| 策略与小模型 | 导入规则、ETF/行业轮动、LightGBM/XGBoost排序和CPU小型MLP集成；通过YAML预览参数并冻结运行。 |
| 图形组合与风控 | 将规则→模型→Agent级联筛选，或并行投票/评分，组合Portfolio配置与Risk组件；点击节点查看上下游。 |
| 回测与模拟 | 设置日期、佣金/税费/滑点等执行假设，查看净值、回撤、成交、归因和参数快照。 |
| Alpha与多Agent | 假设→实现→评估，主题/体制实验，多空辩论和团队竞赛；保留证据、预算及人工复核门槛。 |
| AI、CLI与Skill | 项目会话、附件与Enter发送；选择后端、权限、模型及思考配置。支持API/Codex/Qoder/TRAE/CodeBuddy，实际可用性取决于安装、认证和研究资格。 |
| 知识与文件 | 带引用的本地RAG问答，HTML/Office/PDF预览，Markdown编辑及历史报告浏览。 |
| 学习与运行管理 | 按章节学习量化基础，配置定时任务、MCP和Skill，查看通知及运行状态。 |

### GIF：看看实际操作

**同一页面切换九个模块**：账户总览→市场研究→ETF研究→学习空间→收起左侧导航。

![一体化工作台导航与账户总览](.README_images/workspace/zh/navigation.gif)

**图形策略与回测**：载入预置、查看并拖动节点，设置回测，核对结果与冻结参数。

![图形策略构建与回测证据](.README_images/workspace/zh/strategy-backtest.gif)

**AI会话与知识引用**：添加附件、Enter发送并查看留档状态，提出知识问题并核对引用，再进入Skill报告面板。

![AI会话附件与知识库引用](.README_images/workspace/zh/ai-knowledge.gif)

本页使用中文界面与中文字幕，英文和日文README共用英文界面实录与英文字幕。

三段GIF均为隔离服务中的**实际页面点击**，使用明确标注的**模拟行情/模拟回答**。进入Skill面板没有运行报告；演示不证明投资收益，也不代表调用了真实付费CLI或模型。[录制来源和边界](.README_images/workspace/README.md)。

### 源码分工与启动

| 目录 | 主要职责 |
| --- | --- |
| [`src/frontend`](src/frontend)、[`src/api`](src/api)、[`src/cli`](src/cli) | Gradio模块、REST/WebSocket和命令行入口，共用业务服务。 |
| [`src/strategy`](src/strategy)、[`src/engine`](src/engine)、[`src/portfolio`](src/portfolio)、[`src/risk`](src/risk) | 标准策略端口、图形编排、执行账本、组合配置与风控。 |
| [`src/agent`](src/agent)、[`src/alpha_mining`](src/alpha_mining)、[`src/agent_strategies`](src/agent_strategies)、[`src/skills`](src/skills) | 模型/CLI后端、研究编排与原生Skill。 |
| [`src/data`](src/data)、[`src/documents`](src/documents), [`src/knowledge`](src/knowledge)、[`src/integration`](src/integration) | 行情数据、文档与知识支持、MCP等集成。 |
| [`src/core`](src/core)、[`src/scheduler`](src/scheduler)、[`src/notifications`](src/notifications) | 配置、存储、访问/执行基础设施、任务所有权和提醒。 |
| [`egs/`](egs)、[`tests/`](tests)、[`doc/`](doc)、[`docs/`](docs) | YAML和启动样例、回归测试、设计、使用/原理文档。 |

工作台要求**Python3.11+**及根目录固定依赖。按[环境安装](docs/usage/installation.md)准备后，在仓库根目录启动：

```text
.venv-secure/Scripts/python.exe -B egs/check_runtime.py --role web
.venv-secure/Scripts/python.exe -B start.py --host 127.0.0.1 --port 8000
```

访问`http://127.0.0.1:8000/app/`。Linux按配置创建环境，使用`.venv-secure/bin/python`。业务配置在`egs/`的YAML中，密钥只放本地`.env`或`.llm_env`。远程访问与自定义源码先看[访问和复核规则](docs/usage/access_and_execution.md)。Qlib信号分析与原生Workflow分别配置、分别验证；实盘也需实际通道和检查，不能由演示推断已可实盘。

---

## 4. 📖 简介

### 适合人群

- 🏢 **机构投资者**
- 👨‍💻 **散户（有编程基础）**
- 🌱 **散户（无编程基础）**

### 项目结构

```
ai_quant_trade
├── ai_notes ........... 金融量化交易知识（Markdown / Jupyter Notebook 知识体系）
│   ├── 资源 ........... 持续收录全网优秀资源
│   ├── 实战 ........... 各类工具、框架、库的使用及踩坑实录
│   └── 热点 ........... 金融市场热点、技术热点、论文解读
├── src ................ 一体化工作台业务服务与模块化Gradio界面
├── egs ................ 工作台YAML配置和启动样例
├── tests .............. 工作台单元、集成与浏览器检查
├── doc ................ 设计文档
├── docs ............... 使用/原理文档与整合站点
├── start.py ........... 工作台服务入口
├── egs_aide ........... 辅助操盘工具（看盘神器等）
├── egs_alpha .......... 因子库 & 因子挖掘
├── egs_data ........... 数据获取及处理（Wind / 开源工具）
├── egs_fin_nlp ........ 文本分析（情感分析等）
├── egs_llm ............ 大模型应用（股价预测 / 金融分析）
├── egs_online_platform  在线投研平台策略（优矿 / 聚宽）
├── egs_trade .......... 本地量化炒股策略
│   ├── paper_trade .... 实盘模拟（Wind万得）
│   ├── rl ............. 强化学习炒股
│   ├── ms_qlib ........ 微软Qlib框架
│   └── vanilla ........ 传统规则类策略
├── runtime ............ 模型部署和实际使用
├── tools .............. 辅助工具
└── README.md
```

> 一体化工作台使用根目录`requirements.txt`、`pyproject.toml`及可选模型依赖和项目环境；历史`egs_*/`示例保留自己的依赖文件，按所选项目安装，不要将全部示例混装到工作台环境。

---

## 5. 🌟 awesome_projects（重点推荐）

> 📁 **目录**：[awesome_projects](awesome_projects)
>
> ⭐ **本仓库精华版块**：从全网海量资料中筛选、整理、点评的优质量化资源，一站式获取！

### 🎯 这是什么？

这是本仓库最核心的"资源宝库"——**我们花费大量精力从全网数万份资料中筛选、整理并附上点评**，按量化交易全流程分类，方便你快速找到所需工具和资料，少走弯路。

### ✨ 四大特色

- 🔍 **优中选优**：从全网海量资源中精选，避免你重复踩坑
- 📂 **分类清晰**：按量化交易全流程（数据→策略→回测→交易）分类，便于按需查找
- 📝 **含点评解读**：不只是罗列链接，附有优缺点分析、上手指南
- 🔄 **持续更新**：紧跟技术发展，持续收录新资源

### 📚 资源分类一览

| 序号 | 类别 | 核心内容 |
|:---:|:---|:---|
| 📚 [00-basics](awesome_projects/00-basics.md) | 入门学习 | 股票学习指南、入门教程 |
| 🎓 [00-learning-resources](awesome_projects/00-learning-resources.md) | 学习资源 | GitHub量化资源、开源项目汇总 |
| 📊 [01-data](awesome_projects/01-data.md) | 数据获取 | 数据获取工具、新闻数据、多模态数据 |
| 🏗️ [02-comprehensive-frameworks](awesome_projects/02-comprehensive-frameworks.md) | 主流量化框架 | Qlib、WonderTrader 等 |
| 🔄 [03-backtesting-frameworks](awesome_projects/03-backtesting-frameworks.md) | 回测工具 | Backtrader、Zipline、RQAlpha 等 |
| ⛏️ [04-factors](awesome_projects/04-factors.md) | 因子库 | alphalens、ta_lib 等 |
| 💹 [05-trading-strategies](awesome_projects/05-trading-strategies.md) | 策略资源 | 传统/深度学习/强化学习/研报复现/投资组合 |
| 🛠️ [06-assistant-tools](awesome_projects/06-assistant-tools.md) | 辅助工具 | K线形态识别、盯盘、办公工具 |
| 📊 [07-visualization](awesome_projects/07-visualization.md) | 可视化 | 量化图表与可视化 |
| 🧠 [08-knowledge-graphs](awesome_projects/08-knowledge-graphs.md) | 知识图谱 | 传统方案与大模型方案 |
| ⚡ [09-high-frequency-trading](awesome_projects/09-high-frequency-trading.md) | 高频交易 | 加密货币高频交易 |
| 🤖 [10-llm](awesome_projects/10-llm.md) | LLM 金融应用 | FinGPT、FinRobot、TradingAgents、Agent、RAG 等 |
| 🌐 [11-research-platforms](awesome_projects/11-research-platforms.md) | 投研平台 | 免费量化平台汇总 |
| 💻 [12-trading-platforms](awesome_projects/12-trading-platforms.md) | 交易平台 | EasyTrader、VN.Py 等 |
| 📄 [13-research-reports](awesome_projects/13-research-reports.md) | 研报类 | 研报复现与来源 |

### 🔥 重点推荐内容

- 🤖 **大模型在金融的应用**：覆盖 FinGPT、FinMem、Self-Reflective、Stock-chain、TradingAgents、FinRobot 等最新研究与实战
- 🛠️ **Skill 包合集（60+）**：包含缠论、技术分析、量化统计、基本面分析、加密货币、宏观分析等专业 Skill
- 📊 **回测框架多维对比**：Backtrader、Zipline、RQAlpha、PyAlgoTrade、QuantDigger 等多框架实测对比
- 🔬 **研报复现**：精选高质量券商研报并附复现代码
- 💹 **交易策略全套**：从传统双均线到强化学习、图神经网络，覆盖各类型策略资源

> 💡 **使用建议**：进入 [awesome_projects](awesome_projects) 目录按需浏览；每个项目条目已补充 Stars、License、维护状态、文档/主页和价值点评。

---

## 6. 🚀 快速开始

使用新的**`src`工作台**，先按[环境安装](docs/usage/installation.md)和[快速上手](docs/usage/quick_start.md)准备Python3.11+项目环境，在仓库根目录运行`start.py`；主要能力与操作见[工作台章节](#integrated-workspace)。

使用历史示例时，克隆仓库后进入对应`egs_*/`目录，按该项目自己的requirements和README安装运行。示例的Python/可选依赖要求可能不同，不默认复用工作台环境。

---

## 7. 📊 本地量化策略

> 📁 **代码目录**：[egs_trade](egs_trade)
>
> 🎯 每个实例均配备完善的教程，从原理、使用到代码解读。

可在本地构建一套独立的量化交易系统，涵盖以下策略类型：

| 类别 | 策略 | 状态 |
|:---:|:---|:---:|
| 🤖 AI策略 | 强化学习、图网络、深度学习、机器学习、高频交易、因子挖掘、大模型 | ✅ / 🔨 |
| 📐 传统策略 | 规则类策略（双均线、投资组合管理等） | ✅ |

### 🧠 强化学习策略

> 📁 **代码目录**：`egs_trade/rl`

自从2017年 AlphaGo 与柯洁围棋大战之后，深度强化学习大火。

相比于机器学习和深度学习，强化学习以**最终目标为导向**（以交互作为目标），而很多其他方法考虑的是孤立的子问题（如"股价预测"、"大盘预测"、"交易决策"等），并不能直接获得交互的动作。强化学习则直接面向"完成命令者的任务"，可以获得一连串的动作序列。

**策略列表：**

| **序号** | **策略** | **论文** |
|:---:|:---|:---|
| 1 | [原型](egs_trade/rl/a001_proto_sb3) | — |
| 2 | [FinRL教程0-NeurIPS2018](egs_trade/rl/a002_finRL_tutorial/a01_Stock_NeurIPS2018) | [Practical Deep Reinforcement Learning Approach for Stock Trading](https://arxiv.org/abs/1811.07522) |

**回测结果：**

| **序号** | **策略** | **市场** | **年化收益** | **最大回撤** | **夏普率** |
|:---:|:---|:---|:---:|:---:|:---:|
| 1 | [原型](egs_trade/rl/a001_proto_sb3) | 中国A股 | — | — | — |
| 2 | [FinRL教程0-NeurIPS2018](egs_trade/rl/a002_finRL_tutorial/a01_Stock_NeurIPS2018) | 美股道琼斯30 | 53.1% | -10.4% | 2.17 |

### 📐 传统策略

> 传统策略虽然看似昨日黄花，但其可操作性更强，仍有一定使用价值。深度学习和机器学习往往需要配合规则使用。

1. **[双均线策略 + 简易手写回测框架](egs_trade/vanilla/double_ma)**
   - [详细使用教程](egs_trade/vanilla/double_ma/文档教程)
   - 包含策略代码 + 自建纯手写回测框架
   - 包含良好的绘图，指示买点和卖点
   - 🎯 目标：通过这个实例了解量化交易的完整框架构建方式

2. **[投资组合管理7节教学](egs_trade/vanilla/portfolio_optimization)**

---

## 8. 💰 实盘交易

> 📁 **代码目录**：[egs_trade](egs_trade)

### 实盘模拟

1. **[Wind本地实盘模拟：双均线策略](egs_trade/paper_trade/wind)**
   - 利用 Wind 软件实现的实盘模拟
   - Wind 常作为各大金融机构的首选数据源，由于价格较高，更适合机构使用
   - 🏢 使用对象：机构

---

## 9. 🛠️ 辅助操盘工具

> 📁 **代码目录**：[egs_aide](egs_aide)

1. **[利用EXCEL看盘 V1](egs_aide/excel_stock_monitor/v1)**
   - 👀 看盘时不容易被发现
   - 📋 可自定义添加要盯盘的股票
   - ⚡ 可利用 Excel 快速计算和处理数据

2. **[上班"摸鱼炒股"神器 V2：模块化盯盘系统](egs_aide/excel_stock_monitor/v2)** 🆕

   ![看盘神器V2演示](.README_images/workspace/zh/legacy-monitor.gif)

   - 🏗️ **架构重构**：从单文件升级为模块化 `excel_monitor` 包，Sheet Handler 模式，每个 Sheet 刷新互相隔离
   - 🔔 **预警监控**：自定义涨跌幅/价格上下限，触发后整行变红 + 弹窗提醒
   - 📈 **K 线图**：Excel 里点按钮即画 K 线（mplfinance 蜡烛图 + 均线），无需切软件
   - 💰 **资金情绪**：新增 Sheet 聚合北向资金 + 微博舆情 + 新闻情绪 + 股吧热门
   - 🔍 **股票池选股**：内置全 A 股，代码/名称/拼音首字母模糊搜索 + 下拉框直接选，不用再查代码
   - 🔄 **多源 fallback**：qstock 主源 + akshare/东财/腾讯/网易/efinance 备选源，单个挂了自动切换
   - ⚙️ **配置热重载**：YAML + Excel "配置" Sheet，自选股/刷新间隔在 Excel 里改完热生效，无需重启
   - 🧪 **开箱即用**：一条命令自动生成 Excel 模板（7 个 Sheet），不再需要额外准备股票列表
   - ✅ **单元测试**：pytest 覆盖核心逻辑（156 项），可长时间稳定运行

3. **[Streamlit实时行情监控](egs_tools/a02_market_monitor_via_streamlit)**
   - 🌐 基于 Web 的实时行情看板

---

## 10. ⛏️ 因子挖掘

> 📁 **代码目录**：[egs_alpha](egs_alpha)

### 因子挖掘策略

| **序号** | **策略** | **论文** |
|:---:|:---|:---|
| 1 | [机器学习自动挖掘5000个因子及股票趋势预测](egs_alpha/auto_alpha/tsfresh) | — |

### 因子库

| **序号** | **因子库** |
|:---:|:---|
| 1 | [alpha101](egs_alpha/alpha_libs/alpha101) |
| 2 | [stockstats](egs_alpha/alpha_libs/stockstats) |
| 3 | [ta_lib](egs_alpha/alpha_libs/ta_lib) |

---

## 11. 💾 数据处理

> 📁 **代码目录**：[egs_data](egs_data)

- 各类常见数据源使用详解
- 统一数据源接口

![数据源示意图](.README_images/数据源.png)

---

## 12. 📝 文本分析

> 📁 **代码目录**：[egs_fin_nlp](egs_fin_nlp)

| **序号** | **工具** |
|:---:|:---|
| 1 | [**StructBERT市场情绪分析**](egs_fin_nlp/emotion_analysis/01_StructBert_Binary_Class) |

---

## 13. 🤖 大模型应用

> 📁 **代码目录**：[egs_llm](egs_llm)

| **序号** | **工具** |
|:---:|:---|
| 1 | [**大模型金融市场分析（视频教程见星球或公众号）**](egs_llm/b01_app/a01_hot_topic_report/v1_proto_internet) |
| 2 | [**Unsloth推理型股价预测模型训练（代码开源、详细指南+模型见星球）**](egs_llm/a01_train/a01_unsloth_stock_forcaster) |

---

## 14. 📚 编程及AI基础知识

为了便于维护，已将原有的 `ai_wiki` 目录内容（系统操作、编程基础、AI基础、AI实践等）独立同步至仓库 **AI大模型避坑指南**。

里面记录了大量实际开发中遇到的问题和解决方案，并实时追踪前沿技术发展，欢迎大家关注和 Star ⭐

> ✨ **AI大模型避坑指南**
> - **Github**: https://github.com/charliedream1/ai_wiki
> - **Gitee（国内镜像）**: https://gitee.com/charlie1/ai_wiki.git
> - **简介**: 分享各种实用案例，追踪前沿技术发展，囊括 AI 全栈知识，涵盖大模型、编程技术、机器学习、深度学习、强化学习、图神经网络、语音识别、NLP 及图像识别等领域

---

## 15. 🌐 在线投研平台

> 📁 **代码目录**：[egs_online_platform](egs_online_platform)

国内量化平台如聚宽、优矿、米筐、果仁和 BigQuant 等，感兴趣的读者可自行尝试。

投研平台是为量化爱好者（宽客）量身打造的云平台，提供免费股票数据获取、精准的回测功能、高速实盘交易接口、易用的 API 文档、由易入难的策略库，便于快速实现和验证策略。

> ⚠️ **注意**：如下策略仅在所述回测段有效，没有进行详细的调优和全周期验证。没有策略能保证全周期有效，如实盘使用请慎重。

### 聚宽平台

> 🔗 [聚宽平台](https://www.joinquant.com/) · 欢迎关注我：**量客攻城狮**
>
> - 具体策略详细介绍和源码请点击对应策略链接查看
> - 聚宽使用介绍：[egs_online_platform/聚宽_JoinQuant](https://github.com/charliedream1/ai_quant_trade/tree/master/egs_online_platform/%E8%81%9A%E5%AE%BD_JoinQuant)
> - 该部分代码仅能在 [**聚宽平台**](https://www.joinquant.com/) 运行

**股票量化策略：**

| 策略 | 收益 | 最大回撤 |
|:---|:---:|:---:|
| [**机器学习-动态因子选择策略**](https://www.joinquant.com/view/community/detail/f2a9d2ec6d4ad18882fa0a364fb9123d) | 12.3% | 38.93% |
| [**小市值+多均线量化炒股**](https://www.joinquant.com/view/community/detail/c754d315a391f39f61858dfe3275f45f) | 58.4% | 46.61% |
| [**龙虎榜-看长做短**](https://www.joinquant.com/view/community/detail/0986c3b92578952cc22c52f0a5ea4664) | 41.82% | 26.89% |
| [**强势股+趋势线判断+止损止盈**](https://www.joinquant.com/view/community/detail/c0390ceabdc1b3365df343490b7caf28) | 10.09% | 21.449% |

**股票分析研究：**

- [手把手教你"机器学习-动态多因子选股"(附保姆级教程)](https://www.joinquant.com/view/community/detail/4fa769264b0bf6489b36351b43e37012)
- [龙虎榜数据筛选和过滤](https://www.joinquant.com/view/community/detail/a3a95cc7e53092aaea510d93bab9cb96)
- [概念板块数据获取和选股](https://www.joinquant.com/view/community/detail/d1bf674ad163654aa263dac859762c90)
- [详解: 股票数据获取及图形分析(附详细代码)](https://www.joinquant.com/view/community/detail/8fe84d0d25dcf1a6da72e442460cdf36)

---

## 16. 📖 量化资源集合

> [(我们在知乎上2.6万阅读的文章) 史上最全AI股票量化交易工具和开源项目汇总](https://zhuanlan.zhihu.com/p/562878605)

我们将所有工具重新进行了分类并点评，收录在 [ai_notes](ai_notes) 文件夹下，方便大家查找。

🎯 **开发中：**
- 陆续对所有工具进行点评，方便选择
- 陆续记录各工具的优缺点，形成对比表，方便选型
- 陆续记录使用方法：我们不做大而全的教程，只列举最常用且实用的功能，让你快速上手

---

## 17. 🎁 配套资源

本代码仓秉承 **收费与免费并行** 的原则。

### 💎 收费资源 — 知识星球

> 知识星球官网注册，用户权益有保障。[星球内容介绍](docs/03_星球使用和介绍)

<font face="逐浪立楷" color=#00bfff>
🔥低至每日1毛|独家速成课|无痛学课|📺视频教程|答疑解惑|
开源避坑指南|自研工具代码|3分钟视频论文速度|图书馆|
全网最低价量化类星球之一|3天不满意免费退款
</font>

👇 下方扫描二维码或点击链接，进入星球查看更详细的介绍 🎏

**星球视频介绍：**
- 星球使用指南：https://mp.weixin.qq.com/s/SGc49e0xf24q5aUbf3rO0g?token=2028063978&lang=zh_CN
- 学习路线及群内资源使用：https://mp.weixin.qq.com/s/3-U048mc0riVsdETrKr77g

**星球加入链接：**
- [AI智投星球](https://t.zsxq.com/dHt9l)：AI量化交易速成、前沿技术、实战案例、资源库
- [AI速成营](https://t.zsxq.com/q42Js)：深入补充编程、大模型、AI基础、原理及金融方向实战及求职等的速成和案例分享，与 AI智投星球 形成互补

**星球介绍：**
- [**星球内容介绍**](docs/03_星球使用和介绍/01_星球介绍.md)
- [**新人使用指南**](docs/03_星球使用和介绍/02_新人使用指南.md)

👇 扫码查看"星球"更详细的介绍（里面有搞笑漫画哦）！

<div align="center">
<img src=".README_images/知识星球_量化海报.png" width=245 height="520" alt="知识星球-量化"/>
<img src=".README_images/知识星球_大模型海报.png" width=245 height="620" alt="知识星球-大模型"/>
</div>

> 🎯 本代码仓会持续更新，但部分代码转为私有化维护仅在星球中可见，对应功能会在仓库中标注。

---


### 🆓 免费资源

**微信公众号**

🔥 最新资讯实时关注
🎁 <font color=orange>关注并点赞任一篇文章，私信管理员，领取精美量化资料包一份！</font>

<img src=".README_images/公众号链接.png" width="320" height="120" alt="微信公众号" align=center />

---

- [知乎：576关注者](https://www.zhihu.com/people/yi-dui-ji-mu-zai-kuang-xiang)
- [聚宽：599关注者](https://www.joinquant.com/user/d7aafd0b8b767b735bfb6f3639c81a6c)

---

**代码仓（永久免费）**

> ✨ **AI量化交易操盘手**
> - **Github**: https://github.com/charliedream1/ai_quant_trade
> - **Gitee（国内镜像）**: https://gitee.com/charlie1/ai_quant_trade.git

**本仓库配套项目**

> ✨ **AI驯龙笔记**
> - **Github**: https://github.com/charliedream1/ai_wiki
> - **Gitee（国内镜像）**: https://gitee.com/charlie1/ai_wiki.git
> - **简介**: 分享各种实用案例，追踪前沿技术发展，囊括 AI 全栈知识，涵盖大模型、编程技术、机器学习、深度学习、强化学习、图神经网络、语音识别、NLP 及图像识别等领域

---

## 18. 💖 打赏我

您的支持是我前进的动力，即便"1毛钱"我也很开心，感谢您的打赏和支持 \(^o^)/

<div align="center">
<img src=".README_images/支付宝收款码_alma_new.jpg" width="300" height="390" alt="支付宝收款码"/>
&nbsp;&nbsp;&nbsp;&nbsp;
<img src=".README_images/微信收款码_alma_new.jpg" width="300" height="390" alt="微信收款码"/>
</div>

---

## 19. 💬 讨论

欢迎在 [Github Discussions](https://github.com/charliedream1/ai_quant_trade/discussions) 中发起讨论。

## 20. 🐛 技术支持

- 欢迎在 [Github Issues](https://github.com/charliedream1/ai_quant_trade/issues) 中提交问题
- 加入知识星球，获取更多技术支持
  - [AI智投星球](https://t.zsxq.com/dHt9l)：专注AI量化交易知识分享
  - [大模型避坑指南](https://t.zsxq.com/q42Js)：专注编程、大模型、AI应用赋能

## 21. ❓ 常见问题

请查看文档 → [**常见问题**](docs/02_常见问题)

## 22. 📄 引用

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

**如果本项目对你有帮助，请给一个 Star ⭐ 支持一下！**

[![Stargazers over time](https://api.star-history.com/svg?repos=charliedream1/ai_quant_trade&type=Date)](https://star-history.com/#charliedream1/ai_quant_trade&Date)

</div>
