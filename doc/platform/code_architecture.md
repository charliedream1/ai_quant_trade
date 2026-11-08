# AIQuant智投 一体化量化交易平台 - 代码架构设计文档

2026-10-30实施增量以[28号设计](../security/code_health_security_concurrency_design.md)为准：核心安全/网络/凭据/租约模块独立，模型配置和知识操作供API与Gradio共享；FrontendService兼容入口保留，默认按回调所属领域惰性构建。AI区域/事件、主题资源、图谱构建与数据库迁移拆分，图形布局和事件证据下沉strategy/composition。当前完整业务源码类型检查不以全局Any忽略替代，可选库仅补已用接口声明；egs/entrypoints/check_quality.py提供项目内质量门禁。既有目录树和接口数量为历史规划，不代表当前精确清单。

> 本文档承接《01_overview.md》（八大分层/技术选型/目录规划）、《02_backend_design.md》（各模块后端设计）、《03_frontend_design.md》（模块化 Gradio 页面、回调服务与 AI 悬浮窗）、《04_database_design.md》（44 张业务表 + 3 张 FTS5 虚拟表）、《05_api_design.md》（130 个 REST 接口 + 单端点 WebSocket 主题订阅）的既定术语与约定，描述代码层面的组织方式。
>
> 路径约定：REST 接口前缀与 WebSocket 端点以《05_api_design.md》为准（/api/v1 与单一 /ws）；数据库表名以《04_database_design.md》为准；前端导航以《03_frontend_design.md》左侧边栏为准。

---

## 1. 代码架构总览

### 1.1 仓库组织（单仓 monorepo）

单一仓库同时容纳后端、前端、数据、文档与示例配置，与《01_overview.md》第 6 章规划一致，并补充工程化配套目录：

```
AIQuant智投/
├── src/                        后端源代码（八大分层，Python 3.10+，文件级规划见 2.1）
├── src/frontend/               模块化 Gradio 前端源代码（文件级规划见 3.1）
├── src/help_docs/              MkDocs 帮助文档构建、挂载与 Gradio iframe 辅助
├── doc/                        设计文档（01_overview ～ 06_code_architecture，共 6 份）
├── docs/usage/                 使用文档与操作截图
├── docs/principles/            原理文档；MkDocs 按两类导航构建
├── egs/                        样例配置与运行入口
│   ├── config.example.yaml     配置样例（四级配置中 YAML 层的模板，含全部可配置项注释）
│   └── strategy_examples/      统一策略接口示例策略（供上传校验与 CLI 生成的参照）
├── data/                       运行时数据（目录规划与《04_database_design.md》1.2 一致）
│   ├── all_in_one.db           SQLite 单文件（业务表 + FTS5 虚拟表 + 索引 + 触发器）
│   ├── strategies/             策略代码文件存储（upload/ 上传归档、cli_generated/ CLI 产物）
│   ├── knowledge/              知识库文档存储（notes/ 笔记、documents/ 上传文档、papers/ 论文 PDF、reports/ 研报 PDF）
│   ├── reports/                报告产物（backtest/ 回测明细与绩效、model/ 模型市场分析报告）
│   ├── help_site/              MkDocs 构建产物（运行时生成，不提交）
│   ├── logs/                   运行日志（loguru 按天轮转；CLI 会话日志、实盘运行日志子目录）
│   └── backup/                 数据库与文件存储的手动/定时备份产物
├── tests/                      测试代码（pytest 单测、集成测试与 Gradio 挂载冒烟）
├── pyproject.toml              后端项目配置（依赖锁定 + ruff/mypy/pytest 工具链，风格对齐 a001_news_track）
├── README.md                   项目说明
└── .gitignore                  版本忽略（data/ 运行时数据、密钥文件、本地缓存等）
```

要点说明：

| 项 | 约定 |
|----|------|
| 单仓单进程交付 | 前端构建产物由 FastAPI 静态托管（01 §7.2），仓库内无需独立前端部署单元 |
| data/ 不入版本库 | 运行时数据目录整体忽略，仅保留目录结构与 .gitkeep；备份产物亦不提交 |
| 密钥不落仓 | AES 加密密钥来自环境变量或本地密钥文件（04 §6.5），任何配置样例中凭证字段留空 |
| tests/ 与源码同仓 | 后端和模块化 Gradio 前端统一使用 pytest；前端重点覆盖独立挂载、懒构建、组件预算、回调服务和页面工作流 |

### 1.2 分层依赖规则

后端八大分层与依赖方向总览（层名与《01_overview.md》§3.2 一致）：

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  API 层  src/api/      routes/（REST） │ ws_hub（WS 主题） │ schemas │ deps │
├─────────────────────────────────────────────────────────────────────────────┤
│  智能层  src/agent/    llm_client │ generic_agent_runtime │ rag（按序：分析/推荐/策略生成） │
├─────────────────────────────────────────────────────────────────────────────┤
│  引擎层  src/engine/   market/ │ backtest/ │ paper/ │ live/（互相不直接依赖）│
├─────────────────────────────────────────────────────────────────────────────┤
│  策略层  src/strategy/ strategy_base │ registry │ uploader │ cli_builder     │
├─────────────────────────────────────────────────────────────────────────────┤
│  任务层  src/scheduler/ scheduler │ registry │ executor │ jobs/（调度触发方）│
├─────────────────────────────────────────────────────────────────────────────┤
│  集成层  src/integration/ mcp_client │ remote_sources/ │ broker/ │ cli_runner│
├─────────────────────────────────────────────────────────────────────────────┤
│  数据层  src/data/      DataSourceManager │ 四类数据源（行情/新闻/研报/论文）│
├─────────────────────────────────────────────────────────────────────────────┤
│  核心层  src/core/      config │ logger │ exceptions │ cache │ database │ …  │
└─────────────────────────────────────────────────────────────────────────────┘

依赖方向（默认自上而下，例外见规则表 R7）：
  API ──→ 智能层 / 引擎层 / 策略层 / 任务层 / 数据层 / 集成层 / 核心层
  引擎层 ──→ 策略层 / 数据层 / 智能层 / 集成层（实盘经 broker 适配器）
  智能层 ──→ 集成层（Skill 绑定 MCP 工具）/ 核心层
  策略层 ──→ 集成层（CLI 构建器子进程）/ 核心层
  集成层 ──→ 数据层（远程文档拉取后落库）/ 核心层
  数据层 ──→ 核心层
  所有层 ──→ 核心层（配置/日志/异常/存储为公共底座）
```

分层依赖规则表（与《02_backend_design.md》§1.3 层间调用约定一致）：

| 编号 | 规则 | 说明 |
|------|------|------|
| R1 | 仅允许上层依赖下层 | import 方向必须与上图箭头方向一致；API 层为唯一编排出入口，可按需直调任意下层 |
| R2 | 同层禁止横向 import | 同层模块间不直接依赖，经核心层事件总线（core/events）或 API 层编排解耦；引擎层五大引擎（market/backtest/paper/live 及其子引擎）互相不直接依赖，实盘引擎对模拟盘引擎的调用经集成层 broker 模拟适配器间接完成 |
| R3 | 下层禁止反向依赖上层 | 下层需要与上层协作时，通过回调函数或注入的上下文对象间接完成（如策略统一接口的上下文注入，02 §3.2） |
| R4 | 集成层只出不进横扩 | 集成层被 API 层、智能层、引擎层（实盘）、策略层（CLI 构建器）调用，自身仅依赖数据层与核心层，不得调用引擎层/智能层 |
| R5 | 数据层不感知业务 | 数据层只提供统一数据模型与多源 fallback，不包含任何策略/回测/交易语义；业务计算一律在引擎层 |
| R6 | 核心层零业务 | 核心层不 import 任何其他层，是纯基础设施 |
| R7 | 任务层反向调用例外 | 任务层虽位于策略层之下，但作为周期性调度触发方，允许调用引擎层/数据层/策略层执行体（02 §1.2"反向调用引擎层/数据层"）；该调用只能经 scheduler/registry 注册表按任务类型间接解析，jobs/ 执行体不得被其他层 import |
| R8 | 循环依赖零容忍 | ruff 的循环依赖检查纳入 CI，出现即构建失败 |

### 1.3 命名与编码约定

| 对象 | 约定 | 示例 |
|------|------|------|
| Python 包/模块名 | 全小写下划线 | `strategy_registry.py`、`paper_accounts.py` |
| Python 类名 | PascalCase | `DataSourceManager`、`BacktestRunner` |
| Python 函数/变量 | 小写下划线 | `fetch_news`、`retry_times` |
| Python 常量 | 全大写下划线 | `DEFAULT_PAGE_SIZE` |
| Pydantic 请求模型 | 资源名单数 + 动作后缀 | `StrategyCreate`、`StrategyUpdate`、`BacktestCreate`、`JobQuery` |
| Pydantic 响应模型 | 资源名单数 + Item/Detail/Page 后缀 | `NewsItem`、`StrategyDetail`、`BacktestPage`；分页结构统一复用 `common.py` 中的通用分页容器 |
| Pydantic 枚举字段值 | 与 04 §6.6 状态机枚举逐字一致 | 策略状态：草稿/可用/停用；委托状态：待撮合/部分成交/已成交/已撤销/已拒绝 |
| 路由文件名 | 资源复数名词、小写下划线（与 05 路径资源对应） | `paper_accounts.py` 对应 /api/v1/paper-accounts |
| 数据库表名 | 小写下划线（以 04 命名为准） | `paper_nav_history`、`kb_document_chunks_fts` |
| Gradio 组件变量 | 小写下划线，按页面语义命名 | `stock_symbol`、`relation_plot` |
| 回调服务函数 | 小写下划线，输入输出与 Gradio 组件绑定保持一致 | `relations`、`cli_build` |
| 页面状态 | 持久状态落 SQLite/文件存储，轻量浏览器状态落 localStorage | AI 悬浮按钮位置 |
| 前端服务适配 | `src/frontend/services.py` 方法与领域服务/路由能力对应 | `FrontendService.cli_build` 对应 CLI 会话 |
| SCSS/工具文件 | 小写下划线 | `variables.scss`、`datetime.js` |
| WS 主题名 | 与 05 §3.4 主题表逐字一致 | `market`、`notify`、`backtest:{task_id}`、`cli:{session_id}` |
| 注释语言 | 后端中文 docstring 说明职责与入出参；前端组件顶部注释用途 | — |
| 类型注解 | 后端全量注解（mypy strict 检查公共模块）；前端可用 JSDoc 注记 | — |

---

## 2. 后端代码架构

### 2.1 目录结构（文件级）

在《01_overview.md》第 6 章八目录规划基础上细化到 .py 文件；各包 `__init__.py` 统一略去不列。

```
src/
├── main.py                              进程入口：读取启动参数、调用应用工厂创建应用、uvicorn 启动引导
│
├── core/                                核心层 —— 基础设施公共底座（零业务依赖）
│   ├── config.py                        配置管理：默认值→YAML→环境变量三级合并、运行时设置对象
│   ├── system_settings.py               全局设置读写：分组字段、来源识别、YAML 持久化、存储选型摘要
│   ├── logger.py                        日志系统：loguru 初始化、按天轮转、级别控制、关键业务埋点封装
│   ├── exceptions.py                    异常体系：错误码枚举（对齐 05 §4.2）、业务异常基类与子类层次
│   ├── cache.py                         TTL 缓存：线程安全、键规范、容量与过期策略、命中统计
│   ├── database.py                      存储管理：SQLite 连接、WAL 模式、写串行化、外键开关、建表迁移
│   ├── market_lake.py                   Parquet 行情湖与 DuckDB 查询入口：列式落盘、查询状态、可选依赖诊断
│   ├── repository.py                    Repository 基类：通用 CRUD、分页查询、事务上下文，供各层仓储继承
│   ├── fts.py                           FTS5 管理：虚拟表与触发器同步、MATCH 检索、LIKE 兜底合并
│   ├── file_storage.py                  文件存储：data/ 目录读写、相对路径管理、路径穿越校验
│   ├── crypto.py                        敏感信息加解密：历史 api_key 迁移兼容、连接凭证 AES 加密、脱敏输出
│   ├── events.py                        进程内事件总线：发布订阅（模型配置变更、数据源状态变化等事件）
│   └── timeutil.py                      时间工具：UTC 存储、ISO 8601 序列化、交易日历判断
│
├── data/                                数据层 —— 四类数据源多源 fallback 统一供给
│   ├── base.py                          数据源基类：四类方法族统一签名、源元信息（名称/类型/优先级）声明
│   ├── manager.py                       DataSourceManager：优先级 fallback、失败冷却、健康检查、切换事件上报
│   ├── cache.py                         数据缓存装饰器：按"类别+参数摘要"生成缓存键、TTL 表驱动（对齐 02 §2.1 缓存策略）
│   ├── models.py                        统一数据模型：行情/新闻/研报/论文的 Pydantic 出参模型（源无关）
│   ├── health.py                        数据源健康状态：状态记录、冷却剩余时间、健康摘要查询（供 /api/v1/health）
│   ├── quotes/                          行情数据源族
│   │   ├── eastmoney_source.py          东方财富 push2 源：实时行情/K 线（盘中主源）
│   │   ├── akshare_source.py            AKShare 源：指数/板块/K 线/财务/涨跌榜（备源与统计口径）
│   │   └── baostock_source.py           BaoStock 源：历史 K 线全量补源（回测数据基础）
│   ├── news/                            新闻数据源族
│   │   ├── akshare_source.py            AKShare 新闻源：国内/国外财经、财联社电报
│   │   └── eastmoney_source.py          东方财富资讯源：快讯、个股资讯（公司新闻）
│   ├── reports/                         研报数据源族
│   │   └── eastmoney_source.py          东方财富研报中心源：研报元数据（标题/机构/评级/目标价）
│   └── papers/                          论文数据源族
│       ├── arxiv_source.py              arXiv q-fin 源：关键词/分类检索、元数据抽取
│       └── ssrn_source.py               SSRN 源：量化论文增量抓取（扩展源机制示例）
│
├── strategy/                            策略层 —— 策略资产管理与 AI 辅助生成编排
│   ├── strategy_base.py                 统一策略接口：元信息契约（name/version/params/uni/desc）+ 生命周期方法声明（02 §3.2）
│   ├── strategy_registry.py             策略注册中心：按策略 id+版本加载代码、实例化、执行上下文注入、运行缓存
│   ├── strategy_uploader.py             策略上传：接收 .py/.zip、七步校验链（接收→解压→安全→接口→参数→入库→报告）
│   ├── validator.py                     契约校验器：安全黑名单扫描/接口完整性/参数定义合法性，上传与 CLI 产物共用
│   ├── strategy_store.py                策略库仓储：strategies 表 CRUD、版本文件落盘（data/strategies/）、checksum
│   └── cli_builder.py                   CLI 构建器：trae/workbuddy/codex 会话编排、产物扫描、复用校验链入库（草稿态）
│
├── engine/                              引擎层 —— 五大业务引擎（子包间禁止互相 import，见 R2）
│   ├── market/                          市场分析引擎
│   │   ├── news_aggregator.py           新闻聚合：四类新闻去重入库编排、双模式分析（jieba TF-IDF / LLM 降级）
│   │   ├── quote_service.py             行情服务：指数/板块/热力图聚合、自选行情批量、market 主题推送帧组装
│   │   ├── relation_graph.py            关联关系：四类边构建（板块成分/产业链/概念/共现）与图扩散查询（stock_relations 表）
│   │   ├── resource_pool.py             资源池：手工/CSV/Excel 标的导入、资源池列表和推荐候选沉淀
│   │   ├── stock_analyzer.py            个股分析：四维加权评分（趋势0.3/量能0.2/基本面0.3/舆情0.2）、风险扫描、LLM 点评
│   │   ├── recommender.py               股票推荐：双路径（quick 快速过滤 / deep LLM 精选）、候选池预处理、结果落库
│   │   ├── report_generator.py          模型市场分析报告：输入聚合（行情+板块+新闻+概况）→ LLM 生成 → model_reports 入库
│   │   └── paper_search.py              论文服务：多源检索编排、收藏与知识库导入联动（papers 表）
│   ├── backtest/                        回测引擎
│   │   ├── runner.py                    回测运行器：事件驱动主循环（行情注入→策略→信号→撮合→账户）、进度节流回调
│   │   ├── event.py                     事件序列构建：历史 K 线预加载、时间轴对齐、复权统一（BaoStock 主源/AKShare 补源）
│   │   ├── matcher.py                   回测撮合器：当 bar 收盘价（可配置次 bar 开盘）± 滑点、费率扣除
│   │   └── performance.py               绩效计算器：总/年化收益、最大回撤、夏普、索提诺、Calmar、胜率、盈亏比、基准对比
│   ├── paper/                           模拟盘引擎（paper trading）
│   │   ├── engine.py                    模拟盘引擎主循环：实时行情驱动、净值快照（盘中周期+收盘定例）、例行任务衔接
│   │   ├── matcher.py                   模拟撮合器：市价/限价触及成交、涨跌停限制、可选部分成交模式、费用扣减
│   │   ├── account.py                   账户管理：市价即时成交、限价待撮合、手动撮合、撤单、资金/持仓/T+1 可用数量（paper_accounts/paper_positions 表）
│   │   └── order_state.py               订单状态机：待撮合/部分成交/已成交/已撤销/已拒绝五态单向流转与守卫
│   └── live/                            实盘引擎
│       ├── runner.py                    实盘运行器：运行状态机（starting/running/paused/stopping/stopped/error）、启动门槛、心跳
│       ├── risk_controller.py           前置风控：六规则检查链（黑名单→资金足额→单笔限额→最大持仓→重复抑制→熔断）
│       └── channel.py                   通道事件：适配器状态查询、heartbeat/error 事件归一分发、异常冻结
│
├── agent/                               智能层 —— AI 能力供给
│   ├── llm_client.py                    LLM 客户端管理器：OpenAI 兼容多配置、用途分级（快速/深度/问答）、热切换、降级 fallback、调用统计
│   ├── prompts.py                       Prompt 模板管理：新闻分析/推荐精选/市场报告/RAG 问答/策略生成的模板集中维护
│   ├── analysis_agent.py                分析 Agent：新闻摘要与情绪、市场分析报告生成（走深度模型，失败降级）
│   ├── recommend_agent.py               推荐 Agent：候选标的批量深度精选、结构化 JSON 输出解析、Token 截断控制
│   ├── strategy_agent.py                策略生成 Agent：CLI 构建需求组装（需求+接口契约说明+输出约定）、产物预期描述
│   └── rag.py                           RAG 问答管线：检索→上下文拼装（8K 预算截断）→生成（约束引用来源）→降级纯检索
│
├── scheduler/                           任务层 —— 周期性调度
│   ├── runtime.py                       调度器封装：APScheduler 优先、线程轮询兜底、应用生命周期启停、表驱动热重载
│   ├── cron.py                          Cron 校验和下次执行时间计算，APScheduler 缺包时提供轻量解析
│   ├── executor.py                      执行器：CRUD、同任务/互斥组互斥、手动/cron 触发、job_executions 历史记录
│   ├── jobs.py                          表驱动任务执行体：news_fetch、market_refresh、recommend、report、backtest、paper_check、calendar_refresh、calendar_reference_refresh、system_health_check、data_maintain、kb_sync
│   ├── registry.py                      自定义执行体白名单注册：executor_key → 项目内 Python 函数
│   └── process_runner.py                调度任务子进程执行器：timeout_mode=process 硬超时终止
│
├── integration/                         集成层 —— 外部系统连接
│   ├── mcp_client.py                    MCP 客户端：stdio/http 请求级探测与调用、失败冷却、工具枚举与调用；长连接池复用待增强
│   ├── cli_runner.py                    CLI 子进程管理：trae/workbuddy/codex 可执行检测、独立工作目录、流式读行、超时强杀、并发上限
│   ├── skill_manager.py                 Skill 管理：skills 表注册表、params_schema 校验、手动执行入口、MCP 工具绑定
│   ├── remote_sources/                  远程知识源统一抽象
│   │   ├── base.py                      远程源基类：connect/list_nodes/search/fetch_doc/disconnect 统一契约与动作权限
│   │   ├── feishu_source.py             飞书文档源：经 MCP 连接飞书、文档树列举、拉取转 Markdown、动作权限白名单
│   │   └── ima_source.py                腾讯 ima 源：经 MCP 连接 ima、检索与拉取、导入本地知识库
│   └── broker/                          券商适配器（预留扩展点）
│       ├── __init__.py                  适配器常量和注册表导出
│       └── adapters.py                  适配器注册表：paper 可用、broker 预留不可用、支持 heartbeat/error 事件声明
│
└── api/                                 API 层 —— 系统唯一出入口
    ├── app.py                           应用工厂：create_app 装配、生命周期管理（启动/停机顺序）、Gradio 挂载、帮助文档静态挂载与静态资源缓存
    ├── ws_hub.py                        WebSocket 主题订阅管理：单一 /ws 端点、订阅表、心跳/空闲超时、六类主题分发
    ├── errors.py                        全局异常处理：业务异常→统一信封（code/message/data）、HTTP 200 原则、错误码映射
    ├── deps/                            依赖注入
    │   └── services.py                  服务提供者：各层服务单例的构造与缓存，路由函数经 Depends 注入
    ├── routes/                          REST 路由（按功能模块划分，共 25 文件对应 130 接口，见 2.9 路由表）
    │   ├── news.py                      新闻与舆情（2 个）
    │   ├── market.py                    行情看盘：指数/板块/热力图（3 个）
    │   ├── watchlist.py                 自选管理：分组与成员（7 个）
    │   ├── relations.py                 关联关系图（1 个）
    │   ├── stocks.py                    个股详情聚合（1 个）
    │   ├── recommend.py                 股票推荐任务（3 个）
    │   ├── reports.py                   研报列表详情 + 模型市场分析报告（5 个）
    │   ├── papers.py                    论文搜索、收藏与导入知识库（4 个）
    │   ├── strategies.py                策略库 CRUD/启停/参数定义（8 个）
    │   ├── cli_sessions.py              CLI 构建会话（4 个）
    │   ├── backtests.py                 回测任务（7 个）
    │   ├── paper_accounts.py            模拟盘账户/下单/手动撮合/委托/成交/持仓/净值（10 个）
    │   ├── live_configs.py              实盘配置 CRUD 与风控参数（6 个）
    │   ├── live_runs.py                 实盘启停/状态/委托/持仓（5 个）
    │   ├── kb_local.py                  本地知识库：分类/文档/笔记/检索/问答（11 个）
    │   ├── kb_remote.py                 远程知识库：源管理/测试/文档/拉取（7 个）
    │   ├── jobs.py                      定时任务管理与执行历史（9 个）
    │   ├── settings.py                  系统设置读写、环境变量校验和单项删除（4 个）
    │   ├── llm_models.py                LLM 模型管理（6 个）
    │   ├── mcp_servers.py               MCP 服务管理（8 个）
    │   ├── skills.py                    Skill 管理（4 个）
    │   └── system.py                    通用：健康检查/系统信息（2 个）
    └── schemas/                         Pydantic 模型（按模块组织，见 2.9）
        ├── common.py                    统一信封结构、分页结构（items/page/page_size/total）、通用枚举
        ├── market.py                    市场分析模块请求/响应模型（新闻/行情/自选/关系/个股/推荐/研报/论文）
        ├── strategy.py                  策略构建模块模型（策略元信息/参数定义/CLI 会话）
        ├── simulation.py                策略仿真模块模型（回测任务/绩效/曲线/模拟盘账户/委托/成交/持仓）
        ├── live.py                      实盘模块模型（配置/风控/运行状态/委托/持仓）
        ├── knowledge.py                 知识库模块模型（分类/文档/检索命中/问答/远程源）
        ├── scheduler.py                 定时任务模块模型（任务定义/cron 校验/执行历史）
        └── settings.py                  模型配置模块模型（系统设置/LLM 模型/MCP 服务/Skill）
```

### 2.2 核心层模块表

| 模块文件 | 核心类/组件 | 职责 | 被谁使用 |
|----------|-------------|------|----------|
| `config.py` | Settings（配置模型） | 默认值→YAML→环境变量三级合并，提供数据目录、SQLite 主库、文档目录、Parquet 行情湖、DuckDB 路径、网络超时和缓存 TTL 等运行配置 | 所有层启动时 |
| `system_settings.py` | GlobalSettingField、全局设置服务 | 系统设置页字段定义、当前值来源识别、YAML 持久化、存储选型摘要；局部参数不进入全局设置 | API 设置路由、前端系统设置页 |
| `logger.py` | Logger（日志门面） | loguru 初始化（按天轮转、保留天数、级别）、关键埋点辅助方法 | 所有层 |
| `exceptions.py` | ErrorCode（错误码枚举）、AppError 及子类 | 错误码分段枚举（0/1xxx/2xxx/3xxx/4xxx/5xxx，对齐 05 §4）、业务异常基类（携带 code 与 message） | 所有层抛出；仅 API 层统一捕获转换 |
| `cache.py` | TTLCache | 线程安全 TTL 缓存、容量上限与淘汰、命中/未命中统计 | 数据层缓存装饰器、引擎层结果缓存、API 层读缓存 |
| `database.py` | Database（存储管理器） | SQLite 连接供给、WAL 模式与 busy_timeout、写事务串行化队列、外键开关、建表与迁移执行 | 各层仓储（经 Repository） |
| `market_lake.py` | MarketDataLake | 将行情/因子面板写入 Parquet，并在 duckdb 可用时执行本地查询；缺依赖时返回明确配置依赖错误，不影响 SQLite 主库启动 | 数据层、回测/因子后续面板、系统设置状态 |
| `repository.py` | Repository 基类 | 通用 CRUD、分页查询（page/page_size/total）、事务上下文管理 | strategy_store、jobs 历史仓储、kb 文档仓储等各层仓储类 |
| `fts.py` | FtsIndex（全文检索器） | news_items_fts/kb_documents_fts/kb_document_chunks_fts 触发器同步管理、MATCH 检索、LIKE 兜底、知识库 `local/remote/all` 来源过滤与来源标识；知识库优先检索分块，未命中再退回整篇 | 新闻检索、知识库检索（本地、远程已入库与混合） |
| `file_storage.py` | FileStorage | data/ 各子目录读写、相对路径登记、路径穿越与类型白名单校验 | 策略层版本文件、知识库文档、报告产物、日志归档 |
| `kb_chunks.py` | 知识分块器 | Markdown 风格正文按标题、段落和长度切分，刷新 kb_document_chunks，并为旧文档提供轻量回填 | 本地上传、笔记、论文导入、远程知识源、FTS/RAG |
| `kb_importer.py` | 知识文档导入器 | 上传文件大小/扩展名校验、UTF-8/GB18030 解码、HTML 文本化、文本层 PDF 提取、DOCX 段落/表格提取、Markdown 落盘、kb_documents 入库并刷新文档分块 | 本地知识库上传、前端上传回调、FTS/RAG 入库 |
| `crypto.py` | SecretCrypto | 历史 llm_models.api_key 迁移兼容、remote_sources/mcp_services 凭证字段加解密、脱敏输出 | 智能层配置读取、集成层连接建立、模型配置路由回显 |
| `events.py` | EventBus | 进程内发布订阅：模型配置变更（触发客户端懒重建）、数据源状态变化（触发 notify 推送） | 智能层与 API 层订阅；数据层/模型配置发布 |
| `timeutil.py` | 时间工具集 | UTC 统一换算、ISO 8601 序列化（Z 结尾）、日期格式、交易日历判断 | 所有层时间处理（禁止各处手写格式化） |

### 2.3 数据层设计

#### 2.3.1 数据源基类约定（统一方法族签名）

数据源基类 `data/base.py` 定义四类方法族，所有数据源实现类（AKShare/东方财富/BaoStock/arXiv/SSRN 等）遵循同一签名，输入输出均为 `data/models.py` 统一模型（源无关），异常统一抛数据源异常（错误码 2xxx）：

| 方法族 | 统一方法名 | 输入 | 输出（统一模型） | 说明 |
|--------|-----------|------|------------------|------|
| 行情-指数板块 | get_indices / get_sector_quotes | 板块类型、条数 | 指数行情项列表、板块行情项列表 | 通用看盘与 market 主题推送数据源 |
| 行情-K 线 | get_kline | 标的、周期、起止日期、复权方式 | OHLCV 序列 | BaoStock 主源（历史回测）、东财/AKShare 补源 |
| 行情-个股快照 | get_stock_quotes / get_stock_detail | 标的代码数组 | 个股行情快照（最新价/涨跌幅/量额/换手） | 自选行情批量、模拟盘/实盘行情驱动 |
| 行情-财务统计 | get_financial / get_market_stats | 标的 / 无 | 财务摘要、市场概况统计 | 个股分析基本面评分、看盘市场概况 |
| 新闻-分类拉取 | fetch_news | 类别（国内/国外/财经）、分页 | 新闻项列表（标题/来源/链接/时间） | 定时采集与按需查询 |
| 新闻-公司新闻 | fetch_company_news | 标的代码、分页 | 新闻项列表 | 个股详情与公司新闻页 |
| 研报-列表检索 | fetch_reports | 关键词、标的、机构、分页 | 研报元数据项列表 | 研报中心页与个股研报卡 |
| 论文-检索 | search_papers | 关键词、来源、年份区间、排序、分页 | 论文元数据项列表 | 论文搜索页 |
| 元信息-能力声明 | source_meta | 无 | 源名称、数据类型集合、优先级、启用状态 | 供 Manager 装配 fallback 链 |

#### 2.3.2 各数据源实现模块

| 模块 | 数据类型 | 定位（对齐 01 §2.2/02 §2.1-2.2） | 备注 |
|------|----------|------|------|
| `data/quotes/eastmoney_source.py` | 行情 | 实时行情/K 线盘中主源（push2 直连） | 3~5 秒推送帧数据主力 |
| `data/quotes/akshare_source.py` | 行情 | 指数/板块/财务/涨跌榜备源与统计口径 | 失败自动冷却切换 |
| `data/quotes/baostock_source.py` | 行情 | 历史 K 线补源（回测数据基础） | 全量区间拉取、复权统一 |
| `data/news/akshare_source.py` | 新闻 | 国内/国外财经、财联社电报主源 | 类别栏目归类 + 关键词词表 |
| `data/news/eastmoney_source.py` | 新闻 | 快讯、个股资讯（公司新闻）主源 | 按需拉取 + 定时增量 |
| `data/reports/eastmoney_source.py` | 研报 | 东方财富研报中心源（复用 a001 扩展源思路） | 元数据入库供 FTS5 检索 |
| `data/papers/arxiv_source.py` | 论文 | arXiv q-fin 检索主源 | 关键词/分类/年份过滤 |
| `data/papers/ssrn_source.py` | 论文 | SSRN 扩展源 | 演示扩展源接入机制 |

#### 2.3.3 DataSourceManager：fallback 与健康检查

| 机制 | 设计约定 |
|------|----------|
| fallback 链装配 | 按"数据类型"分组装配有序源链（顺序来自 settings 的数据源优先级配置）；调用时依序尝试，首源成功即返回并记录命中源 |
| 失败冷却 | 源调用异常即记入冷却（默认 60 秒内跳过该源），冷却期内直接尝试下一源；全链失败抛数据源异常（2001/2002/2003 按类型） |
| 健康检查 | `data/health.py` 周期探活（任务层 data_maintain 驱动）+ 被动失败统计；健康摘要供 /api/v1/health 与前端状态条展示 |
| 状态事件 | 源切换/进入冷却/恢复均经核心层事件总线上报，由 ws_hub 转为 notify 主题 data_source 事件（05 §3.4.7） |
| 结果落库 | 新闻/研报/论文拉取结果按 04 约定入库（dedup_hash 唯一约束去重、FTS5 触发器同步），行情快照走缓存不入库 |

#### 2.3.4 数据缓存装饰器

| 项 | 约定 |
|----|------|
| 形态 | `data/cache.py` 提供缓存装饰器，标注在引擎层/数据层取数函数上 |
| 缓存键 | "数据类别 + 关键参数摘要"（如 类别+页码、标的+周期、类别+分析模式），与 02 §2.1 缓存策略表逐项对齐 |
| TTL | 表驱动：分类新闻 5 分钟、公司新闻 10 分钟、聚合分析 30 分钟、个股分析 10 分钟、K 线交易日内有效；可通过 settings 覆盖 |
| 旁路 | 请求带 refresh=true 时绕过缓存强制刷新（对齐 05 §2.1.2 行情接口约定） |

### 2.4 策略层设计

| 模块文件 | 职责 | 关键类/组件 | 依赖 |
|----------|------|-------------|------|
| `strategy_base.py` | 定义统一策略接口契约：元信息（name/version/params/uni/desc）与六个生命周期方法（on_init/on_bar/on_tick/generate_signals/on_risk_check/on_stop），签名与语义严格对齐 02 §3.2；策略对回测/模拟/实盘三种环境无感知（环境差异由引擎侧上下文注入承担） | 策略基类（统一接口契约）、执行上下文对象（行情馈送/账户接口/日志接口） | 核心层 |
| `strategy_registry.py` | 策略加载与注册：按策略 id+版本从版本目录装载代码、安全实例化、上下文注入、运行期实例缓存与失效；回测/模拟/实盘引擎统一经此获取策略实例 | 策略注册中心 | 核心层 file_storage、strategy_store |
| `strategy_uploader.py` | 上传校验入库：执行 02 §3.1 七步校验链（接收→解压展开→安全校验→接口校验→参数校验→入库落盘→校验报告），版本目录只写不改、checksum 记录 | 上传处理器 | validator、strategy_store、核心层 |
| `validator.py` | 契约校验器：危险调用黑名单扫描（系统命令/动态执行/网络后门）、统一接口完整性（元信息齐备+生命周期方法存在）、params 定义合法性；上传、CLI 产物、自研接入三入口共用，保证规格一致 | 校验链（安全→接口→参数） | strategy_base |
| `strategy_store.py` | 策略库仓储：strategies 表 CRUD（含状态机 草稿/可用/停用）、版本文件落盘（data/strategies/{策略}/{版本}/）、(name, version) 唯一约束、被引用停用保护 | 策略仓储 | 核心层 repository/file_storage |
| `cli_builder.py` | CLI 构建器：编排 trae/workbuddy/codex 构建会话（需求+契约说明+输出目录约定）、流式日志转 ws_hub 的 cli:{session_id} 主题、进程结束产物扫描、复用校验链后以草稿版本入库（cli_sessions 表，成功回填 strategy_id）；排队与并发上限（默认 1）、超时强杀 | CLI 构建器（会话状态机：进行中/成功/失败） | 集成层 cli_runner、validator、strategy_store、API 层 ws_hub |

### 2.5 引擎层设计

#### 2.5.1 market/（市场分析引擎）

| 文件 | 职责 | 关键类/组件 | 依赖 |
|------|------|-------------|------|
| `news_aggregator.py` | 四类新闻采集编排（多源拉取→主键/标题相似去重→入库）；聚合分析双模式：传统模式（jieba 分词+金融停用词+TF-IDF+行业同义词，零成本）与 LLM 模式（深度模型结构化输出，失败自动降级）；结果按"类别+模式"缓存 | 新闻聚合器、双模式分析器 | 数据层 news 源与缓存、智能层 analysis_agent、核心层 fts |
| `quote_service.py` | 指数/板块/热力图聚合查询；自选分组行情批量组装；market 主题推送帧组装（quote/index/sector/trade_notice 事件，3~5 秒批量合并）；交易时段判断与非交易时段停推 | 行情服务、推送帧组装器 | 数据层 quotes 源、核心层 cache/timeutil、API 层 ws_hub |
| `relation_graph.py` | 四类关系边构建（板块成分/概念归属每日全量、产业链人工映射版本管理、新闻共现 30 日滚动增量，先置 valid=0 再写新批次）；图扩散查询（一度/二度展开、节点分类着色与连接度定大小），输出 nodes/edges 结构 | 关系图构建器、图扩散查询器 | 数据层（成分/概念/新闻）、核心层（stock_relations 表）、任务层触发 |
| `stock_analyzer.py` | 个股全景分析：四维加权评分（趋势 0.3/量能 0.2/基本面 0.3/舆情 0.2）、风险扫描（涨跌幅≥8%、量比≥3、PE≥100、ST 分级告警）、子数据聚合降级（任一失败返回空结构标记缺失不阻塞）、可选 LLM 点评（失败静默降级） | 个股分析器、风险扫描器 | 数据层多类源、智能层、核心层 cache |
| `recommender.py` | 双路径推荐：quick 快速过滤（候选池预处理剔除 ST/停牌/次新 → 形态规则库（独立开关）→ 本地小模型轻量评分 → Top N）；deep 在 quick 基础上逐批 LLM 精选（评级/核心逻辑/风险提示/置信度）；LLM 全败降级返回 quick 结果并标注"未精选"；结果入 recommend_tasks/recommend_results | 推荐引擎、形态规则库、小模型评分器 | 数据层、智能层 recommend_agent、核心层存储 |
| `report_generator.py` | 模型市场分析报告：输入聚合（大盘行情+板块涨跌+新闻聚合+市场概况）→ 深度模型生成结构化报告（综述/多空研判/主线板块/风险提示）→ model_reports 入库与归档；支持手动触发与定时生成，结果缓存复用 | 报告生成器 | 数据层、智能层 analysis_agent、任务层触发 |
| `paper_search.py` | 论文检索编排：多源检索合并、收藏状态管理（papers.is_favorite）、一键将论文元数据与摘要写入 kb_documents；PDF 正文抽取作为后续增强 | 论文服务 | 数据层 papers 源、核心层 file_storage/kb_importer/logger |

#### 2.5.1.1 research/（投研服务）

| 文件 | 职责 | 关键类/组件 | 依赖 |
|------|------|-------------|------|
| `factor_monitor.py` | 因子定义同步、股票池 K 线归一化、RankIC/ICIR/分位收益/分层收益时序/相关性、前瞻周期 IC 衰减、稳定性、风格代理暴露与流动性容量代理计算、告警生成和 Qlib 环境状态输出 | FactorMonitorService | 数据层、核心层 repository、backtest.engines qlib 诊断 |
| `qlib_workflow.py` | Qlib 配置读取、pyqlib 环境诊断、workflow/backtest/factor 运行创建、qrun 调用、输出尾部回填、训练指标解析、组合回测指标解析、产物路径解析和 qlib_runs 留痕；未就绪时 blocked 留痕 | QlibWorkflowService | 核心层 repository、backtest.engines qlib 诊断、egs/qlib 配置、可选 qrun 命令 |
| `quant_workflow.py` | 量化闭环 SOP、证据快照、规则归因、智能问数、迭代建议和闭环运行落库；支持模拟研究闭环与真实交易观测闭环 | QuantWorkflowService | 核心层 repository、策略/回测/因子/模拟盘/实盘表 |

#### 2.5.2 backtest/（回测引擎）

| 文件 | 职责 | 关键类/组件 | 依赖 |
|------|------|-------------|------|
| `runner.py` | 回测任务门面：策略端口预检、策略加载、引擎选择、任务/结果落库、绩效/曲线/交易明细读取与归因摘要计算；API 和前端只依赖 Runner，不直接绑定具体回测库 | BacktestRunner | engines、策略层 store/loader、数据层 manager、核心层 repository |
| `strategy/models/` | 特征、成熟标签、日期切分、滚动拟合与截面预测；三个后端按需加载，上一交易日特征形成的决策在次日开盘执行 | ModelStrategy、FeatureRow | YAML、可选 LightGBM/XGBoost/PyTorch |
| `agent/research_team.py`、`research_protocol.py` | 四角色回测复核、只读证据工具、文本 ReAct、JSON 修复与引用校验、研究报告保存；不提供下单能力 | ResearchTeam | LLMClient、BacktestRunner、YAML、json_repair |
| `engines.py` | 回测引擎注册与诊断：内置 simple 日 K 事件回测、qlib 可选环境诊断、引擎 key 规范化和配置依赖错误；simple 负责 K 线事件驱动、long/flat 撮合、佣金滑点、资金/暴露曲线、交易成本和分组绩效计算；Qlib 只在产出逐日组合曲线时提供完整曲线，否则明确返回指标摘要 | SimpleBacktestEngine、QlibBacktestEngine | 核心层 exceptions、策略端口、数据层 manager、可选 qlib 环境 |
| `event.py` | 行情事件序列构建：按区间与标的池取历史 K 线（BaoStock 主源/AKShare 补源）、统一复权、多标的时间轴对齐、截止当 bar 的历史窗口供给 | 事件序列构建器 | 数据层 quotes 源 |
| `matcher.py` | 回测撮合：默认当 bar 收盘价（可配置次 bar 开盘价）± 滑点模拟成交、佣金与印花税扣除、成交明细记录 | 回测撮合器 | 核心层（Decimal 域资金计算） |
| `performance.py` | 绩效计算器：总收益率、年化收益率、最大回撤（含区间与持续天数）、夏普（无风险 2%）、索提诺、Calmar、胜率、盈亏比、交易统计、基准对比与超额收益 | 绩效计算器 | 核心层 |

#### 2.5.3 paper/（模拟盘引擎）

| 文件 | 职责 | 关键类/组件 | 依赖 |
|------|------|-------------|------|
| `engine.py` | 模拟盘主循环：实时行情驱动（行情推送→待成交委托撮合判定→策略 on_tick/周期 on_bar→信号→账户更新）；净值快照（盘中每 5 分钟+收盘定例）；paper:{account_id} 主题推送（order_update/fill/position_update/equity_update 事件） | 模拟盘引擎 | 数据层实时行情、matcher/account、策略层、API 层 ws_hub |
| `matcher.py` | 模拟撮合：市价单最新价全额成交、限价单触及即成交、可选成交量比例部分成交、涨跌停不成交保持待撮合、买卖前资金/持仓校验不足拒单、费用扣减 | 模拟撮合器 | account |
| `account.py` | 账户管理：市价即时成交、限价待撮合、手动撮合挂单、撤单、资金、持仓与 T+1 可用数量、委托-成交-持仓-净值联动更新（04 §6.7 事务约定） | 模拟账户（paper_accounts/paper_positions 表） | 核心层 repository/database、数据层行情 |
| `order_state.py` | 订单状态机：待撮合/部分成交/已成交/已撤销/已拒绝五态单向流转守卫（非法迁移抛 3xxx 业务异常）、状态变更时间回写 | 订单状态机 | 核心层 exceptions |

#### 2.5.4 live/（实盘引擎）

| 文件 | 职责 | 关键类/组件 | 依赖 |
|------|------|-------------|------|
| `runner.py` | 实盘运行器：基础状态机（starting/running/paused/stopping/stopped/error，已拦截重复启动、非法迁移和终态重复停止，展示层提供中文状态标签）；启动前校验发布证据、风控阈值和通道适配器可用性；心跳字段更新；异常冻结下单并告警 | 实盘运行器、运行状态机 | 策略层 registry、risk_controller、channel、集成层 broker、数据层、API 层 ws_hub |
| `risk_controller.py` | 前置风控检查链：黑名单→资金足额→单笔限额→最大持仓→重复信号抑制（60 秒窗口）→日内亏损熔断（默认 3%，熔断后冻结下单待人工恢复）；风控事件全部落库并推送；支持运行中热更新可热更项（单日亏损比例/最大持仓数），不可热更项返回 4004 | 风控检查链、熔断器 | 核心层存储与 exceptions |
| `channel.py` | 通道事件服务：读取适配器注册表，返回通道状态；接收 heartbeat 刷新心跳，接收 error 事件写入 `error` 冻结态并保留异常原因；终态运行拒绝写入事件 | `LiveBrokerEventService` | runner、集成层 broker |

### 2.6 智能层设计

| 模块文件 | 职责 | 关键类/组件 | 依赖 |
|----------|------|-------------|------|
| `llm_client.py` | LLM 客户端管理器：OpenAI 兼容接口封装（base_url/api_key_env/model_name 来自 llm_models 表，密钥从环境文件或进程环境解析且不落日志）；用途分级路由（快速/深度/问答 → settings 中的默认模型绑定）；热切换（订阅核心层"模型配置变更"事件，懒重建客户端实例，进程不重启）；调用失败按同用途其他启用配置 fallback，全部失败按调用方降级策略处理；调用统计（次数、成功失败、耗时和最近状态，供模型管理页） | LLM 客户端管理器、用途分级路由 | 核心层 config/env_file/events、数据库 llm_models 表 |
| `prompts.py` | Prompt 模板集中管理：新闻分析、推荐精选、市场分析报告、RAG 问答（含"仅依据给定资料回答并标注来源"约束）、策略生成等模板；模板变量占位与版本化管理 | Prompt 模板库 | 核心层 |
| `analysis_agent.py` | 分析 Agent：新闻 LLM 摘要与情绪结构化输出（快速模型）；模型市场分析报告生成（深度模型，结构化分节）；失败降级传统模式（新闻）或空报告标记（报告） | 分析 Agent | llm_client、prompts |
| `recommend_agent.py` | 推荐 Agent：候选标的输入组装（个股分析摘要+新闻情绪+板块热度，单标的 Token 截断）、分批（5~10 只/批）深度精选、结构化 JSON 输出解析与容错、全败降级返回 quick 结果 | 推荐 Agent | llm_client、prompts、引擎层 stock_analyzer 输出 |
| `strategy_agent.py` | 策略生成 Agent：CLI 构建需求组装（自然语言需求 + 统一策略接口契约说明 + 输出目录约定 + 参考策略），供 CLI 构建器组装子进程任务文件；产物预期校验说明生成 | 策略生成 Agent | prompts、策略层 strategy_base 契约文本 |
| `rag.py` | RAG 问答管线：问题解析（关键词、过滤条件和 session_id 识别）→ 分块优先的 FTS5 检索（无结果 LIKE 兜底，支持本地、远程已入库和混合范围）→ 当前追问无命中时使用同一会话最近问答回退检索 → 上下文拼装（会话内最近问答 + 资料片段按相关度截断，引用带 chunk/source_scope/source_name）→ LLM 生成（约束引用来源）→ 答案+引用清单按 session_id 落 kb_qa_history；同时维护 kb_qa_sessions 会话名称、摘要和最近活动时间；支持清空单个会话历史；LLM 不可用降级返回纯检索片段；支持流式（stream=true，SSE 分片） | RAG 管线 | 核心层 fts、llm_client、集成层 remote_sources、prompts |

### 2.7 任务层设计

| 模块文件 | 职责 | 关键类/组件 | 依赖 |
|----------|------|-------------|------|
| `runtime.py` | APScheduler 封装：进程内后台调度（随应用生命周期启停）；APScheduler 缺包时使用内置线程轮询兜底；启动时装载 enabled 任务，增删改后热重载 | 调度器封装 | executor、cron、核心层 repository/timeutil |
| `cron.py` | Cron 表达式校验和下次执行时间计算；优先使用 APScheduler CronTrigger，缺包时支持 5 段 cron 的轻量解析 | Cron 工具 | 核心层 exceptions/timeutil、可选 APScheduler |
| `jobs.py` | 任务类型执行体映射：news_fetch、market_refresh、recommend、report、backtest、paper_check、calendar_refresh、calendar_reference_refresh、calendar_announcement_profile_check、system_health_check、data_maintain、kb_sync；未支持类型尝试按 `executor_key` 走自定义 registry，仍未命中则记录为跳过，不伪造成功 | 任务执行体 | engine/market、engine/backtest、engine/paper、scheduler/calendar_updater、核心层 repository/FTS、registry |
| `calendar_updater.py` | 交易日历自动更新与健康告警：从 AKShare/Sina 或 inline 数据源生成紧凑 YAML 日历，写入项目内 calendar_path；可将人工日期或公告文本/项目内公告文件/指定公告 URL/公告列表页发现结果/项目内交易所公告源 profile 保守解析后写入官方参考 YAML；可只读核验 profile 文件、列表页可达性和关键词命中；输出状态摘要，并识别缺失、解析异常、过期、即将过期、更新时间偏久和官方参考 YAML 差异 | 交易日历更新器 | 核心层 config/timeutil、PyYAML、可选 AKShare |
| `registry.py` | 自定义执行体注册：从 `scheduler_executors_path` YAML 白名单读取 key 到模块/文件函数的映射，限制文件位于项目根目录内，执行结果标准化为调度历史摘要 | 自定义执行体注册器 | 核心层 config/logger、PyYAML、标准库 importlib |
| `process_runner.py` | 子进程隔离执行：使用 spawn 启动定时任务执行体，超时后 terminate/kill 子进程，结果通过队列回传主进程 | 调度子进程执行器 | 标准库 multiprocessing |
| `policies.py` | 调度策略：交易日过滤、YAML 交易日历文件加载、节假日/补班交易日参数覆盖、失败重试次数、指数退避、超时时间、超时执行模式和互斥组解析 | 调度策略 | 核心层 config、PyYAML、标准库 datetime/pathlib |
| `executor.py` | 执行器：任务 CRUD、同任务/互斥组互斥、手动/cron 触发、交易日过滤、失败重试、线程/进程超时、notify 推送、执行历史入 job_executions（成功/失败/跳过/超时、输出摘要、错误信息）；增删改启停后通知 runtime 热重载 | 任务执行器 | 核心层存储、runtime、jobs、policies、process_runner、api/ws_hub |

任务类型注册映射表（表驱动，与 scheduled_jobs.job_type 枚举对齐 04 §6.6）：

| job_type 枚举值 | 执行体模块 | 典型计划（02 §7.2） |
|-----------------|-----------|---------------------|
| news_fetch | `jobs.py:_run_news_fetch` | 交易日盘中每 10 分钟 |
| market_refresh | `jobs.py:_run_market_refresh` | 交易日 16:00 |
| report | `jobs.py:_run_report` | 交易日 08:30 与 16:30 |
| recommend | `jobs.py:_run_recommend` | 用户自定义 |
| backtest | `jobs.py:_run_backtest` | 策略版本或参数更新后定期复核 |
| paper_check | `jobs.py:_run_paper_check` | 交易日 09:15 / 盘中每 5 分钟 / 15:30 |
| calendar_refresh | `jobs.py:_run_calendar_refresh` | 每周日 05:10 更新项目内交易日历 YAML |
| calendar_reference_refresh | `jobs.py:_run_calendar_reference_refresh` | 按人工日期、本地公告、指定公告 URL、公告列表页发现结果或交易所公告源 profile 生成项目内官方参考交易日历 YAML |
| calendar_announcement_profile_check | `jobs.py:_run_calendar_announcement_profile_check` | 只读检查交易所公告源 profile 的列表页可达性、关键词命中数和候选链接 |
| system_health_check | `jobs.py:_run_system_health_check` | 每个交易日上午检查交易日历健康状态，可选对比官方参考 YAML，发现异常时向 `notify/system_alert` 推送告警 |
| data_maintain | `jobs.py:_run_data_maintain` | 新闻/远程缓存/问答历史保留期清理、执行历史裁剪、FTS 对账修复、SQLite checkpoint/optimize，可选裁剪回测、Qlib 和闭环流程历史 |
| kb_sync | `jobs.py:_run_kb_sync` | 每周日 03:00 索引重建；远程源状态同步 |
| custom | `registry.py:CustomExecutorRegistry` 按 executor_key 白名单加载 | 用户自定义 |

定期回测（backtest 类型）经 `jobs.py:_run_backtest` 执行体按参数快照重跑，归入"自定义"之外的单列类型，映射表同步登记。自定义执行体不允许任意文件路径扩散，必须先在 YAML 白名单中登记，任务参数用 `executor_key` 选择。长任务需要硬超时时可显式配置 `timeout_mode=process` 或 `hard_timeout=true`，默认线程模式仍以标记和通知为主。

### 2.8 集成层设计

| 模块文件 | 职责 | 关键类/组件 | 依赖 |
|----------|------|-------------|------|
| `mcp_client.py` | MCP 客户端：配置 stdio/http/sse 传输探测与单次调用；stdio 执行 initialize/tools-list/tools-call 握手，http 执行带会话头的 JSON-RPC 探测与工具调用，sse 执行可达性检查；保存最近探测、调用摘要、工具摘要和失败冷却状态，冷却期内短路重复重试供 API 与前端查询 | MCP 探测与调用器 | 核心层 config、Repository、requests、标准库 subprocess |
| `remote_sources/base.py` | `RemoteSourceAdapter`：解析 mcp_server_id、tool_map、base_arguments、argument_map，调用 MCP 工具并归一化列表/正文返回；list/search/fetch/import 允许，write/move 不开放；凭证配置脱敏 | 远程源统一适配器 | mcp_client、核心层 exceptions/repository |
| `remote_sources/service.py` | 远程源 CRUD、真实探测、列表/关键词检索、当前结果限量批量同步、remote_docs_cache 缓存、Markdown 文件落盘、kb_documents/kb_document_chunks/FTS5 幂等导入和状态更新 | 远程知识源服务 | base、核心层 repository/file_storage/kb_chunks |
| `broker/adapters.py` | 券商适配器注册表：声明 `paper` 模拟通道可用、`broker` 真实券商通道预留不可用；输出适配器状态、启动拦截原因和支持事件类型 | `BrokerAdapterRegistry` | 核心层 |
| `cli_runner.py` | CLI 子进程管理：trae/workbuddy/codex 可执行路径检测（CLI 可用性状态）；每次构建独立临时工作目录隔离产物；命令行参数与任务文件组装；标准输出按行流式读取回调（供 cli_builder 转 WebSocket）；超时强杀（默认 30 分钟）与非零退出处理；并发上限控制 | CLI 子进程运行器 | 核心层 config/file_storage |
| `skill_manager.py` | Skill 管理：skills 表注册表维护、内置 Skill schema 补齐、参数类型与范围校验；提供 API/前端手动运行入口，内置 `news_summary` 读取本地新闻快照，未接入执行器的 Skill 返回 blocked，不伪造成功 | Skill 注册表与执行入口 | 核心层、engine/market、mcp_client（后续工具绑定） |

> 说明：当前 `broker/adapters.py` 不直接 import 引擎层模块，只暴露注册表、状态和事件类型；后续接真实下单或模拟撮合适配器时，仍需经 `live/channel.py` 装配，避免 broker 模块反向依赖 engine。

### 2.9 API 层设计

#### 2.9.1 应用工厂与生命周期

| 项 | 约定 |
|----|------|
| 应用工厂 | `api/app.py` 提供 create_app：装配 `/api/v1` 路由、异常处理器、`/ws`、静态资源、帮助文档、九个 `/app/<module>` 延迟 Gradio 挂载和 `/app/` 持久工作台；根路径跳转 `/app/` |
| 启动顺序 | ① Config 与 Logger 初始化 → ② 文件存储和 Database 初始化 → ③ API、WebSocket、静态资源与帮助文档注册 → ④ 先注册九个模块和兼容页面，再注册父级工作台延迟 ASGI 包装器，不构建 Blocks → ⑤ 生命周期启动调度器；首次访问工作台或模块时只构建对应应用，并在当前事件循环启动队列一次 |
| 停机顺序 | 已启动的 Gradio 模块队列逐个关闭 → 调度器优雅停机（等待在执行任务收尾或按超时放弃）→ ws_hub 广播断开 → 数据库写队列排空 → 日志 flush；未访问模块不执行队列关闭 |
| 单例管理 | deps/services.py 持有各层服务单例（懒构造 + 缓存），保证单进程内 DataSourceManager、调度器、ws_hub 等唯一实例 |

#### 2.9.2 routes/ 路由文件划分表（130 接口 ↔ 25 文件）

| 路由文件 | 所属模块 | 覆盖接口（05 章节） | 接口数 |
|----------|----------|---------------------|--------|
| `news.py` | 市场分析 | 2.1.1 新闻与舆情（GET /news、GET /news/keyword-cloud） | 2 |
| `market.py` | 市场分析 | 2.1.2 行情看盘（indices/sectors/heatmap） | 3 |
| `watchlist.py` | 市场分析 | 2.1.5 自选管理（分组 CRUD、自选行情、成员增删） | 7 |
| `relations.py` | 市场分析 | 2.1.6 关联关系图数据 | 1 |
| `stocks.py` | 市场分析 | 2.1.6 个股详情聚合 | 1 |
| `recommend.py` | 市场分析 | 2.1.7 推荐任务创建/状态/结果 | 3 |
| `reports.py` | 市场分析 | 2.1.8 研报列表/详情 + 模型分析报告生成/列表/详情 | 5 |
| `papers.py` | 市场分析 | 2.1.9 论文搜索/收藏/取消收藏/导入知识库 | 4 |
| `factors.py` | 市场分析 | 2.1.3 因子监控与 Qlib 状态 | 3 |
| `qlib_workflows.py` | 市场分析 | 2.1.4 Qlib 配置、状态、运行创建/列表/详情 | 4 |
| `strategies.py` | 策略构建 | 2.2 策略 CRUD/启停/参数定义 | 8 |
| `cli_sessions.py` | 策略构建 | 2.2 CLI 会话创建/状态/日志/产物入库 | 4 |
| `backtests.py` | 策略仿真 | 2.3.1 回测引擎诊断、任务创建/列表/详情/删除/绩效/曲线/明细 | 8 |
| `paper_accounts.py` | 策略仿真 | 2.3.2 模拟账户创建/重置/总览/下单/手动撮合/撤单/委托/成交/持仓/净值 | 10 |
| `live_configs.py` | 实盘 | 2.4 实盘配置 CRUD + 风控参数局部更新 | 6 |
| `live_runs.py` | 实盘 | 2.4 启动/停止/状态/委托/持仓 | 5 |
| `kb_local.py` | 知识库 | 2.5.1 分类 CRUD、文档上传/列表/详情/删除、笔记、检索、问答 | 11 |
| `kb_remote.py` | 知识库 | 2.5.2 远程源 CRUD/测试/文档列表/拉取入库 | 7 |
| `jobs.py` | 定时任务 | 2.6 任务 CRUD/启停/手动触发/执行历史 | 9 |
| `settings.py` | 模型配置 | 2.7.1 系统设置读写、环境变量校验和单项删除 | 4 |
| `llm_models.py` | 模型配置 | 2.7.2 LLM 模型 CRUD/设默认/测试 | 6 |
| `mcp_servers.py` | 模型配置 | 2.7.3 MCP 服务 CRUD/启停/测试/工具调用 | 8 |
| `skills.py` | 模型配置 | 2.7.4 Skill 列表/启停/参数保存 | 4 |
| `quant_workflows.py` | AI量化闭环 | 2.8 闭环模式、SOP、快照和运行记录 | 6 |
| `system.py` | 通用 | 2.9 健康检查、系统信息 | 2 |
| **合计** | — | — | **130** |

> 接口数以 05 §2.10 汇总表为准（各模块 32/12/17/11/18/9/19/6/2）。

#### 2.9.3 ws_hub（WebSocket 主题订阅管理）

| 项 | 约定（对齐 05 §3） |
|----|------|
| 端点 | 单一端点 /ws，全部实时数据经主题订阅模式推送（02 各模块设计中的多端点形态以本约定为准） |
| 主题 | 六类：market、notify（非实例）；backtest:{task_id}、cli:{session_id}、paper:{account_id}、live:{run_id}（实例主题） |
| 订阅协议 | 客户端 subscribe/unsubscribe 控制消息（topic + params 实例参数）；服务端回 subscribed/unsubscribed/error 确认；实例资源结束自动清理订阅 |
| 心跳与超时 | 客户端 30 秒 ping、服务端即时 pong；服务端 90 秒空闲主动断开 |
| 推送接口 | 引擎层/任务层/数据层经核心层事件总线或回调将事件交 ws_hub，ws_hub 统一组装 topic/type/payload/ts 帧（时间 ISO 8601 UTC）批量推送；同步任务线程通过 nowait 广播安全投递到 WebSocket 事件循环 |
| 节流 | market 主题 3~5 秒批量合并一帧；backtest progress 按交易日/百分比节流；cli output 按行节流合并 |

#### 2.9.4 schemas/（Pydantic 模型组织）

| 组织约定 | 说明 |
|----------|------|
| 按模块分文件 | 与 routes/ 模块一一对应（market/strategy/simulation/live/knowledge/scheduler/settings），公共结构入 common.py |
| 命名 | 请求：资源名单数+Create/Update/Query；响应：资源名单数+Item/Detail/Page（分页复用 common 的 items/page/page_size/total 容器） |
| 信封 | 所有响应包装统一信封（code/message/data），由 errors.py 全局构造，业务代码只返回 data 载荷模型 |
| 枚举一致 | 状态字段枚举值与 04 §6.6 状态机总表逐字一致；WS 帧模型按 05 §3.2/§3.4 定义 |
| 复用 | 引擎层/数据层输出模型（data/models.py、performance 输出）直接作为响应模型基类，避免二次映射 |

#### 2.9.5 deps/（依赖注入）

| 服务提供 | 来源层 | 主要消费路由 |
|----------|--------|--------------|
| Config / Database / FileStorage / FtsIndex | 核心层 | 全部 |
| DataSourceManager | 数据层 | market/news/watchlist/papers/reports |
| 各引擎服务（QuoteService/NewsAggregator/StockAnalyzer/Recommender/ReportGenerator/PaperSearch/RelationGraph） | 引擎层 market | 市场分析 8 个路由文件 |
| StrategyStore / StrategyRegistry / StrategyUploader / CliBuilder | 策略层 | strategies、cli_sessions |
| BacktestRunner | 引擎层 backtest | backtests |
| FactorMonitorService | 引擎层 research | factors、qlib-status |
| QlibWorkflowService | 引擎层 research | qlib-workflows |
| QuantWorkflowService | 引擎层 research | quant_workflows |
| PaperEngine | 引擎层 paper | paper_accounts |
| LiveRunner / RiskController | 引擎层 live | live_configs、live_runs |
| KnowledgeService（fts + rag + remote_sources 组装） | 核心层+智能层+集成层 | kb_local、kb_remote |
| SchedulerService（scheduler/registry/executor） | 任务层 | jobs |
| LlmManager / McpManager / SkillManager | 智能层+集成层 | settings、llm_models、mcp_servers、skills |

### 2.10 异步与并发模型

#### 2.10.1 执行形态选型

| 执行形态 | 适用场景 | 平台落位 | 选型理由 |
|----------|----------|----------|----------|
| 进程池（ProcessPoolExecutor） | CPU 密集型计算 | 回测任务主循环（事件驱动回放+指标计算）、绩效计算 | 绕开 GIL 利用多核；子进程崩溃不拖垮主进程（隔离性）；支持强制终止（超时回测任务）；策略代码执行风险隔离 |
| 线程池（ThreadPoolExecutor） | 同步阻塞 IO | APScheduler 任务执行体（jobs/ 各模块）、akshare 等同步数据源库调用、SQLite 写事务执行 | 三方库为同步实现，线程切换开销小；与调度器线程模型天然配合；写串行化队列以线程锁实现简单可靠 |
| asyncio 子进程（create_subprocess） | IO 型长进程流式输出 | trae/workbuddy/codex CLI 构建会话 | 异步逐行读取 stdout/stderr 不占工作线程；天然支持超时取消与流式回调；子进程独立工作目录便于清理 |
| asyncio 协程 | 高并发网络 IO | LLM 调用（OpenAI 兼容异步客户端）、WebSocket 推送、东方财富 push2 实时行情拉取 | 事件循环单线程承载大量并发连接，避免线程爆炸；与 FastAPI/uvicorn 原生契合 |

结论：**回测任务用进程池；CLI 会话用 asyncio 子进程；定时任务默认执行体与同步数据源用线程池，显式硬超时任务用独立子进程；LLM 与推送走 asyncio**。

#### 2.10.2 长任务进度推送链路

| 任务类型 | 执行形态 | 进度推送 |
|----------|----------|----------|
| 回测任务 | 进程池 | runner 按交易日/百分比节流回调 → ws_hub 推 backtest:{task_id} 的 progress/stage/completed/failed 事件；断线经 GET /backtests/{task_id} 补查 |
| CLI 会话 | asyncio 子进程 | cli_runner 逐行读取 → cli_builder 节流合并 → ws_hub 推 cli:{session_id} 的 output/status/artifact 事件；断线经 logs 接口按 offset 增量补拉 |
| 推荐任务 | 线程池+asyncio（LLM 段） | 状态落 recommend_tasks；完成/失败经 notify 主题 task_done/task_failed 事件 |
| 远程文档拉取 | 线程池 | 进度经 notify 主题推送；结果汇总返回 |
| 模型分析报告 | 线程池+asyncio（LLM 段） | 生成完成经 notify 主题 task_done 事件；报告列表轮询兜底 |

#### 2.10.3 SQLite 并发写控制

| 机制 | 约定 |
|------|------|
| WAL 模式 | 启动时开启 journal_mode=WAL，读写连接不互斥，读并发不受写阻塞（04 §5.1 量级下性能充裕） |
| 写串行化 | 全局唯一写队列：所有写事务经统一入口按序执行（线程锁+队列）；委托-成交-持仓-净值联动更新在单一事务内完成（04 §6.7） |
| 连接策略 | 读连接按线程/任务独立短连接；写连接单例长连接；busy_timeout 5 秒，超时抛数据库错误（5001） |
| 批量导入 | 新闻入库、知识库导入等批量写分批提交，避免长事务阻塞写队列与 WAL 膨胀 |
| 进程池写回 | 回测子进程不直接写库：计算结果序列化后经结果队列交主进程统一落库（backtest_results），规避多进程写 SQLite |

---

## 3. 前端代码架构

当前前端不采用独立 Web 工程，不使用 Vue、React、Vite、Element Plus、Vue Router、Pinia 或 TypeScript 构建链。产品主界面集中在 `src/frontend/`，由 FastAPI 在同一进程中挂载持久 Gradio 工作台和九个业务模块；帮助文档由 `src/help_docs/` 构建并挂载 MkDocs 静态站点。

### 3.1 目录结构（src/frontend 文件级）

```text
src/frontend/
├── app.py             迁移期单体兼容装配与公共导出
├── modular.py         单模块 Blocks 工厂、公共外壳和基础事件
├── mounting.py        独立应用的延迟构建、缓存、队列启动和 ASGI 挂载
├── shell.py           持久工作台、模块容器和三实例客户端缓存
├── registry.py        九个模块的 key、标题、slug、顺序和路径
├── navigation.py      跨应用 URL 导航
├── theme.py           CSS、JS、主题与 Gradio 挂载选项
├── constants.py       前端稳定选项和默认参数
├── common/            公共回调保护与组件工厂
├── handlers/          各业务域可访问回调的精确边界
├── features/          dashboard 至 admin 的九个页面模块及悬浮助手
├── service/           领域回调实现、共享展示转换和跨域契约
├── services.py        稳定导入与旧调用兼容门面
├── header.py          顶部品牌栏与外链按钮 HTML
└── i18n.py            本地中英文词典与浏览器切换脚本

src/help_docs/
├── __init__.py        导出帮助文档构建、挂载和 iframe 辅助
├── builder.py         MkDocs 构建、增量判断和 fallback 页面
├── mount.py           FastAPI `/help-docs/` 静态挂载
└── ui.py              Gradio 帮助页 iframe HTML
```

| 文件 | 职责 | 依赖 |
|------|------|------|
| `modular.py` | 按注册表 key 构建单个 Gradio 应用，装配页头、URL 导航、市场切换和当前业务页 | Gradio、features、registry |
| `mounting.py` | 为每个模块维护独立构建锁、异步启动锁和缓存；首次请求时挂载应用并启动 Gradio 队列一次 | FastAPI、Gradio、modular |
| `shell.py` | 提供 `/app/` 持久工作台、可收起模块/页面导航、同源 iframe 容器、最近三个实例缓存和主题切换 | Gradio、registry、theme |
| `features/*.py` | 创建本模块组件并绑定本模块事件；禁止引用其他应用中的组件实例 | Gradio、FrontendService |
| `handlers/*.py` | 以精确方法白名单限制每个 feature 可访问的兼容服务回调 | FrontendService |
| `app.py` | 迁移期装配完整单体 `/legacy-app/`，同时兼容导出主题和回调辅助函数 | Gradio、features、theme |
| `service/<domain>.py` | 按 dashboard、market、research、strategy、simulation、live、AI、knowledge、admin 和 assistant 归档实际回调 | engine、strategy、scheduler、integration、agent |
| `service/foundation.py`、`visuals.py`、`dashboard_views.py` | 集中参数解析、缓存、表格、Plotly 和看板展示转换 | pandas、Plotly、core |
| `features/home.py`、`service/home_*.py` | 首页的图表布局、单次持仓估值、摘要和语义色阶分离；保留 `DashboardServiceMixin` 对外回调门面 | pandas、Plotly、YAML、现有账户与行情服务 |
| `egs/config/ui/home_dashboard.yaml`、`assets/styles/home_dashboard.css` | 首页展示数量、观察参考线、配色与独立样式；CSS 只随首页模块及兼容单体加载 | YAML、浏览器 CSS |
| `service/contracts.py` | 声明少量明确允许的跨域工作流类型契约 | typing、pandas、Plotly |
| `services.py` | 聚合各业务域实现，保留原有服务名、常量和帮助函数导入路径 | service |
| `__init__.py` | 对外暴露前端构建函数和 Gradio 挂载选项 | app.py |
| `help_docs/builder.py` | 通过 `python -m mkdocs build` 构建 usage/principles 与兼容入口，跟踪正文和图片变更，排除历史附件；失败时生成 fallback 页面 | core.config、core.logger、mkdocs |
| `help_docs/mount.py` | 启动阶段构建并挂载 `/help-docs/` 静态站点 | FastAPI、StaticFiles、builder |

### 3.2 页面层约定

| 页面层 | 约定 |
|--------|------|
| 默认主界面 | `/` 和 `/app` 跳转 `/app/`；持久工作台与全部业务能力均由 Gradio 提供 |
| 一级导航 | 工作台左侧在同一顶层页面切换九个独立 Gradio 应用；地址栏记录当前模块和页面 |
| 模块内导航 | 模块一级页面并入工作台折叠导航；内容区只保留规模受控的明细 `gr.Tabs`，可见导航最多两层 |
| AI工作台导航 | 主界面、智能洞察和工作流中心并入工作台左侧导航；工作流中心内部保留阶段导航，因子挖掘和 Qlib 位于策略构建模块 |
| 表格 | 使用统一 `_table` 帮助函数，返回 Pandas DataFrame，设置稳定高度与 `data-table` 样式 |
| 图表 | 使用 Plotly Figure，空数据统一走 `empty_figure` |
| 状态提示 | 使用 Markdown + `status-strip` / `compact-note` 样式 |
| 长文本与代码 | 使用 Markdown、Textbox 或 Code，避免长文本挤入表格 |
| AI 悬浮窗 | 使用固定按钮 + 面板 + 自定义 JS，位置保存到 localStorage |
| 帮助文档 | Gradio 内嵌 `/help-docs/` iframe；正文分类维护在 `docs/usage/` 与 `docs/principles/`，学习阅读器将图片和交叉链接指向帮助站点 |

### 3.3 回调服务层

`FrontendService` 是 Gradio 前端的稳定兼容门面。实际回调已按业务域迁移到 `service/`，页面继续复用原方法名和返回契约；handler 负责访问边界，领域逻辑不得复制到页面文件：

| 方法类别 | 代表方法 | 输出 |
|----------|----------|------|
| 驾驶舱 | `dashboard` | Markdown、HTML、DataFrame、Plotly Figure |
| 市场分析 | `market_overview`、`factor_monitor_summary`、`factor_monitor_details`、`stock`、`relations`、`resource_pools`、`add_resource_pool_symbols`、`recommend` | DataFrame、Plotly Figure、Markdown、HTML |
| 策略构建 | `strategy_lifecycle`、`strategies`、`create_strategy`、`cli_build`、`import_cli_artifact` | 生命周期 HTML、状态文本、代码、日志、产物表 |
| 仿真交易 | `create_backtest`、`paper_order`、`paper_cancel` | 绩效表、曲线、持仓/委托表 |
| AI工作台 | `ai_console_nav`、`ai_console_sessions`、`ai_console_send`、`ai_console_file_preview`、`dashboard_ai_workbench_entry`、`factor_monitor_summary`、`qlib_workflow_status`、`dashboard_market_brief`、`ai_workbench_overview`、`ai_workbench_chat`、`quant_workflow_snapshot` | HTML、Chatbot messages、DataFrame、Plotly Figure、状态文本 |
| 知识库 | `kb_search`、`kb_qa`、`remote_documents` | 文档表、答案、引用表 |
| 系统配置 | `settings`、`models`、`mcp_servers`、`skills` | 配置 JSON、配置表、状态文本 |
| AI 悬浮窗 | `floating_chat`、知识问答和 CLI 辅助方法 | Chatbot messages、状态文本 |

约定：

- 所有回调函数必须返回稳定数量和稳定类型的输出，避免 Gradio 运行时绑定失败。
- 输入校验统一使用 `require_text`、`require_id`、`parse_json`、`parse_csv` 等帮助函数。
- 跨业务域复用仅限契约中声明的工作流，新增跨域调用需要同步更新类型契约和边界测试。
- 服务层不得保存前端会话全局变量；持久状态落数据库或文件存储。
- 短只读查询可 `queue=False`，外部请求、LLM、CLI、同步任务必须由按钮显式触发。

### 3.4 与 API 层的关系

Gradio 回调直接调用与 REST 路由相同的领域服务，而不是通过 HTTP 回调本机 API。这样可以减少本地部署复杂度，并确保前端页面与 REST 共享校验、存储、异常和日志。

| 前端页面 | 服务层/领域能力 |
|----------|----------------|
| 市场分析 | QuoteService、RelationGraphService、ResourcePoolService、StockAnalyzer、Recommender、MarketReportGenerator、PaperSearchService |
| 策略构建 | StrategyStore、BacktestRunner、PaperAccountService、LiveTradingService、CliBuilder、Validator |
| 策略仿真 | BacktestRunner、PaperAccountService |
| 实盘 | LiveTradingService |
| AI工作台 | QuantWorkflowService、QlibWorkflowService、FactorMonitorService、BacktestRunner、PaperAccountService、LiveTradingService、LLMClient、GenericAgentRuntime、LangfuseObserver（可选 no-op 观测）、SchedulerService、MCP/Skill 管理服务、AI 操作台会话持久化 |
| 知识库 | kb routes 服务函数、RAG、RemoteSourceService |
| 系统配置 | settings、LLM models、MCP、Skill 管理服务 |

### 3.5 前端性能与资源策略

| 场景 | 策略 |
|------|------|
| 首屏加载 | FastAPI 启动不构建 Blocks；进入 `/app/` 先构建小型工作台壳，再按需构建默认看板，重数据由 `load`、页面选择或按钮触发 |
| 页面切换 | 同源 iframe 按第一次选择创建，浏览器端按最近使用顺序保留三个；服务端模块 Blocks 继续独立缓存 |
| 主题与视觉 | `Settings.ui_theme` 通过 YAML/环境变量配置 `light/dark/system`，浏览器可本地覆盖；共享变量统一蓝白渐变、圆角、阴影和暗色控件 |
| AI工作台切换 | 一级页签默认只加载操作台轻量列表、会话和文件预览，因子/Qlib/专家/归因等重数据进入具体子页再请求 |
| 外部数据 | 新闻同步、论文检索、LLM、CLI 均显式按钮触发 |
| 表格渲染 | 限制默认页大小或查询数量，避免一次性展示超大 DataFrame |
| 关系图谱 | 限制节点/边数量，用关系类型筛选、Top-K 或最小生成树过滤 |
| 静态资源 | Gradio 资源同源挂载，FastAPI 对 assets 增加长期缓存头 |
| 压缩 | FastAPI GZip 中间件压缩 HTML/API 响应 |

### 3.6 前端测试策略

| 测试项 | 工具 | 说明 |
|--------|------|------|
| 挂载冒烟 | pytest + TestClient | `/` 跳转 `/app/`，工作台壳与九个模块 HTML、`/config` 可访问 |
| 工作台审计 | Playwright | 顶层 URL 不跳转、模块/页面可切换、活动 iframe 唯一、缓存不超过三个、重复导航隐藏且无横向溢出 |
| 模块隔离 | pytest + TestClient | 首次访问一个模块时，当前模块队列只启动一次，其他八个模块保持未构建且未启动 |
| 布局约束 | pytest | 检查主导航、表格高度、AI 悬浮窗组件和 Chatbot 类型 |
| 服务回调 | pytest | 直接调用 `FrontendService`，验证 DataFrame 列、Plotly trace 和核心工作流 |
| 压缩缓存 | pytest | 检查 GZip 和 Gradio assets cache-control |
## 4. 横切关注点

### 4.1 错误处理链路

异常自底向上的流转链路（错误码分段对齐 05 §4）：

| 层 | 职责 | 典型处理 |
|----|------|----------|
| 数据源/集成层（底层抛出） | 将外部失败归一为数据源异常/外部服务异常（2xxx），标注源名与失败原因；DataSourceManager 先行 fallback（切备源、进入冷却），全链失败才向上抛 | 行情全源失败→2001；LLM 失败→2004；MCP 连接失败→2005；CLI 异常→2006 |
| 引擎层（包装决策） | 捕获底层异常做业务降级（LLM 不可用降传统算法、子数据缺失返回空结构标记），可降级则吞并记录、不可降级则包装为业务异常（保留 code）上抛 | 个股分析聚合降级不阻塞；回测失败包装任务失败状态+错误信息落库 |
| API 层（统一出口） | 全局异常处理器将业务异常转为统一信封（code/message/data=null，HTTP 200 原则）；未捕获异常兜底 5999；请求不可解析才 400、路径不存在才 404 | 参数校验失败→1xxx；状态冲突→3xxx/4xxx |
| 前端（提示呈现） | Gradio 回调统一用 `_safe` 包装；业务异常转为 Markdown/状态文本，表单参数错误就地提示；网络层错误联动状态区 | 风控拦截 4005→状态区高亮；参数 1xxx→回调错误信息 |

### 4.2 日志规范

| 项 | 约定 |
|----|------|
| 框架与输出 | loguru；文件落 data/logs/（按天轮转，保留天数可配，默认 30 天），控制台同步输出（级别可独立配置） |
| 级别 | DEBUG 数据源原始报文与调试细节；INFO 常规业务流转；WARNING 可自动恢复的异常（源切换、LLM 降级、重试）；ERROR 需人工介入的失败（任务失败、实盘异常、数据库错误） |
| 格式 | 统一含时间、级别、channel、业务模块名、代码模块/函数/行号；回调日志包含 operation_id、业务函数源码位置与耗时，请求诊断包含 request_id；禁止打印明文密钥/凭证（04 §6.5） |
| 禁用项 | 业务代码禁止 `print`、标准库 `logging` 和 pylogrus；标准库日志只允许在 `src/core/logger.py` 内作为第三方桥接实现使用 |
| 框架降噪 | `start.py` 和 `src.main` 均关闭 uvicorn access log；uvicorn/httpx/httpcore/urllib3/numexpr 经 loguru 桥接，控制台默认隐藏第三方 WARNING 及以下噪声，文件日志保留审计记录；第三方 stdout 在 Gradio 构建/挂载阶段转成 loguru 记录 |
| 后端细节 | Gradio 回调在 INFO 记录“页面动作触发后端方法”的开始/完成与耗时，非预期失败在 ERROR 附堆栈；不记录回调参数与返回值。HTTP 中间件在 DEBUG 记录 request_id、method、path、route、endpoint、status、duration_ms、client、User-Agent、Referer、Accept 和脱敏 query；成功请求默认不进入 INFO，浏览器 `/manifest.json` 与静态资源探测不作为后端 404 告警；慢请求阈值由 `backend_slow_request_ms` / `ALL_IN_ONE_BACKEND_SLOW_REQUEST_MS` 控制。外部行情请求由 `data.source` 记录 provider、host、path、状态码和耗时；代理断开、连接超时等预期网络异常只输出单行失败原因，不输出完整第三方 traceback；真实行情 HTTP 只对 429/5xx 做退避重试，连接/读取异常快速失败 |
| 关键埋点表 | 见下 |

关键埋点表：

| 埋点 | 级别 | 记录内容 |
|------|------|----------|
| 数据源切换 | WARNING/INFO | 数据类型、失败源、切换目标源、冷却时长、恢复事件 |
| LLM 调用 | INFO | 用途分级、模型名、耗时、Token 消耗、成功/失败、降级目标 |
| 订单生命周期 | INFO | 账户/运行 ID、委托号、状态迁移（受理→部分成交→终态）、金额数量、风控拦截原因 |
| 启动阶段 | INFO/WARNING | 文件存储、数据库、API 路由、帮助文档构建/挂载、Gradio 构建、Gradio 挂载、路由摘要、接口布局说明、第三方 stdout 捕获 |
| 调度任务 | INFO/WARNING/ERROR | job_id、任务名、任务类型、触发方式、超时模式、重试次数、耗时、执行摘要和历史 ID |
| 回测阶段 | INFO | 任务 ID、阶段切换（加载/运行/评估）、进度里程碑、耗时 |
| CLI 会话 | INFO | 会话 ID、CLI 类型、启动/退出码、超时终止、产物数量 |
| 定时任务 | INFO/WARNING | 任务 ID、触发方式、开始/结束、耗时、重试、失败原因 |
| 实盘运行 | INFO/ERROR | 运行 ID、状态机迁移、心跳异常、熔断触发与恢复 |

### 4.3 配置加载顺序

| 优先级 | 来源 | 说明 |
|--------|------|------|
| 1（最低） | 代码默认值 | 各模块声明式默认（与文档默认值一致） |
| 2 | YAML 配置文件 | egs/ 下配置样例为模板；部署时复制为实际配置（路径经 AIO_CONFIG 指定） |
| 3 | 环境变量 | 部署环境覆盖（端口、数据目录、密钥、日志级别） |
| 4（最高） | settings 表 | 运行时经系统设置页读写（数据源优先级、缓存 TTL、CLI 路径等），变更即时生效 |

说明：层级 1→2→3 为《01_overview.md》"YAML + 环境变量 + 默认值"三级配置；层级 4 为《02 §8.1/04 §2.1》约定的最高优先级持久层（数据库 > 配置文件 > 默认值）。四级合并由 core/config 统一完成，任何配置读取方只面对合并后的视图。

### 4.4 时间与编码

| 项 | 约定 |
|----|------|
| 存储 | 数据库时间字段一律 TEXT 存 UTC ISO 8601（04 §6.2）；日期类字段 YYYY-MM-DD |
| 传输 | REST 与 WebSocket 时间字段统一 ISO 8601 UTC 字符串（Z 结尾，05 §1.6）；交易时段本地时区语义由后端转换 |
| 展示 | 前端经 utils/datetime 统一按浏览器本地时区本地化渲染；数据源带时区时间入库前统一换算 UTC |
| 编码 | 全链路 UTF-8（数据库、文件、HTTP、WS 文本帧）；金额精度与 Decimal 计算约定见 04 §6.3 |

### 4.5 测试策略

| 层/端 | 测试重点 | 工具与形态 |
|--------|----------|-----------|
| 核心层 | 配置四级合并优先级、缓存过期与并发、Repository 分页与事务、FTS5 触发器同步与 LIKE 兜底、crypto 脱敏 | pytest 单测（内存/临时库） |
| 数据层 | 数据源基类契约一致性（mock 外部响应）、fallback 切换与冷却、缓存装饰器键与 TTL | pytest + 响应桩 |
| 策略层 | 校验链三分支（安全/接口/参数）、版本落盘与 (name,version) 唯一、registry 加载注入 | pytest 单测 |
| 引擎层（重点） | 回测事件循环与撮合精度（Decimal）、绩效指标对拍样本、模拟订单状态机全迁移、风控检查链顺序与熔断、运行状态机迁移 | pytest 单测+固定行情样本回放 |
| 智能层 | LLM 客户端 mock（热切换/降级）、RAG 检索拼装与降级、推荐 JSON 解析容错 | pytest + LLM 桩 |
| 任务层 | 注册映射表装配、互斥/超时/重试语义、执行历史记录 | pytest（内存调度器） |
| API 层 | 统一信封与错误码映射、130 接口冒烟（TestClient）、WS 主题订阅/退订/心跳 | pytest + FastAPI TestClient |
| 前端 | Gradio 挂载冒烟、组件配置、回调服务、Plotly 图和 DataFrame 输出稳定性 | pytest + TestClient |

### 4.6 代码质量工具

| 端 | 工具 | 约定 |
|----|------|------|
| 后端 | ruff | lint + format（import 排序、行宽统一），含循环依赖检查；规则集在 pyproject.toml 声明，配置风格与 a001_news_track 一致 |
| 后端 | mypy | 核心层/数据层/策略层 strict；其余层渐进标注；schemas 全量注解 |
| 后端 | pytest | 分层目录镜像 src/ 结构；覆盖率门槛：核心层/引擎层为主（合计 ≥ 80%） |
| 前端 | pytest | Gradio 挂载、组件配置与回调服务测试（见 4.5） |
| 提交门禁 | — | ruff、mypy、pytest、pip-audit、gitleaks 按任务要求执行；如环境缺工具需记录原因 |

---

## 5. 模块依赖全景图

### 5.1 前后端模块依赖全景总图

模块数量为第 2/3 章目录树的文件计数；依赖方向遵守 1.2 分层依赖规则（R1～R8）。

```
┌────────────────────────── 前端 src/frontend（Gradio） ──────────────────────────┐
│  app.py：总览、市场分析、策略构建、策略仿真、实盘、知识库、学习、任务、配置、帮助 │
│    │ 编排：声明 Gradio 组件 / 绑定回调 / 注入 CSS 与轻量 JS                    │
│    ▼                                                                          │
│  services.py：输入校验 / 调领域服务 / 转 DataFrame、Plotly、Markdown、JSON      │
│    │ 业务状态与缓存                                                           │
│    ▼                                                                          │
│  Gradio 回调直接调用领域服务，与 REST 路由共享业务实现                         │
│  自定义样式和 JS 仅负责视觉、布局和 AI 悬浮窗拖动                              │
│                                                                                │
└──────┬─────────────────────────────────────────────────────┬──────────────────┘
       │ Gradio 回调（进程内调用）                         │ WS：保留 /ws 供 REST/未来实时增强
       │     REST 路由同源复用                                │     /ws · 6 类主题订阅
       ▼                                                     ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ API 层（36）：app │ errors │ deps/services │ ws_hub │ schemas（8）│ routes（24）│
│   编排入口：经 deps/services 注入各层服务单例；可按需直调任意下层（R1）         │
└──┬───────────────┬────────────────┬────────────────┬────────────────┬────────┘
   ▼               ▼                ▼                ▼                ▼
 智能层（6）     引擎层（18）     策略层（6）      任务层（13）     集成层（8）
 llm_client      market（7）      strategy_base   scheduler（3）   mcp_client
 prompts         backtest（4）    registry        registry         cli_runner
 analysis_agent  paper（4）       uploader        executor         skill_manager
 recommend_agent live（3）        validator       jobs/（10）      remote_sources(3)
 strategy_agent  strategy_store   cli_builder                      broker（2）
 rag                                                                              │
   │               │                │                │                │
   │  （R7 例外：任务层经 registry 表驱动调用引擎层/数据层/策略层执行体）          │
   └───────────────┴───────┬────────┴────────────────┴────────────────┘
                           ▼
 数据层（13）：base │ manager │ cache │ models │ health + quotes（3）news（2）reports（1）papers（2）
                           │
                           ▼
 核心层（11）：config │ logger │ exceptions │ cache │ database │ repository │ fts │
               file_storage │ crypto │ events │ timeutil（公共底座，所有层依赖，零业务）
                           │
                           ▼
 底层存储：SQLite + FTS5（39 业务表 + 3 虚拟表） │ 文件存储 data/（strategies/knowledge/reports/logs/backup）
```

推送回链（与请求链路反向）：ws_hub ◀─ 各层进度/状态事件（回测进度、CLI 输出、模拟盘/实盘委托回报、任务完成、数据源切换）──▶ REST/Gradio 页面按需刷新；后续若恢复浏览器实时订阅需另行补充前端状态设计。

### 5.2 模块级依赖弧线清单（跨层）

层内依赖（同目录内模块协作）不在此列；下表只列跨层、跨子包的关键依赖弧（调用方 → 被调方）：

| # | 调用方模块 | 被调方模块 | 依赖内容 | 典型场景 |
|---|-----------|-----------|----------|----------|
| A1 | engine/market 全部 7 服务 | data/manager | 统一取数入口（行情/新闻/研报/论文四类方法族） | 新闻聚合、行情服务、研报/论文编排 |
| A2 | engine/market/news_aggregator、report_generator | agent/analysis_agent | LLM 分析增强（jieba 为主、LLM 按需） | 新闻双模式分析、模型市场分析报告 |
| A3 | engine/market/recommender | agent/recommend_agent | 候选池批量深度精选（deep 路径） | 大模型推荐与组合推荐 |
| A4 | engine/market/stock_analyzer | data/manager + agent/analysis_agent | 四维评分取数 + LLM 点评 | 个股详情聚合页 |
| A5 | engine/backtest/runner | strategy/registry | 按策略 id+版本加载实例并注入上下文 | 回测事件回放执行策略 |
| A6 | engine/backtest/event | data/manager（quotes 族） | 历史 K 线区间取数与复权统一 | 回测数据准备（BaoStock 主源） |
| A7 | engine/paper/engine | strategy/registry + data/manager | 实时行情驱动策略与撮合 | 模拟盘主循环 |
| A8 | engine/live/runner | strategy/registry + integration/broker | 策略执行 + 通道下单/回报 | 实盘主循环（首期模拟通道） |
| A9 | engine/live/channel | integration/broker/adapters | 通道状态查询、启动拦截原因、heartbeat/error 事件类型 | 实盘通道观测和事件冻结 |
| A10 | agent/rag | core/fts + agent/llm_client | 分块优先检索（FTS5+LIKE 兜底）→ 上下文拼装 → 生成 | 知识库问答管线 |
| A11 | agent/llm_client | 外部 LLM API（OpenAI 兼容） | 多配置、用途分级、热切换、降级 | 所有 LLM 调用的唯一出口 |
| A12 | strategy/cli_builder | integration/cli_runner + agent/strategy_agent | 需求组装 → 子进程编排 → 产物扫描 | CLI 构建会话（trae/workbuddy/codex） |
| A13 | strategy/uploader、cli_builder | strategy/validator | 复用同一契约校验链（安全/接口/参数） | 上传入库与 CLI 产物入库 |
| A14 | strategy/store | core/file_storage + core/database | 版本文件落盘 + strategies 表 CRUD | 策略资产管理 |
| A15 | scheduler/registry → scheduler/jobs | engine/market、engine/backtest、engine/paper、data/manager、core/fts | 表驱动执行体（R7 例外，jobs 不得被其他层 import） | 新闻采集、行情入库、报告定时生成等 10 类任务 |
| A16 | scheduler/executor | core/database + api/ws_hub 转发（经事件） | 执行历史入库 + notify 主题推送 | 任务执行状态可观测 |
| A17 | integration/remote_sources | integration/mcp_client | 通过工具映射接入飞书/ima/自定义源并拉取文档 | 远程知识库 |
| A18 | integration/skill_manager | integration/mcp_client | Skill 绑定 MCP 工具执行 | Skill 手动执行与配置 |
| A19 | data/manager | data/ 各源实现 + core/cache | fallback 链装配、失败冷却、缓存装饰 | 所有取数的统一路径 |
| A20 | api/deps/services | 上述各层服务构造 | 单例构造与缓存、Depends 注入路由 | 全部 130 接口的服务装配 |

### 5.3 七大功能模块前后端映射全景表

前端 api 模块 ↔ 后端路由的文件级对应见 3.2.2；本表自上而下贯通"功能模块 → 前端 → 后端 → 数据 → 推送"五级（含通用模块合计 9 行，覆盖 20 个前端能力模块、25 个后端路由文件、130 接口）：

| 功能模块 | 前端 api 模块 | 后端路由（接口数） | 依托层与关键模块 | 主要数据表 | WS 主题 |
|----------|--------------|-------------------|------------------|-----------|---------|
| 市场分析 | news、market、watchlist、relations、stocks、recommend、reports、papers、factors、qlibWorkflows（10 模块） | 同名 10 文件（33） | engine/market 全部 8 服务 + engine/research/factor_monitor、qlib_workflow + data/manager + agent（analysis/recommend/llm_client） | news_items、watchlist_group、watchlist、resource_pools、resource_pool_items、stock_relations、recommend_tasks、recommend_results、model_reports、papers、factor_definitions、factor_metrics_daily、factor_alerts、qlib_runs | market、notify |
| 策略构建 | strategies、cliSessions（2 模块） | strategies、cli_sessions（12） | strategy 层全部 6 模块 + integration/cli_runner + agent/strategy_agent | strategies、cli_sessions | cli:{session_id}、notify |
| 策略仿真 | backtests、paperAccounts（2 模块） | backtests、paper_accounts（18） | engine/backtest（4）+ engine/paper（4）+ strategy/registry + data/quotes | backtest_tasks、backtest_results、paper_accounts、paper_orders、paper_trades、paper_positions、paper_nav_history | backtest:{task_id}、paper:{account_id}、notify |
| 实盘 | live（1 模块） | live_configs、live_runs（11） | engine/live（3）+ integration/broker + strategy/registry | live_configs、live_runs、live_orders | live:{run_id}、notify |
| 知识库 | knowledge（1 模块） | kb_local、kb_remote（18） | core/fts + agent/rag + integration/remote_sources、mcp_client | kb_categories、kb_documents、kb_qa_history、remote_sources、remote_docs_cache | notify |
| 定时任务 | scheduler（1 模块） | jobs（9） | scheduler 全部（scheduler/registry/executor/jobs 12 执行体） | scheduled_jobs、job_executions | notify |
| 模型配置 | settings（1 模块） | settings、llm_models、mcp_servers、skills（21） | core/config/env_file + agent/llm_client + integration/mcp_client、skill_manager | settings、llm_models、mcp_services、skills | notify |
| AI量化闭环 | AI工作台闭环流程与操作台（1 模块） | quant_workflows（6） | engine/research/quant_workflow + core/repository + agent/llm_client | quant_workflow_runs、quant_workflow_steps、quant_workflow_artifacts、ai_workspace_sessions、ai_workspace_messages | notify |
| 通用系统 | system（1 模块） | system（2） | core/config + data/health | settings（只读） | — |

### 5.4 关键链路数据流图

与《01_overview.md》§3.3 五大数据流对应，细化到模块级并补充知识库问答与配置变更两条链路（共 7 条）：

```
① 研读流（新闻/行情）
  MarketNews/MarketDashboard ─▶ api/news·market ─▶ routes/news·market
    ─▶ engine/market/news_aggregator·quote_service ─▶ data/manager
    ─▶ quotes/eastmoney·akshare·baostock │ news/akshare·eastmoney ─▶ 外部数据源
    落库：news_items（FTS5 触发器同步）；行情快照走 TTL 缓存不入库
    返回：统一模型 ─▶ FrontendService 适配 ─▶ DataFrame/Plotly/Markdown ─▶ 页面渲染
    推送：quote_service 组帧 ─▶ ws_hub（market 主题）─▶ REST/Gradio 页面按需刷新或后续实时订阅
    降级：源失败 ─▶ manager 冷却切备源 ─▶ core/events ─▶ notify（data_source 事件）─▶ 状态条

② 策略构建流（CLI 会话）
  StrategyWorkbench ─▶ api/cliSessions ─▶ routes/cli_sessions ─▶ strategy/cli_builder
    ─▶ agent/strategy_agent（需求+接口契约+输出约定组装）
    ─▶ integration/cli_runner（asyncio 子进程、独立工作目录、流式逐行读取）
    ─▶ ws_hub（cli:{session_id}：output/status/artifact）─▶ strategyStore 流式渲染
    产物：data/strategies/cli_generated/ ─▶ validator（安全/接口/参数校验）
    ─▶ strategies 表（草稿态）+ cli_sessions（log_path 落 data/logs/）

③ 回测流（进程池）
  BacktestHome ─▶ api/backtests ─▶ routes/backtests ─▶ engine/backtest/runner（进程池）
    ├─ event ◀─ data/quotes/baostock（历史 K 线、复权统一）
    ├─ strategy/registry（按 id+版本加载策略、注入上下文）
    └─ matcher（撮合）─▶ performance（绩效指标）
    落库：backtest_results（trades_path/report_path 落 data/reports/backtest/）
    推送：runner 节流回调 ─▶ ws_hub（backtest:{task_id}：progress/stage/completed/failed）
    回写：子进程计算结果经结果队列交主进程统一落库（2.10.3，子进程不直接写库）

④ 模拟盘/实盘流（交易主循环）
  PaperTrading/LiveTrading ─▶ api/paperAccounts·live ─▶ engine/paper/engine │ engine/live/runner
    ─▶ strategy/registry（实时行情驱动：data/manager get_stock_quotes）
    ─▶ 策略信号 ─▶ risk_controller（六规则前置检查链，拦截即 4xxx）
    ─▶ paper/matcher │ integration/broker/adapters（通道状态/事件）
    落库：paper_* 五表 │ live_* 三表（单事务联动更新，04 §6.7）
    回报：channel 归一分发 ─▶ ws_hub（paper:{account_id} │ live:{run_id}）
    ─▶ simulationStore/tradingStore（持仓、净值、委托实时刷新）

⑤ 任务流（周期调度）
  APScheduler/线程轮询触发 ─▶ scheduler/runtime ─▶ scheduler/executor
    ─▶ scheduler/jobs（表驱动任务类型）─▶ engine/* · data/* · core/fts（R7 例外弧 A15）
    落库：job_executions（触发方式/耗时/结果）
    推送：executor ─▶ ws_hub（notify：task_done/task_failed）─▶ taskStore/appStore

⑥ 知识库问答流（RAG）
  KnowledgeLocal ─▶ api/knowledge ─▶ routes/kb_local ─▶ agent/rag
    ─▶ core/fts（kb_document_chunks_fts 优先，kb_documents_fts 与 LIKE 兜底）
    ─▶ 同一会话最近问答历史（追问无命中时回退检索 + 生成上下文）
    ─▶ 上下文拼装（会话内历史问答 + chunk 标题/正文 + 8K Token 预算截断）─▶ agent/llm_client（生成、约束引用来源）
    降级：LLM 失败 ─▶ 纯检索结果返回（2xxx 错误码 + 降级标记）
    落库：kb_qa_sessions + kb_qa_history(session_id) ─▶ ChatPanel 流式渲染（引用来源可点击）

⑦ 模型配置变更流（事件驱动热生效）
  ModelSettings ─▶ api/settings ─▶ routes/llm_models ─▶ core/env_file（凭证写入环境文件）
    ─▶ llm_models 表 ─▶ core/events（发布配置变更事件）
    ─▶ agent/llm_client（订阅：懒重建客户端，下次调用生效，不中断在途请求）
    ─▶ ws_hub（notify：配置变更）─▶ settingsStore 刷新 + 状态条提示
```

---

## 6. 开发里程碑建议

### 6.1 划分原则与依赖关系

| 原则 | 说明 |
|------|------|
| 依赖驱动 | 里程碑顺序严格遵循 5.1/5.2 依赖全景：核心层 → 数据层 → 引擎层 → 策略/交易链路，下层未稳定不上上层 |
| 垂直切片 | 每个里程碑交付"接口 + 页面 + 落库 + 推送"的最小闭环（垂直切片），而非按层横切；每个里程碑结束都有可运行、可点击、可验证的系统增量 |
| 契约先行 | 里程碑内部先冻结接口契约（schemas + 路由骨架 + 统一信封 + WS 主题帧），前后端再并行开发 |
| 测试随行 | 每个里程碑同步补充 4.5 测试策略表中对应该层的测试，不欠账；覆盖率门槛（核心+引擎 ≥ 80%）在 M4 结束时首次核算 |
| 文档同步 | 接口/表结构/配置项如有变更，随代码合入同步回写 01～05 号设计文档 |

里程碑依赖关系（M6 的知识库子块依赖 M2 的 LLM 基础设施，可与 M3～M5 并行）：

```
M0 工程底座
 └─▶ M1 数据层与看盘基础（含 WS 基础、调度器基础）
      └─▶ M2 市场分析完整 + LLM 基础设施
           ├─▶ M3 策略构建 ─▶ M4 策略仿真 ─▶ M5 实盘与风控 ─┐
           └─▶ M6a 知识库与远程集成（可与 M3～M5 并行）      │
                                                           ▼
                              M6b 一体化部署与收尾（全量回归）
```

### 6.2 里程碑总表

参考周期为单人全职投入的粗估，可按实际投入比例伸缩；范围均指累计交付（含前序里程碑）。

| 里程碑 | 主题 | 交付范围（本阶段新增） | 依赖前置 | 可验证交付物 | 参考周期 |
|--------|------|------------------------|----------|--------------|----------|
| M0 | 工程底座 | 仓库与工具链（pyproject/CI 双端工具链）；Gradio 前端骨架；核心层 11 模块；API 骨架（app/errors/schemas/common/routes/system）；Gradio 主导航、总览页、状态提示与挂载入口 | — | 健康检查与系统信息接口返回统一信封；配置四级合并优先级单测通过；CI 全绿；前端空壳起服务可见整体布局 | 1 周 |
| M1 | 数据层与看盘基础 | 数据层 13 文件（8 数据源 + manager fallback/冷却/健康）；engine/market 先行 2 服务（quote_service/news_aggregator）；调度器基础（scheduler/registry/executor + news_fetch/market_refresh）；ws_hub 基础（订阅/心跳 + market/notify 主题）；3 路由 12 接口；Gradio 市场页面（新闻/看盘）与前端回调服务 | M0 | 新闻四类列表、关键词云、大盘指数、自选分组 CRUD 页面可用；模拟主源失败自动切备源且状态条可观察（日志埋点可查）；market 主题 3~5 秒推送、断线重连后订阅自动恢复 | 2 周 |
| M2 | 市场分析完整 + LLM 基础设施 | engine/market 其余 5 服务；agent 先行 4 模块（llm_client/prompts/analysis_agent/recommend_agent）；4 个调度任务（relation_build/report_job/recommend_job/paper_fetch）；6 路由 21 接口（含 llm_models 和环境变量管理）；Gradio 市场分析页面（板块/关系图/个股/推荐/研报/模型分析/论文/模型管理） | M1 | 市场分析 25 接口冒烟全通；推荐 quick/deep 两路径出结果且落库；双模型热切换与主模型故障降级可观察；模型分析报告按任务定时生成并可查看 | 2~3 周 |
| M3 | 策略构建 | 策略层 6 文件（统一接口/注册中心/上传校验/仓储/CLI 构建器）；agent/strategy_agent；integration/cli_runner；2 路由 12 接口 + cli 主题；Gradio 策略构建页面（策略库/上传/CLI 工作台） | M2 | 示例策略上传通过校验链入库，(name,version) 重复被拒；恶意代码样例被安全黑名单拦截；CLI 会话流式日志实时显示、超时强杀生效、产物入库为草稿态 | 2 周 |
| M4 | 策略仿真 | engine/backtest 4 文件（进程池执行）+ engine/paper 4 文件；2 个调度任务（backtest_job/paper_job）；2 路由 18 接口 + backtest/paper 主题；Gradio 策略仿真页面（回测/模拟交易） | M3 | 示例策略完整回测产出绩效/曲线/明细（与固定样本对拍通过）；进度推送与断线补查一致；模拟盘开户→下单→限价待撮合→手动撮合→持仓→净值链路正确；覆盖率首次核算达标 | 3 周 |
| M5 | 实盘与风控 | engine/live 3 文件（状态机/风控链/通道）；integration/broker 2 文件（接口 + 模拟适配器）；2 路由 11 接口 + live 主题；Gradio 实盘管理页面 | M4 | 实盘经模拟通道完整运行一个交易日（启停/暂停/恢复状态机正确）；六条风控规则逐条拦截用例通过；心跳异常与熔断触发/恢复经日志与 notify 可观测 | 2 周 |
| M6a | 知识库与远程集成 | agent/rag；integration/mcp_client/skill_manager + remote_sources（飞书/ima）；kb_local/kb_remote/mcp_servers/skills 4 路由 29 接口；2 个调度任务（kb_sync/data_maintain）；Gradio 知识库与 MCP/Skill 配置页面 | M2（可与 M3～M5 并行） | 本地导入→FTS 检索→RAG 问答（引用来源可点击）→LLM 失败降级纯检索；飞书/ima 经 MCP 拉取文档入库；MCP 服务探活失败冷却可观察 | 3 周 |
| M6b | 一体化部署与收尾 | jobs/settings 路由 13 接口；SystemSettings/SchedulerTasks/帮助页；FastAPI 挂载 Gradio `/app/`；启动/停机顺序；备份与恢复 | M5 + M6a | 40 表/130 接口全量冒烟通过；单进程一体化部署后全功能回归；数据备份→清空→恢复演练成功；定时任务全类型触发一轮正常 | 2 周 |

### 6.3 贯穿性工作

策略参数由 src/strategy/parameters.py 解析，parameter_profiles.py 读取 egs/examples/strategy_params；前端 features/parameters.py 和 service/parameters.py 复用选择与预览。回测 runner 统一注入同一解析结果给预检、加载器和引擎，experiments.py 生成运行快照与 OHLCV 摘要，沿用原任务 JSON 存储并兼容旧任务。设计见 `10_strategy_parameter_design.md`。

ETF 研究由 `src/data/etf.py` 读取 `egs/config/strategies/etf_universes.yaml`，策略入口复用标准端口，回测引擎在 ETF 元数据存在时增加资产类型、池标识和跟踪误差。`ResearchTeam` 通过 workflow 选择普通回测复核或 ETF 专用复核，两个流程都禁止委托。

统一 CLI 已完成 A/B/C 实施。`egs/entrypoints/cli.py` 为源码薄入口、`src/cli/` 为客户端模块，通过 REST 调用同一领域服务；`egs/config/cli/commands/*.yaml` 按领域登记显式命令，parser/client/input/output/policy/operations 分别处理解析、传输、请求、结果、确认和结果组合。业务 CLI 不导入 Gradio 或直接打开生产数据库，system serve 单独复用前台启动入口。

AI 工作台共用 `agent/workspace.py:AIWorkspaceService` 和 `workspace_backend.py:backend_events`，原页面回调与新 REST 都调用相同会话/附件/后台逻辑；附件实现移动到 `agent/attachments.py`，旧前端模块保留兼容导出。`api/event_stream.py` 只编码实际生成器事件；`api/market_context.py` 通过 ContextVar 隔离市场。范围和阶段验收见 `12_cli_interface_design.md`。

前端 `common/callbacks.py:safe()` 区分普通函数与生成器，统一错误和耗时范围覆盖整个调用或迭代；注册契约测试验证工作台/悬浮消息的两种触发器都被 Gradio 标记为 generator。`service/chat_content.py` 负责文本内容块规范化，`service/assistant.py` 迭代既有 Codex 事件，兼容同步调用。新闻初始化使用 SQLite 去重键原子冲突处理，不再依赖先查后插；单独验证八路空库并发和 CN/US 样例初始化。

| 事项 | 约定 |
|------|------|
| 测试补充 | 随每个里程碑合入对应层的测试（4.5 测试策略表），不集中到最后补 |
| 埋点接入 | 数据源切换、LLM 调用、订单生命周期、任务执行四类关键埋点（4.2）随该功能首个可用版本同步接入 |
| 状态可观测 | 底部状态条（WS 状态/数据时间/行情源/后端健康）随 M1 建立，后续里程碑只扩展不重构 |
| 版本管理 | 每个里程碑结束打标签并归档一份可运行备份（data/backup），便于回退对照 |
| 文档回写 | 里程碑复盘时核对 01～05 文档与实现的偏差，偏差要么改实现要么改文档，不允许漂移 |

## 2026-10-22 组合策略实现边界

策略工坊是独立领域模块，Gradio、REST 和 CLI 只调用共享服务，不各自拼接训练或模拟逻辑。配置与固定提示词位于 `egs/config/strategies/strategy_components.yaml`，七套方案位于 `egs/examples/strategy_pipelines/`。

| 位置 | 已接入职责 |
| --- | --- |
| src/strategy/composition | 有类型的时点输入、DAG/参数校验、版本/数据摘要、模型原生产物、异步执行与模拟账户CAS |
| src/strategy/components | 规则/形态、真实模型评分、可比语义下的排名/投票及弃权 |
| src/portfolio/allocation.py | 等权、评分、逆波动、ERC、HRP、最小方差及子策略预算 |
| src/risk/policies.py | 持仓独立风险、行业/资产类别/相关集中、波动与回撤、日损失及冷却状态 |
| src/engine/composition | 共享行情、历史能力检查、树形预算、批次账本、证券净额、日线撮合、Agent决定归档、报告和监控 |
| src/agent/decision_team.py | 有限候选的一/三角色文本ReAct终审与证据校验 |
| src/frontend/features/composition.py、composition_editor.py | 首次进入才构建的工坊、结构化步骤和只读依赖图 |
| src/api/routes/strategy_pipelines.py、egs/config/cli/commands/pipeline.yaml | 统一业务接口与声明式命令契约 |

运行目录保存 JSON 内容寻址面板和原生模型；本轮不新增未知 pickle 加载、分布式训练、全市场批量行情或真实券商自动执行。工作台通过动态挂载后的激活按钮初始化工坊，避免隐藏页签过早触发而出现空白。
