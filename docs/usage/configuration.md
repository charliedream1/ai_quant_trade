# 配置说明

## 常用配置

中英文界面按浏览器选择切换；模块化工作台补充文案在`egs/ui_translations.yaml`，其他共用标签见`src/frontend/i18n.py`。翻译只改变界面标签、占位提示和下拉框显示，不改模型/权限等提交标识或用户输入；原始研究资料和模型回答保持原文。动态按钮更新会按最新文字重新翻译，中文/英文往返切换保留当前业务状态。

| 配置 | 作用 |
|------|------|
| `ALL_IN_ONE_DATA_DIR` | 运行数据目录 |
| `ALL_IN_ONE_DB_PATH` | SQLite 数据库路径 |
| `ALL_IN_ONE_DOCUMENT_STORAGE_DIR` | 文档原文存储目录 |
| `ALL_IN_ONE_MARKET_PARQUET_DIR` | Parquet 行情湖目录 |
| `ALL_IN_ONE_DUCKDB_PATH` | DuckDB 查询库路径 |
| `ALL_IN_ONE_HOST` | 后端监听地址 |
| `ALL_IN_ONE_PORT` | 后端监听端口 |
| `ALL_IN_ONE_LOG_LEVEL` | loguru 日志级别 |
| `ALL_IN_ONE_UI_THEME` | 默认主题：light、dark 或 system；浏览器内切换可覆盖 |
| `ALL_IN_ONE_DATA_MODE` | 数据模式，真实行情或 mock |
| `ALL_IN_ONE_DATA_TIMEOUT_SECONDS` | 外部数据请求超时 |
| `ALL_IN_ONE_DATA_HTTP_RETRIES` | 429/5xx 请求重试次数 |
| `ALL_IN_ONE_DATA_CACHE_TTL_SECONDS` | 行情缓存 TTL 上限 |
| `ALL_IN_ONE_ENABLE_REAL_CLI` | mock 行情下是否显式允许真实 Codex CLI；real 模式仍需 CLI 和认证就绪 |
| `ALL_IN_ONE_CODEX_CLI` | Codex 可执行文件路径或命令名 |
| `ALL_IN_ONE_CODEX_TIMEOUT_SECONDS` | Codex 单次调用超时 |
| `ALL_IN_ONE_QLIB_QRUN` | 可选 qrun 绝对路径 |
| `ALL_IN_ONE_FRONTEND_ROOT_PATH` | 反向代理外部前缀，本地启动通常留空 |
| `GRADIO_TEMP_DIR` | Gradio 上传缓存目录；需要限制在项目内时，在启动前指定项目内的绝对路径 |

系统设置页只放全局配置。AI/CLI、图谱深度、知识库 TopK、推荐参数等局部设置放在对应业务页面。通用监控参数与Qlib解释器在 `egs/factor_monitor.yaml`，因子目录在 `egs/factor_research.yaml`；图谱口径、上传校验、全站图表解释分别在 `egs/relation_graph.yaml`、`egs/resource_import.yaml`、`egs/chart_explanations.yaml`。

后端默认读取 `egs/config.yaml`，运行环境和密钥保存在项目 `.env`；导入 `.llm_env` 的方式见系统配置页。更换监听端口、数据模式或 CLI 可执行文件后重启服务；只刷新浏览器不会替换已有 Python 回调。行情模式、模型 API 和本机 CLI 的认证是三项独立配置，real 不表示它们都已可用。

首页展示数量、配色、图高和观察参考线在 `egs/home_dashboard.yaml`；当前新闻数为 8，观察参考线不会修改交易风控。GenericAgent 文本 REACT 参数在 `egs/generic_agent.yaml`。`egs/qlib.example.yaml` 是实验登记配置，引用的原生 Workflow 与真实数据需单独准备，不能仅凭该文件认定 Qlib 可运行。

帮助文档自动构建由 `ALL_IN_ONE_HELP_DOCS_AUTO_BUILD` 控制；关闭后复用已有静态站点，刷新浏览器不会自动重新生成文档。学习专栏的“刷新当前章节”会更新正文，但不负责重新扫描章节目录。附件上限、扩展名和文本预算位于 `egs/ai_workbench_presets.yaml`。

## 可选观测配置

AI 工作台 GenericAgent 后端可选接入 Langfuse。默认不开启，未安装 SDK 或未配置密钥时会自动降级为 no-op，不影响模型回答；Codex、Trae、WorkBuddy CLI 分支不接入 Langfuse。

| 配置 | 作用 |
|------|------|
| `ALL_IN_ONE_GENERIC_AGENT_LANGFUSE_ENABLED` | 是否启用 GenericAgent Langfuse 观测，默认 `false` |
| `ALL_IN_ONE_GENERIC_AGENT_LANGFUSE_CAPTURE_CONTENT` | 是否上传 prompt/output 正文，默认 `false` |
| `ALL_IN_ONE_GENERIC_AGENT_LANGFUSE_FLUSH_ON_FINISH` | 会话结束后是否 best-effort flush，默认 `true` |
| `ALL_IN_ONE_GENERIC_AGENT_LANGFUSE_ENVIRONMENT` | Langfuse environment 标签 |
| `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` | Langfuse 项目密钥 |
| `LANGFUSE_BASE_URL` | Langfuse 服务地址，云端可用 `https://cloud.langfuse.com` |

## 存储模式

当前推荐 `SQLite 主库 + 文件系统文档存储 + Parquet 行情湖 + DuckDB 查询引擎`。

| 存储 | 适合内容 |
|------|----------|
| SQLite | 配置、任务、策略、回测记录、资源池、知识库元数据、FTS 索引 |
| 文件系统 | PDF、Word、Markdown、报告和导出文件 |
| Parquet | 历史行情、因子截面、回测面板 |
| DuckDB | 本地查询 Parquet 行情湖 |

完整依赖说明见[环境安装](installation.md)，存储选型见[存储原理](../principles/storage.md)。

## 帮助文档配置

| 配置 | 默认值 | 说明 |
|------|--------|------|
| `ALL_IN_ONE_HELP_DOCS_MOUNT_PATH` | `/help-docs` | 帮助文档静态站点挂载路径 |
| `ALL_IN_ONE_HELP_DOCS_SITE_DIR` | `./data/help_site` | MkDocs 构建产物目录 |
| `ALL_IN_ONE_HELP_DOCS_AUTO_BUILD` | `true` | 启动时文档源更新后自动构建 |

正式正文位于 `docs/usage/` 和 `docs/principles/`，MkDocs 配置位于项目根目录 `mkdocs.yml`；`docs/help/` 与旧帮助地址保留迁移入口。构建只收录两类文档、截图和兼容页，不复制历史验收附件；产物默认写入 `data/help_site/`。

新增章节或更新正文后，默认在下一次服务启动时检查并构建。若关闭自动构建，需要先手动构建再重启；浏览器刷新只会读取已有站点。学习专栏的目录在进程内缓存，新增章节后重启服务再查看。

## 平台命令行配置

CLI 是连接后端的客户端；它不代替 `egs/config.yaml` 设置服务端行情模式。可将 `egs/cli.example.yaml` 复制为项目内的 `egs/cli.yaml`，配置多个 context。直接使用样例默认值也能连接本地 8000 端口。

| 配置入口 | 用途 |
| --- | --- |
| `--config` / `ALL_IN_ONE_CLI_CONFIG` | 指定 CLI YAML 配置文件 |
| `--context` / `ALL_IN_ONE_CLI_CONTEXT` | 选择 context |
| `--base-url` / `ALL_IN_ONE_CLI_BASE_URL` | 覆盖后端地址 |
| `--api-prefix` / `ALL_IN_ONE_CLI_API_PREFIX` | 覆盖 REST 前缀，默认 /api/v1 |
| context.authorization_env | 引用认证环境变量，样例名为 ALL_IN_ONE_CLI_AUTHORIZATION |
| `--format` | auto、table、json 或事件接口的 jsonl |
| `--connect-timeout` / `--read-timeout` / `--deadline` | 覆盖连接、响应和整体等待限制，单位秒 |

连接配置按“命令行 → 环境变量 → 所选 context”的优先级生效。CLI 自动读取项目 `.env`，进程环境优先；不要假设它自动读取 `.llm_env`。授权值应按网关要求写入环境变量，普通 YAML 和请求文件不保存密钥。

样例连接超时 5 秒，普通响应 30 秒，长任务响应 600 秒，整体 deadline 900 秒；`--read-timeout` 同时覆盖普通和长任务响应限制。长任务超时不等于服务端已取消，先查记录再决定是否重试。完整流程见 [命令行](cli.md)。

## 日志配置

回测成本另由`egs/execution_costs.yaml`管理，包含A股/ETF示例、日期表、可覆盖字段与界面单位；本次运行费用单独冻结。详见[交易成本设置](backtest_execution.md)。市场时区由标准库zoneinfo配合固定版本tzdata解析，Windows/Linux均不依赖硬编码时差；当前已做Windows验收。

系统日志统一使用 loguru。默认 INFO 控制台显示业务日志、启动阶段日志、页面回调日志、调度任务日志和数据源异常摘要；成功 HTTP 接口流水保留在 DEBUG 级别，避免淹没真实后端运行状态。

页面回调会记录“页面动作触发后端方法”的开始、完成、实际后端方法、源码位置和耗时；外部行情请求由 `data.source` 输出 provider、host、path、状态码或失败原因。
