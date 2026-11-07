# AIQuant智投 一体化量化交易平台 - API 接口设计文档

2026-11-02补充：命名知识库、文件分块检索、会话附件隔离、递归关键词与左侧引用阅读见[31号设计](31_named_knowledge_library_design.md)。

本轮知识库新增契约（优先于旧FTS描述）：

| 接口 | 输入与行为 |
| --- | --- |
| GET /api/v1/kb/libraries | 返回可选库名，含默认库和已创建空库 |
| POST /api/v1/kb/libraries | name为库名，按库创建独立文件目录 |
| POST /api/v1/kb/urls | url、library_name、chunk_chars及可选title；有界下载并走统一解析 |
| POST /api/v1/kb/documents | multipart新增library_name、chunk_chars；attachment_session限制为对应会话附件 |
| GET /api/v1/kb/documents、GET /api/v1/kb/search | library_name限定库，缺省默认库；公共列表与搜索排除会话附件 |
| POST /api/v1/kb/qa | 新增library_name、retrieval_rounds；返回retrieval_trace、retrieval_status和引用库名、分块标题、命中行 |
| POST /api/v1/reports/import | report_id、library_name及可选chunk_chars；下载研报原文入库 |
| POST /api/v1/papers/import | download_fulltext为真时下载原文，并接受library_name、chunk_chars；旧摘要保存契约保留 |
| POST /api/v1/kb/remote-sources/{source_id}/pull、sync | 新增library_name、chunk_chars，来源与库共同隔离 |

问答按普通模型生成规划关键词，再调用zvec-grep词法检索；不创建向量索引。规划失败明确返回planner_unavailable，回答生成失败保留可用引用并返回model_unavailable。

2026-10-30增量：全局访问控制覆盖REST、WebSocket、Gradio和静态挂载，默认回环local；token模式使用Bearer或签名HttpOnly会话，远程要求TLS、明确Host和同源。新增GET/POST /access/login、POST /access/logout，公开/_health仅回最小存活状态。访问边界使用HTTP401/403/413/429；业务错误继续兼容原信封，未知异常不回显内部消息，request_id校验后关联日志。校验错误只返回位置/类型/说明，不回显敏感输入。

策略新增POST /api/v1/strategies/{strategy_id}/source-review，字段为source_sha256和reviewer；详情返回当前摘要，创建/详情不执行源码。未复核自定义源码拒绝运行，源码变更后复核失效；已结束回测任务不能再次覆盖执行。环境导入有全量预校验与体积限制，模型/MCP公开表示递归脱敏。模型/知识共享操作下沉领域服务；SSE改用独立有界线程通道，保留事件/业务信封。详见28号设计与docs/usage/access_and_execution.md。

2026-10-29补充：新增agent-providers能力目录和research-skills的目录、预览、运行、详情、事件、取消及产物接口；模型选择扩展到API/Codex/Qoder/TRAE/CodeBuddy，旧model_id请求默认API。ResearchTeam增加默认provider与角色覆盖。写操作同站点校验，远程导入继续走原有数据接口。

2026-10-27新增`/alpha`领域（仍在配置的API总前缀下）：config、datasets列表/登记/upload/snapshot/attest、templates及template-info；studies列表/创建/读取、candidates、seal、actions/cancel、events/stream/run-stream、reviews/export、artifacts、artifact-text及files。CLI显式映射相同流程，二进制下载由列表的download_url提供。新写入检查同站点Origin；研究动作有阶段/预算/摘要约束，审批和导出不能覆盖硬失败。模板/查看/刷新不会调用模型，执行才计费；完整契约与边界见23号设计。

2026-10-26入口兼容：原研报页面根地址重定向到知识与资料对应子页，旧配置/API访问仍保留；其他业务REST契约和任务ID不变。页面统一任务/报告/归因只复用服务，不因跳转重复提交。环境预检单独读取解释器、声明与包来源，不启动服务或修改依赖。见[20号设计](20_dependency_navigation_consolidation_design.md)。

2026-10-25成本契约：普通回测与组合运行接收可选对象execution_costs，包含方案、分方向费率、最低佣金、滑点、结算、量能及校验模式；API费率使用内部小数，页面百分数在提交前换算。字段白名单、类型及范围统一校验。普通任务在parameter_snapshot.run.execution_costs保存不可变配置；组合另存execution_cost_snapshot且不改写策略版本，结果含实际费用分类及execution_orders。旧任务不回算，Qlib与前向模拟显式通用费用覆盖拒绝。CLI backtest/pipeline同步支持。见[19号设计](19_backtest_execution_costs_design.md)。

2026-10-25补充：回测创建缺省引擎按实际策略能力解析，显式引擎不兼容提前拒绝；同步API/CLI与网页后台任务共用持久化Runner，运行失败返回task_id并保留failed/timeout/cancelled记录，组合使用冻结执行参数。新增同源缓存资源GET `/ui/runtime.js`，按服务主题返回共享前端初始化脚本，不返回模型凭据。RAG返回status以区分no_hits/model_unavailable，引用保留编号、范围与上下文片段摘要。见[18号设计](18_workspace_navigation_backtest_learning_design.md)。

2026-10-25通用监控与资源校验：现有GET factors/monitor保留兼容，增加范围、资源/账户ID、后端、观察日、历史版本和强制刷新参数；POST factors/jobs启动后台任务，GET factors/jobs/{job_id}返回实际阶段与结果；GET factors/universes列出范围，POST factors/universes/memberships登记历史清单。资源池提供模板下载、import/preview、import/errors及带预览摘要的import提交；CLI复用相同服务。GET ui/chart-explanations提供可缓存解释目录。Qlib状态为独立工作进程真实诊断，与原生模型Workflow分别验证。详见[17号设计](17_monitor_graph_resource_design.md)。

2026-10-24 因子研究扩展：复用现有组件、模板、方案预览/发布、运行、节点证据与CLI接口，未增加平行执行入口。新增四种因子组件；编译冻结定义与预处理，结果增加 factor_diagnostics，模型拟合证据增加特征集及名称。面板型连接禁止直接进入资金分配，全部调用方共用时点、统计和缓存规则，详见16号设计。

## 1. 总体约定

### 1.1 接口总体形态

- 后端基于 FastAPI，REST 接口统一前缀 /api/v1；实时推送统一走 WebSocket 端点 /ws。
- 接口按功能模块分组（市场分析、策略构建、策略仿真、实盘、知识库、定时任务、模型配置、AI量化闭环），另设通用系统接口。
- 路径风格：资源用复数名词（news、strategies、backtests、paper-accounts、live-runs），多单词资源用连字符（live-runs）；状态变更类动作用 POST 子路径表达（如 /api/v1/live-runs/{run_id}/stop）；查询类子资源用 GET（如 /api/v1/backtests/{task_id}/equity-curve）。
- HTTP 方法语义：GET 查询、POST 创建与动作触发、PUT 全量更新、PATCH 局部更新、DELETE 删除。
- 异步长任务（推荐任务、市场分析报告生成、回测任务、CLI 构建会话）统一采用"创建任务返回任务 ID → 轮询状态接口 + WebSocket 主题推送进度 → 完成后拉取结果接口"的模式。

### 1.2 统一响应结构

所有 REST 接口（除健康检查可精简外）返回统一信封结构，由 code、message、data 三个字段组成：

| 字段 | 类型 | 说明 |
|------|------|------|
| code | 整数 | 业务状态码。0 表示成功；非 0 表示失败，具体含义见第 4 章错误码规范 |
| message | 字符串 | 状态描述。成功时可为空或返回通用描述；失败时返回人类可读的错误说明（中文），可直接用于前端提示 |
| data | 对象或数组或 null | 业务数据载荷。失败时为 null；分页场景为分页结构（见 1.4）；空数据集返回空数组而非 null，便于前端统一处理 |

约定要点：

- 业务成功与否优先以 code 判断；HTTP 状态码仅表达传输层与请求本身的合法性（见 1.3），前端不得仅凭 HTTP 200 判定成功。
- 接口内部抛出的业务异常（资源不存在、参数非法、外部数据源失败等）由全局异常处理器转换为统一信封结构，保证任意接口的失败响应形态一致。

### 1.3 HTTP 状态码使用约定

| 状态码 | 使用场景 | 说明 |
|--------|----------|------|
| 200 | 成功 | 绝大多数成功请求，含创建异步任务成功（任务体在 data 中返回） |
| 400 | 请求不合法 | 请求体格式错误、必填参数缺失、参数取值非法；业务语义上的参数错误返回信封 code=1xxx，HTTP 仍为 200，仅当请求本身无法解析时使用 400 |
| 401 | 未认证 | 预留。首期本机部署不启用鉴权，后续启用 token 后返回 |
| 404 | 路径不存在 | 请求了未定义的路由；路径已定义但资源 ID 不存在时 HTTP 返回 200、信封 code=1004 |
| 409 | 状态冲突 | 对处于不可操作状态的对象执行动作（如对已停止的实盘再次 stop）时，HTTP 200、信封 code=3001/4001 等业务码 |
| 500 | 服务器内部错误 | 未捕获异常；业务侧对应信封 code=5xxx，HTTP 仍为 200 |

简化原则：除路由不存在与请求体不可解析外，业务错误一律以 HTTP 200 + 非 0 code 返回，前端仅需要一套 code 处理逻辑。

### 1.4 分页参数约定

列表类接口统一使用以下分页参数与响应结构：

| 项 | 名称 | 类型与默认 | 说明 |
|----|------|-----------|------|
| 请求参数 | page | 整数，默认 1 | 页码，从 1 开始 |
| 请求参数 | page_size | 整数，默认 20，上限 100 | 每页条数 |
| 响应字段（data 下） | items | 数组 | 当前页数据列表，空页返回空数组 |
| 响应字段（data 下） | page | 整数 | 当前页码，回显请求值 |
| 响应字段（data 下） | page_size | 整数 | 每页条数，回显实际生效值 |
| 响应字段（data 下） | total | 整数 | 符合过滤条件的总条数 |

补充约定：不使用 offset/limit 风格；数据量确定较小的字典类接口（分类树、主题列表等）不分页，直接返回完整数组。

### 1.5 ID 参数风格

- 路径中的资源 ID 一律使用小写 snake_case 占位符，如 {strategy_id}、{task_id}、{session_id}、{account_id}、{run_id}、{doc_id}、{job_id}。
- 内部主键为不透明的字符串或整数 ID（雪花/自增），前端只做透传，不做任何解析；请求体与响应体中的外键字段统一为"资源名单数 + _id"形式（如 strategy_id、account_id、model_id）。
- 证券标的代码使用字符串类型的交易所标准代码（如 600519、000001、300750），市场前缀遵循数据层统一映射。

### 1.6 时间格式

- 所有接口输入输出的时间字段统一使用 ISO 8601 格式的 UTC 时间字符串，形如 2026-08-15T02:30:00Z（日期为 2026-08-15 形式、时间 HH:mm:ss、以 Z 结尾表示 UTC）。
- 仅表示日期的字段（如回测区间的起止日）使用 2026-08-15 形式。
- 交易相关的本地时区语义（A 股交易时段）由后端负责转换，前端不做时区换算。
- WebSocket 推送消息中的 ts 字段为 ISO 8601 UTC 时间字符串，与 REST 保持一致。

### 1.7 鉴权预留说明

- 首期定位为本机单用户部署，所有接口不做鉴权，任何请求直接放行。
- 鉴权能力在协议层预留：请求头 Authorization: Bearer {token} 为后续启用的标准认证头，服务端当前忽略该头，启用后校验失败统一返回 401。
- WebSocket 连接预留 token 查询参数，语义与请求头一致，首期同样忽略。
- 启用鉴权不影响本文档所列接口的路径与请求/响应结构。

---

## 2. REST 接口清单

### 2.1 市场分析模块（28 个接口）

#### 2.1.1 新闻与舆情

| 方法 | 路径 | 用途 | 关键请求参数/请求体要点 | 响应 data 要点 |
|------|------|------|--------------------------|----------------|
| GET | /api/v1/news | 新闻列表 | category：分类（domestic 国内/international 国外/finance 财经/company 公司）；keyword：标题与摘要关键词模糊匹配；source：来源过滤；start_time、end_time：ISO 8601 时间区间；page、page_size 分页 | 分页结构；items 含新闻 ID、标题、摘要、分类、来源、来源链接、发布时间、情感倾向（positive/negative/neutral）、涉及标的列表 |
| GET | /api/v1/news/keyword-cloud | 新闻关键词云 | scope：统计范围（day/week/month，默认 day）；category：可选分类过滤；top_n：返回词数上限（默认 50） | 词数组，每项含关键词、词频、权重、关联涨跌情绪（可选） |

#### 2.1.2 行情看盘

| 方法 | 路径 | 用途 | 关键请求参数/请求体要点 | 响应 data 要点 |
|------|------|------|--------------------------|----------------|
| GET | /api/v1/market/indices | 大盘指数行情 | 无必填参数；refresh：是否强制绕过缓存刷新（默认 false） | 指数数组，每项含指数代码、名称、最新价、涨跌点、涨跌幅、成交量、成交额、数据源、更新时间 |
| GET | /api/v1/market/sectors | 板块行情 | board：板块类型（industry 行业/concept 概念，默认 industry）；sort：排序字段（涨跌幅/成交额）；limit：返回条数上限 | 板块数组，每项含板块代码、名称、涨跌幅、领涨股、总成交额、上涨/下跌家数 |
| GET | /api/v1/market/heatmap | 热力图数据 | level：聚合层级（industry 板块/stock 个股，默认 industry）；board：可选指定板块树节点；threshold：最低成交额过滤阈值 | 树形/扁平节点数组，含节点名称、代码、市值或成交额权重、涨跌幅、子节点列表 |

#### 2.1.3 因子监控

| 方法 | 路径 | 用途 | 关键请求参数/请求体要点 | 响应 data 要点 |
|------|------|------|--------------------------|----------------|
| GET | /api/v1/factors/definitions | 因子定义列表 | 无 | 启用的因子定义、方向、前瞻窗口和阈值 |
| GET | /api/v1/factors/monitor | 因子监控快照 | universe：逗号分隔股票池，留空时使用自选池或配置默认股票池 | KPI、有效性指标、RankIC 历史、分位收益、分层收益时序、前瞻周期 IC 衰减、稳定性与容量代理指标、风格代理暴露、相关性矩阵、截面快照、告警和 qlib 状态 |
| GET | /api/v1/factors/qlib-status | Qlib 状态 | 无 | qlib 是否可用、版本、授权和下一步配置建议 |

#### 2.1.4 Qlib实验

| 方法 | 路径 | 用途 | 关键请求参数/请求体要点 | 响应 data 要点 |
|------|------|------|--------------------------|----------------|
| GET | /api/v1/qlib-workflows/status | Qlib 配置与环境状态 | 无 | 当前配置文件、provider_uri、workflow_path、实验参数、pyqlib 诊断和最新运行记录 |
| POST | /api/v1/qlib-workflows/runs | 创建 Qlib 运行记录并尝试执行 | 请求体：run_type、workflow_path、provider_uri、params、timeout_seconds；pyqlib/provider/workflow/qrun 均就绪时调用 Qlib 原生 workflow，params 可传 artifact_dir/output_dir/result_dir 等产物路径 | 运行详情，含 run_id、running/finished/failed/blocked 状态、参数、诊断指标、返回码、输出尾部、训练指标、组合回测指标、产物数量和阻塞/失败原因 |
| GET | /api/v1/qlib-workflows/runs | Qlib 运行列表 | run_type、page、page_size | 分页结构；items 含运行类型、状态、实验名、市场、workflow、provider_uri、创建时间、训练指标摘要、组合指标摘要和产物数量 |
| GET | /api/v1/qlib-workflows/runs/{run_id} | Qlib 运行详情 | 路径参数运行 ID | 单条运行记录，解析 params、metrics、artifacts、training_metrics、portfolio_metrics 和 artifact_count |

#### 2.1.5 自选管理

| 方法 | 路径 | 用途 | 关键请求参数/请求体要点 | 响应 data 要点 |
|------|------|------|--------------------------|----------------|
| GET | /api/v1/watchlist/groups | 自选分组列表 | 无参数 | 分组数组，含分组 ID、名称、排序号、标的数量、创建时间 |
| POST | /api/v1/watchlist/groups | 新建自选分组 | 请求体：name（必填）、sort_order（可选） | 新建分组对象（含分组 ID） |
| PUT | /api/v1/watchlist/groups/{group_id} | 修改自选分组 | 请求体：name、sort_order（至少一项） | 更新后的分组对象 |
| DELETE | /api/v1/watchlist/groups/{group_id} | 删除自选分组 | 路径参数分组 ID；query 参数 force：分组下有标的时是否级联删除标的（默认 false，非空且未 force 时返回 code=1005） | data 为 null |
| GET | /api/v1/watchlist/quotes | 自选行情 | group_id：可选分组过滤，缺省返回全部分组标的 | 按分组组织的行情数组，每项含标的代码、名称、最新价、涨跌幅、成交量、换手率、分组归属 |
| POST | /api/v1/watchlist/groups/{group_id}/symbols | 向分组添加标的 | 请求体：symbols（标的代码数组，必填） | 更新后的分组成员摘要（标的数量、新增列表） |
| DELETE | /api/v1/watchlist/groups/{group_id}/symbols/{symbol} | 从分组移除标的 | 路径参数分组 ID 与标的代码 | data 为 null |

#### 2.1.6 关联关系与个股

| 方法 | 路径 | 用途 | 关键请求参数/请求体要点 | 响应 data 要点 |
|------|------|------|--------------------------|----------------|
| GET | /api/v1/relations/graph | 关联关系图数据 | symbol：中心标的代码；relation_types：关系类型多选（industry 同行业/concept 概念/supply_chain 产业链/shareholder 股东/news_cooccurrence 新闻共现/correlation 收益相关，缺省全部）；depth：展开深度（1-2，默认 1） | 图数据结构：nodes（节点 ID、名称、类型、涨跌幅、连接度、节点大小）、edges（源节点、目标节点、关系类型、关系描述、权重） |
| GET | /api/v1/stocks/{symbol}/detail | 个股详情聚合 | 路径参数为标的代码；sections：需要的分区多选（quote 行情/kline K 线/finance 财务/news 新闻/score 评分/report 研报，缺省全部）；kline_period、kline_count 控制 K 线分区 | 聚合对象，按请求分区返回：实时行情快照、K 线序列、财务摘要指标、近期相关新闻列表、综合评分与分项评分、近期研报摘要列表 |

#### 2.1.7 股票推荐（双层过滤）

推荐任务创建支持**双路径参数**：请求体 path 字段二选一——quick（快速路径：形态识别 + 小模型快速过滤，成本低、分钟级返回）与 deep（深度路径：在快速过滤基础上叠加 LLM 深度推荐精选，成本高、异步等待）。

| 方法 | 路径 | 用途 | 关键请求参数/请求体要点 | 响应 data 要点 |
|------|------|------|--------------------------|----------------|
| POST | /api/v1/recommend-tasks | 创建推荐任务 | 请求体：path（quick/deep，必填）；universe：标的池（all 全市场/group:{group_id} 指定自选分组/symbols 显式代码数组）；filters：过滤条件对象（最小成交额、最小换手率、剔除 ST 等，可选）；count：期望推荐数量（默认 10） | 任务对象：task_id、path、状态（pending）、创建时间；同时向 notify 主题推送任务创建事件 |
| GET | /api/v1/recommend-tasks/{task_id} | 查询任务状态 | 路径参数任务 ID | 任务对象：task_id、path、状态（pending/running/finished/failed）、进度百分比、当前阶段描述、耗时 |
| GET | /api/v1/recommend-tasks/{task_id}/result | 获取推荐结果 | 路径参数任务 ID；仅状态为 finished 时返回完整结果，否则返回 code=3002 | 推荐列表，每项含标的代码、名称、推荐理由（quick 为规则与形态摘要，deep 为 LLM 生成的深度分析）、评分、关键指标快照（估值/动量/资金面）、入选时间 |

#### 2.1.8 研报与模型分析报告

| 方法 | 路径 | 用途 | 关键请求参数/请求体要点 | 响应 data 要点 |
|------|------|------|--------------------------|----------------|
| GET | /api/v1/reports | 研报列表 | keyword：标题关键词；symbol：关联标的；org：发布机构；start_date、end_date；page、page_size 分页 | 分页结构；items 含研报 ID、标题、发布机构、分析师、发布日期、评级、关联标的、页数 |
| GET | /api/v1/reports/{report_id} | 研报详情 | 路径参数研报 ID；include_body：是否返回正文文本（默认 true） | 研报对象：元信息字段、正文分段文本或分页文本、图表说明列表；PDF 原文通过返回的文件路径由静态资源下载 |
| POST | /api/v1/market-analysis-reports | 生成模型市场分析报告（异步任务） | 请求体：report_type（daily 每日盘后/weekly 周度/topic 专题，默认 daily）；topic：专题主题（report_type=topic 时必填）；depth：分析深度（standard/deep）；use_llm：是否调用 LLM 增强（默认 true） | 任务对象：task_id、报告类型、状态、创建时间 |
| GET | /api/v1/market-analysis-reports | 报告列表 | report_type：类型过滤；status：状态过滤；page、page_size 分页 | 分页结构；items 含报告 ID、类型、标题、主题、状态、生成耗时、创建时间 |
| GET | /api/v1/market-analysis-reports/{report_id} | 报告详情 | 路径参数报告 ID | 报告对象：标题、类型、生成时间、市场综述（LLM 生成）、板块热点列表、关键事件摘要、风险提示、引用的数据来源清单 |

#### 2.1.9 论文

| 方法 | 路径 | 用途 | 关键请求参数/请求体要点 | 响应 data 要点 |
|------|------|------|--------------------------|----------------|
| GET | /api/v1/papers/search | 论文搜索 | keyword：检索词（必填）；source：论文数据源（可选，缺省全部启用源）；year_from、year_to：年份区间；sort：排序（relevance 相关度/date 发布时间）；page、page_size 分页 | 分页结构；items 含论文 ID、标题、作者、摘要、发布日期、来源、原文链接、是否已收藏 |
| POST | /api/v1/papers/favorites | 收藏论文 | 请求体：paper_id（必填）；note：收藏备注（可选）；本地留存摘要字段随论文元信息自动带入 | 收藏记录对象（含收藏 ID、收藏时间） |
| DELETE | /api/v1/papers/favorites/{paper_id} | 取消收藏 | 路径参数论文 ID | data 为 null |
| POST | /api/v1/papers/import | 导入论文到知识库 | 请求体：paper_id（必填）；category_id：知识库分类（可选）；tags：标签数组或逗号分隔字符串（可选） | 知识文档对象；含 doc_id、paper_id、file_path、doc_type=论文、imported 是否新建、chunk_count 分块数 |

### 2.2 策略构建模块（12 个接口）

| 方法 | 路径 | 用途 | 关键请求参数/请求体要点 | 响应 data 要点 |
|------|------|------|--------------------------|----------------|
| GET | /api/v1/strategies | 策略列表 | keyword：名称/描述关键词；status：状态过滤（enabled/disabled）；tag：标签过滤；page、page_size 分页 | 分页结构；items 含策略 ID、名称、描述、版本号、状态、标签、创建/更新时间、最近回测绩效摘要（年化/最大回撤，若有） |
| GET | /api/v1/strategies/{strategy_id} | 策略详情 | 路径参数策略 ID；include_code：是否返回策略代码全文（默认 true） | 策略对象：元信息、默认参数值、依赖数据说明、代码全文、文件路径、版本历史摘要 |
| POST | /api/v1/strategies | 上传/新建策略 | 请求体：name（必填）、description、code（策略代码全文）或 file_path（文件存储路径，二选一）、default_params（默认参数对象）；后端校验统一策略接口合规性，不合规返回 code=3003 | 新建策略对象（含策略 ID、版本号 1） |
| PUT | /api/v1/strategies/{strategy_id} | 更新策略元信息或代码 | 请求体：name、description、default_params、code（至少一项）；更新代码时版本号自增 | 更新后的策略对象（含新版本号） |
| DELETE | /api/v1/strategies/{strategy_id} | 删除策略 | 路径参数策略 ID；策略被回测任务或实盘配置引用时返回 code=1006，需先解除引用 | data 为 null |
| POST | /api/v1/strategies/{strategy_id}/enable | 启用策略 | 路径参数策略 ID | 策略对象（status=enabled） |
| POST | /api/v1/strategies/{strategy_id}/disable | 停用策略 | 路径参数策略 ID；停用不影响进行中的回测/实盘运行 | 策略对象（status=disabled） |
| GET | /api/v1/strategies/{strategy_id}/params | 获取策略参数定义 | 路径参数策略 ID | 参数定义数组，每项含参数名、类型（int/float/str/bool/enum）、默认值、取值范围或枚举项、说明——供回测与实盘配置页动态渲染表单 |
| POST | /api/v1/cli-sessions | 创建 CLI 构建会话 | 请求体：cli_type（trae/workbuddy/codex，必填）；requirement：需求描述（必填）；base_strategy_id：基于已有策略改造时传入（可选）；working_params：CLI 附加参数（可选） | 会话对象：session_id、cli_type、状态（starting）、创建时间 |
| GET | /api/v1/cli-sessions/{session_id} | 查询会话状态 | 路径参数会话 ID | 会话对象：session_id、cli_type、状态（starting/running/completed/failed/cancelled）、已运行时长、产物文件数 |
| GET | /api/v1/cli-sessions/{session_id}/logs | 拉取会话日志 | 路径参数会话 ID；offset：日志行偏移（增量拉取，默认 0）；limit：本次拉取行数上限 | 日志对象：logs（行数组，含行号、级别、内容、时间）、next_offset（下次增量拉取偏移）、ended：会话是否已结束 |
| POST | /api/v1/cli-sessions/{session_id}/import | 会话产物入库 | 路径参数会话 ID；请求体：file：产物文件名（会话已生成文件中选一个）；name、description：入库后的策略名称与描述 | 入库后的策略对象（含策略 ID）；入库前自动校验统一策略接口合规性 |

> 说明：CLI 会话的实时输出以 WebSocket 主题 cli:{session_id} 推送为主（见 3.4），logs 接口用于断线后补拉与全量回放；入库接口仅在会话状态为 completed 时可用。

### 2.3 策略仿真模块（18 个接口）

#### 2.3.1 回测

| 方法 | 路径 | 用途 | 关键请求参数/请求体要点 | 响应 data 要点 |
|------|------|------|--------------------------|----------------|
| GET | /api/v1/backtest-engines | 回测引擎诊断 | 无 | simple/qlib 等引擎状态、版本、授权与下一步配置建议 |
| POST | /api/v1/backtests | 创建回测任务 | 请求体：strategy_id（必填）；engine：回测引擎（默认 simple）；params：策略参数（缺省用策略默认参数）；start_date、end_date（YYYY-MM-DD，必填）；initial_capital：初始资金（默认 1000000）；benchmark：基准指数代码（默认沪深 300）；commission_rate、slippage_rate：费率与滑点（可选）；order_type：market/open/limit；price_adjustment：qfq/hfq/none；max_position_count、max_position_weight、lot_size：组合约束 | 任务对象：task_id、策略 ID、引擎、状态（当前 simple 同步返回 finished）、创建时间；执行假设会进入 params._backtest 与绩效 metrics |
| GET | /api/v1/backtests | 回测任务列表 | strategy_id：策略过滤；status：状态过滤（pending/running/finished/failed）；page、page_size 分页 | 分页结构；items 含 task_id、策略名称、参数摘要、区间、状态、进度、创建时间、耗时 |
| GET | /api/v1/backtests/{task_id} | 回测任务详情 | 路径参数任务 ID | 任务对象：完整创建参数、状态、进度百分比、当前回测日期、错误信息（failed 时） |
| DELETE | /api/v1/backtests/{task_id} | 删除回测任务 | 路径参数任务 ID；运行中任务返回 code=3004，需先等待完成或失败 | data 为 null |
| GET | /api/v1/backtests/{task_id}/performance | 回测绩效汇总 | 路径参数任务 ID；仅 finished 状态返回完整绩效 | 绩效对象：总收益率、年化收益率、最大回撤及区间、夏普比率、索提诺比率、胜率、盈亏比、交易次数、相对基准超额收益、订单类型、复权方式和组合约束摘要 |
| GET | /api/v1/backtests/{task_id}/equity-curve | 回测权益曲线 | 路径参数任务 ID | 曲线对象：dates（日期序列）、equity（策略净值序列）、benchmark（基准净值序列）、drawdown（回撤序列） |
| GET | /api/v1/backtests/{task_id}/trades | 回测交易明细 | 路径参数任务 ID；page、page_size 分页 | 分页结构；items 每笔含开仓/平仓时间与价格、方向、数量、订单类型、成交说明、盈亏金额、盈亏比例、信号来源 |
| GET | /api/v1/backtests/{task_id}/attribution | 回测归因摘要 | 路径参数任务 ID | 归因对象：summary、by_symbol、by_signal、drawdown、risk_flags，用于页面归因图和闭环证据 |

Gradio 回测页在上述 REST 能力之上组合出四类前端服务动作：读取任务详情形成参数快照，读取 `/trades` 导出 CSV 到 `data/reports/backtest/exports/`，复用多个任务的详情与绩效生成参数对比视图，并复用模拟盘创建接口将回测绑定策略和资金转为 paper trading 账户。页面参数对比会同时展示订单类型、复权口径和组合约束，避免只比较收益而忽略执行假设。

回测参数补充：创建回测可传可选 parameter_profile，使用参数方案列表返回的 ID；params 缺省或空对象均继承默认配置。任务详情与列表提供 parameter_snapshot，包含各层参数、方案摘要、策略与相关源码摘要、运行环境和实际数据证据；旧任务为 null。GET /api/v1/strategies/{strategy_id}/parameter-profiles 返回当前入口可用方案；POST /api/v1/strategies/{strategy_id}/resolve-params 使用与创建回测相同的 params 和 parameter_profile，返回生效参数及来源，不运行策略。输入不合法或方案不属于当前策略时返回业务错误 1002。完整规则见 `10_strategy_parameter_design.md`。

#### 2.3.2 模拟盘（paper trading）

| 方法 | 路径 | 用途 | 关键请求参数/请求体要点 | 响应 data 要点 |
|------|------|------|--------------------------|----------------|
| POST | /api/v1/paper-accounts | 创建模拟账户 | 请求体：name（必填）；initial_capital：初始资金（默认 1000000）；strategy_id：绑定策略（可选，绑定后由策略信号自动下单） | 账户对象：account_id、名称、初始资金、状态、创建时间 |
| POST | /api/v1/paper-accounts/{account_id}/reset | 重置模拟账户 | 路径参数账户 ID；请求体：initial_capital：可选重置后资金（缺省沿用原值） | 重置后的账户对象（持仓清空、净值归一） |
| GET | /api/v1/paper-accounts/{account_id}/overview | 模拟账户总览 | 路径参数账户 ID | 总览对象：现金余额、总市值、总资产、当日盈亏、累计盈亏、当前净值、持仓只数、账户状态 |
| POST | /api/v1/paper-accounts/{account_id}/orders | 模拟账户下单 | 请求体：symbol（必填）、side（buy/sell，必填）、order_type（market 市价/limit 限价，必填）、quantity（必填，正整数）、price（order_type=limit 时必填） | 委托对象：order_id、受理状态（accepted）、委托状态、成交备注；市价单立即成交，限价未触发时进入待撮合 |
| POST | /api/v1/paper-accounts/{account_id}/orders/match | 手动撮合待撮合委托 | 路径参数账户 ID；按最新行情检查账户下待撮合委托 | 撮合摘要：matched_count、pending_count、matched_orders 和 skipped 原因 |
| DELETE | /api/v1/paper-accounts/{account_id}/orders/{order_id} | 撤单 | 路径参数账户 ID 与委托 ID；仅待成交状态可撤，已成交返回 code=3005 | 撤单结果对象：order_id、状态（cancelled） |
| GET | /api/v1/paper-accounts/{account_id}/orders | 委托列表 | 路径参数账户 ID；status：状态过滤（pending 待成交/filled 已成交/cancelled 已撤单/partial 部分成交）；page、page_size 分页 | 分页结构；items 含委托 ID、标的、方向、类型、价格、数量、已成交数量、状态、委托时间、更新时间 |
| GET | /api/v1/paper-accounts/{account_id}/fills | 成交列表 | 路径参数账户 ID；symbol：标的过滤；page、page_size 分页 | 分页结构；items 含成交 ID、关联委托 ID、标的、方向、成交价、成交量、成交金额、手续费、成交时间 |
| GET | /api/v1/paper-accounts/{account_id}/positions | 持仓列表 | 路径参数账户 ID | 持仓数组，每项含标的代码、名称、持仓数量、可用数量、成本价、最新价、市值、浮动盈亏与盈亏比例 |
| GET | /api/v1/paper-accounts/{account_id}/equity-history | 净值历史 | 路径参数账户 ID；start_date、end_date：区间过滤（可选） | 序列对象：dates、net_values（每日净值）、daily_returns（每日收益率） |

### 2.4 实盘模块（12 个接口）

| 方法 | 路径 | 用途 | 关键请求参数/请求体要点 | 响应 data 要点 |
|------|------|------|--------------------------|----------------|
| GET | /api/v1/live-configs | 实盘配置列表 | page、page_size 分页 | 分页结构；items 含配置 ID、名称、绑定策略 ID 与名称、通道类型（paper 内部模拟通道/broker 券商通道预留）、资金规模、风控参数摘要、状态、创建/更新时间 |
| POST | /api/v1/live-configs | 新建实盘配置 | 请求体：name（必填）、strategy_id（必填）、params（策略参数，缺省用策略默认值；可包含 `_live_validation.backtest_id` 和 `_live_validation.paper_account_id` 作为发布验证证据）、channel（通道，默认 paper）、capital（投入资金）、risk_controls（风控参数对象：单票最大仓位、单日最大亏损比例、最大持仓只数等） | 新建配置对象（含配置 ID） |
| GET | /api/v1/live-configs/{config_id} | 实盘配置详情 | 路径参数配置 ID | 配置对象：全部字段含完整风控参数与最近一次运行摘要 |
| GET | /api/v1/live-configs/{config_id}/validation | 发布验证检查 | 路径参数配置 ID | 检查数组：回测验证、模拟验证的当前值、状态和说明；缺少完成回测或模拟账户时返回拦截项 |
| PUT | /api/v1/live-configs/{config_id} | 更新实盘配置 | 请求体同新建，字段均可选；配置关联运行中的实盘时返回 code=4002，需先停止 | 更新后的配置对象 |
| DELETE | /api/v1/live-configs/{config_id} | 删除实盘配置 | 路径参数配置 ID；存在运行中实盘时返回 code=4002 | data 为 null |
| PATCH | /api/v1/live-configs/{config_id}/risk-controls | 更新风控参数 | 请求体：risk_controls（部分风控字段，运行中热更新仅支持可热更新项：单日最大亏损比例、最大持仓只数等；不可热更新项返回 code=4004） | 更新后的风控参数全量对象 |
| GET | /api/v1/live-broker-adapters | 通道适配器列表 | 无 | 适配器数组：channel、name、available、status、note、event_types；当前 `paper` 可用，`broker` 为预留不可用 |
| POST | /api/v1/live-runs | 启动实盘 | 请求体：config_id（必填）；启动前校验配置启用、通道适配器可用、资金、最大持仓数、单日亏损阈值、验证回测存在且完成、验证模拟账户存在且策略一致；前置校验失败返回 code=4003，同一配置已有 active 运行时返回 code=4001 | 运行对象：run_id、config_id、状态（running）、状态标签、是否终态、是否可暂停、是否可恢复、是否可停止、是否冻结、连续运行时长、启动时间 |
| POST | /api/v1/live-runs/{run_id}/pause | 暂停实盘 | 路径参数运行 ID；仅 running 可暂停，非法迁移返回 code=4001 | 运行对象（状态 paused），含状态标签、是否可恢复和是否可停止 |
| POST | /api/v1/live-runs/{run_id}/resume | 恢复实盘 | 路径参数运行 ID；paused 或 error 可恢复，error 恢复会清空 error_msg；非法迁移返回 code=4001 | 运行对象（状态 running），含状态标签和可执行动作 |
| POST | /api/v1/live-runs/{run_id}/mark-error | 标记异常冻结 | 路径参数运行 ID；请求体可选 message；终态不可标记，非法迁移返回 code=4001 | 运行对象（状态 error），含冻结标识、异常原因、是否可恢复和是否可停止 |
| POST | /api/v1/live-runs/{run_id}/broker-events | 写入通道事件 | 路径参数运行 ID；请求体 event_type 支持 `heartbeat/error`，message 可选，error 事件需要异常说明；终态不可写入，异常事件会进入 error 冻结态 | 运行对象，附 event_type、adapter_channel、adapter_status 和 adapter_available |
| POST | /api/v1/live-runs/{run_id}/stop | 停止实盘 | 路径参数运行 ID；请求体可选 graceful：是否等待在途委托处理完毕（默认 true）；starting/running/paused/stopping/error 可停止，终态重复停止返回 code=4001 | 运行对象（状态 stopping→stopped），含状态标签、是否终态和是否可停止 |
| GET | /api/v1/live-runs/{run_id}/status | 运行状态查询 | 路径参数运行 ID | 状态对象：run_id、状态机当前值（starting/running/paused/stopping/stopped/error）、中文状态标签、是否终态、是否可暂停、是否可恢复、是否可停止、是否冻结、连续运行时长、今日成交笔数、今日盈亏、最近心跳时间、最近错误信息（error 时） |
| GET | /api/v1/live-runs/{run_id}/orders | 实盘委托查询 | 路径参数运行 ID；status、page、page_size 同模拟盘委托约定 | 分页结构；字段同模拟盘委托，另含通道回执号 |
| GET | /api/v1/live-runs/{run_id}/positions | 实盘持仓查询 | 路径参数运行 ID | 持仓数组，字段同模拟盘持仓，另含通道侧对账状态 |

Gradio 发布策略页复用 `PATCH /live-configs/{config_id}/risk-controls` 更新风控阈值，并基于运行状态、最近心跳、通道类型和错误信息组合展示风控摘要、异常告警和运行日志。页面还提供通道适配器列表、通道事件写入、发布验证门槛与 dry-run 订单计划：发布验证读取 `_live_validation` 中的回测 ID 和模拟账户 ID，展示回测完成、策略一致、模拟账户存在和基础证据状态；dry-run 按配置资金、目标占比、标的行情和 A 股一手规则生成计划订单，检查通道适配器、资金规模、最大持仓数、单日亏损阈值、发布验证、资金占用和行情手数；检查失败时阻止从 Gradio 和 REST API 启动。运行状态机用于区分启动中、运行中、已暂停、停止中、已停止和错误冻结态，并避免同一配置重复启动；通道 `error` 事件同样会进入错误冻结态。该监控仍是当前占位实盘能力的观测面板，不代表真实 broker 已接入。

### 2.5 知识库模块（18 个接口）

#### 2.5.1 本地知识库

| 方法 | 路径 | 用途 | 关键请求参数/请求体要点 | 响应 data 要点 |
|------|------|------|--------------------------|----------------|
| GET | /api/v1/kb/categories | 分类树查询 | 无参数 | 树形数组：节点含分类 ID、名称、父分类 ID、文档数、排序号、children 子树 |
| POST | /api/v1/kb/categories | 新建分类 | 请求体：name（必填）、parent_id（为空建根分类）、sort_order | 新建分类节点 |
| PUT | /api/v1/kb/categories/{category_id} | 修改分类 | 请求体：name、parent_id、sort_order（至少一项；不允许把分类移动到自身子树下，返回 code=1007） | 更新后的分类节点 |
| DELETE | /api/v1/kb/categories/{category_id} | 删除分类 | 路径参数分类 ID；含子分类或文档时返回 code=1005，需先清空或级联删除 | data 为 null |
| POST | /api/v1/kb/documents | 上传文档/兼容创建文档 | multipart 表单：file（Markdown/TXT/CSV/JSON/HTML/YAML/LOG、文本层 PDF、DOCX）；category_id（可选，默认根分类）；title（可选，缺省用文件名）；tags（可选，逗号分隔或 JSON 数组）。兼容 JSON 请求体：title、content、category_id、tags、doc_type | 文档对象：doc_id、标题、分类、大小、解析类型 encoding、解析状态 ready、file_path、chunk_count；扫描 PDF 无文本层时返回解析错误 |
| POST | /api/v1/kb/notes | 新建笔记 | 请求体：title（必填）、content（Markdown 文本）、category_id（必填）、tags（可选） | 笔记对象：doc_id、标题、分类、创建时间、chunk_count |
| GET | /api/v1/kb/documents | 文档列表 | category_id：分类过滤（含子分类）；keyword：标题关键词；doc_type：类型过滤（document 上传文档/note 笔记/all）；page、page_size 分页 | 分页结构；items 含 doc_id、标题、类型、分类、标签、解析状态、分块数、创建/更新时间 |
| GET | /api/v1/kb/documents/{doc_id} | 文档详情 | 路径参数文档 ID；include_content：是否返回正文（默认 true） | 文档对象：元信息、正文内容（Markdown 化后的文本）、所属分类路径、标签、chunk_count、chunks 分块摘要 |
| DELETE | /api/v1/kb/documents/{doc_id} | 删除文档 | 路径参数文档 ID；同步删除 FTS5 索引与文件存储原文 | data 为 null |
| GET | /api/v1/kb/search | 全文检索 | keyword（必填）；category_id：范围限定（可选）；doc_type：类型限定（可选）；scope：检索范围（local 本地/remote 远程/all 全部，默认 local）；page、page_size 分页 | 分页结构；items 每项含 doc_id、标题、chunk_id、chunk_index、chunk_heading、命中片段摘要（高亮定位信息）、来源范围 source_scope、本地知识库或远程源名称 source_name、得分、更新时间 |
| POST | /api/v1/kb/qa | 知识库问答 | 请求体：question（必填）；scope：检索范围（local/remote/all，默认 all）；category_id：知识限定（可选）；top_k：引用条数上限（默认 5）；session_id：问答会话 ID（可选，默认 default）；context_turns：使用同一会话最近问答上下文轮数（默认 3，最大 5）；reset_context：是否本次忽略最近上下文；stream：是否流式返回（默认 false） | 非流式：答案文本、引用来源数组（doc_id、标题、chunk_id、chunk_index、chunk_heading、命中片段、source_scope、source_name）、session_id、context_used 和 context_turns。流式（stream=true）：响应以 SSE 分片返回，每个分片含增量文本或最终引用来源事件；流式期间错误以专用分片事件返回 |
| GET | /api/v1/kb/qa/sessions | 知识问答会话列表 | limit：返回数量，默认 50，最大 100 | 会话数组：session_id、name、summary、turn_count、latest_question、created_at、updated_at |
| PUT | /api/v1/kb/qa/sessions | 保存知识问答会话信息 | 请求体：session_id、name、summary | 会话元信息 |
| POST | /api/v1/kb/qa/clear | 清空问答会话 | 请求体：session_id（可选，默认 default） | session_id、deleted 删除条数 |

#### 2.5.2 远程知识库

| 方法 | 路径 | 用途 | 关键请求参数/请求体要点 | 响应 data 要点 |
|------|------|------|--------------------------|----------------|
| GET | /api/v1/kb/remote-sources | 远程源连接列表 | 无分页（数量少） | 连接数组：source_id、名称、类型（feishu/ima）、接入方式（MCP 服务引用）、状态（connected/disconnected/error）、最近同步时间 |
| POST | /api/v1/kb/remote-sources | 新建远程源连接 | 请求体：name（必填）、type（feishu/ima，必填）、mcp_server_id：关联的 MCP 服务 ID（必填）、root_folder：根目录映射（可选）、auth 配置引用（可选） | 新建连接对象（含 source_id） |
| PUT | /api/v1/kb/remote-sources/{source_id} | 更新远程源连接 | 请求体：name、root_folder、mcp_server_id（至少一项） | 更新后的连接对象 |
| DELETE | /api/v1/kb/remote-sources/{source_id} | 删除远程源连接 | 路径参数连接 ID；已拉取入库的文档保留 | data 为 null |
| POST | /api/v1/kb/remote-sources/{source_id}/test | 测试连接 | 路径参数连接 ID | 测试结果对象：success（布尔）、延迟毫秒、错误说明（失败时）、可达能力列表（列表/读取/搜索） |
| GET | /api/v1/kb/remote-sources/{source_id}/documents | 远程文档列表/检索 | 路径参数连接 ID；folder：远程目录路径（可选，缺省根）；keyword：远程关键词（可选，存在时调用 search 工具）；page、page_size 分页（通过 argument_map 尽力映射） | 分页结构；items 含远端文档 ID、标题、摘要、类型、更新时间、URL、是否已拉取入库 |
| POST | /api/v1/kb/remote-sources/{source_id}/pull | 拉取远程文档入库 | 请求体：remote_doc_id（单篇，必填）；folder：远端目录上下文（可选）；category_id：入库目标分类（可选，默认根分类）；fetch 工具参数可经 argument_map 映射 | 同步返回导入结果：成功数、跳过数、失败数、远程文档 ID、本地文档 ID、本地 Markdown 路径、chunk_count；正文会写入 remote_docs_cache、kb_documents、kb_document_chunks、FTS5 和 RAG |
| POST | /api/v1/kb/remote-sources/{source_id}/sync | 批量同步当前远程结果 | 请求体：folder、keyword、category_id、limit；按当前目录或关键词命中限量列出并逐篇拉取 | 同步返回 scanned_count、success_count、skipped_count、failed_count、failures、imported（含 chunk_count）；单篇失败计入 failures，不中断整批 |

### 2.6 定时任务模块（9 个接口）

| 方法 | 路径 | 用途 | 关键请求参数/请求体要点 | 响应 data 要点 |
|------|------|------|--------------------------|----------------|
| GET | /api/v1/jobs | 定时任务列表 | job_type：类型过滤（news_fetch 新闻采集/market_refresh 行情刷新/recommend 候选池刷新/report 模型报告/backtest 定期回测/paper_check 模拟盘巡检/calendar_refresh 交易日历更新/calendar_reference_refresh 官方参考日历导入/calendar_announcement_profile_check 交易所公告源核验/system_health_check 系统健康告警/data_maintain 数据维护/kb_sync 知识库同步/other）；enabled：启用状态过滤；page、page_size 分页 | 分页结构；items 含 job_id、名称、类型、cron 表达式、目标参数、启用状态、下次执行时间 |
| POST | /api/v1/jobs | 新建定时任务 | 请求体：name（必填）、job_type（必填）、cron（cron 表达式，必填，服务端校验合法性，非法返回 code=1002）、target：执行目标参数对象（按 job_type 约定，如 backtest 任务的 strategy_id 与区间模板；通用策略可传 trading_day_only、calendar_path、trading_calendar_path、trading_calendar.holidays、trading_calendar.extra_trading_days、retry_times、retry_interval_seconds、timeout_seconds、timeout_minutes、timeout_mode、hard_timeout、mutex_group、executor_key；calendar_refresh 可传 source、market、range_start、range_end、trade_dates、write_full_trading_days；calendar_reference_refresh 可传 official_calendar_path/reference_calendar_path、range_start、range_end、holidays、trading_days、announcement_text、announcement_path、announcement_url、announcement_index_url、announcement_profiles_path、announcement_profile、announcement_link_keywords、announcement_discovery_limit、announcement_url_timeout_seconds、announcement_url_max_bytes、official_source；calendar_announcement_profile_check 可传 announcement_profiles_path、announcement_profile、announcement_profile_min_links、announcement_profile_check_limit、announcement_url_timeout_seconds、announcement_url_max_bytes；system_health_check 可传 official_calendar_path/reference_calendar_path、calendar_warn_days、calendar_stale_days、calendar_diff_limit；data_maintain 可传 news_retain_days、remote_cache_retain_days、qa_history_retain_days、execution_keep_per_job、backtest_keep_per_strategy、qlib_keep_per_type、workflow_keep_per_mode、rebuild_fts_on_mismatch、optimize_fts、wal_checkpoint、database_optimize、vacuum；`custom` 任务需通过 executor_key 命中白名单执行体；timeout_mode=process 或 hard_timeout=true 时使用子进程硬超时）、enabled（默认 true） | 新建任务对象（含 job_id、下次执行时间） |
| GET | /api/v1/jobs/{job_id} | 任务详情 | 路径参数任务 ID | 任务对象：全部字段含完整 target 参数与最近一次执行记录 |
| PUT | /api/v1/jobs/{job_id} | 更新任务 | 请求体同新建（字段均可选）；运行中的触发不受影响，下次生效 | 更新后的任务对象 |
| DELETE | /api/v1/jobs/{job_id} | 删除任务 | 路径参数任务 ID；执行历史保留 | data 为 null |
| POST | /api/v1/jobs/{job_id}/enable | 启用任务 | 路径参数任务 ID | 任务对象（enabled=true、含下次执行时间） |
| POST | /api/v1/jobs/{job_id}/disable | 禁用任务 | 路径参数任务 ID | 任务对象（enabled=false） |
| POST | /api/v1/jobs/{job_id}/trigger | 手动触发一次 | 路径参数任务 ID；无视 cron 立即执行一次，不影响原调度 | 执行记录对象：history_id、job_id、触发方式（manual）、终态状态（成功/失败/跳过）、耗时、产出摘要和错误信息 |
| GET | /api/v1/jobs/{job_id}/histories | 执行历史查询 | 路径参数任务 ID；status：结果过滤（成功/失败/运行中/跳过）；start_time、end_time：时间区间；page、page_size 分页 | 分页结构；items 含 history_id、触发方式（cron/manual）、触发时间、耗时、状态、错误信息（failed 时）、产出摘要（如报告 ID、采集条数） |

### 2.7 模型配置模块（21 个接口）

#### 2.7.1 系统设置

| 方法 | 路径 | 用途 | 关键请求参数/请求体要点 | 响应 data 要点 |
|------|------|------|--------------------------|----------------|
| GET | /api/v1/settings | 读取全局系统设置 | 无参数 | 全局设置 payload：values 当前值、rows 配置来源明细、config_path、env_overrides；字段覆盖数据目录、SQLite 主库、文档目录、Parquet 行情湖、DuckDB 查询库、请求超时、HTTP 重试、缓存 TTL、交易日历和执行体白名单 |
| PUT | /api/v1/settings | 保存全局系统设置 | 请求体：全局设置白名单字段；保存到 `egs/config.yaml`，环境变量仍保持更高优先级；未知字段返回参数错误 | 保存后的全局设置 payload（回显当前值和来源） |
| POST | /api/v1/settings/environment/check | 校验环境变量 | 请求体：name（必填）；检查进程环境、`.llm_env` 和项目 `.env` | 变量状态对象：configured、masked_value、locations 和 source |
| DELETE | /api/v1/settings/environment/{name} | 删除单个环境变量 | 路径参数变量名；删除 `.llm_env` 中对应项并清理当前进程环境变量 | 删除结果：deleted、file_deleted、process_deleted 和 path |

#### 2.7.2 LLM 模型管理

| 方法 | 路径 | 用途 | 关键请求参数/请求体要点 | 响应 data 要点 |
|------|------|------|--------------------------|----------------|
| GET | /api/v1/llm-models | 模型列表 | 无分页（数量少） | 模型数组：model_id、名称、provider（openai 兼容供应商标识）、base_url、模型名、级别（fast 快速/deep 深度）、是否默认、状态、调用次数、成功/失败次数、平均耗时、最近状态、最近调用时间；密钥字段仅返回掩码 |
| POST | /api/v1/llm-models | 新增模型 | 请求体：name（必填）、base_url（必填）、model_name（必填）、api_key_env 或 api_key（可选，api_key 会写入 `.llm_env` 并转为变量名）、level（fast/deep）、max_tokens 等可选参数 | 新建模型对象（密钥不回显） |
| PUT | /api/v1/llm-models/{model_id} | 更新模型 | 请求体：同新建字段均可选；api_key 传入空或不传表示不修改，非空时写入 `.llm_env` 并更新 api_key_env | 更新后的模型对象 |
| DELETE | /api/v1/llm-models/{model_id} | 删除模型 | 路径参数模型 ID；被系统设置绑定为默认分级模型时返回 code=5002，需先改绑定 | data 为 null |
| POST | /api/v1/llm-models/{model_id}/set-default | 设为默认模型 | 请求体：level（fast/deep，必填，将该模型设为对应分级的默认） | 绑定结果对象：fast_default_model_id、deep_default_model_id |
| POST | /api/v1/llm-models/{model_id}/test | 连通性测试 | 路径参数模型 ID；服务端用该模型配置发送一次最小补全请求 | 测试结果对象：success、首字延迟、总耗时、返回内容摘要或错误说明 |

#### 2.7.3 MCP 服务管理

| 方法 | 路径 | 用途 | 关键请求参数/请求体要点 | 响应 data 要点 |
|------|------|------|--------------------------|----------------|
| GET | /api/v1/mcp-servers | MCP 服务列表 | 无分页 | 服务数组：server_id、名称、command/args/url 启动或连接配置、启用状态、连接状态、工具数量、最近连接时间、失败冷却状态、剩余冷却秒数、连续失败次数 |
| POST | /api/v1/mcp-servers | 新增 MCP 服务 | 请求体：name（必填）、transport（stdio 命令行/sse 远程，必填）、command、args、url（按 transport 提供对应必填项）、env 环境变量、enabled（默认 true） | 新建服务对象 |
| PUT | /api/v1/mcp-servers/{server_id} | 更新 MCP 服务 | 请求体：同新建字段均可选 | 更新后的服务对象 |
| DELETE | /api/v1/mcp-servers/{server_id} | 删除 MCP 服务 | 路径参数服务 ID；被远程知识源引用时返回 code=1006 | data 为 null |
| POST | /api/v1/mcp-servers/{server_id}/enable | 启用 MCP 服务 | 路径参数服务 ID；启用后自动建立连接 | 服务对象（enabled=true、连接状态） |
| POST | /api/v1/mcp-servers/{server_id}/disable | 停用 MCP 服务 | 路径参数服务 ID；断开连接，引用该服务的远程源转 disconnected | 服务对象（enabled=false） |
| POST | /api/v1/mcp-servers/{server_id}/test | 测试 MCP 服务 | 路径参数服务 ID；尝试建立连接并列举工具；失败冷却期内短路返回，不重复探测 | 测试结果对象：success、延迟、可用工具名列表、错误说明、cooldown、short_circuited、retry_after_seconds、failure_count |
| POST | /api/v1/mcp-servers/{server_id}/tools/call | 调用 MCP 工具 | 请求体：name/tool_name（必填）、arguments（JSON 对象，可选）；stdio/http 执行一次工具调用，SSE 返回明确不支持；失败冷却期内短路返回，不重复调用传输层 | 调用结果对象：success、transport_success、tool_name、content、structured_content、is_error、error、延迟、cooldown、short_circuited、retry_after_seconds、failure_count |

#### 2.7.4 Skill 管理

| 方法 | 路径 | 用途 | 关键请求参数/请求体要点 | 响应 data 要点 |
|------|------|------|--------------------------|----------------|
| GET | /api/v1/skills | Skill 列表 | 无分页 | Skill 数组：skill_id、名称、描述、来源（内置/MCP 服务）、启用状态、参数定义、当前参数值 |
| POST | /api/v1/skills/{skill_id}/enable | 启用 Skill | 路径参数 Skill ID | Skill 对象（enabled=true） |
| POST | /api/v1/skills/{skill_id}/disable | 停用 Skill | 路径参数 Skill ID | Skill 对象（enabled=false） |
| PUT | /api/v1/skills/{skill_id}/params | 保存 Skill 参数 | 请求体：params（与该 Skill 参数定义匹配的对象）；不匹配定义返回 code=1002 | 更新后的 Skill 对象（含新参数值） |
| POST | /api/v1/skills/{skill_id}/run | 手动运行 Skill | 请求体可传 params；Skill 必须已启用，内置 `news_summary` 返回本地新闻快照，未接入执行器的 Skill 返回 blocked | 执行状态、结果摘要、结果数据或阻塞原因 |

### 2.8 AI量化闭环模块（6 个接口）

| 方法 | 路径 | 用途 | 关键请求参数/请求体要点 | 响应 data 要点 |
|------|------|------|--------------------------|----------------|
| GET | /api/v1/quant-workflows/modes | 闭环模式列表 | 无 | simulation、live 等模式定义 |
| GET | /api/v1/quant-workflows/sops | SOP 列表 | mode：可选，按闭环模式过滤 | SOP 定义、阶段、目标 |
| GET | /api/v1/quant-workflows/snapshot | 生成闭环快照 | mode、sop_id、strategy_id、backtest_id、account_id、live_run_id 均可选 | 步骤、归因洞察、智能问数、迭代建议、产物引用和证据快照 |
| POST | /api/v1/quant-workflows/runs | 保存闭环运行 | 请求体：mode、sop_id、title、strategy_id、backtest_id、account_id、live_run_id | 已保存运行详情、步骤和产物 |
| GET | /api/v1/quant-workflows/runs | 闭环运行列表 | mode、page、page_size | 分页结构；items 含运行 ID、模式、SOP、标题、状态、摘要和创建时间 |
| GET | /api/v1/quant-workflows/runs/{run_id} | 闭环运行详情 | 路径参数运行 ID | 运行上下文、步骤列表和产物列表 |

### 2.9 通用接口（2 个接口）

| 方法 | 路径 | 用途 | 关键请求参数/请求体要点 | 响应 data 要点 |
|------|------|------|--------------------------|----------------|
| GET | /api/v1/health | 健康检查 | 无参数 | 精简结构（可不受统一信封约束）：status（ok/degraded）、数据库可写状态、调度器运行状态、交易日历文件状态（路径、市场、来源、更新时间、覆盖区间、日期统计）、系统告警列表、各数据源健康摘要 |
| GET | /api/v1/system/info | 系统信息 | 无参数 | 版本号、构建时间、进程启动时间、运行时长、Python 版本、操作系统、数据目录占用大小、当前连接的 WebSocket 客户端数 |

### 2.10 接口数量汇总

| 模块 | 接口数 |
|------|--------|
| 市场分析 | 33 |
| 策略构建 | 12 |
| 策略仿真 | 18 |
| 实盘 | 12 |
| 知识库 | 18 |
| 定时任务 | 9 |
| 模型配置 | 21 |
| AI量化闭环 | 6 |
| 通用 | 2 |
| **合计** | **130** |

---

## 3. WebSocket 接口设计

### 3.1 连接与协议总体约定

- 平台提供**单一 WebSocket 端点 /ws**，所有实时数据通过"主题订阅"模式推送：客户端连接后发送订阅消息声明关注主题，服务端仅向订阅者推送对应主题数据。
- 一个连接可同时订阅多个主题；实例主题通过实例参数区分（如多个回测任务），订阅与退订均以"主题名 + 实例参数"为粒度。
- 服务端按主题维护订阅表；实例主题对应资源结束（回测完成、会话结束、实盘停止）后自动清理订阅，无需客户端显式退订。
- 消息为文本帧承载的 JSON 文本，字符集 UTF-8；所有时间字段均为 ISO 8601 UTC 字符串。

### 3.2 消息结构

**服务端 → 客户端（推送消息）** 字段约定：

| 字段 | 类型 | 说明 |
|------|------|------|
| topic | 字符串 | 主题名。实例主题携带实例标识，如 backtest:bt-1001、cli:cs-2033、paper:acc-7、live:run-12；非实例主题为主题名本身，如 market、notify |
| type | 字符串 | 事件类型，见 3.4 各主题事件表，如 progress、quote、order_update |
| payload | 对象 | 事件载荷，结构随 topic 与 type 变化 |
| ts | 字符串 | 服务器生成该消息的时间，ISO 8601 UTC |

**客户端 → 服务端（控制消息）** 字段约定：

| 字段 | 类型 | 说明 |
|------|------|------|
| action | 字符串 | subscribe（订阅）、unsubscribe（退订）、ping（心跳） |
| topic | 字符串 | 订阅/退订的目标主题名，如 market、backtest |
| params | 对象 | 实例主题的实例参数：订阅 backtest 主题时传 task_id；cli 主题传 session_id；paper 主题传 account_id；live 主题传 run_id；非实例主题可省略 |
| seq | 整数 | 可选。客户端自增序号，用于关联服务端确认消息 |

服务端对控制消息的应答：订阅/退订成功返回 type 为 subscribed/unsubscribed 的确认消息（topic 字段带实例标识）；订阅失败（实例不存在等）返回 type 为 error 的确认消息（payload 含原因）；ping 返回 pong。

### 3.3 心跳与重连约定

| 项 | 约定 |
|----|------|
| 心跳间隔 | 客户端每 30 秒发送一次 action=ping 的控制消息；服务端立即回复 pong |
| 空闲超时 | 服务端超过 90 秒未收到任何客户端消息（含心跳）则主动断开连接 |
| 断线判定 | 客户端超过 60 秒未收到任何服务端消息（含 pong）视为断线 |
| 重连策略 | 客户端指数退避重连（1s、2s、4s，上限 60s）；重连成功后必须重新发送全部订阅消息（服务端不保留断线期间的订阅关系） |
| 断线补数 | 行情类主题断线期间数据不补发，重连后由 REST 接口拉取最新快照；CLI 会话日志通过 logs 接口按 offset 增量补拉；回测进度通过任务状态接口补查 |

### 3.4 主题表与推送事件表

#### 3.4.1 主题总表

| 主题 | 形态 | 说明 |
|------|------|------|
| market | 非实例主题 | 行情推送：自选标的、大盘指数、板块行情的周期性推送与异动提醒 |
| backtest:{task_id} | 实例主题 | 单个回测任务的进度与状态推送 |
| cli:{session_id} | 实例主题 | 单个 CLI 构建会话的实时输出与状态推送 |
| paper:{account_id} | 实例主题 | 单个模拟账户的委托/成交/持仓/净值动态推送 |
| live:{run_id} | 实例主题 | 单个实盘运行的运行状态与交易动态推送 |
| notify | 非实例主题 | 全局通知：异步任务完成/失败、定时任务事件、系统告警、数据源状态变化 |

订阅实例主题时，控制消息 topic 传主题名（如 backtest），实例标识放 params（如 task_id）；推送消息的 topic 字段为完整的"主题名:实例 ID"形式。

#### 3.4.2 market 主题事件

| 事件 type | 触发时机 | payload 要点 |
|-----------|----------|--------------|
| quote | 自选标的行情刷新（定时批量，默认 3-5 秒/批） | quotes：数组，每项含标的代码、名称、最新价、涨跌幅、成交量、时间戳 |
| index | 大盘指数刷新 | indices：数组，每项含指数代码、名称、最新价、涨跌幅、时间戳 |
| sector | 板块行情刷新 | sectors：数组，每项含板块代码、名称、涨跌幅、领涨股 |
| trade_notice | 盘中重要异动提醒（快速涨跌、放量） | symbol、名称、异动类型、当前价、涨跌幅、触发阈值说明 |

#### 3.4.3 backtest:{task_id} 主题事件

| 事件 type | 触发时机 | payload 要点 |
|-----------|----------|--------------|
| progress | 回测进度推进（按交易日或数据批次节流推送） | task_id、progress（0-100 百分比）、current_date（当前回测到的交易日）、processed_bars、speed（bar 数/秒） |
| stage | 阶段切换（数据加载/回放计算/绩效评估） | task_id、stage（loading/running/evaluating）、stage 描述 |
| completed | 回测正常完成 | task_id、耗时、总收益率、年化收益率、最大回撤、夏普比率（绩效摘要，详细数据走 REST） |
| failed | 回测异常终止 | task_id、错误码、错误描述 |

#### 3.4.4 cli:{session_id} 主题事件

| 事件 type | 触发时机 | payload 要点 |
|-----------|----------|--------------|
| output | CLI 子进程 stdout/stderr 有新输出（按行推送，节流合并） | session_id、stream（stdout/stderr）、lines：文本行数组、行号偏移 |
| status | 会话状态变更 | session_id、status（starting/running/completed/failed/cancelled）、变更时间 |
| artifact | 检测到新生成产物文件 | session_id、file：文件名、size、修改时间 |
| error | 会话进程异常（崩溃、超时） | session_id、错误码、错误描述 |

#### 3.4.5 paper:{account_id} 主题事件

| 事件 type | 触发时机 | payload 要点 |
|-----------|----------|--------------|
| order_update | 委托状态变更（受理/部分成交/全部成交/已撤单） | account_id、order_id、标的、方向、状态、已成交数量、更新时间 |
| fill | 新成交回报 | account_id、fill_id、order_id、标的、方向、成交价、成交量、手续费、成交时间 |
| position_update | 持仓变动（成交驱动） | account_id、positions：变动标的的持仓快照（数量、成本、市值、浮盈） |
| equity_update | 账户净值更新（定时与成交驱动） | account_id、总资产、现金、市值、净值、累计收益率、时间 |

#### 3.4.6 live:{run_id} 主题事件

| 事件 type | 触发时机 | payload 要点 |
|-----------|----------|--------------|
| status | 实盘运行状态机变更 | run_id、status（starting/running/paused/stopping/stopped/error）、说明、时间 |
| heartbeat | 运行心跳（默认 10 秒/次，证明引擎存活） | run_id、uptime_seconds、当前持仓只数、今日成交笔数 |
| order_update | 实盘委托状态变更 | run_id、order_id、标的、方向、状态、通道回执号、时间 |
| position_update | 实盘持仓变动 | run_id、positions：变动标的持仓快照 |
| risk_alert | 风控触发告警 | run_id、规则类型（单日最大亏损/单票仓位上限/最大持仓数等）、触发值与阈值、处置动作（拒绝委托/强制停止） |

#### 3.4.7 notify 主题事件

| 事件 type | 触发时机 | payload 要点 |
|-----------|----------|--------------|
| task_done | 异步任务完成（推荐任务、市场分析报告、远程文档拉取、文档解析等） | task_type、task_id、摘要（如报告标题、推荐数量）、耗时 |
| task_failed | 异步任务失败 | task_type、task_id、错误码、错误描述 |
| scheduler_skipped | 定时任务跳过 | task_type=scheduler、job_id、job_type、history_id、summary、trigger_type |
| system_alert | 系统健康告警 | task_type=system_health、source、severity、code、title、message、created_at |
| scheduler | 定时任务开始/结束 | job_id、job_name、event（started/finished/failed）、执行记录 ID |
| system | 系统级告警（磁盘不足、数据库异常等） | 级别（warning/critical）、模块、描述 |
| data_source | 数据源状态变化（fallback 切换、失败冷却、恢复） | source_name、data_type（行情/新闻/研报/论文）、event（switch/cooldown/recover）、说明 |

---

## 4. 错误码规范

### 4.1 分段规则

| 分段 | 含义 | 典型场景 |
|------|------|----------|
| 0 | 成功 | 一切成功响应 |
| 1xxx | 参数与资源错误 | 参数缺失/非法、资源不存在、通用资源状态冲突 |
| 2xxx | 数据源/外部服务错误 | 行情/新闻/研报/论文数据源失败、LLM 调用失败、MCP 连接失败、CLI 子进程异常 |
| 3xxx | 策略/回测/仿真错误 | 策略代码不合规、回测任务状态错误、模拟盘下单校验失败 |
| 4xxx | 实盘与风控错误 | 实盘状态冲突、风控拦截、通道异常 |
| 5xxx | 系统内部错误 | 数据库错误、存储写入失败、未知异常 |

### 4.2 常见错误码枚举

| 错误码 | 含义 | 典型触发接口 |
|--------|------|--------------|
| 0 | 成功 | 全部接口 |
| 1001 | 缺少必填参数 | 各创建类接口 |
| 1002 | 参数格式或取值非法 | cron 表达式非法、日期区间倒置、参数类型不符 |
| 1003 | 请求体无法解析 | 各 POST/PUT/PATCH 接口 |
| 1004 | 资源不存在 | 各路径 ID 类接口（策略/任务/账户/文档等不存在） |
| 1005 | 资源非空禁止删除 | 删除含标的的分组、含文档的分类 |
| 1006 | 资源被引用禁止操作 | 删除被回测/实盘引用的策略、被远程源引用的 MCP 服务 |
| 1007 | 关系约束冲突 | 分类移动到自身子树下 |
| 2001 | 行情数据源失败 | 行情类接口（多源全部失败时） |
| 2002 | 新闻数据源失败 | 新闻列表/关键词云 |
| 2003 | 研报/论文数据源失败 | 研报与论文接口 |
| 2004 | LLM 调用失败 | 推荐任务（deep 路径）、模型分析报告、知识库问答 |
| 2005 | MCP 服务连接失败 | 远程知识源相关接口 |
| 2006 | CLI 子进程异常 | CLI 会话创建/产物入库（进程崩溃、超时） |
| 3001 | 策略状态不允许操作 | 停用被实盘引用的策略等 |
| 3002 | 任务尚未完成无法获取结果 | 推荐任务/回测结果接口在非 finished 状态调用 |
| 3003 | 策略代码不符合统一策略接口 | 策略上传/CLI 产物入库校验失败 |
| 3004 | 回测任务运行中禁止删除 | 回测删除接口 |
| 3005 | 委托状态不允许撤单 | 对已成交委托撤单 |
| 3006 | 模拟盘下单校验失败 | 资金不足、数量非法、标的不可交易 |
| 4001 | 实盘状态冲突 | 对已停止实盘 stop、对运行中实盘重复启动 |
| 4002 | 配置被运行中实盘引用 | 更新/删除运行中实盘对应的配置 |
| 4003 | 实盘前置校验失败 | 策略未启用、策略无完成回测记录 |
| 4004 | 风控参数不可热更新 | 运行中修改仅停机可改的风控项 |
| 4005 | 风控拦截 | 下单触发风控规则被拒绝 |
| 5001 | 数据库错误 | 各写接口底层异常 |
| 5002 | 配置依赖冲突 | 删除被默认分级绑定的 LLM 模型 |
| 5003 | 文件存储读写失败 | 文档上传、策略代码保存 |
| 5999 | 未知内部错误 | 兜底异常 |

---

## 5. 接口与页面映射

当前前端采用 Gradio Blocks 挂载在 `/app/`，以主导航 Tabs 与模块内 Tabs 组织七大功能页面。核心页面与 API、WebSocket 主题的映射如下：

| 前端页面 | 所属模块 | 调用的核心接口 | 使用的 WebSocket 主题 |
|----------|----------|----------------|----------------------|
| 新闻消息页 | 市场分析 | 新闻列表、新闻关键词云 | notify（采集任务完成提醒） |
| 行情看盘页（通用） | 市场分析 | 大盘指数行情、板块行情、热力图数据 | market（index/sector/trade_notice 事件） |
| 行情看盘页（个性化/自选） | 市场分析 | 自选分组增删改查、自选行情 | market（quote 事件） |
| 关联关系图页 | 市场分析 | 关联关系图数据、个股详情聚合（跳转）；支持接收个股页或推荐页同步过来的中心代码 | 无 |
| 个股详情页 | 市场分析 | 个股详情聚合、研报列表；前端服务可复用关系图接口同步当前代码 | market（quote 事件，可选订阅该标的） |
| 股票推荐页 | 市场分析 | 推荐任务创建/状态/结果；前端服务复用自选、关系图和回测接口完成批量入自选、首只候选看关系、条件模板、候选对比和推荐候选一键回测 | notify（task_done/task_failed 事件） |
| 研报页 | 市场分析 | 研报列表、研报详情 | 无 |
| 模型分析报告页 | 市场分析 | 报告生成、报告列表、报告详情 | notify（task_done/task_failed 事件） |
| 论文搜索页 | 市场分析 | 论文搜索、论文收藏/取消收藏、导入知识库 | 无 |
| 策略库页 | 策略构建 | 策略列表/详情/上传/删除/启停 | 无 |
| 策略构建工作台页 | 策略构建 | CLI 会话创建/状态/日志/产物入库 | cli:{session_id}（output/status/artifact 事件） |
| 回测列表页 | 策略仿真 | 回测任务创建/列表/详情/删除 | notify |
| 回测报告页 | 策略仿真 | 分组绩效与指标解释、权益/基准/回撤、月度收益、滚动风险、交易分布、持仓暴露、归因和交易明细 | backtest:{task_id}（进行中任务的 progress 事件） |
| 模拟盘页 | 策略仿真 | 账户创建/重置/总览、下单、手动撮合挂单、撤单、委托/成交/持仓/净值历史 | paper:{account_id}（order_update/fill/position_update/equity_update 事件） |
| 实盘配置页 | 实盘 | 实盘配置增删改查、风控参数更新 | 无 |
| 实盘监控页 | 实盘 | 实盘启动/停止、运行状态、委托/持仓查询 | live:{run_id}（status/heartbeat/order_update/position_update/risk_alert 事件） |
| 本地知识库页 | 知识库 | 分类树管理、文档上传/新建笔记/列表/详情/删除 | notify（文档解析完成） |
| 知识库问答页 | 知识库 | 全文检索、问答（流式） | 无（问答流式走 REST SSE） |
| 远程知识库页 | 知识库 | 远程源增删改查/测试、远程文档列表/拉取入库 | notify（拉取进度） |
| 定时任务页 | 定时任务 | 任务增删改查/启停/手动触发、执行历史 | notify（scheduler 事件） |
| 系统设置页 | 模型配置 | 系统设置读取/保存 | 无 |
| LLM 模型管理页 | 模型配置 | 模型增删改查/设为默认/连通性测试/调用统计；环境变量校验和单项删除 | 无 |
| MCP 服务页 | 模型配置 | MCP 服务增删改查/启停/测试 | notify（data_source 事件，可选） |
| Skill 配置页 | 模型配置 | Skill 列表/启停/参数保存 | 无 |
| 全局布局（顶栏/通知中心） | 通用 | 健康检查、系统信息 | notify（全部事件，全局订阅） |

---

## 6. 设计要点回顾

### 模型与多 Agent 当前扩展

ETF 投研接口：GET `/api/v1/etf/universes` 返回配置池和基准；GET `/api/v1/etf/universes/{universe}` 返回池元数据；GET `/api/v1/etf/universes/{universe}/snapshot` 返回真实行情、历史点数、平均成交额和缺失状态。创建回测时，ETF 策略参数中的 `universe` 会进入参数快照；绩效中额外记录 `asset_type=etf`、`tracking_error`、`etf_universe` 和调仓周期。跟踪误差相对回测标的池等权基准计算。

多 Agent 复核请求新增 `workflow`：`backtest_review` 或 `etf_review`。ETF 工作流读取 `etf` 证据并使用 ETF 专用四角色配置，仍返回角色轨迹、证据引用和最终结论，`can_trade` 固定为 false。

回测绩效接口新增模型诊断对象，包含拟合次数、训练/验证日期、标签到期日、样本外预测、验证与样本外 MSE、耗时和配置快照。内置引擎实际比较基准为标的池等权买入持有，任务基准名称与计算口径保持一致。

| 方法 | 路径 | 输入与结果 |
| --- | --- | --- |
| POST | /api/v1/research-team/runs | 输入已完成回测 ID、研究目标和可选模型配置 ID；返回四角色研究复核报告、证据引用、工具轨迹、系统检查与最终状态 |
| GET | /api/v1/research-team/runs/{run_id} | 按运行标识读取已保存的报告；非法标识或不存在时返回业务错误 |

多 Agent 的 API 创建当前同步执行，Gradio 通过生成器按角色进度更新。没有真实模型配置或协议输出无效时返回失败状态，不伪装为模型成功；不开放委托接口。

- **统一信封 + 执行状态**：先检查信封 code；创建/运行动作还须检查 data 中的 failed、blocked 等最终状态，不能以 HTTP 200 或 code=0 单独判定执行成功。
- **长任务实际边界**：资源接口可提供创建、状态和结果查询，但当前内置回测、多 Agent 和 Qlib 创建主要同步执行；创建响应之前不保证取得任务 ID。后台执行、断线恢复和取消能力须另行实现，不能当作现有统一异步能力。
- **单一 WebSocket 端点 + 主题订阅**：一个连接服务全部实时场景，实例主题按资源 ID 区分，断线重连后由 REST 补齐快照、WebSocket 续推增量。
- **路径风格统一**：资源复数名词、连字符分词、动作 POST 子路径、查询 GET 子资源，与总体设计文档的七大模块划分一一对应。

### 统一命令行已实现扩展

统一 CLI 的业务映射、输入/输出、退出码、同步调用与流式方案见 `12_cli_interface_design.md`。新增证券搜索、预制策略、资源池、模拟账户列表、AI 工作台会话与附件，以及多 Agent 渐进事件端点；保持已有 REST 行为兼容。

| 方法 | 路径 | 实际行为 |
| --- | --- | --- |
| GET | /api/v1/system/capabilities | 数据模式、实际市场和来源、后台接入边界，无网络探活 |
| GET | /api/v1/securities/search | query、market、limit，复用证券主数据检索 |
| GET/POST | /api/v1/strategy-examples；/strategy-examples/detail；/strategy-examples/import | 示例列表、预览和导入；detail/import 使用 example 相对路径白名单 |
| GET/POST | /api/v1/resource-pools | 资源池列表与创建 |
| GET/POST | /api/v1/resource-pools/{pool_id}/items、/symbols、/import | 成员查询、代码添加、CSV/XLSX multipart 导入，不接收服务器任意路径 |
| GET | /api/v1/paper-accounts | 分页模拟账户，统一 account_id |
| GET/POST | /api/v1/ai-workspace/sessions | 分页会话、新建会话 |
| GET | /api/v1/ai-workspace/sessions/{session_id} | 会话与持久消息，历史条数受配置限制 |
| POST | /api/v1/ai-workspace/attachments | multipart 上传，返回 attachment_id，类型和大小复用附件配置 |
| POST | /api/v1/ai-workspace/sessions/{session_id}/messages；/messages/stream | 同步最终结果或真实 SSE；message、backend、模型、思考强度、attachments 标识列表 |
| POST | /api/v1/research-team/runs/stream | 同一复核服务的实际阶段及终态，event_id/time/type/data；原同步接口继续提供 |

CLI 对支持市场的命令发送 X-AIQuant-Market: CN/US。ASGI 中间件在当前请求 ContextVar 中绑定和恢复，不调用全局 set_current_market；查询参数中的 CN/US 也按同一范围处理。Qlib 的 csi300 等原生研究池不作为 CN/US 市场切换。

## 2026-10-22 策略工坊接口

新增路由由 `src/api/routes/strategy_pipelines.py` 提供，复用原响应封装；配置校验失败返回参数业务错误，不包装成未知内部错误。预览不会训练或调用模型。

| 接口 | 操作与口径 |
| --- | --- |
| GET /api/v1/strategy-components；/strategy-pipeline-templates | 组件、风险/分配能力目录及七套预置 |
| GET/POST /api/v1/strategy-pipelines；GET/PUT /{pipeline_id} | 查询、创建、读取和保存草稿 |
| POST /api/v1/strategy-pipelines/preview | definition、variant、overrides 的完整生效预览 |
| POST /api/v1/strategy-pipelines/{pipeline_id}/publish；GET /versions | 冻结新版本与登记组合策略，不原地更新历史版本 |
| POST /api/v1/strategy-pipelines/{pipeline_id}/enabled | enabled 布尔查询参数；停用阻断新研究，保留持仓风险监控 |
| POST /api/v1/strategy-pipeline-runs；/stream | template/definition/version_id、股票池或资源池、日期、模式与后端；普通接口返回任务，SSE返回真实事件和终态 |
| GET /api/v1/strategy-pipeline-runs；/{run_id}；/{run_id}/events；/{run_id}/result | 历史、状态、事件及结果 |
| GET/PUT /api/v1/strategy-pipelines/{pipeline_id}/layout | 独立布局；写入definition_digest、layout和revision，修订冲突拒绝覆盖，不生成计算版本 |
| GET /api/v1/strategy-pipeline-runs/{run_id}/nodes | 只读节点证据及cursor；after为非负事件游标，预览有界，完整记录仍用events/result或附件 |
| POST /api/v1/strategy-pipeline-runs/{run_id}/cancel | 任务进入取消中并通知执行器；不冒充立即终止阻塞 API 或原生训练 |
| GET /api/v1/strategy-pipeline-runs/{run_id}/files/{name} | 仅白名单的报告、请求、定义、行情、事件、账本和结果附件 |
| GET /api/v1/strategy-pipeline-accounts；/{account_id} | 独立持久模拟账本；与旧单策略模拟接口区分 |
| POST /api/v1/strategy-pipeline-accounts/{account_id}/monitor；/risk-reset | 显式启停监控或解除本地冻结，记录审计，不发送券商指令 |

历史回测的 agent_mode 默认 off，replay 只接受当时决定ID列表，live 只允许当期目标/筛选/前向模拟。require_real 在服务端和 CLI 最终结果双重检查。CLI pipeline run 通过 SSE 等待终态，JSON仅输出一次最终结果，JSONL显示进程事件。最终路径以 OpenAPI 和 `egs/cli/commands/pipeline.yaml` 为准。

## 2026-10-26 图片附件入口约定

工作台附件上传与消息发送复用同一内容校验。图片上传在持久保存前由项目内Pillow13进程校验，发送时再次校验实际字节；UI本地附件、悬浮助手与CLI走相同业务服务。格式、损坏、像素、帧、总量和超时失败返回既有参数错误，不调用模型或写入用户消息。视觉API使用校验快照，CLI使用项目内快照文件；端点与上传标识契约不变。主Gradio环境Pillow告警另记，不将图片工作进程通过等同于全环境无漏洞。

## 文件阅读与Markdown保存

2026-10-27按22号方案接入，前缀仍由平台API配置决定。

| 接口 | 契约 |
| --- | --- |
| POST /file-previews/project | 项目内相对path登记；拒绝环境密钥、运行数据与越界路径 |
| POST /file-previews/uploads | 有界multipart上传，保存原始字节和格式身份，不自动入知识库或调用模型 |
| POST /file-previews/knowledge/{doc_id} | 读取知识库原件；旧无原件记录明确标识提取文本 |
| GET /file-previews/{id}；/{id}/view；/{id}/raw | 元数据、内嵌阅读界面、原件；raw的download选项提供下载，HTML原件以文本类型返回 |
| POST /file-previews/{id}/conversion；GET /{id}/pdf | Office后台转换及完成产物；真实queued/running/completed/failed状态，原件始终只读 |
| PUT /file-previews/{id}/markdown | 提交revision及content；只允许Markdown可编辑来源，版本冲突使用既有1007业务码，失败不覆盖原文 |
| GET /file-previews/{id}/assets/{relative} | 项目Markdown的受控本地图片，拒绝越界或其他文件类型 |

文件ID由服务端产生，客户端不能修改来源、内部存储路径或可编辑标记。新增登记/写入接口检查网页Origin同站点，查看器只允许同源页面嵌入；无Origin的既有本地API客户端继续可用。此约束不替代平台登录认证。Office及所有非Markdown格式直接调用保存接口也被拒绝。

知识库Markdown保存同步原件、提取正文、摘要和分块，并保留修改前版本。Office转换缓存以原件及转换环境身份区分，格式损坏、加密或超时如实返回，不用空PDF冒充完成。完整设计及回归范围见22号设计与本轮验收。

## 中文多空与双团队竞赛接口

AI会话的后端及权限补充见本文末尾，策略内部角色不自动切换Qoder。

2026-10-28按24号设计接入，前缀继续沿用平台API配置，CLI分组为agent-strategy。

| 接口 | 契约 |
| --- | --- |
| GET /agent-strategies/recipes | 六套方案、深度及默认预算 |
| GET、POST /agent-strategies/runs | 有界列表、创建单时点后台研究；行情与documents复用Alpha数据集 |
| GET /agent-strategies/runs/{id} | 冻结请求/证据、实际状态及结果 |
| POST /agent-strategies/runs/{id}/cancel | 请求停止后续工作，已发生的模型费用不撤销 |
| GET /agent-strategies/runs/{id}/events；/stream | 游标事件及真实SSE，工具/角色/终态使用同一运行ID |
| GET /agent-strategies/runs/{id}/scores | 已成熟的影子研究成绩 |
| GET /agent-strategies/runs/{id}/files/{name}；/file-info/{name} | 白名单只读HTML/JSON/模型产物及CLI文本/链接 |

普通模型生成使用文本ReAct与json_repair，不要求function calling或结构化输出。API/既有Codex后端、角色模型与总调用预算在配置中冻结。写接口核查网页同源；缺资料、未成熟、负效用、失败与取消不转成成功配资。组合接口增加agent_documents_dataset_id、agent_strategy_options以及显式research模式，沿用Portfolio/Risk与严格决定回放，不把今天生成的历史研究伪装当时决定。

## 工作台对话的后端与访问权限

2026-10-28按25号设计扩展既有ai-workspace消息及SSE接口，路径和会话/附件契约不变。消息新增可选access_mode，只允许read-only或workspace-write，缺省只读；不支持的后端/权限或推理组合在写消息前拒绝。流式端点先校验，再建立SSE，非法权限使用既有业务错误码，不在流已打开后才抛异常。

backend支持generic_agent、codex、qoder及原别名；qorder/qodercli归一为qoder。模型API的model_id只查平台配置，CLI使用model_name，不把同名平台ID混入。后端、权限、模型和思考强度保留于消息元数据；过程事件保存实际公开CLI原始事件。认证缺失、不可用、超时与已完成区分，CLI未返回正文不得报对话成功。ai CLI命令同步access_mode字段，旧请求兼容默认只读。

## 全局提醒接口

2026-10-29按26号设计接入；前缀沿用api_prefix，写操作复用同源约束，无Origin的本地CLI客户端保持兼容。

| 接口 | 行为 |
| --- | --- |
| GET /notifications/config | 有界公开显示参数、界面文案及已校验本地助手素材，无凭据 |
| GET /notifications | client_id为UUID，after增量游标、before历史分页、initial首次获取；返回列表、新事件、未读、严重摘要、范围提示和后续游标 |
| POST /notifications/{id}/state | client_id加read/dismiss操作，只更新该浏览器客户端显示状态 |
| POST /notifications/read-all | 将该客户端所有可见记录标为已读，包含当前页之外；不解决真实告警 |

没有提供任意网页发布告警、运行命令或解除风控的API。来源只消费既有本地记录与健康状态，模型/行情不会为通知而被调用；AI报告在终态保存后尽力发布，通知失败不使原报告保存失败。列表/增量有界，未解决严重项不被普通保留期隐藏。

## Optional SAG retrieval

`GET /api/v1/kb/retrieval/status` returns safe configuration readiness without contacting providers. `POST /api/v1/kb/sag/sync` indexes only the selected library or document and current attachment session, with bounded batches and same-origin write validation. Existing `POST /kb/qa` accepts optional `document_id`, `retrieval_backend` and `retrieval_strategy`; omitted values preserve local library behavior. Responses add actual backend/strategy and fallback reasons while keeping local original-source references. Foreign source IDs or evidence that does not match current originals fail closed. Single-document history has an independent scope.
