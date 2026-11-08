# AIQuant智投 一体化量化交易平台 - 数据库设计文档

2026-11-02补充：命名知识库、文件分块检索、会话附件隔离、递归关键词与左侧引用阅读见[31号设计](../knowledge/named_knowledge_library_design.md)。

兼容迁移第2版为知识文档增加library_name、attachment_session和chunk_chars，为问答历史增加library_name。历史记录归入默认库；文档来源去重同时限定库名。文件正文及当前分块清单按库保存，SQLite原正文及分块继续供旧调用兼容，不作为新问答的检索后端；该迁移可应用于已完成第1版迁移的数据库。

2026-10-30增量：基础建表声明移至core/database_schema.sql，core/migrations.py记录schema_migrations版本并保持重复启动幂等；初始化通过线程锁与进程文件锁串行化。task_leases保存任务种类/键、owner、expires、cancel_requested和状态，供Web/CLI独立进程共享所有权、取消及调度选主。旧金融业务表与账本继续使用，不因前端拆分重写。凭据使用环境引用，未来审计数据库/原生模型默认不进入Git；旧历史证据未删除。

2026-10-29补充：研究身份快照随原Alpha/Agent配置冻结，原有业务表及账本继续复用；本地Skill运行在项目数据目录skill_runs按运行ID保存状态、事件、实际业务ID和JSON/HTML，不新增重复策略或回测表。缺失usage与外层CLI账单保持未知，不存认证密钥。

2026-10-27新增alpha独立表：datasets保存原件内容/摘要/来源，studies保存冻结政策/提示/模型与状态，candidates保留人工或AI假设/实现/技术失败，trials保留每次验证/留出，events提供顺序摘要链，reviews记录两轨人工证据，holdouts记录跨项目不可重复消费的证券日期范围。来源核验新增数据版本，不回写已登记研究。旧业务表不重写；本地记录不冒充不可篡改外部审计或双人认证。详见23号设计及`src/alpha_mining/schema.sql`。

2026-10-25增量：新增monitor_universes保存历史成员版本、来源与观察时间，monitor_reports保存版本化监控缓存；factor_alerts新增scope以隔离股票池、因子和后端周期。已有指标表的universe保存范围摘要，metadata保留池与日期口径；旧记录不覆盖。资源导入使用Database.transaction保存点，预览不写标的，提交绑定目标修订并原子写入。当前资源池保持单市场，混合市场文件阻断，没有破坏原唯一约束。详见[17号设计](../data/monitor_graph_resource_design.md)。

## 1. 存储总览

### 1.1 存储形态

平台采用 **SQLite 单文件数据库（data/all_in_one.db）+ FTS5 全文检索 + 文件存储 + Parquet 行情湖 + DuckDB 本地查询** 的组合方案：

- 结构化业务数据（配置、任务、交易记录等）统一存入 SQLite 单文件数据库；
- 全文检索能力由 SQLite 内建 FTS5 虚拟表提供（复用 a001_news_track 已验证的"虚拟表 + 触发器同步 + LIKE 兜底"模式）；
- 大体积非结构化内容（策略代码、笔记 Markdown、论文/研报 PDF、回测产物）落文件存储目录，数据库中仅保存文件相对路径引用。
- 持续增长的行情、因子截面和回测面板不长期堆入 SQLite 主库，优先写入 Parquet 行情湖，并由 DuckDB 做本地分析查询。

### 1.2 data/ 目录规划

```
data/
├── all_in_one.db            SQLite 数据库单文件（业务数据 + FTS5 虚拟表 + 索引 + 触发器）
├── strategies/              策略代码文件存储
│   ├── upload/              用户上传的策略代码（按策略 id + 版本归档）
│   └── cli_generated/       CLI（trae / workbuddy）生成的策略代码产物
├── knowledge/               知识库文档存储
│   ├── notes/               个人笔记（Markdown）
│   ├── papers/              量化论文（元数据摘要 Markdown；后续支持 PDF 下载/上传）
│   └── reports/             研报（PDF）
├── reports/                 报告产物存储
│   ├── backtest/            回测交易明细、绩效报告（JSON / HTML / Markdown）
│   └── model/               模型市场分析报告归档（Markdown）
├── market_lake/              行情与因子列式数据
│   ├── parquet/              Parquet 行情湖（按 dataset / market / dt 分区）
│   └── market.duckdb         DuckDB 本地查询库
├── logs/                    运行日志（loguru 按天轮转；CLI 会话日志、实盘运行日志亦落此处的子目录）
└── backup/                  数据库与文件存储的手动/定时备份产物
```

文件存储约定：

| 目录 | 承载内容 | 数据库引用方式 |
|------|----------|----------------|
| strategies/ | 策略代码文件（.py），按策略 id + 版本命名 | strategies.file_path 保存相对路径 |
| knowledge/ | 知识库原始文档（笔记 / 论文 / 研报） | kb_documents.file_path 保存相对路径 |
| reports/ | 回测明细与报告等大体积产物 | backtest_results.trades_path / report_path 保存相对路径 |
| market_lake/parquet/ | 历史行情、因子截面、回测面板等列式数据 | SQLite 仅保存产物路径或运行记录，批量分析由 DuckDB 查询 Parquet |
| logs/ | CLI 会话日志、实盘运行日志 | cli_sessions.log_path、live_runs.log_path 保存相对路径 |

### 1.3 表分组总览

全部业务表共 44 张，另有 3 张 FTS5 虚拟表（第 4 章单独描述）。主键约定：**所有业务表统一使用自增整型主键 id（INTEGER PRIMARY KEY AUTOINCREMENT 语义，下文表格中不再重复列出）**。

| 分组 | 表名 | 用途 | 数据量级 |
|------|------|------|----------|
| 通用 | settings | key-value 系统设置 | 配置级（百条以内） |
| 市场分析 | news_items | 新闻条目（四类：国内/国外/财经/公司） | 时序级（每日数百条，持续增长） |
| 市场分析 | watchlist_group | 自选分组 | 配置级（十条级） |
| 市场分析 | watchlist | 个性化自选标的 | 配置级（百条级） |
| 市场分析 | resource_pools | 资源池定义 | 配置级（十条～百条） |
| 市场分析 | resource_pool_items | 资源池标的明细 | 配置级（百条～千条） |
| 市场分析 | security_master | 本地证券主数据与模糊输入索引 | 配置级（千条～万条） |
| 市场分析 | stock_relations | 个股/板块关联关系（板块成分/产业链/概念/共现） | 配置级～日志级（万条级） |
| 市场分析 | recommend_tasks | 股票推荐任务（快速过滤/大模型/组合三路径） | 日志级（每次推荐一条） |
| 市场分析 | recommend_results | 推荐结果明细 | 日志级（每次数十条） |
| 市场分析 | recommend_templates | 股票推荐参数模板 | 配置级（十条级） |
| 市场分析 | model_reports | 模型市场分析报告 | 日志级（每日数条） |
| 市场分析 | papers | 量化论文索引与收藏 | 配置级（千条级） |
| 市场分析 | factor_definitions | 因子定义 | 配置级（十条级） |
| 市场分析 | factor_metrics_daily | 因子日度有效性指标 | 时序级（因子 × 交易日） |
| 市场分析 | factor_alerts | 因子有效性告警 | 日志级（告警事件） |
| 市场分析 | qlib_runs | Qlib 运行记录 | 日志级（每次运行一条） |
| 策略构建 | strategies | 策略元信息与版本 | 配置级（百条级） |
| 策略构建 | cli_sessions | CLI 构建会话（trae / workbuddy） | 日志级（每次构建一条） |
| 策略仿真 | backtest_tasks | 回测任务 | 日志级（每次回测一条） |
| 策略仿真 | backtest_results | 回测结果（绩效/曲线/明细路径） | 日志级（与任务一对一） |
| AI工作台 | quant_workflow_runs | 量化闭环运行记录 | 日志级（每次保存一条） |
| AI工作台 | quant_workflow_steps | 闭环步骤快照 | 日志级（运行 × 阶段） |
| AI工作台 | quant_workflow_artifacts | 闭环产物引用 | 日志级（运行 × 产物） |
| AI工作台 | ai_workspace_sessions | AI 操作台项目会话 | 日志级（每次新建会话一条） |
| AI工作台 | ai_workspace_messages | AI 操作台消息历史 | 日志级（会话 × 消息） |
| 策略仿真 | paper_accounts | 模拟盘账户 | 配置级（个位数～十条） |
| 策略仿真 | paper_orders | 模拟盘委托 | 时序级（随交易持续增长） |
| 策略仿真 | paper_trades | 模拟盘成交记录 | 时序级（随交易持续增长） |
| 策略仿真 | paper_positions | 模拟盘持仓快照 | 配置级（账户数 × 标的数） |
| 策略仿真 | paper_nav_history | 模拟盘净值曲线 | 时序级（账户数 × 交易日） |
| 实盘 | live_configs | 实盘配置 | 配置级（十条级） |
| 实盘 | live_runs | 实盘运行记录 | 日志级（每次启停一条） |
| 实盘 | live_orders | 实盘委托 | 时序级（随交易持续增长） |
| 知识库 | kb_categories | 知识库分类树 | 配置级（百条级） |
| 知识库 | kb_documents | 知识库文档索引 | 配置级（千条级） |
| 知识库 | kb_document_chunks | 知识库文档分块 | 随文档增长（每篇数段～数十段） |
| 知识库 | kb_qa_sessions | 知识库问答会话元数据 | 配置级（百条级） |
| 知识库 | kb_qa_history | 知识库问答历史 | 日志级（每次问答一组） |
| 知识库 | remote_sources | 远程知识源（飞书/腾讯 ima 等） | 配置级（十条级） |
| 知识库 | remote_docs_cache | 远程文档缓存 | 日志级（随同步增长，可重建） |
| 定时任务 | scheduled_jobs | 定时任务定义 | 配置级（百条级） |
| 定时任务 | job_executions | 定时任务执行历史 | 时序级（每次触发一条，增长最快） |
| 模型配置 | llm_models | LLM 模型配置 | 配置级（十条级） |
| 模型配置 | mcp_services | MCP 服务配置 | 配置级（十条级） |
| 模型配置 | skills | Skill 配置 | 配置级（十条级） |

---

## 2. 表结构设计

字段类型统一使用 SQLite 习惯写法：INTEGER（整型，兼做布尔 0/1）、TEXT（文本，兼做 ISO8601 时间与 JSON 字符串）、REAL（浮点，用于价格/金额/权重等）。时间字段一律为 TEXT，存 UTC ISO8601 字符串（详见 6.2）。

### 2.1 通用

#### settings（系统设置，key-value）

| 字段名 | 类型 | 约束/默认 | 说明 |
|--------|------|-----------|------|
| id | INTEGER | 主键，自增 | 自增主键 |
| key | TEXT | NOT NULL，UNIQUE | 设置项键名，点分命名（如 news.retain_days） |
| value | TEXT | NOT NULL | 设置项值（统一以文本存储） |
| value_type | TEXT | NOT NULL，默认 'string' | 值类型标注：string / int / float / bool / json |
| description | TEXT | | 设置项人类可读说明 |
| updated_at | TEXT | NOT NULL | 最近更新时间（UTC） |

说明：与 a001_news_track 的 settings 表同构，三级配置（默认值 → 环境变量 → 数据库）中的最高优先级持久层。

### 2.2 市场分析

#### news_items（新闻条目）

| 字段名 | 类型 | 约束/默认 | 说明 |
|--------|------|-----------|------|
| id | INTEGER | 主键，自增 | 自增主键 |
| source | TEXT | NOT NULL | 新闻来源名称（如东方财富/新浪/金十） |
| category | TEXT | NOT NULL | 新闻分类，枚举：国内 / 国外 / 财经 / 公司 |
| title | TEXT | NOT NULL | 新闻标题 |
| summary | TEXT | | 新闻摘要（正文截取或模型生成） |
| url | TEXT | NOT NULL | 原文链接 |
| published_at | TEXT | NOT NULL | 发布时间（UTC） |
| fetched_at | TEXT | NOT NULL | 抓取入库时间（UTC） |
| keywords | TEXT | | 关键词列表，JSON 数组（如 ["降准","银行"]） |
| dedup_hash | TEXT | NOT NULL，UNIQUE | 去重哈希（标题+链接或正文的摘要哈希），重复抓取直接跳过 |
| sentiment | REAL | | 情绪分（-1.0 ～ 1.0，jieba/LLM 分析产物，可空） |

说明：dedup_hash 唯一约束承担入库去重；标题与摘要通过触发器同步至 news_items_fts（见第 4 章）。

#### watchlist_group（自选分组）

| 字段名 | 类型 | 约束/默认 | 说明 |
|--------|------|-----------|------|
| id | INTEGER | 主键，自增 | 自增主键 |
| name | TEXT | NOT NULL，UNIQUE | 分组名称（如"核心持仓"、"观察池"） |
| sort_order | INTEGER | NOT NULL，默认 0 | 分组展示排序 |
| created_at | TEXT | NOT NULL | 创建时间（UTC） |
| updated_at | TEXT | NOT NULL | 更新时间（UTC） |

#### watchlist（个性化自选标的）

| 字段名 | 类型 | 约束/默认 | 说明 |
|--------|------|-----------|------|
| id | INTEGER | 主键，自增 | 自增主键 |
| group_id | INTEGER | NOT NULL，外键 → watchlist_group.id | 所属分组（级联删除） |
| symbol | TEXT | NOT NULL | 标的代码（如 600519） |
| market | TEXT | NOT NULL | 市场：SH / SZ / BJ |
| name | TEXT | NOT NULL | 标的名称 |
| sort_order | INTEGER | NOT NULL，默认 0 | 组内排序 |
| remark | TEXT | | 自选备注 |
| created_at | TEXT | NOT NULL | 创建时间（UTC） |
| updated_at | TEXT | NOT NULL | 更新时间（UTC） |

约束：同一分组内 (group_id, symbol) 唯一（唯一索引保证）。

#### resource_pools（资源池定义）

| 字段名 | 类型 | 约束/默认 | 说明 |
|--------|------|-----------|------|
| id | INTEGER | 主键，自增 | 自增主键 |
| name | TEXT | NOT NULL，UNIQUE | 资源池名称 |
| description | TEXT | | 资源池说明 |
| source_type | TEXT | NOT NULL，默认 manual | 来源类型，manual / recommendation / import 等 |
| created_at | TEXT | NOT NULL | 创建时间（UTC） |
| updated_at | TEXT | NOT NULL | 更新时间（UTC） |

说明：资源池用于沉淀研究候选池、推荐候选池和人工观察池，前端支持手工维护和 CSV/Excel 导入。

#### resource_pool_items（资源池标的）

| 字段名 | 类型 | 约束/默认 | 说明 |
|--------|------|-----------|------|
| id | INTEGER | 主键，自增 | 自增主键 |
| pool_id | INTEGER | NOT NULL，外键 → resource_pools.id | 所属资源池（级联删除） |
| symbol | TEXT | NOT NULL | 标的代码 |
| market | TEXT | NOT NULL，默认 CN | 市场标识 |
| name | TEXT | NOT NULL，默认空字符串 | 标的名称 |
| weight | REAL | NOT NULL，默认 1.0 | 资源池权重 |
| tags | TEXT | | 标签，逗号分隔或 JSON 文本 |
| remark | TEXT | | 备注 |
| source | TEXT | NOT NULL，默认 manual | 标的来源，manual / import / recommendation 等 |
| created_at | TEXT | NOT NULL | 创建时间（UTC） |
| updated_at | TEXT | NOT NULL | 更新时间（UTC） |

约束：同一资源池内 (pool_id, symbol) 唯一，重复导入按最新名称、权重、标签、备注和来源更新。

#### security_master（证券主数据）

| 字段名 | 类型 | 约束/默认 | 说明 |
|--------|------|-----------|------|
| id | INTEGER | 主键，自增 | 自增主键 |
| symbol | TEXT | NOT NULL | 标准代码，A 股保存 6 位代码，美股保存 ticker |
| market | TEXT | NOT NULL | 市场标识：CN / US |
| name | TEXT | NOT NULL | 标的名称 |
| abbr | TEXT | NOT NULL，默认空字符串 | 简称或拼音首字母 |
| pinyin | TEXT | NOT NULL，默认空字符串 | 拼音检索字段 |
| aliases | TEXT | NOT NULL，默认空字符串 | 别名，使用 `|` 分隔 |
| exchange | TEXT | NOT NULL，默认空字符串 | 交易所或数据源市场标识 |
| asset_type | TEXT | NOT NULL，默认 stock | 资产类型 |
| is_active | INTEGER | NOT NULL，默认 1 | 是否启用 |
| updated_at | TEXT | NOT NULL | 最近更新时间（UTC） |

约束：`(symbol, market)` 唯一。初始种子位于 `egs/examples/data/security_master.seed.csv`，用于离线支持代码、名称、拼音和别名模糊输入；后续全市场主数据可通过导入或数据源刷新写入该表。

#### stock_relations（关联关系）

| 字段名 | 类型 | 约束/默认 | 说明 |
|--------|------|-----------|------|
| id | INTEGER | 主键，自增 | 自增主键 |
| relation_type | TEXT | NOT NULL | 关系类型，枚举：industry / concept / supply_chain / shareholder / news_cooccurrence / correlation |
| source_code | TEXT | NOT NULL | 关系起点编码（股票代码，或板块/概念编码） |
| target_code | TEXT | NOT NULL | 关系终点编码（股票代码，或板块/概念编码） |
| weight | REAL | NOT NULL，默认 1.0 | 关系权重（共现强度/置信度，0～1） |
| source_note | TEXT | | 来源说明（如"申万行业成分"、"近 30 日新闻共现"） |
| valid | INTEGER | NOT NULL，默认 1 | 是否有效（软删除标记） |
| created_at | TEXT | NOT NULL | 创建时间（UTC） |

说明：关联关系图的前置数据表，起点/终点统一用编码表示，股票、板块、概念、机构和事件节点均可入表；新闻共现和收益相关类关系由分析任务定期重建（先置 valid=0 再写入新批次）。

#### recommend_tasks（推荐任务）

| 字段名 | 类型 | 约束/默认 | 说明 |
|--------|------|-----------|------|
| id | INTEGER | 主键，自增 | 自增主键 |
| path | TEXT | NOT NULL | 推荐路径，枚举：快速过滤 / 大模型 / 组合 |
| conditions | TEXT | NOT NULL | 筛选条件 JSON（板块范围、指标阈值、形态参数等） |
| model_name | TEXT | | 本次使用的模型标识（大模型路径填写，快速过滤可空） |
| status | TEXT | NOT NULL，默认 '排队' | 任务状态，枚举：排队 / 运行中 / 完成 / 失败 |
| error_msg | TEXT | | 失败原因 |
| created_at | TEXT | NOT NULL | 创建时间（UTC） |
| started_at | TEXT | | 实际开始时间（UTC） |
| finished_at | TEXT | | 实际结束时间（UTC） |

#### recommend_results（推荐结果）

| 字段名 | 类型 | 约束/默认 | 说明 |
|--------|------|-----------|------|
| id | INTEGER | 主键，自增 | 自增主键 |
| task_id | INTEGER | NOT NULL，外键 → recommend_tasks.id | 所属推荐任务（级联删除） |
| rank | INTEGER | NOT NULL | 推荐排名（1 起） |
| symbol | TEXT | NOT NULL | 标的代码 |
| name | TEXT | NOT NULL | 标的名称 |
| score | REAL | NOT NULL | 综合评分（0～100） |
| reason | TEXT | | 推荐理由（模型生成或规则命中说明） |
| factors | TEXT | | 因子明细 JSON（形态/技术指标/消息面各分项得分） |
| created_at | TEXT | NOT NULL | 生成时间（UTC） |

#### recommend_templates（推荐参数模板）

| 字段名 | 类型 | 约束/默认 | 说明 |
|--------|------|-----------|------|
| id | INTEGER | 主键，自增 | 自增主键 |
| name | TEXT | NOT NULL，UNIQUE | 模板名称 |
| plan | TEXT | NOT NULL | 推荐方案，枚举：defensive / momentum / quality / event / chan / balanced |
| path | TEXT | NOT NULL | 分析路径，枚举：quick / deep |
| limit_count | INTEGER | NOT NULL，默认 10 | 推荐数量上限 |
| universe_text | TEXT | NOT NULL，默认空字符串 | 股票池原始输入，逗号分隔 |
| created_at | TEXT | NOT NULL | 创建时间（UTC） |
| updated_at | TEXT | NOT NULL | 更新时间（UTC） |

说明：用于保存股票推荐页常用观察模板，可按名称更新并在页面中按更新时间倒序加载。

#### model_reports（模型市场分析报告）

| 字段名 | 类型 | 约束/默认 | 说明 |
|--------|------|-----------|------|
| id | INTEGER | 主键，自增 | 自增主键 |
| title | TEXT | NOT NULL | 报告标题 |
| report_type | TEXT | NOT NULL | 报告类型，枚举：日报 / 周报 / 板块分析 / 个股分析 / 自定义 |
| content | TEXT | NOT NULL | 报告正文（Markdown） |
| model_name | TEXT | NOT NULL | 生成模型标识 |
| generated_at | TEXT | NOT NULL | 生成时间（UTC） |
| file_path | TEXT | | 归档文件相对路径（data/reports/model/ 下，正文过大时冗余存档） |

#### papers（量化论文）

| 字段名 | 类型 | 约束/默认 | 说明 |
|--------|------|-----------|------|
| id | INTEGER | 主键，自增 | 自增主键 |
| title | TEXT | NOT NULL | 论文标题 |
| authors | TEXT | | 作者列表，JSON 数组 |
| abstract | TEXT | | 摘要 |
| source | TEXT | | 来源（arXiv / SSRN / 期刊名等） |
| url | TEXT | | 论文链接 |
| pdf_path | TEXT | | 本地 PDF 相对路径（已下载并转入知识库时填写） |
| published_at | TEXT | | 发表时间（UTC，粒度到日） |
| is_favorite | INTEGER | NOT NULL，默认 0 | 收藏标记：0 否 / 1 是 |
| fetched_at | TEXT | NOT NULL | 抓取入库时间（UTC） |

说明：收藏且下载的论文同步在 kb_documents（知识库）建立索引记录，二者通过 file_path 指向同一份 PDF。

### 2.3 策略构建

#### strategies（策略元信息）

| 字段名 | 类型 | 约束/默认 | 说明 |
|--------|------|-----------|------|
| id | INTEGER | 主键，自增 | 自增主键 |
| name | TEXT | NOT NULL | 策略名称 |
| version | TEXT | NOT NULL，默认 'v1' | 版本号（同一名称多版本并存） |
| description | TEXT | | 策略描述 |
| param_schema | TEXT | | 参数定义 JSON（参数名/类型/默认值/取值范围，供前端渲染表单） |
| file_path | TEXT | NOT NULL | 策略代码文件相对路径（data/strategies/ 下） |
| interface_type | TEXT | NOT NULL，默认 '统一接口' | 接口类型，枚举：统一接口（Strategy 基类契约）/ 自定义 |
| status | TEXT | NOT NULL，默认 '草稿' | 策略状态，枚举：草稿 / 可用 / 停用 |
| origin | TEXT | NOT NULL | 来源，枚举：上传 / CLI 生成 / 手动创建 |
| tags | TEXT | | 标签 JSON 数组（如 ["趋势","日内"]） |
| created_at | TEXT | NOT NULL | 创建时间（UTC） |
| updated_at | TEXT | NOT NULL | 更新时间（UTC） |

约束：(name, version) 唯一（唯一索引保证）。

#### cli_sessions（CLI 构建会话）

| 字段名 | 类型 | 约束/默认 | 说明 |
|--------|------|-----------|------|
| id | INTEGER | 主键，自增 | 自增主键 |
| cli_type | TEXT | NOT NULL | CLI 类型，枚举：trae / workbuddy |
| requirement | TEXT | NOT NULL | 需求描述（用户输入的策略需求文本） |
| status | TEXT | NOT NULL，默认 '进行中' | 会话状态，枚举：进行中 / 成功 / 失败 |
| strategy_id | INTEGER | 外键 → strategies.id | 产物策略外键，生成成功并入库后回填（可空） |
| log_path | TEXT | | 会话日志文件相对路径（data/logs/ 下） |
| error_msg | TEXT | | 失败原因 |
| created_at | TEXT | NOT NULL | 会话创建时间（UTC） |
| finished_at | TEXT | | 会话结束时间（UTC） |

说明：先建会话、后产策略，strategy_id 为可空外键，成功后回填，避免与 strategies 形成插入顺序死锁。

### 2.4 策略仿真

#### backtest_tasks（回测任务）

| 字段名 | 类型 | 约束/默认 | 说明 |
|--------|------|-----------|------|
| id | INTEGER | 主键，自增 | 自增主键 |
| strategy_id | INTEGER | NOT NULL，外键 → strategies.id | 回测策略 |
| engine | TEXT | NOT NULL，默认 simple | 回测引擎标识，当前支持 simple 诊断与 qlib 可选接入 |
| symbols | TEXT | NOT NULL | 标的列表 JSON 数组（如 ["600519","000858"]） |
| start_date | TEXT | NOT NULL | 回测区间开始日（YYYY-MM-DD） |
| end_date | TEXT | NOT NULL | 回测区间结束日（YYYY-MM-DD） |
| initial_cash | REAL | NOT NULL | 初始资金（元） |
| commission_rate | REAL | NOT NULL，默认 0.0003 | 交易费率（比例） |
| params | TEXT | | 解析后的策略实参 JSON；内部保留执行条件与不可变试验快照，API 分别以 params 和 parameter_snapshot 返回；旧任务快照为空 |
| status | TEXT | NOT NULL，默认 '排队' | 任务状态，枚举：排队 / 运行中 / 完成 / 失败 |
| error_msg | TEXT | | 失败原因 |
| created_at | TEXT | NOT NULL | 任务创建时间（UTC） |
| started_at | TEXT | | 实际开始执行时间（UTC） |
| finished_at | TEXT | | 实际结束时间（UTC） |

#### backtest_results（回测结果）

| 字段名 | 类型 | 约束/默认 | 说明 |
|--------|------|-----------|------|
| id | INTEGER | 主键，自增 | 自增主键 |
| task_id | INTEGER | NOT NULL，UNIQUE，外键 → backtest_tasks.id | 对应回测任务（一对一，级联删除） |
| metrics | TEXT | NOT NULL | 绩效指标 JSON（收益、年化波动率、最大回撤/Calmar/VaR、Sharpe/Sortino、交易盈亏、手续费、换手、持仓暴露和回撤持续/恢复等） |
| equity_curve | TEXT | NOT NULL | 收益曲线 JSON（日期 + 净值/总资产序列） |
| trades_path | TEXT | | 交易明细文件相对路径（data/reports/backtest/ 下的 JSON 文件，明细较大不入库） |
| report_path | TEXT | | 绩效报告文件相对路径（HTML/Markdown） |
| created_at | TEXT | NOT NULL | 结果生成时间（UTC） |

#### factor_definitions（因子定义）

| 字段名 | 类型 | 约束/默认 | 说明 |
|--------|------|-----------|------|
| id | INTEGER | 主键，自增 | 自增主键 |
| factor_key | TEXT | NOT NULL，UNIQUE | 因子唯一键 |
| name | TEXT | NOT NULL | 因子中文名 |
| category | TEXT | NOT NULL，默认 style | 因子分类 |
| expression_key | TEXT | NOT NULL | 因子计算表达式键，映射服务层计算器 |
| description | TEXT | | 因子说明 |
| direction | TEXT | NOT NULL，默认 positive | 因子方向 |
| horizon_days | INTEGER | NOT NULL，默认 5 | 前瞻收益窗口 |
| rebalance_frequency | TEXT | NOT NULL，默认 daily | 观察/调仓频率 |
| enabled | INTEGER | NOT NULL，默认 1 | 是否启用 |
| source | TEXT | NOT NULL，默认 config | 定义来源 |
| threshold_ic | REAL | NOT NULL，默认 0.02 | RankIC 告警阈值 |
| threshold_coverage | REAL | NOT NULL，默认 0.7 | 覆盖率告警阈值 |
| created_at | TEXT | NOT NULL | 创建时间（UTC） |
| updated_at | TEXT | NOT NULL | 更新时间（UTC） |

#### factor_metrics_daily（因子日度指标）

| 字段名 | 类型 | 约束/默认 | 说明 |
|--------|------|-----------|------|
| id | INTEGER | 主键，自增 | 自增主键 |
| factor_key | TEXT | NOT NULL，外键 → factor_definitions.factor_key | 因子键 |
| metric_date | TEXT | NOT NULL | 指标日期 |
| universe | TEXT | NOT NULL | 股票池快照 |
| ic / rank_ic / icir | REAL | | 有效性指标 |
| hit_rate | REAL | | 多空方向命中率 |
| long_short_return | REAL | | 高低分位多空收益 |
| coverage | REAL | | 可计算覆盖率 |
| turnover | REAL | | 因子排序换手 |
| quantile_monotonicity | REAL | | 分位收益单调性 |
| sample_size | INTEGER | NOT NULL，默认 0 | 滚动样本数量 |
| metadata | TEXT | | 扩展 JSON |
| created_at | TEXT | NOT NULL | 写入时间（UTC） |

#### factor_alerts（因子告警）

| 字段名 | 类型 | 约束/默认 | 说明 |
|--------|------|-----------|------|
| id | INTEGER | 主键，自增 | 自增主键 |
| factor_key | TEXT | NOT NULL，外键 → factor_definitions.factor_key | 因子键 |
| severity | TEXT | NOT NULL | 告警级别 |
| title | TEXT | NOT NULL | 告警标题 |
| message | TEXT | NOT NULL | 告警说明 |
| status | TEXT | NOT NULL，默认 open | 处理状态 |
| triggered_at | TEXT | NOT NULL | 触发时间（UTC） |
| resolved_at | TEXT | | 解决时间（UTC） |

#### qlib_runs（Qlib运行记录）

| 字段名 | 类型 | 约束/默认 | 说明 |
|--------|------|-----------|------|
| id | INTEGER | 主键，自增 | 自增主键 |
| run_type | TEXT | NOT NULL | 运行类型，如 workflow/backtest/factor |
| status | TEXT | NOT NULL，默认 pending | 运行状态，包含 running/finished/failed/blocked |
| workflow_path | TEXT | | Qlib workflow 配置路径 |
| provider_uri | TEXT | | Qlib 数据目录 |
| params / metrics / artifacts | TEXT | | 参数、指标和产物 JSON；Qlib实验页写入配置参数、环境诊断、qrun 返回码、执行耗时、输出尾部、训练指标、组合回测指标、产物根目录和产物文件摘要 |
| error_msg | TEXT | | 阻塞原因或失败原因；pyqlib 缺失、provider_uri、workflow_path 或 qrun 未就绪时记录明确下一步 |
| created_at / started_at / finished_at | TEXT | | 生命周期时间 |

#### quant_workflow_runs（量化闭环运行记录）

| 字段名 | 类型 | 约束/默认 | 说明 |
|--------|------|-----------|------|
| id | INTEGER | 主键，自增 | 自增主键 |
| mode | TEXT | NOT NULL | 闭环模式，simulation 或 live |
| sop_id | TEXT | NOT NULL | SOP 标识，来自配置文件 |
| title | TEXT | NOT NULL | 运行标题 |
| status | TEXT | NOT NULL，默认 in_progress | 总体状态 |
| context | TEXT | | 运行上下文 JSON，记录策略、回测、账户和实盘运行 ID |
| summary | TEXT | | 闭环摘要 |
| created_at | TEXT | NOT NULL | 创建时间（UTC） |
| updated_at | TEXT | NOT NULL | 更新时间（UTC） |

#### quant_workflow_steps（闭环步骤快照）

| 字段名 | 类型 | 约束/默认 | 说明 |
|--------|------|-----------|------|
| id | INTEGER | 主键，自增 | 自增主键 |
| run_id | INTEGER | NOT NULL，外键 → quant_workflow_runs.id | 所属闭环运行（级联删除） |
| step_order | INTEGER | NOT NULL | SOP 阶段顺序 |
| stage_key | TEXT | NOT NULL | 阶段键 |
| title | TEXT | NOT NULL | 阶段标题 |
| status | TEXT | NOT NULL | 阶段状态 |
| evidence | TEXT | | 阶段证据摘要 |
| artifacts | TEXT | | 关联产物标题 JSON |
| created_at | TEXT | NOT NULL | 写入时间（UTC） |

#### quant_workflow_artifacts（闭环产物引用）

| 字段名 | 类型 | 约束/默认 | 说明 |
|--------|------|-----------|------|
| id | INTEGER | 主键，自增 | 自增主键 |
| run_id | INTEGER | NOT NULL，外键 → quant_workflow_runs.id | 所属闭环运行（级联删除） |
| artifact_type | TEXT | NOT NULL | 产物类型，如 backtest、factor_monitor、paper_account、diagnosis |
| title | TEXT | NOT NULL | 产物标题 |
| ref_type | TEXT | | 引用资源类型 |
| ref_id | TEXT | | 引用资源 ID |
| summary | TEXT | | 产物摘要 |
| data | TEXT | | 产物结构化 JSON |
| created_at | TEXT | NOT NULL | 写入时间（UTC） |

#### ai_workspace_sessions（AI 操作台会话）

| 字段名 | 类型 | 约束/默认 | 说明 |
|--------|------|-----------|------|
| id | INTEGER | 主键，自增 | 自增主键 |
| project_name | TEXT | NOT NULL，默认 money_maker | 项目或工作区名称 |
| title | TEXT | NOT NULL | 会话标题 |
| session_type | TEXT | NOT NULL，默认 chat | 会话类型，chat / project 等 |
| status | TEXT | NOT NULL，默认 active | 会话状态 |
| created_at | TEXT | NOT NULL | 创建时间（UTC） |
| updated_at | TEXT | NOT NULL | 更新时间（UTC） |

#### ai_workspace_messages（AI 操作台消息）

| 字段名 | 类型 | 约束/默认 | 说明 |
|--------|------|-----------|------|
| id | INTEGER | 主键，自增 | 自增主键 |
| session_id | INTEGER | NOT NULL，外键 → ai_workspace_sessions.id | 所属会话（级联删除） |
| role | TEXT | NOT NULL | 消息角色，user / assistant / system |
| content | TEXT | NOT NULL | 消息正文 |
| metadata | TEXT | | 扩展 JSON |
| created_at | TEXT | NOT NULL | 创建时间（UTC） |

#### paper_accounts（模拟盘账户）

| 字段名 | 类型 | 约束/默认 | 说明 |
|--------|------|-----------|------|
| id | INTEGER | 主键，自增 | 自增主键 |
| name | TEXT | NOT NULL，UNIQUE | 账户名称 |
| strategy_id | INTEGER | 外键 → strategies.id | 绑定策略（手动干预型账户可空） |
| initial_cash | REAL | NOT NULL | 初始资金（元） |
| current_cash | REAL | NOT NULL | 当前可用资金（元） |
| status | TEXT | NOT NULL，默认 '运行中' | 账户状态，枚举：运行中 / 已暂停 / 已停止 |
| created_at | TEXT | NOT NULL | 创建时间（UTC） |
| updated_at | TEXT | NOT NULL | 更新时间（UTC） |

说明：current_cash 类型为 REAL（上表首格笔误更正为 REAL），当前市值与总资产不落本表，以 paper_positions 与 paper_nav_history 的最新记录为准。

#### paper_orders（模拟盘委托）

| 字段名 | 类型 | 约束/默认 | 说明 |
|--------|------|-----------|------|
| id | INTEGER | 主键，自增 | 自增主键 |
| account_id | INTEGER | NOT NULL，外键 → paper_accounts.id | 所属账户（级联删除） |
| symbol | TEXT | NOT NULL | 标的代码 |
| market | TEXT | NOT NULL | 市场：SH / SZ / BJ |
| direction | TEXT | NOT NULL | 方向，枚举：买 / 卖 |
| order_type | TEXT | NOT NULL，默认 '限价' | 委托类型，枚举：限价 / 市价 |
| price | REAL | | 委托价格（市价单可空） |
| quantity | INTEGER | NOT NULL | 委托数量（股） |
| filled_qty | INTEGER | NOT NULL，默认 0 | 已成交数量（股） |
| avg_price | REAL | | 成交均价 |
| status | TEXT | NOT NULL，默认 '待撮合' | 委托状态机，枚举：待撮合 / 部分成交 / 已成交 / 已撤销 / 已拒绝 |
| created_at | TEXT | NOT NULL | 委托时间（UTC） |
| updated_at | TEXT | NOT NULL | 最近状态变更时间（UTC） |

#### paper_trades（模拟盘成交记录）

| 字段名 | 类型 | 约束/默认 | 说明 |
|--------|------|-----------|------|
| id | INTEGER | 主键，自增 | 自增主键 |
| account_id | INTEGER | NOT NULL，外键 → paper_accounts.id | 所属账户（冗余存储，便于直查） |
| order_id | INTEGER | NOT NULL，外键 → paper_orders.id | 来源委托（级联删除） |
| symbol | TEXT | NOT NULL | 标的代码 |
| direction | TEXT | NOT NULL | 方向：买 / 卖 |
| price | REAL | NOT NULL | 成交价格（元） |
| quantity | INTEGER | NOT NULL | 成交数量（股） |
| traded_at | TEXT | NOT NULL | 成交时间（UTC） |

#### paper_positions（模拟盘持仓快照）

| 字段名 | 类型 | 约束/默认 | 说明 |
|--------|------|-----------|------|
| id | INTEGER | 主键，自增 | 自增主键 |
| account_id | INTEGER | NOT NULL，外键 → paper_accounts.id | 所属账户（级联删除） |
| symbol | TEXT | NOT NULL | 标的代码 |
| quantity | INTEGER | NOT NULL，默认 0 | 持仓数量（股） |
| available_qty | INTEGER | NOT NULL，默认 0 | 可用数量（T+1 规则扣除在途卖出） |
| avg_cost | REAL | NOT NULL，默认 0.0 | 持仓均价（元/股） |
| market_value | REAL | NOT NULL，默认 0.0 | 最新市值（元，随行情刷新） |
| updated_at | TEXT | NOT NULL | 快照更新时间（UTC） |

约束：(account_id, symbol) 唯一（每账户每标的一行，增量更新）。

#### paper_nav_history（模拟盘净值曲线）

| 字段名 | 类型 | 约束/默认 | 说明 |
|--------|------|-----------|------|
| id | INTEGER | 主键，自增 | 自增主键 |
| account_id | INTEGER | NOT NULL，外键 → paper_accounts.id | 所属账户（级联删除） |
| nav_date | TEXT | NOT NULL | 净值日期（YYYY-MM-DD） |
| nav | REAL | NOT NULL | 单位净值（初始 1.0） |
| total_asset | REAL | NOT NULL | 总资产（元） |
| cash | REAL | NOT NULL | 现金（元） |
| market_value | REAL | NOT NULL | 持仓市值（元） |
| created_at | TEXT | NOT NULL | 写入时间（UTC） |

约束：(account_id, nav_date) 唯一（每账户每交易日一条）。

### 2.5 实盘

#### live_configs（实盘配置）

| 字段名 | 类型 | 约束/默认 | 说明 |
|--------|------|-----------|------|
| id | INTEGER | 主键，自增 | 自增主键 |
| name | TEXT | NOT NULL，UNIQUE | 配置名称 |
| strategy_id | INTEGER | NOT NULL，外键 → strategies.id | 运行策略（须为"可用"状态） |
| symbols | TEXT | NOT NULL | 交易标的列表 JSON 数组 |
| capital_params | TEXT | NOT NULL | 资金参数 JSON（每标的最大仓位/单笔金额/总资金上限等） |
| risk_params | TEXT | NOT NULL | 风控参数 JSON（止损止盈线/单日最大亏损/最大持仓数等） |
| broker_adapter | TEXT | NOT NULL，默认 '模拟通道' | 券商适配器类型，枚举：模拟通道（默认）/ 预留真实券商适配器标识 |
| status | TEXT | NOT NULL，默认 '停用' | 配置状态，枚举：启用 / 停用 |
| created_at | TEXT | NOT NULL | 创建时间（UTC） |
| updated_at | TEXT | NOT NULL | 更新时间（UTC） |

说明：安全约定——broker_adapter 默认且仅默认绑定模拟通道；真实券商通道需在设置中显式解锁后可选（对应总体设计"实盘安全"原则）。

#### live_runs（实盘运行记录）

| 字段名 | 类型 | 约束/默认 | 说明 |
|--------|------|-----------|------|
| id | INTEGER | 主键，自增 | 自增主键 |
| config_id | INTEGER | NOT NULL，外键 → live_configs.id | 对应实盘配置（级联删除） |
| status | TEXT | NOT NULL，默认 'running' | 运行状态机，枚举：starting / running / paused / stopping / stopped / error；展示层转换为中文状态标签 |
| started_at | TEXT | NOT NULL | 启动时间（UTC） |
| stopped_at | TEXT | | 停止时间（UTC，未停止为空） |
| log_path | TEXT | | 运行日志文件相对路径（data/logs/ 下） |
| error_msg | TEXT | | 异常原因（状态为"异常"时填写） |
| summary | TEXT | | 停止时写入的运行摘要 JSON（盈亏/委托数/成交数） |

#### live_orders（实盘委托）

| 字段名 | 类型 | 约束/默认 | 说明 |
|--------|------|-----------|------|
| id | INTEGER | 主键，自增 | 自增主键 |
| run_id | INTEGER | NOT NULL，外键 → live_runs.id | 所属运行批次（级联删除） |
| config_id | INTEGER | NOT NULL，外键 → live_configs.id | 冗余配置外键（便于按配置直查） |
| symbol | TEXT | NOT NULL | 标的代码 |
| market | TEXT | NOT NULL | 市场：SH / SZ / BJ |
| direction | TEXT | NOT NULL | 方向：买 / 卖 |
| order_type | TEXT | NOT NULL，默认 '限价' | 委托类型：限价 / 市价 |
| price | REAL | | 委托价格（市价单可空） |
| quantity | INTEGER | NOT NULL | 委托数量（股） |
| filled_qty | INTEGER | NOT NULL，默认 0 | 已成交数量（股） |
| avg_price | REAL | | 成交均价 |
| status | TEXT | NOT NULL，默认 '待报' | 委托状态机，枚举：待报 / 已报 / 部分成交 / 已成交 / 已撤销 / 已拒绝 / 未知 |
| adapter_order_no | TEXT | | 适配器侧委托单号（券商/模拟通道返回的原始编号，用于对账） |
| created_at | TEXT | NOT NULL | 委托时间（UTC） |
| updated_at | TEXT | NOT NULL | 最近状态变更时间（UTC） |

说明：成交明细复用委托行内 filled_qty/avg_price 表达，不另设 live_trades 表（实盘成交以适配器回报为准，逐笔回报以日志留痕；如后续需要逐笔明细再按 paper_trades 模式扩展）。

### 2.6 知识库

#### kb_categories（知识库分类树）

| 字段名 | 类型 | 约束/默认 | 说明 |
|--------|------|-----------|------|
| id | INTEGER | 主键，自增 | 自增主键 |
| name | TEXT | NOT NULL | 分类名称 |
| parent_id | INTEGER | NOT NULL，默认 0 | 父级分类外键（自引用 → kb_categories.id；0 表示根分类） |
| sort_order | INTEGER | NOT NULL，默认 0 | 同级排序 |
| created_at | TEXT | NOT NULL | 创建时间（UTC） |

#### kb_documents（知识库文档）

| 字段名 | 类型 | 约束/默认 | 说明 |
|--------|------|-----------|------|
| id | INTEGER | 主键，自增 | 自增主键 |
| title | TEXT | NOT NULL | 文档标题 |
| category_id | INTEGER | NOT NULL，外键 → kb_categories.id | 所属分类 |
| doc_type | TEXT | NOT NULL | 文档类型，枚举：论文 / 研报 / 笔记 |
| tags | TEXT | | 标签 JSON 数组 |
| file_path | TEXT | NOT NULL | 原始文件相对路径（data/knowledge/ 下） |
| summary | TEXT | | 摘要（提取或模型生成，用于列表与检索） |
| content | TEXT | | 正文纯文本（由文件提取，供 FTS5 索引；PDF 提取文本可能较长，属可接受范围） |
| origin | TEXT | | 来源说明（自建 / 论文收藏转入 / 研报下载 / 远程源缓存固化） |
| imported_at | TEXT | NOT NULL | 导入时间（UTC） |
| created_at | TEXT | NOT NULL | 创建时间（UTC） |
| updated_at | TEXT | NOT NULL | 更新时间（UTC） |

说明：与 a001_news_track 的 knowledge_items 同构升级；title/summary/content 三字段经触发器同步至 kb_documents_fts。

#### kb_document_chunks（知识库文档分块）

| 字段名 | 类型 | 约束/默认 | 说明 |
|--------|------|-----------|------|
| id | INTEGER | 主键，自增 | 自增主键 |
| doc_id | INTEGER | NOT NULL，外键 → kb_documents.id | 所属知识文档，随文档级联删除 |
| chunk_index | INTEGER | NOT NULL | 文档内分块序号 |
| heading | TEXT | | 分块标题，优先取 Markdown 标题或文档标题 |
| content | TEXT | NOT NULL | 分块正文，用于精确检索和 RAG 引用 |
| char_count | INTEGER | NOT NULL，默认 0 | 分块字符数 |
| created_at | TEXT | NOT NULL | 创建时间（UTC） |
| updated_at | TEXT | NOT NULL | 更新时间（UTC） |

约束：(doc_id, chunk_index) 唯一。说明：上传文档、笔记、论文摘要和远程文档入库后同步生成分块；旧文档由检索和知识库同步任务渐进回填。

#### kb_qa_sessions（知识库问答会话）

| 字段名 | 类型 | 约束/默认 | 说明 |
|--------|------|-----------|------|
| session_id | TEXT | 主键 | 问答会话 ID |
| name | TEXT | NOT NULL，默认空字符串 | 会话名称，未填写时由最近问题兜底展示 |
| summary | TEXT | NOT NULL，默认空字符串 | 会话摘要，未填写时由最近回答/问题兜底展示 |
| created_at | TEXT | NOT NULL | 创建时间（UTC） |
| updated_at | TEXT | NOT NULL | 最近问答或编辑时间（UTC） |

说明：保存问答会话元信息；问答时自动登记会话，用户可在页面保存名称与摘要，清空历史不删除会话元信息。

#### kb_qa_history（知识库问答历史）

| 字段名 | 类型 | 约束/默认 | 说明 |
|--------|------|-----------|------|
| id | INTEGER | 主键，自增 | 自增主键 |
| session_id | TEXT | NOT NULL，默认 default | 问答会话 ID，用于隔离追问上下文与清空当前会话 |
| question | TEXT | NOT NULL | 用户问题 |
| answer | TEXT | NOT NULL | 模型回答（Markdown） |
| cited_docs | TEXT | | 引用文档 JSON 数组（元素含文档 id/标题/命中片段） |
| model_name | TEXT | | 回答模型标识 |
| created_at | TEXT | NOT NULL | 问答时间（UTC） |

说明：按 session_id 查询最近问答作为 RAG 追问上下文；页面清空会话时仅删除对应 session_id 的历史。

#### remote_sources（远程知识源）

| 字段名 | 类型 | 约束/默认 | 说明 |
|--------|------|-----------|------|
| id | INTEGER | 主键，自增 | 自增主键 |
| source_type | TEXT | NOT NULL | 远程源类型，枚举：飞书 / 腾讯ima（可扩展） |
| name | TEXT | NOT NULL，UNIQUE | 远程源显示名称 |
| conn_config | TEXT | NOT NULL | 连接配置 JSON（含 MCP 服务地址/凭证引用等；凭证字段加密存储，见 6.5） |
| enabled | INTEGER | NOT NULL，默认 1 | 启用状态：0 停用 / 1 启用 |
| last_sync_at | TEXT | | 最近成功同步时间（UTC） |
| created_at | TEXT | NOT NULL | 创建时间（UTC） |
| updated_at | TEXT | NOT NULL | 更新时间（UTC） |

#### remote_docs_cache（远程文档缓存）

| 字段名 | 类型 | 约束/默认 | 说明 |
|--------|------|-----------|------|
| id | INTEGER | 主键，自增 | 自增主键 |
| source_id | INTEGER | NOT NULL，外键 → remote_sources.id | 所属远程源（级联删除） |
| remote_id | TEXT | NOT NULL | 远程文档唯一标识（飞书 token / ima 文档 id） |
| title | TEXT | NOT NULL | 文档标题 |
| summary | TEXT | | 摘要 |
| content | TEXT | | 缓存正文纯文本（供统一检索） |
| local_path | TEXT | | 已下载文件的相对路径（可选） |
| fetched_at | TEXT | NOT NULL | 最近抓取时间（UTC） |
| created_at | TEXT | NOT NULL | 首次缓存时间（UTC） |
| updated_at | TEXT | NOT NULL | 更新时间（UTC） |

约束：(source_id, remote_id) 唯一。说明：缓存表，可随时清除后由同步任务重建；用户"收藏固化"的远程文档会转为 kb_documents 正式记录。

### 2.7 定时任务

#### scheduled_jobs（定时任务定义）

| 字段名 | 类型 | 约束/默认 | 说明 |
|--------|------|-----------|------|
| id | INTEGER | 主键，自增 | 自增主键 |
| name | TEXT | NOT NULL，UNIQUE | 任务名称 |
| cron_expr | TEXT | NOT NULL | cron 表达式（五段式，APScheduler CronTrigger 风格；缺包时由内置轻量解析兜底） |
| job_type | TEXT | NOT NULL | 任务类型，枚举：新闻采集 / 行情更新 / 市场分析 / 股票推荐 / 模拟盘调度 / 交易日历更新 / 官方参考日历导入 / 交易所公告源核验 / 系统健康告警 / 数据维护 / 知识库同步 / 自定义 |
| job_params | TEXT | | 任务参数 JSON（与任务类型配套的实参；通用策略字段包括 trading_day_only、calendar_path、trading_calendar_path、trading_calendar、retry_times、retry_interval_seconds、timeout_seconds、timeout_minutes、timeout_mode、hard_timeout、mutex_group、executor_key；calendar_refresh 额外支持 source、market、range_start、range_end、trade_dates、write_full_trading_days；calendar_reference_refresh 额外支持 official_calendar_path/reference_calendar_path、range_start、range_end、holidays、trading_days、announcement_text、announcement_path、announcement_url、announcement_index_url、announcement_profiles_path、announcement_profile、announcement_link_keywords、announcement_discovery_limit、announcement_url_timeout_seconds、announcement_url_max_bytes、official_source；calendar_announcement_profile_check 额外支持 announcement_profiles_path、announcement_profile、announcement_profile_min_links、announcement_profile_check_limit、announcement_url_timeout_seconds、announcement_url_max_bytes；system_health_check 额外支持 official_calendar_path/reference_calendar_path、calendar_warn_days、calendar_stale_days、calendar_diff_limit；data_maintain 额外支持 news_retain_days、remote_cache_retain_days、qa_history_retain_days、execution_keep_per_job、backtest_keep_per_strategy、qlib_keep_per_type、workflow_keep_per_mode、rebuild_fts_on_mismatch、optimize_fts、wal_checkpoint、database_optimize、vacuum） |
| enabled | INTEGER | NOT NULL，默认 1 | 启用状态：0 停用 / 1 启用 |
| last_run_at | TEXT | | 上次执行时间（UTC） |
| next_run_at | TEXT | | 下次预计执行时间（UTC，由调度器计算回写） |
| created_at | TEXT | NOT NULL | 创建时间（UTC） |
| updated_at | TEXT | NOT NULL | 更新时间（UTC） |

#### job_executions（任务执行历史）

| 字段名 | 类型 | 约束/默认 | 说明 |
|--------|------|-----------|------|
| id | INTEGER | 主键，自增 | 自增主键 |
| job_id | INTEGER | NOT NULL，外键 → scheduled_jobs.id | 所属任务（级联删除） |
| triggered_at | TEXT | NOT NULL | 触发时间（UTC） |
| status | TEXT | NOT NULL，默认 '运行中' | 执行状态，枚举：运行中 / 成功 / 失败 / 超时 / 跳过 |
| duration_ms | INTEGER | | 耗时（毫秒） |
| result_summary | TEXT | | 结果摘要（如"采集新闻 128 条，新增 96 条"） |
| error_msg | TEXT | | 失败/超时错误信息 |
| created_at | TEXT | NOT NULL | 记录创建时间（UTC） |

### 2.8 模型配置

#### llm_models（LLM 模型配置）

| 字段名 | 类型 | 约束/默认 | 说明 |
|--------|------|-----------|------|
| id | INTEGER | 主键，自增 | 自增主键 |
| name | TEXT | NOT NULL，UNIQUE | 模型显示名称（如"DeepSeek-快速"） |
| base_url | TEXT | NOT NULL | OpenAI 兼容接口地址 |
| api_key | TEXT | NOT NULL | 历史兼容字段，迁移后不保存明文密钥 |
| api_key_env | TEXT | | API Key 环境变量名；密钥写入 Git 忽略的 `.env` 或进程环境，接口返回时仅显示变量名和掩码 |
| model_name | TEXT | NOT NULL | 模型标识（如 deepseek-chat / qwen-plus / glm-4） |
| purpose | TEXT | NOT NULL | 用途标记 JSON 数组，取值：快速过滤 / 深度推荐 / 问答 / 策略生成 / 报告生成 |
| level | TEXT | NOT NULL，默认 fast | 模型分级，枚举：fast / deep |
| temperature | REAL | NOT NULL，默认 0.2 | 生成温度 |
| max_tokens | INTEGER | NOT NULL，默认 1200 | 最大输出 Token 数 |
| timeout_seconds | REAL | NOT NULL，默认 60 | 调用超时秒数 |
| system_prompt | TEXT | | 模型默认系统提示词 |
| is_default | INTEGER | NOT NULL，默认 0 | 是否默认模型：0 否 / 1 是（全局至多一个默认） |
| enabled | INTEGER | NOT NULL，默认 1 | 启用状态：0 停用 / 1 启用 |
| call_count / success_count / failure_count | INTEGER | NOT NULL，默认 0 | 调用次数、成功次数和失败次数 |
| total_duration_ms / last_duration_ms | INTEGER | NOT NULL，默认 0 | 累计耗时与最近一次耗时 |
| last_called_at / last_status / last_error | TEXT | | 最近调用时间、最近状态和最近错误摘要 |
| remark | TEXT | | 备注（费率/限制说明等） |
| created_at | TEXT | NOT NULL | 创建时间（UTC） |
| updated_at | TEXT | NOT NULL | 更新时间（UTC） |

#### mcp_services（MCP 服务配置）

| 字段名 | 类型 | 约束/默认 | 说明 |
|--------|------|-----------|------|
| id | INTEGER | 主键，自增 | 自增主键 |
| name | TEXT | NOT NULL，UNIQUE | 服务显示名称 |
| service_type | TEXT | NOT NULL | 服务类型，枚举：飞书 / 腾讯ima / 自定义 |
| conn_params | TEXT | NOT NULL | 连接参数 JSON（stdio 命令或 http 地址、超时、凭证引用；凭证加密存储见 6.5） |
| enabled | INTEGER | NOT NULL，默认 0 | 启用状态：0 停用 / 1 启用 |
| remark | TEXT | | 备注 |
| created_at | TEXT | NOT NULL | 创建时间（UTC） |
| updated_at | TEXT | NOT NULL | 更新时间（UTC） |

#### skills（Skill 配置）

| 字段名 | 类型 | 约束/默认 | 说明 |
|--------|------|-----------|------|
| id | INTEGER | 主键，自增 | 自增主键 |
| name | TEXT | NOT NULL，UNIQUE | Skill 名称 |
| description | TEXT | | Skill 描述 |
| param_schema | TEXT | | 参数定义 JSON（参数名/类型/默认值，供调用侧渲染） |
| enabled | INTEGER | NOT NULL，默认 0 | 启用状态：0 停用 / 1 启用 |
| created_at | TEXT | NOT NULL | 创建时间（UTC） |
| updated_at | TEXT | NOT NULL | 更新时间（UTC） |

---

## 3. 索引设计

除主键与建表时已声明的 UNIQUE 约束自动索引外，关键查询索引规划如下（均为普通索引，命名不落文档）：

| 表 | 索引字段 | 目的 |
|----|----------|------|
| news_items | category, published_at | 新闻页按分类 + 时间倒序查询（最高频查询） |
| news_items | source, published_at | 按来源拉取增量、排查重复抓取 |
| watchlist | group_id, sort_order | 分组内自选列表排序展示 |
| resource_pools | updated_at | 资源池列表按最近更新时间倒序 |
| resource_pool_items | pool_id, symbol | 资源池明细读取与同池代码查重 |
| security_master | symbol, market | 代码精确解析与冲突校验 |
| security_master | market, name | 名称/市场范围模糊检索 |
| stock_relations | source_code, relation_type | 关系图从起点展开邻接边 |
| stock_relations | target_code, relation_type | 关系图从终点反向展开邻接边 |
| recommend_tasks | status, created_at | 任务列表按状态筛选、调度器取排队任务 |
| recommend_results | task_id, rank | 按任务取排名序列结果 |
| recommend_templates | updated_at | 推荐模板库按最近更新时间倒序展示 |
| model_reports | report_type, generated_at | 按类型 + 时间检索报告 |
| papers | published_at | 论文按发表时间倒序浏览 |
| strategies | status | 策略库按状态（可用/草稿/停用）筛选 |
| cli_sessions | status, created_at | 会话列表按状态与时间查询 |
| backtest_tasks | status, created_at | 回测队列调度（取排队任务）与列表筛选 |
| backtest_tasks | strategy_id, created_at | 查看某策略的历史回测记录 |
| factor_metrics_daily | factor_key, metric_date | 因子有效性按因子和日期查询 |
| factor_alerts | status, triggered_at | 因子监控页读取打开告警 |
| qlib_runs | status, created_at | Qlib 运行诊断按状态和时间查询 |
| quant_workflow_runs | mode, created_at | AI 工作台按闭环模式读取历史运行 |
| quant_workflow_steps | run_id, step_order | 闭环详情按运行 ID 读取步骤时间线 |
| quant_workflow_artifacts | run_id, artifact_type | 闭环详情按运行 ID 和产物类型读取引用 |
| ai_workspace_sessions | updated_at | AI 操作台会话列表按最近活动排序 |
| ai_workspace_messages | session_id, id | AI 操作台按会话读取消息历史 |
| paper_orders | account_id, status | 按账户筛选在途/历史委托（状态机推进） |
| paper_orders | account_id, created_at | 账户委托流水按时间倒序 |
| paper_trades | account_id, traded_at | 账户成交流水按时间查询 |
| paper_trades | order_id | 由委托反查成交明细 |
| paper_nav_history | account_id, nav_date | 净值曲线按账户 + 日期区间绘制（UNIQUE 索引兼做唯一保证） |
| live_runs | config_id, started_at | 配置的运行历史批次查询 |
| live_runs | status | 监控面板筛运行中/异常实例 |
| live_orders | run_id, status | 运行批次内在途委托监控 |
| live_orders | run_id, created_at | 运行批次委托流水 |
| kb_documents | category_id | 分类树节点下的文档列表 |
| kb_documents | doc_type, imported_at | 按类型（论文/研报/笔记）筛选与最新导入排序 |
| kb_document_chunks | doc_id, chunk_index | 文档详情按顺序读取分块、删除文档级联清理 |
| kb_qa_sessions | updated_at | 问答会话列表按最近活动排序 |
| kb_qa_history | session_id, id | 问答历史按会话读取最近上下文与清空 |
| kb_qa_history | created_at | 问答历史按时间倒序 |
| remote_docs_cache | source_id, updated_at | 远程源缓存按更新时间增量刷新 |
| scheduled_jobs | enabled, next_run_at | 调度器扫描启用任务与触发时间 |
| job_executions | job_id, triggered_at | 任务执行历史按时间倒序 |
| job_executions | status, created_at | 监控失败/超时记录 |

说明：配置级小表（settings、watchlist_group、kb_categories、llm_models、mcp_services、skills、remote_sources、live_configs、paper_accounts）数据量小，除 UNIQUE 约束外不额外建索引；paper_positions 与 remote_docs_cache 的 UNIQUE 约束索引已覆盖主要访问路径。

---

## 4. FTS5 全文检索设计

复用 a001_news_track 已验证的"FTS5 虚拟表 + 触发器同步 + LIKE 兜底"模式，共 3 张虚拟表。

### 4.1 虚拟表定义

#### news_items_fts（新闻全文检索）

| 字段名 | 类型 | 说明 |
|--------|------|------|
| title | TEXT | 标题（索引列） |
| summary | TEXT | 摘要（索引列） |

- 组织方式：以 news_items.id 作为 FTS 表 rowid 关联，正文存于虚拟表自身（非外部内容表），触发器维护一致性；
- 分词器：采用 trigram 分词器，对中英文统一友好（中文子串可命中、英文单词可命中）。

#### kb_documents_fts（知识库文档全文检索）

| 字段名 | 类型 | 说明 |
|--------|------|------|
| title | TEXT | 标题（索引列） |
| summary | TEXT | 摘要（索引列） |
| content | TEXT | 正文纯文本（索引列） |

- 同样以 kb_documents.id 作为 rowid 关联，trigram 分词器。

#### kb_document_chunks_fts（知识库分块全文检索）

| 字段名 | 类型 | 说明 |
|--------|------|------|
| title | TEXT | 所属文档标题（索引列） |
| heading | TEXT | 分块标题（索引列） |
| content | TEXT | 分块正文（索引列） |

- 以 kb_document_chunks.id 作为 FTS 表 rowid 关联，触发器维护一致性；
- 知识库检索先查分块索引，命中结果带 chunk_id、chunk_index 和 chunk_heading，未命中时再回退到整篇文档索引与 LIKE。

### 4.2 触发器同步思路（文字描述）

对 news_items、kb_documents 与 kb_document_chunks 三类索引主表，各挂三类触发器，模式与 a001_news_track 完全一致：

1. **插入同步**：主表新增记录后，触发器将索引字段写入 FTS 虚拟表，rowid 直接使用主表 id；
2. **更新同步**：主表索引字段（标题/摘要/正文）发生更新后，触发器先按 rowid 删除 FTS 中旧行、再插入新行（FTS5 不支持原地更新，必须"删旧插新"两步）；
3. **删除同步**：主表删除行后，触发器按 rowid 删除 FTS 对应行。

注意点（文字约定）：

- 批量重导数据（如共现关系重建、知识库重导入）时走正常增删改通道，保证触发器必然生效，禁止绕过触发器直接操作 FTS 表；
- FTS 表与主表行数对账可由维护任务定期执行（数量不一致时报警并建议重建索引）。

### 4.3 中文检索与 LIKE 兜底

- trigram 分词器对中文按三字滑窗切分，两字以上的中文关键词可直接通过 MATCH 命中，覆盖绝大多数检索场景；
- **兜底策略**：当 FTS MATCH 查询无结果（如用户输入单字、特殊符号导致查询串无效、或分词边界漏配）时，知识库先对分块 heading/content 执行 LIKE 模糊查询，再降级为对主表 title/summary/content 执行 LIKE，两段结果合并去重后返回；
- LIKE 兜底仅在小结果集（知识库千条级）上执行，性能可接受；新闻表 LIKE 兜底限定在近期数据窗口（如 30 天）内，避免全表扫描;
- 远程文档缓存（remote_docs_cache）检索直接走 LIKE（缓存表体量小，不建 FTS），与本地 FTS 结果统一合并展示。

---

## 5. 数据量与清理策略

### 5.1 增长预估

| 类别 | 表 | 增长预估（个人单机场景） |
|------|-----|--------------------------|
| 配置级（基本不增长） | settings、watchlist_group、watchlist、resource_pools、resource_pool_items、security_master、recommend_templates、strategies、paper_accounts、live_configs、kb_categories、remote_sources、llm_models、mcp_services、skills | 各表十条～万条，长期稳定 |
| 缓慢增长 | papers、kb_documents、kb_document_chunks、model_reports、cli_sessions、remote_docs_cache、ai_workspace_sessions、ai_workspace_messages | 每日新增 0～10 篇文档或会话，分块和消息随使用增长，年级别十万段内 |
| 日志级（持续增长） | recommend_tasks、recommend_results、backtest_tasks、backtest_results、live_runs、job_executions、kb_qa_history | 每日数条～数十条，job_executions 增长最快（每次触发一条） |
| 时序级（增长最快） | news_items、paper_orders、paper_trades、paper_nav_history、live_orders | news_items 每日 100～500 条；模拟/实盘委托随交易频率增长，净值每账户每交易日 1 条 |

SQLite 单文件在该量级下（百万行内）读写性能充裕，配合 WAL 模式即可长期运行。

### 5.2 清理与归档策略

| 对象 | 策略 | 默认参数 | 说明 |
|------|------|----------|------|
| news_items | 定期删除过期新闻（含 FTS 同步删除） | 保留 180 天 | 参数化：settings 中 news.retain_days 可调；删除由定时任务执行 |
| job_executions | 每任务仅保留最近 N 条 + 最近 M 天 | 每任务 500 条 / 90 天 | 超限部分由定时任务删除，先删最旧 |
| kb_qa_history | 定期清理 | 保留 365 天 | 可配置；用户可置顶收藏的问答豁免（如后续需要） |
| backtest_tasks / backtest_results | 结果记录保留、产物文件归档 | 任务记录保留 200 条（每策略），产物文件归档 90 天 | reports/backtest/ 下超过归档期的明细 JSON 移入 backup/ 或删除，库内 trades_path 置空并加"已归档"标注 |
| paper_orders / paper_trades | 已终结委托（已成交/已撤销/已拒绝）定期归档 | 保留 365 天 | 归档前导出 JSON 至 backup/；账户存续期间保留完整流水供对账，默认仅清理已停用账户 |
| paper_nav_history | 按年归档 | 保留 2 年线上数据 | 归档数据导出后删除，净值曲线前端按需加载归档文件 |
| live_orders / live_runs | 长期保留（实盘审计需要） | 永久保留 | 仅当对应配置删除且超过 2 年时随级联清理 |
| remote_docs_cache | 缓存重建型数据 | 保留 90 天未刷新的缓存 | 同步任务按 remote_id 去重刷新，清理不影响正式 kb_documents |
| cli_sessions | 会话记录保留、日志文件轮转 | 记录保留 180 天，日志随 loguru 轮转 | 日志文件按大小/天数轮转删除 |
| backup/ 目录 | 备份产物轮转 | 保留最近 10 份 | 超出轮转删除 |

以上所有清理任务均以"定时任务类型：数据更新"注册进 scheduled_jobs，由任务层统一调度，参数落在 settings 表，避免硬编码。

---

## 6. 数据完整性约定

### 6.1 外键约束

- 数据库连接初始化时统一启用 SQLite 外键约束开关（PRAGMA foreign_keys，连接级设置），保证所有外键声明实际生效；
- 删除策略：从表记录随主表级联删除（如 recommend_results 随 recommend_tasks、paper_orders/paper_trades 随 paper_accounts、kb_documents 随 kb_categories）；策略表（strategies）被 backtest_tasks / paper_accounts / live_configs 引用时不做级联删除，采用"停用保护"——被引用的策略仅允许置为"停用"，不允许物理删除；
- 自引用外键（kb_categories.parent_id）使用 0 表示根分类，避免空值语义歧义。

### 6.2 时间约定

- 所有时间字段统一以 TEXT 存储 UTC 时间，格式 ISO8601（YYYY-MM-DDTHH:MM:SS，必要时含毫秒）；日期类字段（回测区间、净值日期）格式 YYYY-MM-DD；
- 前端展示时由前端按浏览器本地时区本地化渲染，后端接口出入参统一 UTC；
- 数据源带时区的时间（如新闻发布时间）入库前统一换算为 UTC。

### 6.3 金额与数量精度

- 价格、金额、净值、权重、评分等使用 REAL（浮点），展示层保留 2 位小数（净值 4 位）；
- 数量类（股数、委托量、成交量）使用 INTEGER，单位为"股"（A股一手 100 股的整数倍校验由引擎层负责）；
- 涉及资金对账的关键计算（现金增减）由引擎层在 Decimal 域完成后再落库，库内 REAL 值仅为最终舍入结果，避免中间过程浮点误差累积。

### 6.4 JSON 字段使用约定

- 仅用于"结构灵活、整体读写、不作为高频过滤条件"的数据（参数定义、筛选条件、绩效指标、曲线、标签列表、连接配置等）；
- 需要按内部键查询的数据（如新闻分类、委托状态）一律提升为独立字段，不用 JSON 承载；
- JSON 字段统一以 TEXT 存标准 JSON 字符串，写入时序列化、读出时反序列化，空值允许为 NULL 或空串但同一字段全局统一。

### 6.5 敏感信息加密

- llm_models.api_key 仅保留历史兼容空字段，新密钥通过 api_key_env 引用 `.env` 或进程环境；remote_sources.conn_config 与 mcp_services.conn_params 中的凭证字段，以 AES 等对称加密后入库，密钥来自环境变量或本地密钥文件（不入库、不入代码仓库）；
- 任何接口返回上述字段时一律脱敏（仅保留末 4 位）；日志与错误信息中禁止打印明文凭证。

### 6.6 状态机字段合法值枚举总表

| 表.字段 | 合法值 | 流转说明 |
|---------|--------|----------|
| strategies.status | 草稿 / 可用 / 停用 | 草稿校验通过后置可用；被引用的策略只能停用 |
| cli_sessions.status | 进行中 / 成功 / 失败 | 终态不可回退；成功时回填 strategy_id |
| backtest_tasks.status | 排队 / 运行中 / 完成 / 失败 | 排队→运行中→完成/失败；失败可重建新任务 |
| recommend_tasks.status | 排队 / 运行中 / 完成 / 失败 | 同回测任务模式 |
| paper_accounts.status | 运行中 / 已暂停 / 已停止 | 已停止账户不可再发新委托 |
| paper_orders.status | 待撮合 / 部分成交 / 已成交 / 已撤销 / 已拒绝 | 单向流转，已成交/已撤销/已拒绝为终态 |
| live_runs.status | starting / running / paused / stopping / stopped / error | error 为异常冻结态，可人工恢复为 running 或停止为 stopped |
| live_orders.status | 待报 / 已报 / 部分成交 / 已成交 / 已撤销 / 已拒绝 / 未知 | "未知"为适配器回报异常的兜底态，需人工对账 |
| live_configs.status | 启用 / 停用 | 仅"可用"策略可绑定启用 |
| news_items.category | 国内 / 国外 / 财经 / 公司 | 固定四类 |
| stock_relations.relation_type | industry / concept / supply_chain / shareholder / news_cooccurrence / correlation | 固定关系类型集合，可按数据源可用性逐步启用 |
| recommend_tasks.path | 快速过滤 / 大模型 / 组合 | 固定三路径 |
| model_reports.report_type | 日报 / 周报 / 板块分析 / 个股分析 / 自定义 | 固定枚举 |
| kb_documents.doc_type | 论文 / 研报 / 笔记 | 固定三类 |
| remote_sources.source_type | 飞书 / 腾讯ima | 可扩展枚举 |
| scheduled_jobs.job_type | 新闻采集 / 行情更新 / 市场分析 / 股票推荐 / 模拟盘调度 / 数据更新 / 知识库同步 / 自定义 | 可扩展枚举 |
| job_executions.status | 运行中 / 成功 / 失败 / 超时 / 跳过 | 终态不可回退 |
| 通用布尔字段（enabled / is_default / is_favorite / valid） | 0 / 1 | 0 为否，1 为是 |

### 6.7 其他约定

- 软删除：仅 stock_relations（valid 字段）采用软删除（共现关系需保留历史批次对比）；其余表均为物理删除或状态置为停用；
- 唯一性保护：news_items.dedup_hash、strategies(name, version)、watchlist(group_id, symbol)、resource_pools.name、resource_pool_items(pool_id, symbol)、security_master(symbol, market)、paper_positions(account_id, symbol)、paper_nav_history(account_id, nav_date)、backtest_results.task_id、remote_docs_cache(source_id, remote_id) 等由 UNIQUE 约束兜底，重复写入按冲突策略忽略或更新；
- 事务约定：委托-成交-持仓-净值的联动更新在单一事务内完成，保证模拟盘/实盘账务自洽；批量数据导入（新闻入库、知识库导入）分批提交，避免长事务阻塞。

## 七、知识原件与文件版本补充

2026-10-27按22号方案为kb_documents兼容新增original_file_id文本字段，默认空值，不重写历史正文。新上传资料关联data/file_previews中登记的原始文件；原文件名、格式、内容哈希及来源保存在对应文件记录，file_path继续表示既有提取文本。

旧原生Markdown笔记首次阅读时可登记其正文版本；没有原件的历史Office/PDF记录只能读提取文本，不能把该文本宣称为原版文件。文件接口检查知识库记录仍存在，已移除知识记录的原件ID不再可读。原件和版本暂保留于受控存储，不增加自动物理清理。

Markdown写入以当前原件哈希核对并保留旧版本，知识库正文、摘要和分块在数据库事务内更新；文件或元数据步骤失败时恢复原件与提取文件并回滚事务。当前面向单进程本地服务，不提供多主机事务保证。独立上传阅读不写kb_documents，Office转换只新增PDF缓存，不修改策略或交易账本。

## 八、Agent研究运行与延迟成绩

2026-10-28增加三张项目内SQLite表，按需创建，不重写既有策略和Alpha表。agent_strategy_runs保存请求、冻结配置/模型/源摘要、证据、谱系、截止时点、状态及结果；读取时核对摘要。agent_strategy_events顺序保存实际角色请求、正文、工具读取、阶段与取消事件，有界分页，统计用量需遍历全部分页。

agent_strategy_scores保存来源运行、谱系、通道、研究者、实际成熟成绩与可得时间；运行、研究者、通道联合唯一，重复刷新不重复记分。仅早于当期的完整成熟结果进入训练/预算；行情不足时不补零。实际影子账户产物、原生LightGBM模型、HTML与JSON存放在data/reports/agent_strategies的运行目录，由项目内路径与文件名校验控制。

这些哈希及单进程锁用于本地一致性与追溯，不构成外部签名或分布式事务保证。详细字段以src/agent_strategies/schema.sql为准；状态、谱系和成熟边界见24号设计。

## 九、全局提醒与浏览器显示状态

2026-10-29按26号设计增加notifications与notification_states，独立schema按需创建，不修改原告警或任务表。notifications保存来源类型/键、内容签名、发生时间、写入时间、程度、可信导航及来源解决时间；指纹唯一、事务串行，使重复观察不重复写入。内容变化会结束前版本，来源恢复后再次异常可创建新事件。

notification_states以浏览器客户端UUID和提醒ID为联合主键，分别记录已读与收起时间；两者不修改原factor_alerts/backtest_tasks等业务状态。客户端标识只是本地显示范围，不是多用户身份或权限认证。普通历史按配置保留可见范围，未解决严重项不过期；不自动物理删除用户数据。字段以src/notifications/schema.sql为准。
