# Agent统一CLI后端与原生Skill设计

2026-10-29，Codex。状态：已获人工确认，按完整范围实施；本文不含代码。目标是让既有Agent方案可选择API或CLI作为生成后端，同时能在CLI内直接使用相应Skill，保持同一研究逻辑和结果。实施时无法核验的严格研究资格按本设计阻断，不以普通会话冒充合格研究。

## 一、实际现状

| 调用链 | 当前实际生成后端 | 主要缺口 |
| --- | --- | --- |
| 工作台/悬浮对话 | 模型API、Codex、Qoder | 对话接通不等于其他Agent已支持 |
| 普通决策/组合终审 | API、Codex | 未统一接Qoder/Trae/CodeBuddy |
| 中文多空/双团队竞赛 | API、Codex | 后端白名单、角色冻结配置和API契约尚未扩展 |
| Skill市场/个股洞察 | API、Codex | 共享适配器只实现上述两类 |
| Alpha挖掘/主题/体制 | API | AgentSession直接调用LLMClient，ModelSelection强制API模型ID |
| 四角色回测/ETF复核 | API | research_protocol.run_role直接调用LLMClient |

核查位置：agent/workspace_backend.py、engine/insights/backend.py:validate_backend/generate_text、agent_strategies/session.py:Session.role、alpha_mining/agents.py:AgentSession.run、alpha_mining/contracts.py:ModelSelection、agent/research_protocol.py:run_role、agent/research_team.py:ResearchTeam.run_stream，以及API/前端/CLI字段约束。

现有src/skills/market_review与single_stock_analysis为洞察方法资料，不等于已经将全部Agent方案安装成CLI可发现、可执行的原生Skill。新Skill入口复用它们及现有服务，不重写这些研究方法。

## 二、计划支持的后端

首批统一为模型API加四类CLI，分别登记协议已实现、程序已安装、账户已认证、模型可用与严格角色模式可用，不用一个布尔值混淆。尚未安装或未认证时可以完成适配和本地验证，但不宣称真实回复已通过。

| 后端 | 实现目标及协议 | 当前本机证据 |
| --- | --- | --- |
| api | OpenAI兼容普通生成/SSE，继续支持平台模型ID | 已有配置体系，真实可用性按当次配置验证 |
| codex | 复用原生exec JSONL，增加研究角色调用模式 | PATH可找到Codex，参数帮助已核对 |
| qoder | 复用print/stream-json与认证检查，补研究角色模式 | 项目.env指向E盘1.1.80；最近归档为未登录，不当作实时登录状态 |
| trae | 区分现有旧版print/stream-json与官方2.0 exec/JSONL，禁止混用参数 | E:/trae-cli/bin/traecli.exe，实际0.120.42；其帮助没有2.0 exec子命令，不自动升级 |
| codebuddy | 腾讯CodeBuddy Code的非交互消息协议；WorkBuddy内置引擎须显式配置实际入口并核对兼容性 | PATH未发现codebuddy，不把WorkBuddy候选标签当成已接通 |

Claude Code、Gemini CLI和其他工具保留扩展契约，首批不额外安装或承诺这些适配。WorkBuddy桌面应用不与CodeBuddy的程序路径、账户目录自动互换；只有经核验的内置CLI入口才可作为相应后端，旧模拟策略产物不属于真实后端。

CLI作为本地生成通道，不要求把它额外启动成HTTP模型服务器；平台API仍使用OpenAI兼容接口。各CLI自身的私有网络协议不改写为平台function calling。

## 三、统一生成接口

新增独立生成后端服务，输入覆盖后端/模型ID或名称、推理强度、系统提示与历史、冻结证据、角色、超时/取消和调用预算。输出统一为实际正文、实际后端/模型身份、公开事件、返回用量、时延、终态和失败原因。各Agent保留自身的ReAct编排、json_repair、统计/原文/证券校验和结果契约。

全局默认后端可被工作流及角色配置覆盖；同一流程可混合API与CLI。API使用model_id，CLI使用实际model_name，不能把平台ID或mock配置冒充CLI模型。体制八配置仍要求真正可区分的配置，不能换八个角色名称就当独立模型实验。

身份冻结包括后端、程序版本、有效模型/强度与研究模式、相关配置/提示词摘要；更换后端不能默默复用旧成绩、决定或缓存。保持旧只含model_id的请求默认为API，已有构造器注入的测试LLM兼容。

所有调用尝试和可得用量保留，缺失用量为未知；元数据检查与实际生成分开。默认不跨供应商静默回退，不在认证失败后反复重试，也不通过自动选择高权限档位解决错误。共享预算仍跨日期、角色、子策略生效，native事件不能用假日志填补。

## 四、区分模型提供者与Skill宿主

两种方向分别实现，避免递归和重复编排：平台调用CLI提供角色正文；用户在CLI中启用Skill后，由Skill调用平台的本地研究执行器。CLI模型提供模式不再加载并运行相同业务Skill，研究步骤由平台负责。

研究角色模式按实际CLI版本关闭原生Shell、写文件、额外MCP、插件和隐式Skills，使用受控工作目录及只含本轮冻结资料的上下文，不恢复个人历史会话。只读沙箱不等于禁用原生工具，也不证明模型只看到了PIT资料；实施时必须核验实际支持的工具开关，不能照抄不存在或已过时的参数。

无法证明支持必要约束时，严格角色模式在调用前明确不可用；普通工作台对话可保持原能力，不静默把当前CLI交互结果晋级历史合格研究。出现原生越权工具或未知事件时保留证据并拒绝结果，不能当成正常ReAct观察。CLI内生训练记忆风险仍按原研究纪律标识。

执行器设置调用深度和关联运行标识；Skill宿主只启动一次受控执行，模型提供者不得反向再启动同类Skill或执行器。外层CLI宿主的消耗与平台内部调用分开说明，不能把缺少外层账单当作零成本。

## 五、十个原生Skill入口

以研究家族为单位，不为每个细小预置复制一整份提示词：

| 项目Skill名称 | 对应已有流程 |
| --- | --- |
| quant-market-review | 市场复盘，复用原market_review方法与报告服务 |
| quant-stock-analysis | 单股分析，复用single_stock_analysis |
| quant-backtest-review | 四角色回测复核 |
| quant-etf-review | ETF专用多Agent复核 |
| quant-strategy-composition | 规则/模型/Agent级联、并行及Portfolio/Risk工作流 |
| quant-alpha-mining | Idea/Implementer/Evaluator及统一研究门槛 |
| quant-theme-refine | 原文主题/公司关联精炼 |
| quant-regime-research | 四体制与最多八配置、冻结资产权重 |
| quant-cn-debate | 中文多空综合/质量/事件三预置 |
| quant-contest-trade | 信息/研究双团队事件、质量、行业三预置 |

规范源码放src/skills下，每个Skill包含简短SKILL.md及确有需要的脚本/引用。名称和description说明实际触发场景，自动发现默认开启；按需阅读当前模式资料，不一次载入全部预置。脚本只启动现有研究流程、查询进度和打开产物，不自建另一套回测或让LLM补造指标。

现有两份洞察资料保留，不擅自重命名或改动其来源文件。新原生入口使用quant命名空间避免冲突；参数、预算、提示词和方案映射在egs的统一YAML维护。使用skill-creator的结构与验证方法，但是否执行任务仍以用户已有指令和权限为准，不额外添加每次都要批准的流程。

## 六、CLI直接使用与项目级分发

提供一个egs主入口，调用src中的本地工作流执行器。默认本地执行，不要求人工先启动网页或FastAPI服务；需要复用已有远程平台时再显式选择API客户端模式。输入可以来自YAML、已有数据集/运行ID或支持的文件导入，缺少关键资料时明确列出，不自行合成成功样本。

主入口覆盖方案目录、能力/环境检查、解析预览、运行、查看/等待/事件、取消与文件。先保存运行ID和实际配置，返回JSON及HTML产物；长任务离开终端/进程中断的语义必须如实标识，不假称本地后台永远存活。已有egs/cli.py命令继续兼容，不把已授权研究改成另一套API。

原生Skill为薄入口，使用同一执行器。Codex可在CLI提及Skill名称，Qoder用其原生Skill菜单/命令；其他宿主按实际版本核验发现方式。直接通过项目命令行执行并不依赖宿主是否支持Skill菜单。

生成/导出时从同一源码复制到项目内的各宿主目录，保存来源摘要：Codex使用.agents/skills，Qoder使用.qoder/skills，CodeBuddy使用.codebuddy/skills；TRAE项目Skill路径必须结合本机旧版和2.0分别核查，不能仅根据IDE文档断言CLI兼容。不能自动发现时提供显式加载方式并标清能力。

所有Skill分发默认限定本项目，不写个人全局Skills、不迁移账户、不修改Conda包。Windows采用可追踪复制，不依赖管理员符号链接。已存在且不属于本项目的同名内容不覆盖；更新前核对生成清单，未获确认不删除旧文件。本机程序已有则复用，不自动升级Trae或安装其他CLI。

## 七、修改与验收范围

第一阶段落统一后端/能力检测和四类CLI适配，接入洞察、决策、Agent策略、Alpha三模式与ResearchTeam/ETF；同步API类型、角色配置、Gradio选择器、CLI字段及冻结/回放检查。新公共逻辑拆小模块，避免继续扩大现有LLM和frontend大文件。

第二阶段落本地执行器、十个Skill入口、项目内导出/发现、可执行例子和使用图。两阶段同属首批完整交付，不只添加下拉选项或SKILL文本就结束。

先做不收费的进程协议/事件/工具禁用/元数据/预算/取消/认证失败测试，再做各工作流的小数据闭环、旧API请求兼容、同一输入的Web/本地/Skill运行一致性、实际费用账本/研究门禁与HTML引用。注入未来资料、原生工具事件或递归启动时应拒绝，不以更宽权限重跑。

Skill执行官方格式验证，并用真实用户式指令检验触发、缺参数、日志、产物和失败说明；包装脚本必须实际运行。真实服务先确认现有安装/认证/模型能力，再用极少候选和短流程验证，不做调参或为了覆盖每个Skill重复付费；不可用项如实列明，不能拿夹具冒充真实CLI或收益。

完成代码review、单元/集成、浏览器与mypy/Ruff/pytest/pip-audit/Semgrep/Bandit、MkDocs、UTF-8/密钥检查。同步03/04/05及12/13/14/23/24/25相关设计与README、使用/原理、例子、changelog；必要时才改依赖固定版本。停止测试服务，正式证据保留，临时文件删除另行确认。

## 八、官方依据

- [Codex Skill结构与项目目录](https://learn.chatgpt.com/docs/build-skills)；[项目自定义](https://learn.chatgpt.com/docs/customization/overview)。
- [Codex非交互命令](https://learn.chatgpt.com/docs/cli/reference)。
- [Qoder CLI Skills](https://docs.qoder.com/cli/Skills)，注意官方路径大小写；[脚本调用](https://docs.qoder.com/cli/run-in-scripts)。
- [TRAE CLI命令参数](https://docs.trae.cn/cli_command-line-parameters?lang=zh)；[1.0至2.0差异](https://docs.trae.cn/cli_get-started-with-trae-cli)；[CLI扩展入口](https://docs.trae.cn/cli_tools-and-extensions?lang=zh)。
- [CodeBuddy非交互调用](https://www.codebuddy.cn/docs/cli/headless)；[项目Skills](https://www.codebuddy.cn/docs/cli/skills)。

仅参考公开协议及自有现有代码，不复制第三方实现或提示词；不把原生CLI的工具接口改称平台function calling。
