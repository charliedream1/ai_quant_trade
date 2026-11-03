# 操作截图来源

2026-10-31新增[96 章节切换刷新](96-knowledge-refresh.jpg)、[97 阅读关闭与提醒](97-reader-notification.jpg)：8897/8898隔离服务实际点击，包含当前章节保持、Word真实转换及严重摘要下关闭入口；全为mock行情和标注测试资料，不代表实盘或模型收益。原图和结果见docs/audit/code_health_e2e_2026-10-31。

2026-10-30新增[94 源码运行复核](94-source-review.jpg)与[95 浏览器访问验证](95-access-login.jpg)。来自8894本地mock、8898令牌隔离服务的实际点击，源码复核后工作进程完成回测；登录截图未输入令牌，不含凭据。截图仅证明界面/流程，原始图及检查见docs/audit/code_health_fix_2026-10-30。真实模型另做一次29token的连接测试，不与mock行情指标混用。

2026-10-29新增[92 Alpha后端](92-agent-provider-alpha.jpg)、[93 专家团后端](93-agent-provider-team.jpg)：8893隔离Gradio服务实际点击Qoder/Codex、输入模型名和打开专家团。仅展示控件及页面定位，未从浏览器发起付费模型请求；真实API/CLI小样本证据单独保存在本轮验收目录。缺失日历摘要来自隔离环境，不代表账户风险。

2026-10-27新增[74 Alpha入口](74-alpha-main.jpg)、[75 假设实现证据](75-alpha-evidence.jpg)、[76 主题原文关联](76-alpha-theme.jpg)、[77 体制矛盾阻断](77-alpha-regime.jpg)、[78 Alpha报告库](78-alpha-library.jpg)。通过8897隔离服务只读打开真实Qwen3.8-27B试验记录，没有新增模型调用；五股各640根公开行情，主题来自明确标识的官方历史公司简介，体制来自ALFRED请求版本，非八模型绩效验收。真实Alpha未通过，体制矛盾已弃权；不要将completed或validated当成通过门槛。流程逐步点击另有显式协议替身验收，与这些真实证据分开归档。

2026-10-26新增50至58：合并资料、唯一RAG、统一因子监控、ETF入口、图形拖拽全屏、配置捷径、统一任务结果、实盘来源归因及暗色导航。来自8894隔离mock服务的真实浏览器操作；Qlib为独立真实工作进程，图中行情/回答均按模拟模式说明，不代表真实绩效。原始JSON和失败/最终截图在`docs/audit/dependency_navigation_implementation_2026-10-26/`；[统一入口指南](../../navigation_and_environment.md)内嵌配图。原有历史图保留不覆盖。

同轮新增[59 报告库](59-report-library.jpg)：实际打开隔离环境的旧模板记录，保留演示来源说明；未调用新LLM。PDF/DOCX上传与PNG/JPEG解码、报告库JSON及模块性能证据在该验收目录targeted下。

2026-10-25成本改进新增：[46 普通费用设置](46-execution-settings.jpg)、[47 实际成本结果](47-execution-results.jpg)、[48 一键回测成本](48-quick-execution.jpg)、[49 图形工坊费用覆盖](49-graph-execution.jpg)。来自8893隔离mock服务的真实浏览器操作，分别核对到实际执行快照；正式浏览器JSON、首次失败、真实四场景行情和账本另存`docs/audit/execution_costs_2026-10-25/`。图中收益不是真实绩效，未发实盘委托。操作见[费用指南](../../backtest_execution.md)。

2026-10-25工作台改进新增36至45：扁平输入、Skill首屏、RAG引用、独立课程、组合一键回测、冻结图形定位、真实CLI回复、悬浮底栏、全屏图形和生成报告。原始浏览器证据位于项目`docs/audit/workspace_implementation_2026-10-25/`。42使用真实只读Codex进程；45使用真实Codex生成但数据为mock且状态partial；其余展示隔离mock操作，真实六场景回测JSON与行情另存。详见[工作台与课程指南](../../workspace_learning.md)。

2026-10-25新增：[30 通用因子监控](30-factor-monitor.jpg)、[31 模板预览](31-resource-preview.jpg)、[32 错误校验](32-resource-errors.jpg)、[33 自适应图谱](33-relation-evidence.jpg)、[34 关系证据](34-relation-detail.jpg)、[35 暗色图谱](35-relation-dark.jpg)。来自8890隔离mock服务的真实浏览器操作，Qlib使用独立工作进程；真实五股行情对照与300只指数名单证据另外保存在项目 `docs/audit/monitor_platform_2026-10-25/`，不把mock图当成真实关系或绩效。图谱来源不足时不补边，截图未发送实盘委托。

2026-10-24因子研究新增实际配图：[27 量价合成权重](27-factor-equal.jpg)、[28 已到期标签研究](28-factor-research.jpg)、[29 模型特征集](29-factor-model-groups.jpg)。来自8889隔离Gradio服务的最终浏览器操作，原件位于项目 `docs/audit/factor_research_2026-10-24/browser-optimized/`，另保存暗色截图。三套策略实际使用归档真实行情回测，并与CLI重放核对，数据截止2026-10-22；没有发出实盘委托。

## Skill 洞察报告补图

2026-10-22，隔离服务 8884 实际点击采集；real 东方财富行情与已认证的本机 Codex CLI，未执行券商交易。报告保留 `partial` 和缺失项，不代表论断经过完整事实核查。

| 图 | 文件 | 实际操作 |
| --- | --- | --- |
| 18 | [洞察任务及报告](18-insight-market.jpg) | 选择 Codex、执行市场复盘并重开真实历史报告 |
| 19 | [个股价格与成交量](19-insight-stock.jpg) | 贵州茅台 120 日线，实际模型返回与可得数据 |
| 20 | [市场图表](20-insight-market-chart.jpg) | 指数与板块快照涨跌幅，图表可缩放 |

## 原操作指南配图

以下图片随操作步骤内嵌，不依赖历史验收目录。新增截图于 2026-10-22 在隔离服务 8882 中实际点击采集，使用 mock 行情和本地模拟账本，不产生真实券商交易。后台、来源及失败状态保持原样，截图不是收益承诺。

| 图 | 文件 | 实际操作及边界 |
| --- | --- | --- |
| 1 | [工作台总览](01-workspace-home.jpg) | 展开导航、刷新账户与市场；模拟账户两项持仓 |
| 2 | [市场研究](02-market-research.jpg) | 实际刷新指数和板块，mock-local |
| 3 | [研报检索](03-reports.jpg) | 关键词“半导体”，结果来自本地模拟资料 |
| 4 | [策略导入入口](04-strategy-import.jpg) | 刷新 13 套示例，网页实际导入布林带策略返回 ID=2；本图展示列表和入口 |
| 5 | [参数预览](05-parameter-preview.jpg) | 双均线 ID=1，预览 fast_window=5、slow_window=20 |
| 6 | [回测状态](06-backtest-results.jpg) | 网页实际创建任务 2，mock-local、2 笔已平仓；不是实盘绩效 |
| 7 | [回测图表](07-backtest-charts.jpg) | 同一任务的净值、回撤与分期结果 |
| 8 | [模型证据](08-model-evidence.jpg) | 复用 2026-10-19 正式模型验收图，LightGBM 拟合 13 次、预测 384 条、成交 62 笔；来源为归档真实行情，非本轮新训练 |
| 9 | [ETF 快照](09-etf-research.jpg) | 实际打开独立策略页、切换 ETF 研究并刷新；行情为 mock，费率为配置元数据 |
| 10 | [模拟账户](10-paper-trading.jpg) | 账户 ID=1，读取现金、持仓和已成交订单；本地模拟账本 |
| 11 | [AI 会话](11-ai-workspace.jpg) | 新建会话，Enter 发送；GenericAgent mock 回复明确标注测试模式 |
| 12 | [附件输入区](12-ai-attachments.jpg) | 实际选择项目内 question.txt，随后发送并留档；局部截图不展示完整文件路径 |
| 13 | [知识文档](13-knowledge.jpg) | 检索“回测”、读取文档 1 及分块，本地演示笔记 |
| 14 | [任务与历史](14-automation.jpg) | 任务保持关闭，手动模拟盘巡检成功；手动触发不代表启用定时执行 |
| 15 | [系统配置](15-settings.jpg) | 展示配置入口与真实的交易日历缺失提示；未保存设置，未展示密钥 |
| 16 | [多 Agent 边界](16-multi-agent.jpg) | 对任务 2 发起只读复核；未配置真实模型时明确失败，不生成成功结论 |

第 8 图原始证据保留在项目 `docs/audit/screenshots/2026-10-19-model-agent/05-model-training-final.jpg`，复制后不改动历史原件。其他 15 图均为本轮当前界面。

控件截图来自实际页面；局部裁切用于解释输入区，不替换页面文字或数据。完整操作见[使用文档](../../README.md)，指标含义见[原理文档](../../../principles/README.md)。

发布指南配图 [17-help-classification.jpg](17-help-classification.jpg) 复用 2026-10-22 文档分类验收的帮助首页，原件保留在 `docs/audit/documentation_reorganization_2026-10-22/help-home.jpg`。该图只展示实际构建的两类入口，不表示站点已上传外部服务器。

2026-10-23 策略工坊新增实际截图：[18 工坊运行](18-strategy-workshop.jpg)、[19 结构化编辑](19-composition-editor.jpg)、[20 资源池筛选](20-resource-pipeline.jpg)。来自本地8885隔离真实行情服务；只运行研究/模拟，不发送券商委托。正式行情、Agent及回测证据另见项目 `docs/audit/composition_2026-10-22/`。

同日图形工坊配图：[21 实际节点证据](21-graph-execution.jpg)、[22 子策略参数](22-graph-nested.jpg)、[23 暗色级联](23-graph-cascade-dark.jpg)。来自本地8886 Gradio 6.16隔离服务；21使用真实归档行情完成回测，22/23说明导航和编辑，不表示该截图草稿已经执行。验收证据保存在项目 `docs/audit/strategy_graph_2026-10-23/`。

2026-10-26新增[60 独立ETF窗口](60-standalone-etf.jpg)、[61 冻结图形窗口](61-standalone-frozen-graph.jpg)、[62 报告筛选](62-report-library-filter.jpg)、[63 缺失HTML说明](63-report-missing-artifact.jpg)、[64 伪图片拒绝后保留输入](64-invalid-image-rejected.jpg)。来自8895隔离mock服务的实际点击及Enter操作，明确标记报告样本，不表示真实模型生成。完整证据在`docs/audit/startup_experience_2026-10-26/`，真实行情回测另行归档。

2026-10-27新增[65 Markdown双栏](65-markdown-reader-editor.jpg)、[66 版本冲突](66-markdown-version-conflict.jpg)、[67 Word只读](67-word-readonly.jpg)、[68 Excel只读](68-excel-readonly.jpg)、[69 PPT只读](69-presentation-readonly.jpg)、[70 知识原件](70-knowledge-reader.jpg)、[71 会话附件](71-attachment-reader.jpg)、[72 HTML阅读](72-html-reader.jpg)、[73 暗色阅读](73-dark-reader.jpg)。来自8896隔离Gradio服务，Office内容为明确标记的功能样本并实际经LibreOffice转换，下载原件按哈希核对；Markdown演示文件验收后已恢复。测试对话使用mock后台，不代表真实模型分析。原始截图、转换文件与结果在`docs/audit/file_preview_2026-10-26/`（沿用任务开始日期）。

2026-10-24修复后的配图：[24 冻结版本与实际节点证据](24-graph-execution-fixed.jpg)、[25 子策略参数和层级](25-graph-nested-fixed.jpg)、[26 暗色级联](26-graph-dark-fixed.jpg)。来自8888隔离Gradio服务，24仅重开已完成的真实行情运行，没有提交新任务；25/26用于说明编辑和外观。旧21至23保留不覆盖；修复及完整浏览器证据在项目 `docs/audit/strategy_graph_fix_2026-10-24/`。

2026-10-28新增[79 中文事件方案](79-agent-workshop.jpg)、[80 阶段证据](80-agent-process.jpg)、[81 双团队竞赛](81-agent-contest.jpg)、[82 页内报告](82-agent-report.jpg)、[83 暗色工坊](83-agent-dark.jpg)。来自8898隔离Gradio服务的实际选择、配置、执行、取消及报告重开；模型为明确标注的文本ReAct协议夹具，行情AAA/BBB/CCC也为测试数据，图中收益不代表真实业绩。使用现有缩放和面板滚动展示证据，未替换页面文字。真实Qwen与公开行情/新闻结果另见`docs/audit/agent_strategies_2026-10-28/real/`，不与截图混用。

同日新增[84 工作台输入](84-composer-workbench.jpg)、[85 悬浮输入](85-composer-floating.jpg)、[86 暗色输入](86-composer-dark.jpg)。来自8899隔离服务，实际模拟附件/拖放、后端/权限切换及Enter/Ctrl+Enter；对话为明确标注的mock回复，Qoder安装与未认证状态单独验证，不能把截图当成Qoder真实回复。旧11/12等图片保留原始历史，不覆盖。

2026-10-29新增[87 右上提醒](87-global-notifications.jpg)、[88 提醒中心](88-notification-center.jpg)、[89 机器人入口](89-assistant-robot.jpg)、[90 暗色提醒](90-notification-dark.jpg)。来自8890隔离服务的实际关闭、已读、回看、头像切换/拖动及详情跳转；测试消息明确标注，行情为mock，缺失日历提示来自该隔离环境的实际状态。展示交互和外观，不代表真实账户风险或策略收益；原始结果保留在docs/audit/notifications_2026-10-29。

同日[91 导航折叠小图标](91-sidebar-toggle.jpg)来自8891隔离mock服务，28px箭头位于左侧导航栏右上角；展开、收起、暗色及800px窗口均已实际点击和截图。其余原始图与结果保留在docs/audit/sidebar_toggle_2026-10-29，不覆盖旧截图或声明真实金融测试。
