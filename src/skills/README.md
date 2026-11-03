# 内置洞察 Skill 来源与适配

本目录的 Skill、提示词和方法资料从本机 WorkBuddy 安装目录复制，运行时仅访问项目内副本。

| 目录 | 来源与用途 |
| --- | --- |
| market_review | market-review 的 SKILL、六阶段 prompts 和 Report_Layout，保留方法正文，个人路径改为通用表示 |
| single_stock_analysis | stock-analysis 6.2.1 的 SKILL；stock-analysis-23 1.0.2 的 A 股指引及完整技术参考 |

文件来源与当前摘要登记在 provenance.yaml。经过隐私适配的资源另保留 source_sha256、适配日期和说明，不把修改后的副本当作上游原文。未复制用户 token、缓存、组合账本、原生成报告或脚本执行环境；C 盘原件未修改。

平台适配优先于上游运行假设：egs/insight_reports.yaml 固定任务与普通文本 ReAct 协议；执行器复用平台真实数据服务，不运行上游 shell、自动安装、微信发布、PPT/视频或用户目录写入。示例数字不进入事实数据，未实现的 23 项指标、缺失资金和海外数据在报告中列为缺口。生成 HTML 不表示通过原上游的全多模态门禁。

所选任务实际读取 SKILL 及配置指定的参考，运行元数据保存资源摘要、数据来源和实际事件。完整技术参考保留供查阅，不将全部长文或其中示例当作本次行情。
