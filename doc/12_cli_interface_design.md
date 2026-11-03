# 统一命令行接口设计

2026-10-29补充：原统一HTTP客户端增加provider和research-skill命令。另有egs/skills.py本地研究入口，默认直接调用领域服务、不依赖网页，显式远程模式复用原客户端；包括预览、运行、查看、等待、事件、取消、文件与项目内Skill导出。前台进程生命周期如实标识，详见27号设计。

设计及实施日期：2026-10-20，Codex。状态：人工确认后的 A/B/C 完整范围已实现；源码入口、命令参考与验收证据分别见 egs/cli.py、docs/usage/cli_reference.md、docs/audit/cli_validation_2026-10-20.md。旧命令参考入口保留迁移链接。

## 1. 目标和现状

提供与网页共享业务规则的命令行入口，覆盖行情研究、ETF、策略、回测、模拟盘、投研复核、知识库、定时任务和系统管理。既支持人工逐条操作，也支持脚本获取结果和组合流程。

对当前 src/api/routes 源码进行 AST 盘点，共有 26 个业务路由模块、155 个 REST 操作。该数字是源码声明数，实际可用性仍以目标服务的 OpenAPI、运行环境和能力诊断为准；有路由不等于有真实数据、券商或模型能力。

现有 start.py 仅用于启动服务，src/strategy/cli_builder.py 是旧的策略生成模拟器，src/strategy/codex_cli.py 是真实 Codex 对话适配器。新平台 CLI 使用独立命名与模块，避免混淆三者。

## 2. 总体结构与入口

默认链路是命令解析、配置解析、请求验证、REST 客户端、已有 API、已有业务服务。查询和业务操作均连接已启动服务，不直接打开生产数据库，不导入 Gradio，也不启动额外调度器。

源码运行入口为 egs/cli.py 或 src.cli 模块，实现位于 src/cli。统一命令名称为 aiquant，作为可选安装别名；从当前项目源码运行无需安装本项目或修改 conda 包。原 start.py 保持兼容；system serve 包装同一前台启动流程，输出原启动日志。

首期不增加自动后台启动、按端口杀进程、远程关停接口或独立离线数据库执行模式。前台服务通过正常退出处理停止；已有真实能力缺失时给出明确诊断。

CLI 的默认后端地址与连接参数存入 egs/cli.yaml，提供 egs/cli.example.yaml 作为样例；密钥和环境变量保存在项目 .env 中。CLI 配置与后端 egs/config.yaml 分开，修改客户端地址不会改变服务器数据模式或数据库位置。

## 3. 命令组织和覆盖矩阵

命令结构统一为业务域、资源、动作、对象标识及参数。单一资源允许省略资源层，避免重复。list、show、create、update、delete、enable、disable、run、status 等动作保持一致；不为每个 API 临时发明命名。

| 命令组及主要动作 | 业务能力 | 当前后端来源 | 实施说明 |
| --- | --- | --- | --- |
| system health / info / capabilities / serve | 健康、版本、能力与前台启动 | system 路由、OpenAPI、start.py | 能力表区分可用、缺依赖、模拟及尚未提供 |
| market indices / sectors / heatmap | 指数、板块、热力数据 | market 路由 | 返回数据，终端不尝试绘制网页图形 |
| stock show；security search | 个股与证券代码/名称搜索 | stocks 路由、SecurityMasterService | 搜索需增加薄 API，默认不导入整个前端 |
| news list / keywords | 新闻与关键词 | news 路由 | 支持已实现的筛选，不承诺当前被忽略的筛选生效 |
| watchlist group 与 symbol | 自选分组、添加和移除标的 | watchlist 路由 | 批量添加仍使用后端校验 |
| pool list / create / items / add / import | 复用资源池和文件导入 | ResourcePoolService | 当前缺少资源池 REST，需补齐接口 |
| recommend run / show / result | 推荐任务与结果 | recommend_tasks 路由 | 保留实际同步/异步状态 |
| research reports / market-reports / papers | 研报、模型报告、论文检索收藏与入库 | reports、market_analysis_reports、papers 路由 | 命令名称区分论文与模拟交易 |
| etf universe list / show；etf snapshot | ETF 池及快照 | etfs 路由 | 明示真实源、模拟源与字段缺失 |
| factor definitions / monitor / qlib-status | 因子监控、明细与依赖诊断 | factors 路由 | 保留数值、日期与来源 |
| strategy list / show / create / update / enable / disable / delete | 策略库全生命周期 | strategies 路由 | 本地代码内容通过 API 上传，不传客户端路径给服务器读取 |
| strategy examples list / show / import | 预制策略预览和导入 | StrategyStore 示例方法 | 当前无示例 REST，需补三条薄路由 |
| strategy params show / profiles / resolve | 默认参数、方案和生效预览 | strategies 参数路由 | 复用 StrategyParameters，禁止另写继承逻辑 |
| backtest run / list / show / metrics / curve / trades / attribution / snapshot / compare / export | 回测创建、证据、比较和导出 | backtests 路由与已有结果 | 快照取任务详情；比较/导出只组织已有数据，不重新计算绩效 |
| paper create / list / show / reset / positions / orders / fills / equity | 模拟账户与状态 | paper_accounts 路由、PaperAccountService | 账户列表缺少 REST，需补齐；不混用实盘账户 ID |
| paper order / match / cancel | 模拟下单、撮合、撤单 | paper_accounts 路由 | 明确标注模拟模式，复用真实的模拟撮合规则 |
| live config 与 run / pause / resume / stop / status / orders / positions / validation | 实盘配置、状态与现有通道控制 | live 路由 | 默认提供查询、配置和验证；启动/恢复须显式开启对应上下文的交易操作 |
| qlib status / run / list / show | Qlib 原生 Workflow | qlib_workflows 路由 | 环境不足返回 blocked，不降级成另一套回测 |
| workflow modes / sops / snapshot / run / list / show | 量化闭环证据 | quant_workflows 路由 | 该 run 当前是收集证据并保存闭环记录，不保证自动完成整个策略研发链 |
| agent review / show | 普通或 ETF 多 Agent 复核 | research_team 路由 | 使用 backtest_review / etf_review，不开放委托工具 |
| model list / show / create / update / delete / test / default / chat | 模型配置与直接问答 | llm_models 路由 | chat 是普通模型问答，与 AI 工作台带工具会话区分 |
| ai session 与 ask / events | AI 工作台会话、附件和后台选择 | GenericAgentRuntime、CodexCliRunner 及现有页面会话逻辑 | 需先抽取与页面无关的服务并补 API；Trae/WorkBuddy 缺协议仍不可用 |
| kb category / document / note / search / ask / session / remote | 知识分类、文件、RAG、会话与远程源 | kb 路由 | 文件上传使用已有 multipart 接口，远程源引用保持可追踪 |
| job list / show / create / update / delete / enable / disable / trigger / history | 调度管理与执行历史 | jobs 路由 | 命令不创建第二个调度器；trigger 不是修改周期 |
| mcp list / create / update / delete / enable / disable / test / call | MCP 配置和工具调用 | mcp_servers 路由 | 工具结果如实返回，不能统一视作无副作用查询 |
| skill list / create / enable / disable / params / run | Skill 配置与执行 | skills 路由 | 保持现有 Skill 运行边界，不新增任意 shell 透传 |
| settings show / update；env list / check / import / delete | 系统设置和环境变量 | settings 路由 | 敏感值脱敏，不通过命令行参数明文设置密钥 |
| api operations / describe / call | 未提供快捷命令的扩展操作 | 当前服务 OpenAPI 和本地命令登记 | 按已登记的 operation、方法与路径调用，共用错误与操作确认策略 |

既有 /cli-sessions 只提供明确标记为模拟器的兼容读取与产物导入命令，默认不提供其模拟策略生成动作。券商事件注入和 mark-error 属于诊断能力，不作为普通交易命令；需要隔离诊断上下文，不能由通用调用静默绕过限制。

## 4. 全局参数与配置

| 参数 | 约定 |
| --- | --- |
| context、base-url、api-prefix、config | 连接上下文、服务地址、API 前缀和配置文件；连接上下文与策略 parameter-profile 独立命名 |
| format | auto、table、json、jsonl；交互终端 auto 默认表格，管道 auto 默认 JSON |
| output、overwrite | 将结果另存到明确文件；默认拒绝覆盖已有文件，显式开启后才覆盖 |
| page、page-size、all、max-items | 分页、自动遍历与总量上限；只有声明分页的端点接受，避免假分页 |
| connect-timeout、read-timeout、deadline | 连接、等待响应和整条命令时限分别配置；长任务使用独立配置 |
| market | 仅支持声明该字段的行情/研究命令；CN/US 需请求隔离，不能修改进程级网页市场选择 |
| file、params-file、set | 完整请求文件、仅策略参数文件、按字段覆盖；均支持 UTF-8 YAML/JSON |
| dry-run | 本地解析并展示脱敏后的请求方法、目标和请求体；不发送请求，也不宣称完成业务预检 |
| yes、confirm-id | 显式确认有删除、重置或资金风险的指定对象；不批量作用于未知对象 |
| require-real | 要求真实数据或真实模型；配置与结果为模拟时明确失败，不把模拟结果标成真实 |
| quiet、verbose、no-color | 只控制说明与日志，不能隐藏结果中的 blocked、failed、模拟或缺失字段 |

全局选项在业务子命令前后均可使用。连接配置优先级为命令行、环境变量、所选上下文、配置默认值。地址默认取 CLI YAML，后端无需启动也能查看帮助和验证请求文件。

请求体合并顺序为请求文件、params-file 写入的策略参数、set 字段覆盖、显式业务选项。未提供的参数不发送；零值、布尔假值、空列表和显式空值不与缺省混淆，不能使用真假判断丢弃有效值。

set 使用点分字段名，数值、布尔、数组和对象按严格 JSON 值解析，其余按字符串处理；拒绝 NaN/Infinity、未知字段和不允许覆盖的内部快照字段。嵌套对象递归合并，列表整体替换。params-file 只包含本次策略参数对象；带 entry/profiles 的方案文件通过 parameter-profile 选取，不当作运行参数直接展开。

字段校验依据明确的命令请求契约和后端规则；不能仅依赖现有 OpenAPI 中宽泛的字典请求体判断是否合法。只有本身支持扩展参数的对象允许自由键，例如策略 params 和 MCP arguments。严格验证日期与时区，接口日期仍使用原有日期口径，CLI 不把历史区间自动转换成“当前日期”。

file 为标准输入时只能有一个输入消费者，不能同时从标准输入读取问题正文、配置和确认。非交互管道中缺少必要确认直接失败，不挂起等待。二进制附件使用显式文件参数，不能按 YAML 文本解析。

已合成的 params 再交给后端统一处理：模型默认、源码默认、已保存默认、选中方案、本次 params 逐层合并。CLI 不提前把数据库默认复制进 params，否则会错误覆盖方案。

本期 egs/cli.example.yaml 的字段包括 default_context、contexts、base_url、api_prefix、timeouts、output、limits、allow_live_actions。新增环境变量统一使用 ALL_IN_ONE_CLI 前缀；模型服务密钥继续使用原有 api_key_env 约定，不与平台连接凭证混用。

## 5. 输出、日志和退出码

标准输出只包含业务结果，标准错误包含进度与日志。所有终端输出经专用 Loguru 输出通道，机器结果通道使用纯消息格式、无时间前缀、无颜色、无转义污染；帮助输出也适配同一终端输出边界，不使用 print。

JSON 保留后端 code、message、data，并增加 meta：CLI 版本、请求 ID、目标上下文、耗时、数据来源、结果类型和产物路径。字段名稳定，表格可使用中文标题；UTF-8 兼容 Windows/Linux，JSON 不使用转义中文。支持终端颜色自动关闭及完整 stdout/stderr 分流测试。

没有收到后端响应的本地错误使用 code=null，meta.error_origin 与 meta.error_type 标明参数、传输或客户端错误，并记录 exit_code；后端业务码原样保留，不把进程退出码冒充服务端业务码。调试堆栈仅进入标准错误，不能混入机器结果。

JSONL 每行一个事件，字段包括事件 ID、类型、运行 ID、时间、状态和数据。状态、工具动作、消息片段、错误与最终结果分开；同步 API 只产生开始与最终结果，不能伪造逐步进度。

| 退出码 | 含义 |
| --- | --- |
| 0 | 当前命令成功；研究报告中的 watch/reject 是研究结论，不自动等于接口失败 |
| 2 | 参数、文件格式或本地请求校验错误 |
| 3 | 服务连接失败、认证失败、无效响应或不受支持的协议 |
| 4 | 请求超时或连接中断；修改请求的完成结果可能未知 |
| 5 | 后端业务拒绝，或执行动作最终为 failed/error |
| 6 | 环境、依赖、数据或后台能力缺失，执行动作为 blocked/unavailable |
| 7 | 用户要求的结果条件未满足，如 require-real，或显式 fail-on-verdict 规则不满足 |
| 130 | 用户中断本地等待，不等于服务器任务已取消 |

当前错误处理器对业务错误和内部异常也返回 HTTP 200。CLI 必须同时检查 HTTP、业务 code 和运行状态。show 查询成功取得失败记录仍返回 0；run 创建动作得到 failed/blocked 必须非零退出。HTTP 4xx/5xx、返回 HTML 或缺少业务 envelope 均不能判作成功。

列表遍历保留分页信息，达到 max-items 时在 meta 中标明截断。CSV 导出只接受明确表格路径，嵌套对象使用 JSON，不隐式摊平丢字段；CSV 字符串需处理电子表格公式注入并在导出说明中标记。输出文件失败需非零退出，不能声称已导出。

自动遍历按资源 ID 去重；数据在翻页期间变化时不能称作一致性快照。多任务比较必须保留股票池、日期、执行成本和数据摘要差异，不把不同回测条件的收益排名直接当作参数优劣。

## 6. 长任务、流式与重试

内置回测、多 Agent 复核、Qlib 创建和模型问答目前主要同步执行，CLI 默认等待实际响应。首期不提供伪异步的 no-wait，也不在客户端偷偷启动子进程长期工作。已知任务 ID 的查询可以轮询；具体端点是否支持等待由能力描述决定。

POST/PUT/PATCH/DELETE、MCP 工具、Skill、下单、触发任务和模型生成不自动重试。GET 也只有明确登记为无外部动作的查询才有限重试，因为部分查询会拉行情或更新缓存。当前创建回测的任务记录在计算完成后才插入，不能在超时时假定已有可恢复任务 ID。

修改请求超时应返回 outcome=unknown、请求 ID、是否已知资源 ID和不自动重试提示。Ctrl+C 只停止 CLI 的网络等待；必须保留服务器可能继续执行的说明。没有幂等键与持久后台任务前，不承诺 exactly-once、自动续跑或可靠取消。

AI 流式新增服务端 SSE 接口，将现有 Codex 事件转换为统一 JSONL 事件；GenericAgentRuntime 首期只保证当前已有阶段和最终结果，逐 token 流式取决于后端实际支持。多 Agent 服务端 SSE 可消费 ResearchTeam.run_stream；普通同步 API 保留兼容。断流后先查询已持久化报告或会话，不重发用户消息；未保存的 token 不宣称可恢复。

## 7. 操作确认、文件与上下文

普通查询和一般配置写入无需额外确认。删除策略/文档/任务、账户重置、覆盖已有文件等动作显示精确对象；交互终端确认，非交互必须显式传 yes 和匹配对象标识。dry-run 可先查看请求，但不执行验证或下单。

实盘启动、恢复和风险参数放宽，须在启用交易动作的上下文中明确指定配置/运行标识，继续走后端通道诊断、运行前验证和风控。普通 yes 不能绕过这些检查。停止和暂停允许直接执行，避免给止险增加阻碍。CLI 不新增独立的实盘下单捷径。

通用 api call 与语义命令共用方法/路径对应的操作等级、确认、状态规则和禁用清单；未登记的写操作默认不可执行，不能通过拼路径绕过。客户端确认只能防误操作，不替代后端授权。当前平台尚无统一身份认证/角色系统，首期目标为可信本机服务；已有反向代理凭证可由环境提供，不承诺新增远程认证系统。

读取本地文件使用显式 file、code-file、message-file、attachment 等参数，客户端路径与服务器路径分开。策略源码读取后发送内容；知识文档使用 multipart；Qlib Workflow 的 server-workflow 和 provider-uri 指服务器路径，远程连接时不能假装客户端文件已上传。项目自带 CLI 写入与测试产物均限定项目内，不修改环境包。

密钥通过 .env 或环境引用，不进入命令历史、默认日志、请求预览或导出；错误响应中的敏感字段也脱敏。模型接口生成内容按 json_repair 解析；用户配置文件和后端协议响应严格解析，不用自动修复掩盖输入错误。

market 参数需在服务端请求范围内传递至 DataSourceManager，不能调用进程级 set_current_market 来切换网页。现有 US real 实际降级模拟源时保留原始来源标识，require-real 应拒绝。未完成请求隔离前，对不支持的市场选项明确报错，不静默忽略。

## 8. 需要补齐的 API 与职责归属

| 缺口 | 拟定接口 | 复用点及约束 |
| --- | --- | --- |
| 证券检索 | GET /securities/search | SecurityMasterService，支持显式 market |
| 示例策略 | GET /strategy-examples；GET /strategy-examples/detail；POST /strategy-examples/import | StrategyStore，示例相对路径作为参数并校验白名单目录 |
| 资源池 | GET/POST /resource-pools；GET /resource-pools/{id}/items；POST /resource-pools/{id}/symbols；POST /resource-pools/{id}/import | ResourcePoolService，导入明确 CSV/XLSX 文件，不将任意路径作为远程文件 |
| 模拟账户列表 | GET /paper-accounts | 现有页面直接查询账户；在 PaperAccountService 补列表方法后供 API 使用，统一 account_id 返回 |
| AI 工作台 | GET/POST /ai-workspace/sessions；GET /ai-workspace/sessions/{id}；POST /ai-workspace/sessions/{id}/messages；POST /ai-workspace/sessions/{id}/messages/stream；POST /ai-workspace/attachments | 抽取非 Gradio 会话服务，共用附件校验、GenericAgentRuntime 与 CodexCliRunner |
| 多 Agent 渐进事件 | POST /research-team/runs/stream | 同一 ResearchTeam，保存角色和报告，保留原同步创建 |
| 市场请求隔离 | 为支持市场选择的现有 API 添加 market 并贯穿业务服务 | 旧调用不传时兼容原行为，显式调用不得影响其他会话 |

首期不新增通用任务队列、可靠取消、broker 注入权限管理、全量备份恢复等额外平台。能力缺失直接报告，不能为了 CLI 验收临时制造假成功。ETF 策略本身的逻辑和数据约束不由 CLI 扩大或改写。

## 9. 模块与配置分类

| 目录/文件 | 拟定职责 |
| --- | --- |
| egs/cli.py | 源码运行薄入口 |
| src/cli/app.py、parser.py | 命令树、分发和帮助 |
| src/cli/client.py、config.py | REST 连接、上下文、超时、环境引用 |
| src/cli/input.py、output.py、errors.py | 请求合并、数据通道、状态与退出码 |
| src/cli/policy.py、catalog.py | 已登记操作、精确确认、禁用清单与契约加载 |
| egs/cli/commands 下的领域 YAML；src/cli/operations.py | 显式命令字段映射及分页、快照、比较组织 |
| src/cli/client.py、app.py | SSE 到 JSONL 的转换、终态、超时与中断处理 |
| egs/cli.example.yaml、egs/cli 下请求样例 | 配置默认值、字段映射、超时与样例；不存密钥 |
| src/api/routes 下新增薄路由与独立领域服务 | 补齐页面能力，不导入 FrontendService |
| tests/cli、tests/api、tests/agent | 解析/协议、隔离服务和模型事件验收 |
| docs/usage、docs/principles | 命令参考、图文流程、错误说明与协议原理；旧 cli/help 文件兼容 |

实现使用标准库 argparse、既有 requests、PyYAML 和 Loguru，未新增依赖。契约优先使用安全的 C YAML 加载器，无扩展环境回退安全 Python 加载器；仅构建当前命令分支，避免每次冷启动创建完整参数树。

## 10. 实施顺序和验收

| 阶段 | 交付 | 核心验收 |
| --- | --- | --- |
| A：基础与研究交易闭环 | 参数解析、配置、JSON、错误、ETF/策略/回测/模拟盘/Agent 复核等已有 API 命令 | 帮助在服务离线时可用；请求不导入 Gradio；HTTP 200 业务失败非零退出；真实与模拟明确 |
| B：其余主功能与 API 缺口 | 新闻/研报/论文/知识库/资源池/任务/模型/MCP/Skill/设置/受控实盘配置 | 既有 155 个操作按清单至少 90% 有可用调用映射；所有排除操作明确列明原因，不以帮助占位计入覆盖 |
| C：AI 会话与事件 | 后台选择、附件、会话留档、多 Agent 渐进状态、真实 Codex 事件 | 无接口时明确失败；只在真实返回时显示消息与动作，不模拟流式 |

三阶段属于本方案的完整实施范围。优先 A 后 B 再 C，每阶段通过后再扩展；自动参数搜索和策略再开发不属于本次 CLI 范围。

单元测试覆盖命令解析、选项位置、YAML/JSON/标准输入、嵌套覆盖、零值、分页、响应/状态映射、文件路径、脱敏与确认。集成测试以隔离服务执行策略导入、参数解析、回测创建、指标/交易/归因/快照、模拟账户和知识库 CRUD；核对数据库留档、结果数值、日志请求 ID 与错误退出码。

真实小样本验证使用实际行情驱动 ETF 和三类模型策略，检查日期、训练/预测、成交与费用，不能用模拟数据替代真实验收。Agent 协议 fixture 与真实 LLM 运行分别标注；Qlib 缺依赖时应验证非零 blocked，不能记为 Qlib 训练通过。实盘自动化测试使用模拟/干运行适配器。

性能比较同一数据和环境下直接 API 与 CLI 的中位/P95耗时，分开冷启动、请求和结果序列化；本机暖查询额外开销预算 200ms、CLI 冷启动预算 1s，网络与模型耗时另列。CLI 帮助/离线请求检查不触发行情、LLM、数据库或调度器。

完成后 review 并运行 Ruff、mypy、pytest、pip-audit、Bandit、Semgrep；缺工具与已知漏洞如实记录。检查 UTF-8、Windows/Linux 命令和路径，停止本轮服务，按用户确认清理精确测试目录；同步 README、帮助、设计、API 与当周日志，不修改 docs/task 开头文档。

## 11. 实施对照与能力边界

最终 REST 声明为 173 个操作，CLI 映射 168 个普通操作及两个真实 SSE 端点；排除旧策略生成模拟器、券商事件注入、人工标错三项，覆盖率约 98.3%。配置、普通查询和条件未满足的执行均可调用，执行失败以非零退出码表达，不以接口存在替代能力就绪。

页面与 API 共用 AIWorkspaceService；会话历史以数据库为准、同一会话避免并发发送、附件保存 UUID 标识并按现有规则验证。网页继续支持本地选择文件，API 只接受上传标识。请求市场通过 ContextVar 在请求结束后恢复，不改变网页的默认市场。

真实行情验收使用已归档 OHLCV 重放，经独立 CLI 进程和 HTTP 验证三类模型与两套 ETF 策略；不是本轮重新拉取行情。真实 Codex 对话另行实测，多 Agent 使用本地普通文本协议 fixture 验证工具和报告。Qlib 环境缺失按 blocked 验证，未宣称真实训练成功。
