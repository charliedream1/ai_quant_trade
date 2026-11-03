# 文档总索引

因子研究扩展：[使用与配图](usage/factor_research.md)、[时点与评分原理](principles/factor_research.md)、[开源思路取舍](research/composition/factor_research_review.md)。

正式阅读入口分为两类，操作正文和原理正文各自只维护一份。

| 分类 | 从这里开始 | 内容 |
| --- | --- | --- |
| 使用文档 | [操作指南](usage/README.md) | 安装启动、行情资料、策略调参、回测模拟、AI、知识库、自动化与 CLI，配合实际截图 |
| 原理文档 | [原理阅读路线](principles/README.md) | 架构、数据、策略端口、参数、指标、模型、ETF、AI、多 Agent 和存储 |

帮助站点以同样两类导航展示，默认地址为 `/help-docs/`；[首页](index.md)提供首次使用路线。截图随正文维护于 `usage/assets/screenshots/`，日期和数据模式见[截图来源](usage/assets/screenshots/README.md)。

MkDocs 构建、预览、根路径/子路径部署及发布验收见[文档维护与发布](usage/documentation_publish.md)，发布配置模板位于 `egs/mkdocs.publish.example.yaml`。

## 资料档案

| 位置 | 用途 |
| --- | --- |
| [正式设计](../doc/01_overview.md) | doc 目录中的架构、接口及专门设计，不写代码片段；Skill洞察见13号，[策略编排、Risk与Portfolio](../doc/14_strategy_composition_risk_portfolio_design.md)见14号（A/B已接入），[Gradio图形工坊方案](../doc/15_gradio_visual_strategy_editor_design.md)见15号（待确认） |
| [应用调研](research/README.md) | 模型、ETF 和多 Agent 的真实使用证据与选型边界 |
| [外部参考](reference/README.md) | 论文、官方文档和技术资料 |
| [历史验收](audit/README.md) | 测试报告、截图、JSON 和回归证据，保留原路径 |
| gradio_frontend.md、gradio_modularization_plan.md | 实现资料及整改计划，不作为首次操作教程 |
| tasks*.md | 任务规格与功能清单，常规整理不修改 |

## 旧入口与维护

`help/`、`cli/README.md`、`dependency_installation.md`、`storage_selection.md` 等旧文件保留迁移链接，旧帮助地址继续可访问；它们不维护重复正文。

新增教程放在 usage，说明前置条件、入口、步骤、结果及失败处理；关键操作截图放在步骤附近并标明来源。解释计算与设计时放在 principles，引用对应使用指南和正式设计。历史报告不改写成当前状态，也不批量复制到帮助搜索与静态站点。

修改后同步 MkDocs 导航、帮助更新检测、学习目录和 changelog，验证链接、图片、搜索、中文编码与相关功能。删除文件仍需单独确认。
