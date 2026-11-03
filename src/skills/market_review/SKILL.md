---
name: market-review
description: "股市复盘技能：对当天或每月的股市行情进行复盘分析。融合财评网站量化数据与公众号文章舆情观点，生成图文并茂的复盘报告。Invoke when user requests daily/monthly stock market recap, market review, or comprehensive market trend analysis with charts."
---

# market-review — 股市复盘分析技能

## 概述

本技能是一个**自包含**的股市复盘分析工作流，从财评网站（东方财富/同花顺/新浪财经）获取量化市场数据，从微信公众号文章获取定性舆情观点，按时间段（当天复盘/每月复盘）生成图文并茂的股市复盘报告。

## 核心特性

- **双时间段模式**：当天复盘（daily）+ 每月复盘（monthly）
- **双数据源融合**：财评网站量化数据（指数/板块/资金流）+ 公众号文章定性观点
- **报告标题带时间段**：如"A股市场当日复盘（2025.06.19）"或"A股市场月度复盘（2025.05.19-2025.06.19）"
- **图文并茂**：≥10张专业图表（含舆情温度计），覆盖指数走势/板块涨跌/资金流向/市场情绪/海外指数
- **多模态输出**：在 Markdown 报告基础上自动生成 HTML、PPT、高清长图/分段截图与讲解视频
- **程序化校验 + 生成后质检门禁**：独立验证层（陈述三分类 + 结构 + 幻觉 + 实时性）外，新增 `quality_check.py` 作为最终门禁，明确分为**规则质检（章节/配图齐全性）**与**语义质检（事实性/无幻觉/口径一致性）**两层，输出 `quality_report.md` 与 PASS/FAIL 门禁
- **文章索引与规范引用**：HTML 报告内置**可交互左侧目录栏**（即文章索引，点击跳转章节、滚动高亮），全篇关键数字带 `[n]` 角标，文末「引用与数据来源」逐项对应，便于溯源与审计
- **四维拓展覆盖**：在量化复盘之上，补充情绪分析（媒体舆情温度计）、新闻面与政策动态（权威媒体/财评整合）、海外市场及消息（美股/宏观/大宗），数据来自 neodata 金融搜索 + akshare 美股指数

## 工作流 DAG（9阶段）

```
            ┌──────────────┐
            │ 1.Orchestrator│  确定时间段+分析范围 → plan.json
            └──────┬───────┘
       ┌───────────┴───────────┐
       ▼                       ▼
 ┌───────────┐           ┌───────────┐
 │ 2.Searcher │           │ 3.Collector│
 │  公众号文章 │           │  财评数据  │
 │  舆情爬取  │           │  指数/板块  │
 │ →articles/│           │ →market_data/│
 └─────┬─────┘           └─────┬─────┘
       │                       ▼
       │                 ┌───────────┐
       │                 │ 4.Analyst  │
       │                 │  量化分析  │
       │                 │ →charts +  │
       │                 │  analysis  │
       │                 └─────┬─────┘
       └──────────┬────────────┘
                  ▼
           ┌──────────────────┐
           │ 8.NewsOverseas    │  neodata(新闻/舆情/海外)
           │  新闻/舆情/海外    │  + akshare(美股指数)
           │ →articles/ + CSV  │
           └────────┬──────────┘
                  ▼
           ┌───────────┐
           │ 5.Aggregator│  报告聚合 → report.md
           └─────┬─────┘
                 ▼
           ┌───────────┐
           │ 6.Verifier  │  报告校验 → verification_report.md
           └─────┬─────┘
                 ▼
           ┌───────────┐
           │ 7.Publisher │  HTML/PPT/图片/视频 → report.{html,pptx,png,mp4}
           └─────┬─────┘
                 ▼
           ┌───────────┐
           │ 9.QualityGate│ 事实性/引用完整性/索引/口径 → quality_report.md (PASS/FAIL)
           └───────────┘
```

## 文件结构

```
market-review/
├── SKILL.md                           # 本文件 - 工作流总指引
├── prompts/
│   ├── orchestrator.md                # 阶段1：任务拆解
│   ├── searcher.md                    # 阶段2：公众号文章爬取
│   ├── collector.md                   # 阶段3：财评数据获取
│   ├── analyst.md                     # 阶段4：量化分析
│   ├── aggregator.md                  # 阶段5：报告聚合
│   └── verifier.md                    # 阶段6：报告校验
├── scripts/
│   ├── market_data.py                 # 财评网站数据获取（akshare/东方财富API）
│   ├── wechat_fetcher.py              # 公众号文章爬取（wechat_articles_spider）
│   ├── news_overseas_collector.py     # 阶段8：新闻/舆情/海外市场采集（neodata + akshare）
│   ├── media_outlook_collector.py     # 阶段8b：重要媒体源下周预测与操作指导采集（neodata + 公众号）
│   ├── chart_style.py                 # 图表美化（10主题+双后端）
│   ├── report_utils.py                # 报告工具（保存/清理/校验）
│   ├── verifier.py                    # 独立验证层（事实性/无幻觉/结构）
│   ├── quality_check.py               # 阶段9：生成后质检门禁（规则质检:章节/配图 + 语义质检:事实性/无幻觉/口径）
│   ├── build_html_report.py           # 阶段7a：Markdown → 自包含 HTML（明亮专业主题）
│   ├── build_pptx.py                  # 阶段7b：report.md → 明亮专业 PPT（python-pptx，数据驱动）
│   ├── html_to_image.py               # 阶段7c：HTML → 整页长图/分段截图（Playwright）
│   └── make_video.py                  # 阶段7d：长图 + 讲解文本 → MP4 视频
├── refs/
│   └── writing_specs/
│       └── Report_Layout.md           # 报告排版规范
└── tests/
    └── generate_market-review.py      # 端到端测试脚本
```

## 使用方式

### 输入参数
- **timeframe**：`daily`（当天复盘）或 `monthly`（每月复盘）
- **market**：`a_share`（A股）/ `us_stock`（美股）/ `hk_stock`（港股），默认 `a_share`
- **focus**：可选，重点关注板块（如"科技/新能源/消费"）

### 输出
- `A股复盘报告-YYYYMMDD-YYYYMMDD.md`：最终股市复盘报告（Publisher 发布时把 Agent 产出的 `report.md` 规范化为该日期化命名，作为唯一规范报告源）
- `A股复盘报告-YYYYMMDD-YYYYMMDD-事实性校验.md`：语义质检（事实性/无幻觉）核查报告
- `A股复盘报告-YYYYMMDD-YYYYMMDD-质检报告.md`：两层质检门禁报告（规则+语义，PASS/FAIL）
- `market_data/`：CSV 市场数据（再生依据，保留）
- `articles/`：公众号文章聚合（再生依据，保留）
- `sessions/`：图表（再生依据，保留）
- `A股复盘报告-YYYYMMDD-YYYYMMDD.html` / `.pptx` / `.mp4`：由阶段 7 Publisher 生成的 HTML、PPT、讲解视频（可选）
- `_archive/`：旧版本残留与中间产物归档（构建长图/截图 `report_images/`、narration.txt、旧脚本/旧运行产物等），可安全保留或按需删除

## 输出格式扩展：HTML / 图片 / 视频

在 Markdown 报告与校验通过后，可一键生成适合分享与汇报的多模态产物：

### 1. Markdown → 自包含 HTML

```bash
python scripts/build_html_report.py \
  --report-md market_review_output/A股复盘报告-20260810-20260814.md \
  --out market_review_output/A股复盘报告-20260810-20260814.html \
  --title "A股市场周度复盘" \
  --subtitle "分析期间：2026年8月10日—8月14日" \
  --badge "market-review 技能自动生成"
```

- 输出为单个 `.html` 文件，图表以 base64 内嵌，无需外部网络即可打开。
- 自动生成**可交互左侧目录栏**（固定侧边、点击跳转章节、滚动高亮），明亮专业主题（浅色背景 + 深蓝/金色强调、卡片化阴影）、A 股红涨绿跌配色；并将正文 `[n]` 引用角标渲染为金色胶囊，便于溯源。

### 2. HTML → 高清长图 / 分段截图

依赖：已安装 Chromium（Playwright 浏览器），Python 包 `playwright`。

```bash
# 推荐：先生成整页长图（适合朋友圈/公众号/长图分享）
python scripts/html_to_image.py \
  --html market_review_output/A股复盘报告-20260810-20260814.html \
  --out market_review_output/report_images \
  --width 1280 --scale 2 --mode full

# 或同时生成分段截图（mode=full|section|both）
python scripts/html_to_image.py \
  --html market_review_output/A股复盘报告-20260810-20260814.html \
  --out market_review_output/report_images \
  --width 1280 --scale 2 --mode both
```

- `--scale 2` 生成 2× 高清图；`--mode full` 输出 `report_full.png` 整页长图；`--mode section` 按标题切分为多段 PNG。
- 脚本会自动查找本机 `ms-playwright` 目录中的 `chrome.exe` 并注入中文字体回退，避免乱码。

### 3. 长图 + 讲解文本 → MP4 视频

依赖：`pyttsx3`、`Pillow`、`imageio_ffmpeg`。

```bash
# 1. 准备一段 150 字左右的讲解文本
# 2. 运行
python scripts/make_video.py \
  --image market_review_output/report_images/report_full.png \
  --text market_review_output/narration.txt \
  --out market_review_output/A股复盘报告-20260810-20260814.mp4 \
  --min-duration 60 --voice-rate 180
```

- 使用 Windows 自带 SAPI5 中文语音（`pyttsx3`），无需联网即可合成讲解音频。
- 视频以 1920×1080 分辨率从长图顶部平滑滚动到底部，音画同步。
- 若 TTS 不可用，脚本会输出无声滚动视频并给出警告。

### 4. 报告 → 专业 PPT

依赖：`python-pptx`、`Pillow`（已列入 requirements.txt）。

```bash
python scripts/build_pptx.py \
  --report-md market_review_output/A股复盘报告-20260810-20260814.md \
  --session market_review_output/sessions/session_market01 \
  --out market_review_output/A股复盘报告-20260810-20260814.pptx \
  --subtitle "分析期间：2026年8月10日（周一）— 8月14日（周五）· 五个交易日" \
  --badge "market-review 技能自动生成 · 数据截至 2026-08-15"
```

- 输出 17 页**明亮主题** PPT（封面 / 目录 / 执行摘要 / 指数 / 量能 / 板块轮动 / 资金流向 / 涨跌分布 / 资金面口径 / 情绪(量化+媒体) / 新闻面与政策 / 海外市场 / 事件 / **重要媒体源下周预测与操作指导** / 风险 / 展望 / 免责），采用白色卡片 + 深蓝页眉 + 金色强调，圆角卡片化，红涨绿跌配色。
- **数据驱动、可跨期复用**：脚本自动解析 report.md 中的指数表、资金净流入、涨跌家数、上涨占比、年化波动率等关键数字，无需每期手动改数值；各章节叙述要点也直接从对应小节抽取。
- 内嵌 `sessions/<session>/` 下的 8 张标准图表（index_trend / index_comparison / volume_trend / volatility / sector_ranking / sector_flow / sector_pie / daily_returns）；若某图缺失会自动跳过，不会报错。
- 章节标题抽取兼容 `一、…` / `### 标题` 等多种中文排版格式，遇到缺失小节时回退到内置通用要点，保证每期都能产出完整 PPT。

## 阶段8：新闻面 / 舆情 / 海外市场采集

补齐原技能在四个维度的缺口：**情绪分析（媒体舆情温度计）**、**新闻面与政策动态（权威媒体/财评整合）**、**海外市场及消息（美股/宏观/大宗）**。数据来自 `neodata-financial-search` 技能（聚合财经新闻、机构研报、财评、海外市场与宏观）与 akshare 美股指数（直连校验）。

```bash
python scripts/news_overseas_collector.py \
  --start 2026-08-10 --end 2026-08-14 \
  --out market_review_output \
  --session market_review_output/sessions/session_market01 \
  --python /path/to/python
```

产出：
- `articles/news_roundup.md` / `articles/overseas_roundup.md`：聚合的文章与观点（含标题、摘要、来源查询）。
- `market_data/overseas_indices.csv`：美股三大指数周度涨跌（akshare）。
- `market_data/derived_news.csv`：关键派生数字（道指/标普/纳指周涨跌与收盘、隔夜涨跌、黄金/白银/原油/美债、全球资金流向等），**供阶段6 校验器落地**，确保报告数字 0 无法验证。
- `sessions/<session>/overseas_indices.png`：海外市场指数周表现图（图9）。
- `sessions/<session>/sentiment_thermometer.png`：舆情温度计图（图10，由阶段5.2b `sentiment_thermometer.py` 生成）；`market_data/sentiment_scores.json`：5 维情绪得分。
- `market_data/news_overseas_raw.json`：原始聚合结果留存。

要点：
- **凭证自动复用**：`neodata-financial-search` 的 `query.py` 自动读取 `~/.workbuddy/skills/.neodata_token` 缓存（12h），外部无需关心鉴权；若过期，先执行该技能的凭证获取流程。
- **口径严格分离**：美股"周度涨跌"用 akshare（与 A 股周对齐），"隔夜收盘"用 neodata 文档（末收价与 akshare 一致），二者不混用，避免幻觉。
- **优雅降级**：任一 neodata 查询失败时，采集器写入"暂缺"标记并继续，Aggregator 仍须输出对应章节（注明数据暂缺），保证结构完整与校验通过。
- **可借鉴技能**：`stock-catalyst-hunter`（新闻/政策→A股题材映射）、`stock-analysis`（美股 8 维分析）可作为题材与海外个股深度分析的补充。

## 阶段8b：重要媒体源下周预测与操作指导采集

补齐复盘报告"前瞻"维度：聚合**券商研报/财评公众号/权威财经媒体**（财联社/证券时报/新华社/央视财经等）对下一交易周的预测与操作指导。数据来自 `neodata-financial-search` 技能（聚合财经新闻、机构研报、财评观点）与公众号文章，由 `media_outlook_collector.py` 产出 `market_data/media_outlook.json`（结构化条目：来源/来源类型/大势判断/操作建议/观点倾向）与 `articles/media_outlook_roundup.md`，供 Aggregator 拼装「重要媒体源下周预测与操作指导」章（每条来源对应 `[n]` 角标）。

```bash
python scripts/media_outlook_collector.py \
  --start 2026-08-10 --end 2026-08-14 \
  --out market_review_output
```

要点：
- **三类重要媒体源**：券商研报/机构策略、财评类公众号/自媒体、权威财经媒体，覆盖用户指定的"券商+财评号+权威媒体"。
- **优雅降级**：任一 neodata 查询失败时，采集器写入"暂缺"标记并继续，Aggregator 仍须输出对应章节（注明数据暂缺），保证结构完整与质检通过。
- **严禁编造**：仅落地真实可引用数据；媒体观点须标明来源与 `[n]` 引用，与"本技能综合判断"明确区分。

## 阶段9：生成后质检门禁（质量关卡）

在报告与全部多模态产物（HTML/PPT/图片/视频）生成之后运行，**对成品做最终质量门禁**。质检分为两层，两层均通过才算 **PASS**：

- **规则质检（结构完整性 / 确定性检查）**：核对「该有的章节与配图是否齐全」——不依赖主观判断，按固定清单机械比对。
- **语义质检（内容正确性 / 软性校验）**：核对「内容是否真实、有无幻觉」——对陈述做事实性比对与口径一致性检查。

```bash
python scripts/quality_check.py \
  --report market_review_output/A股复盘报告-20260810-20260814.md \
  --data market_review_output/market_data \
  --output market_review_output
```

### 规则质检（章节 + 配图齐全性）
1. **章节齐全性**：报告须含全部必需章节（执行摘要 / 市场总体表现 / 板块表现 / 资金面 / 市场情绪 / 新闻面 / 海外市场 / 重要事件回顾 / **重要媒体源下周预测与操作指导** / 风险提示 / 下周展望 / 引用与数据来源），缺一则 FAIL。
2. **配图齐全性**：必需图表文件（10 张：指数走势/对比、量能、日收益、波动率、板块排行/分布/资金流、海外指数、舆情温度计）是否都生成，并核对——(a) 全部内联进 `report.html`（`<img>` 数 ≥ 必需数）；(b) `report.pptx` 内嵌关键图表（≥5 张）。任一缺失即 FAIL。同时列出「配图 ↔ 归属章节」映射。
3. **文章索引**：检查生成的 HTML 是否含可交互左侧目录栏（class="sidebar" + class="toc-item"，即文章级导航，可点击跳转章节）。
4. **引用完整性**：拆分正文与「引用与数据来源」表，检查正文中每个 `[n]` 角标都在引用表中存在定义（缺失即 FAIL），并提示未被引用的定义（WARN）。

### 语义质检（幻觉 / 事实性）
1. **事实性 / 准确性 / 无幻觉**：复用 `verifier.verify_report`，对每条含数字的陈述做源数据比对（GROUNDED / SPECULATIVE / UNVERIFIABLE），并执行结构、幻觉、实时性检查，写出 `verification_report.md`（Publisher 最终重命名为 `A股复盘报告-YYYYMMDD-YYYYMMDD-事实性校验.md`）。
2. **数据口径一致性**：检查海外市场章节是否同时标注 `akshare`(周度) 与 `neodata`(隔夜/宏观) 来源，避免跨口径混用导致幻觉。

输出：
- `quality_report.md`：综合质量评分（0–100）与 **PASS / FAIL** 门禁，分别列出「规则质检评分」与「语义质检评分」及各自分项（章节/配图/索引/引用、事实性/口径）。Publisher 最终重命名为 `A股复盘报告-YYYYMMDD-YYYYMMDD-质检报告.md`。
- 门禁通过条件：**规则质检通过**（无缺失章节、无缺失配图、索引存在、引用无缺失、HTML/PPT 配图齐全）**且** **语义质检通过**（UNVERIFIABLE=0 且无幻觉结构问题）。

> 建议将本阶段作为发布前的强制关卡：仅当 `quality_report.md` 显示 **PASS** 才对外交付报告与多模态产物。

## 端到端运行脚本（tests/generate_market-review.py）

技能内置一键端到端驱动，自动串联「可脚本化」的各阶段（阶段8 海外采集 → 7a HTML → 7c 图片 → 7d 视频 → 7b PPT → 6 语义质检 → 9 两层质检门禁）。任一非门禁阶段失败均**优雅降级、继续**，仅最终门禁决定是否 PASS；脚本退出码 0 即 PASS。**所有对外交付物按 `A股复盘报告-YYYYMMDD-YYYYMMDD.*` 日期化命名**（驱动自动把 Agent 产出的 `report.md` 规范化为该名并作为唯一报告源，HTML/PPT/视频/质检报告同此命名）。

```bash
# 在 market-review 技能根目录下执行（python 自动解析为隔离环境）
python tests/generate_market-review.py \
  --out <你的输出目录>/market_review_output \
  --start 2026-08-10 --end 2026-08-14 \
  --skip-stage8          # 已有海外数据时可跳过联网采集

# 不跳过阶段8（需 neodata 凭证 + akshare，联网）
python tests/generate_market-review.py --out <输出目录> --start ... --end ...
```

**运行环境说明（双 Python）**：
- 构建类脚本（`build_html_report` / `build_pptx` / `make_video` / `verifier` / `quality_check`）在上游使用 WorkBuddy 隔离的 managed Python，解释器位置和已装依赖以本机配置为准，不依赖某个用户目录。本项目按 `src/skills/README.md` 的适配边界运行，不直接执行这些上游脚本。
- **HTML→图片（阶段7c）需 Playwright + Chromium**，驱动自动改用隔离 venv（`envs/default`，已装 playwright + chromium-1217）执行；若手动运行 `html_to_image.py`，请使用该 venv 的 python。
- 阶段8 `news_overseas_collector.py` 调用 `neodata-financial-search` 技能的 `query.py`（自动复用 `~/.workbuddy/skills/.neodata_token` 凭证缓存）。

## 依赖技能

### wechat-article-skill（公众号文章获取）

本技能依赖同级目录下的 `dependency_skills/wechat-article-skill` 技能，用于搜索微信公众号文章和提取文章正文。

**自动安装**：若同级目录不存在 `dependency_skills/wechat-article-skill`，可执行以下命令自动安装：

```bash
# wechat-article-skill 已预置在同级目录（market-review/wechat-article-skill/），无需额外下载
# 若缺失，可通过 git clone 或手动复制到同级目录

# Python依赖自动检查
python scripts/check_deps.py
```

**引用方式**：
```python
# 从依赖技能导入（相对路径，基于 market-review/ 为当前目录）
import sys
sys.path.insert(0, "../wechat-article-skill/scripts")
from wechat_fetcher import search_wechat_articles, extract_article_content, generate_sentiment_report
```

**功能**：
- `search_wechat_articles(keywords, count)` - 按关键词搜索公众号文章
- `extract_article_content(url)` - 给定文章URL提取正文
- `generate_sentiment_report(articles, output_dir)` - 生成舆情分析报告

### neodata-financial-search（金融数据 / 新闻 / 海外）

本技能依赖同级 `neodata-financial-search` 技能获取**新闻面、舆情、海外市场与宏观**数据，覆盖财经新闻、机构研报、财评观点、美股/全球指数、美联储利率、外汇、大宗商品等。

- 调用方式：`python neodata-financial-search/scripts/query.py --query "..."`（自动处理凭证缓存）。
- 用途映射：
  - 情绪/媒体整合：`--query "本周 A股 重要财经新闻 政策动态 与 机构观点"`（doc 召回）。
  - 海外市场：`--query "本周 美股 纳斯达克 标普500 道琼斯 周涨跌幅 与 美联储 海外市场消息"`（api+doc）。
  - 宏观/大宗：`--query "本周 全球市场 重大宏观事件 美联储 利率 地缘政治 大宗商品 黄金 原油 走势"`。
- 注意：召回结果可能含模型归纳内容，关键数字以 `market_data/` 源文件与 `derived_news.csv` 为准。

### akshare 美股指数（海外行情直连校验）

`news_overseas_collector.py` 通过 `akshare.stock_us_daily(symbol=".INX"/".IXIC"/".DJI")` 直连抓取美股三大指数，作为 neodata 海外数据的交叉校验源，计算周度涨跌。

## 数据源

### 财评网站（量化数据）
| 数据源 | 库/接口 | 数据类型 |
|--------|---------|----------|
| 东方财富 | akshare | 指数行情/板块涨跌/资金流向/北向资金 |
| 同花顺 | pywencai | 问财智能查询/概念板块/资金分布 |
| 新浪财经 | requests | 实时行情/历史K线 |

### 公众号文章（定性观点）
| 工具 | 方式 | 说明 |
|------|------|------|
| wechat_articles_spider | Python库 | 按关键词搜索公众号文章 |
| wechat-article-skill | URL提取 | 给定文章URL提取正文（依赖技能） |
| 搜狗微信搜索 | requests | 按关键词搜索（前10条） |

### neodata 金融搜索（新闻 / 舆情 / 海外 / 宏观）
| 覆盖 | 说明 |
|------|------|
| 财经新闻 / 机构研报 / 财评 | 本周政策、事件、机构观点整合 |
| 海外市场 | 美股指数、美联储、地缘、大宗（黄金/原油/美债） |
| 宏观数据库 | 美债收益率、就业、CPI 等 |

### akshare 美股指数（海外行情校验）
| 标的 | 代码 | 用途 |
|------|------|------|
| 标普500 | .INX | 周度涨跌交叉校验 |
| 纳斯达克 | .IXIC | 周度涨跌交叉校验 |
| 道琼斯 | .DJI | 周度涨跌交叉校验 |

## 报告结构

报告标题格式：
- 当天复盘：**{市场}市场当日复盘（{结束日期}）**，如"A股市场当日复盘（2025.06.19）"
- 每月复盘：**{市场}市场月度复盘（{开始日期}-{结束日期}）**，如"A股市场月度复盘（2025.05.19-2025.06.19）"

1. 执行摘要（金字塔原理：核心结论+3个支撑点）
2. 市场总体表现（指数走势/成交额/波动率）
3. 板块表现分析（涨跌幅排行/轮动分析）
4. 资金面分析（主力资金/北向资金/融资融券）
5. 市场情绪与舆情（5.1 量化情绪 + 5.2 媒体舆情温度计）
6. 新闻面与政策动态（权威媒体/财评整合：政策/事件/机构观点）
7. 海外市场及消息（美股周度/隔夜、美联储、地缘、大宗）
8. 重要事件回顾（政策/经济数据/突发事件）
9. 重要媒体源下周预测与操作指导（券商研报/财评公众号/权威财经媒体：预测+操作指导，[n]引用）
10. 风险提示
11. 次日/下月展望
12. 局限性与免责声明
