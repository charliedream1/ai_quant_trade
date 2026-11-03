# 使用文档

首次使用从[一体化工作台使用指南](workspace.md)开始，统一了解src应用的环境、启动、九模块入口、策略到回测、AI/知识与CLI；对应主题的详细步骤和原理仍在下表的各自正文。

使用文档按操作目标组织，涵盖当前九模块、统一CLI及独立研究入口。关键步骤配实际界面和结果核对，真实行情、模拟行情与模型回复的来源分别说明。想了解计算与设计依据，请进入[原理文档](../principles/README.md)。

## 推荐阅读顺序

| 目标 | 建议页面 |
|------|----------|
| 第一次启动并完成研究闭环 | [工作台使用指南](workspace.md)、[快速上手](quick_start.md) |
| 准备运行环境 | [依赖安装](installation.md) |
| 了解环境边界、导航及访问/源码复核 | [统一入口](navigation_and_environment.md)、[访问控制](access_and_execution.md) |
| 安装、登录并接入AI命令行工具 | [AI CLI安装](cli_installation.md) |
| 读懂首页与研究结果 | [总览](dashboard.md)、[行情与因子](market_research.md)、[研报论文](reports.md) |
| 首次导入和回测策略 | [策略导入](strategy_import.md)、[回测结果核对](backtest.md) |
| 设置手续费、税费、滑点和执行假设 | [交易成本与执行设置](backtest_execution.md) |
| 验证模型与模拟账户 | [模型策略](model_strategies.md)、[模拟交易](paper_trading.md) |
| 网页对话、附件、后台和项目会话 | [AI 工作台](ai_workspace.md) |
| 重要提醒、关闭回看与机器人外观 | [提醒中心与助手形象](notifications.md) |
| 用命令行操作策略、回测和 AI 会话 | [命令行](cli.md) |
| 为Agent选择CLI后端，或不用网页直接运行10类研究 | [Agent后端与原生Skills](agent_cli_skills.md) |
| 了解每个页面做什么 | [功能模块](modules.md) |
| 调整策略参数并比较结果 | [策略调参](strategy_parameters.md) |
| 规则→模型→Agent级联、并行融合、Risk/Portfolio | [策略工坊](strategy_composition.md) |
| 中文多空、信息/研究竞赛及成熟成绩 | [Agent策略](agent_strategies.md) |
| ETF 池、轮动和多 Agent 复核 | [ETF 研究](etf_research.md) |
| 因子研究、股票池监控和Qlib信号 | [多特征策略](factor_research.md)、[因子监控](factor_monitoring.md) |
| 三角色Alpha、主题和市场体制实验 | [Alpha研究](alpha_mining.md) |
| 理解为什么这样组织 | [系统原理](../principles/architecture.md) |
| 调整启动、日志和数据源 | [配置说明](configuration.md) |
| 管理资料和定时任务 | [知识库](knowledge.md)、[自动化](automation.md) |
| 导入股票池/因子池并校验文件 | [资源池模板](resource_pools.md) |
| 阅读Office/PDF/HTML或编辑Markdown | [文件阅读与编辑](file_reader.md) |
| 阅读分章课程及查找系统帮助 | [学习空间](workspace_learning.md) |
| 一键复盘市场或分析个股 | [Skill 洞察报告](insight_reports.md) |
| 排查页面慢、404、行情失败 | [排障指南](troubleshooting.md) |
| 判断系统适用边界 | [风险边界](risk.md) |
| 维护分类、构建和发布帮助站点 | [MkDocs 发布指南](documentation_publish.md) |

## 使用定位

本系统适合个人或小团队做本地投研、策略原型、资料整理、回测演示、模拟交易练习、知识问答和页面化回归验证。系统强调一体化闭环和可解释界面，不替代专业实盘交易终端。

当前版本不适合直接承载真实资金自动交易，也不适合高频交易、低延迟行情、组合级生产风控闭环或合规审计要求很高的场景。

截图与正文一起维护，采集日期、数据模式和历史图来源见[截图索引](assets/screenshots/README.md)。历史设计、调研和验收资料保留在项目原目录，由总索引说明位置。
