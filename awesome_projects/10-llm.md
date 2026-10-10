# LLM Applications

## General Platforms

- **[FinGPT](https://github.com/AI4Finance-Foundation/FinGPT)** — Data-centric financial LLM; FinLLM full-stack framework (data source, data engineering, LLM, task, application layers); 11 fine-tuned models & 14 datasets; FinGPT-Forecaster app. Code paused since Nov 2023.
  - Language: Jupyter Notebook · License: MIT · Stars: 15.9k
  - Docs: https://ai4finance-foundation.github.io/FinNLP/ · HF: https://huggingface.co/FinGPT
- **[QuantDinger](https://github.com/brokermr810/QuantDinger)** — Lets you fully own your quant system: research → backtest → live execution in one place, keeping your API keys and strategies private.
  - Language: Python · Stars: 7.3k · Demo: https://ai.quantdinger.com · Docs: https://docs.quantdinger.com
- **[go-stock](https://github.com/ArvinLovegood/go-stock)** — AI-powered stock analysis & selection tool; multi-market (A/HK/US), local data privacy, AI analysis + alerts; Vue 3 + Go + Wails desktop.
  - Language: Go · License: GPL-3.0
- **[QuantMind](https://github.com/qusong0627/quantmind)** — Next-gen intelligent quant architecture; Qlib-powered (LightGBM, Alpha158, auto feature engineering), dual-engine backtest (Qlib + Pandas), multi-broker live trading.
  - Language: Python · Stars: 455
- **[daily_stock_analysis](https://github.com/ZhuLinsen/daily_stock_analysis)** — LLM-powered A/H/US stock analyzer: multi-source quotes + real-time news + LLM decision dashboard + multi-channel push (WeCom/Feishu/Telegram/Discord/Slack/email).
  - Language: Python · Stars: 33k
- **[OpenStock](https://github.com/Open-Dev-Society/OpenStock)** — Modern stock analysis platform (Next.js 15, React 19, TypeScript); 30+ exchanges, watchlists, embedded TradingView charts, AI welcome email & daily news summary.
  - Language: TypeScript · License: AGPL-3.0 · Stars: 19.5k

## Trading Strategies

- **[FinMem-LLM-StockTrading](https://github.com/pipiku915/FinMem-LLM-StockTrading)** — Performance-enhanced LLM trading agent with hierarchical memory and character design.
  - Language: Python · Paper: https://arxiv.org/abs/2311.13743
- **[sep (Self-Reflective Predict)](https://github.com/koa-fin/sep)** — "Learning to Generate Explainable Stock Predictions using Self-Reflective Large Language Models" (WWW 2024).
  - Language: Python · Paper: https://arxiv.org/abs/2402.03659
- **[AlphaFin / Stock-chain](https://github.com/AlphaFin-proj/AlphaFin)** — RAG-integrated Stock-Chain framework for stock analysis; AlphaFin dataset for fine-tuning FinLLM with hand-written CoT data.
  - Language: Python · License: MIT · Stars: 18 · Paper: https://arxiv.org/pdf/2403.12582.pdf
- **[Polymarket Agents](https://github.com/Polymarket/agents)** — Framework & toolset for building AI agents on Polymarket: API integration, prediction-market agent tools, local/remote RAG, data sources.
  - Language: Python · License: MIT · Stars: 2.8k
- *LLM financial analyst (LangGraph + OpenAI + yfinance)* — Article: https://mp.weixin.qq.com/s/TKgXnUi80TS7Wa5zDf28Hg
- *Combining Financial Data and News for Stock Prediction using LLMs* — Paper: https://arxiv.org/pdf/2411.01368

## Financial LLMs

### Data
- **[finbooks](https://modelscope.cn/datasets/orangemouse/finbooks)** — Finance/economics book collection.
- **[IndustryCorpus2_finance_economics](https://modelscope.cn/datasets/BAAI/IndustryCorpus2_finance_economics)** — BAAI industry corpus (finance subset).
- **[chinese-financial-news-2019](https://modelscope.cn/datasets/tangzhiling/chinese-financial-news-2019)** — Chinese financial news dataset (2019).
- **[FinQA](https://github.com/czyssrs/FinQA) / [ConvFinQA](https://github.com/czyssrs/ConvFinQA) / [FinRED](https://github.com/soummyaah/FinRED) / [CHRNN](https://github.com/wuhuizhe/CHRNN) / [slot](https://github.com/deeptrade-public/slot)** — Financial NLP datasets (reasoning, sentiment, relation extraction).
- **[chatglm_llm_fintech_raw_dataset](https://modelscope.cn/datasets/modelscope/chatglm_llm_fintech_raw_dataset/summary)** — ChatGLM fintech challenge dataset.
- **[bs_challenge_financial_14b_dataset](https://modelscope.cn/datasets/BJQW14B/bs_challenge_financial_14b_dataset)** — BoJin LLM challenge financial 14B dataset.

### Training
- **[CFGPT1](https://github.com/TongjiFinLab/CFGPT1)** — "Chinese Financial Assistant with Large Language Model" (CPT/SFT/RLHF).
  - Paper: https://arxiv.org/abs/2309.10654
- **[InternLM](https://github.com/InternLM/InternLM)** — Base LLM (Apache-2.0).
- **[Firefly](https://github.com/yangjianxin1/Firefly)** — LLM fine-tuning framework.

### Evaluation
- **Public benchmark suites**: CFBenchmark-Basic, FinDER, FinQABench, FinanceBench, TATQA, FinQA, ConvFinQA, MultiHiertt.

## RAG

- **[FinanceRAG](https://github.com/cv-lee/FinanceRAG)** — Multi-reranker RAG for finance.
  - Language: Python · Paper: https://arxiv.org/abs/2411.16732

## Agents

- **[FinRobot](https://github.com/AI4Finance-Foundation/FinRobot)** — Open-source AI agent platform for financial applications: market forecasting, report analysis, trading strategy agents; financial CoT prompting; LLMOps + DataOps.
  - Language: Python · License: Apache-2.0 · Stars: 2.3k · Paper: https://arxiv.org/pdf/2405.14767
- **[TradeMaster](https://github.com/TradeMaster-NTU/TradeMaster)** — RL-powered quant trading platform (see also [Trading Strategies](05-trading-strategies.md)).
  - Language: Python · Stars: 1.7k
- **[TradingAgents](https://github.com/TauricResearch/TradingAgents)** — Multi-agent trading framework: fundamental/sentiment/technical analysts, trader, risk team collaborate via dynamic discussion.
  - Language: Python · License: Apache-2.0 · Stars: 14.3k · Paper: https://arxiv.org/pdf/2412.20138
- **[TradingAgents-CN](https://github.com/hsliuping/TradingAgents-CN)** — Chinese financial trading decision framework based on TradingAgents; A-share adaptation with Streamlit UI.
  - Language: Python · Stars: 1.4k
- **[ContestTrade](https://github.com/FinStep-AI/ContestTrade)** — Trading agent framework for competitions.
  - Language: Python · License: Apache-2.0
- **[ai-hedge-fund](https://github.com/virattt/ai-hedge-fund)** — AI hedge fund team: multiple investor agents making trading decisions (educational).
  - Language: Python · License: MIT
- **[Vibe-Trading](https://github.com/HKUDS/Vibe-Trading)** — AI-powered multi-agent financial workbench: natural language → strategy, 6 data sources, 29 expert teams, cross-session memory, 7 backtest engines, multi-platform export.
  - Language: Python · License: MIT · Stars: 4.1k
- **[AlphaCrafter](https://github.com/NJU-LINK/AlphaCrafter)** — Multi-agent framework for cross-sectional quant trading (LLM factor discovery + state-aware selection + adaptive execution).
  - Language: Python · License: MIT · Stars: 18 · Paper: https://arxiv.org/abs/2605.05580

## Skill Packs

- **[investment-master-mindset](https://github.com/Cat-Geek/investment-master-mindset)** — Investment master skill (Buffett, Graham, Livermore, Soros, Lynch, Simons, etc.).
  - Language: (skill) · Stars: 20
- **[Anthropic Financial Services](https://github.com/anthropics/financial-services)** — 11 end-to-end agents + 7 vertical skill packs for financial services (pitch, model builder, GL reconciler, earnings reviewer, etc.).
  - Stars: 23.9k
- **[a-stock-data](https://github.com/simonlin1212/a-stock-data)** — Full-stack China A-share data toolkit for AI agents: 11 layers, 54 endpoints, 19 sources, zero-auth.
  - Language: Python · Stars: 9.3k
- *OpenClaw popular skills* — Article: https://mp.weixin.qq.com/s/wzRmdM5vQacxPrAMB9F6Fw

## Alpha Mining

- **[AlphaCrafter](https://github.com/NJU-LINK/AlphaCrafter)** — Full-stack multi-agent framework for cross-sectional quant trading. License: MIT · Paper: https://arxiv.org/pdf/2605.05580
- **[AlphaAgent](https://github.com/hongha5192-bit/AlphaAgent)** — LLM-driven alpha mining with regularized exploration to counteract alpha decay.
  - Language: Python · Stars: 3 · Paper: https://arxiv.org/abs/2502.16789
- **[AlphaAgentEvo](https://github.com/hongha5192-bit/AlphaAgentEvo)** — Evolution-oriented alpha mining via self-evolving agentic reinforcement learning.
  - Language: Python · Stars: 7 · Paper: https://openreview.net/forum?id=lNmZrawUMu
- **[AI_factor](https://github.com/MikeYan8080/AI_factor)** — "Beyond Prompting: An Autonomous Framework for Systematic Factor Investing via Agentic AI" (54.81% annualized, Sharpe 2.75).
  - Language: Python · Stars: 4 · Paper: https://arxiv.org/html/2603.14288v1

## Tool Search

- **[QVeris](https://github.com/QVerisAI/QVerisAI)** — Financial data navigation system for agents: QVeris CLI, MCP Server, QVerisBot, REST API.
  - Language: JavaScript · License: MIT · Website: https://qveris.cn
