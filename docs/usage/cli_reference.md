# 平台 CLI 命令参考

2026-10-30补充：`provider list`、`research-skill list/preview/run/show/events/files/cancel`及`notification list/config/state/read-all`复用平台接口；本地无需Web的十类研究、按角色后端覆盖和原生Skill导出见[Agent后端与原生Skills](agent_cli_skills.md)。通知状态仍按client_id区分，读取/关闭不消除风险来源。

2026-10-25追加：`backtest run`及`pipeline run`支持`--execution-costs` JSON，也可在`--file`请求中填写同名对象。支持方案、最低佣金、分方向税费及成交约束，费率使用内部小数。实际示例与快照位置见[交易成本指南](backtest_execution.md)。Qlib及前向模拟不接受通用费用覆盖。

更新于 2026-10-22，A/B/C 已实现。CLI 通过 REST 复用网页的业务服务，涵盖 29 个命令组、168 个普通 REST 操作和 2 个 SSE 端点。先读[命令行上手](cli.md)和[协议原理](../principles/cli_protocol.md)。正式设计保留在项目 `doc/platform/cli_interface_design.md`，实测记录保留在 `docs/audit/cli_validation_2026-10-20.md`、`docs/audit/platform_fix_2026-10-21/README.md`。

## 入口与常用命令

在项目根目录使用 Python 3.10+ 执行 `python egs/entrypoints/cli.py`，也支持 `python -m src.cli`。下表用 `aiquant` 简写同一入口；安装本项目后可使用该别名，从源码运行无需安装。先启动现有后端；CLI 默认连接 `http://127.0.0.1:8000`，可用 `--base-url` 覆盖。所有示例在 Windows PowerShell 和 Linux shell 中均为单行命令。

| 目标 | 调用形式 |
| --- | --- |
| 查看完整帮助 | `aiquant --help` |
| 查看回测参数帮助 | `aiquant backtest run --help` |
| 查看当前服务能力 | `aiquant system capabilities --format json` |
| 检查服务 | `aiquant system health` |
| 显式连接测试服务 | `aiquant --base-url http://127.0.0.1:8879 system info` |
| 前台启动服务 | `aiquant system serve --host 127.0.0.1 --port 8000` |
| 查证券名称和代码 | `aiquant security search --query 沪深300 --market CN` |
| 读取日 K | `aiquant stock show 510300 --sections kline --kline-count 240 --market CN` |
| ETF 池 | `aiquant etf universe list` |
| ETF 当前快照 | `aiquant etf snapshot cn_core --require-real` |
| 因子监控 | `aiquant factor monitor --universe 510300,510500,159915` |
| 查看已导入策略 | `aiquant strategy list --all --max-items 100` |
| 查看预制策略 | `aiquant strategy examples list` |
| 导入 ETF 策略 | `aiquant strategy examples import --example egs/examples/strategy_examples/etf_momentum_rotation_strategy.py --name ETF轮动研究` |
| 启用策略 | `aiquant strategy enable 12` |
| 读取方案列表 | `aiquant strategy params profiles 12` |
| 预览参数 | `aiquant strategy params resolve 12 --parameter-profile etf_momentum.yaml:baseline --params-file egs/config/cli/params/etf.yaml` |
| 从 YAML 运行回测 | `aiquant backtest run --file egs/config/cli/requests/etf_backtest.yaml --format json` |
| 单次覆盖选股数 | `aiquant backtest run --file egs/config/cli/requests/etf_backtest.yaml --set params.top_n=2` |
| 查看绩效和净值 | `aiquant backtest metrics 42`；`aiquant backtest curve 42 --format json` |
| 查看运行快照 | `aiquant backtest snapshot 42 --format json` |
| 比较多个任务 | `aiquant backtest compare --ids 41,42` |
| 导出交易 | `aiquant backtest export 42 --kind trades --output data/reports/backtest/42-trades.csv` |
| ETF 多 Agent 复核 | `aiquant agent review --backtest-id 42 --workflow etf_review --objective 核查ETF换手和成本 --model-id 3` |
| 保存复核报告 | `aiquant agent show RUN_ID --format json --output data/reports/research_team/review.json` |
| 创建模拟账户 | `aiquant paper create --name ETF模拟研究 --strategy-id 12 --initial-capital 1000000` |
| 查看模拟账户 | `aiquant paper show 7`；`aiquant paper positions 7` |
| 模拟下单 | `aiquant paper order 7 --symbol 510300 --side buy --order-type market --quantity 100` |
| 查看实盘配置验证 | `aiquant live validation 3` |
| Qlib 环境诊断 | `aiquant qlib status --format json` |
| Qlib Workflow | `aiquant qlib run --server-workflow egs/qlib_workflows/alpha158_lgb.yaml --provider-uri data/qlib` |
| 知识库文档上传 | `aiquant kb document upload --file doc/strategies/etf_strategy_design.md --category-id 2` |
| 知识检索 | `aiquant kb search --keyword ETF轮动` |
| 知识问答 | `aiquant kb ask --question ETF轮动的回测限制是什么` |
| 定时任务 | `aiquant job list`；`aiquant job trigger 5`；`aiquant job history 5` |
| 模型配置诊断 | `aiquant model list`；`aiquant model test 3` |
| 普通模型问答 | `aiquant model chat --model-id 3 --question-file egs/config/cli/prompts/question.txt` |
| 工作台真实后台消息 | `aiquant ai ask --session-id 8 --backend codex --message-file egs/config/cli/prompts/question.txt --format jsonl` |
| 环境变量状态 | `aiquant env check --name OPENAI_API_KEY`，只返回状态，不输出密钥 |

表中的资源 ID 和运行标识需要替换为实际创建结果。`egs/config/cli/requests/etf_backtest.yaml`、`params/etf.yaml`、`prompts/question.txt` 已提供；回测样例的 strategy_id 也需替换。Qlib 的 workflow/provider 路径属于服务端，示例不附带原生训练数据或 workflow 文件。

## 第一次跑通策略与回测

先在一个终端执行 `python start.py --host 127.0.0.1 --port 8000`，在另一个终端从项目根目录执行下面命令。前两步可直接执行；后续 12、42 只是占位 ID，必须先读取实际返回值再替换，不要把整组命令不加修改连续执行。

```text
python egs/entrypoints/cli.py system health --format json
python egs/entrypoints/cli.py strategy examples import --example egs/examples/strategy_examples/etf_momentum_rotation_strategy.py --name ETF首次验证 --format json
python egs/entrypoints/cli.py strategy enable 12
python egs/entrypoints/cli.py strategy params resolve 12 --parameter-profile etf_momentum.yaml:baseline --format json
python egs/entrypoints/cli.py backtest run --file egs/config/cli/requests/etf_backtest.yaml --set strategy_id=12 --dry-run --format json
python egs/entrypoints/cli.py backtest run --file egs/config/cli/requests/etf_backtest.yaml --set strategy_id=12 --format json
python egs/entrypoints/cli.py backtest metrics 42 --format json
python egs/entrypoints/cli.py backtest snapshot 42 --format json
python egs/entrypoints/cli.py backtest curve 42 --format json
python egs/entrypoints/cli.py backtest trades 42 --format json
```

运行前核对请求 YAML 的日期与可得行情；真实行情无区间内数据会明确失败。完成后对照曲线日期、成交、费用、持仓及来源，不能把零成交、HTTP 200 或 mock 回测当作真实策略表现。需要强制来源检查时，可在支持来源证据的运行或指标接口加 --require-real；曲线等不含来源证据的结果也会被该选项拒绝。

| 创建对象 | 后续命令使用的返回字段 |
| --- | --- |
| 策略导入 | data.strategy_id |
| 创建回测 | data.task_id |
| AI 会话 | data.id |
| 模拟账户 | data.account_id |
| 多 Agent 复核 | data.run_id，字符串运行标识 |

更多页面操作与限制见 [策略调参](strategy_parameters.md)、[ETF 研究](etf_research.md)和 [AI 工作台](ai_workspace.md)。

## 配置与发现

策略工坊新增 `pipeline` 命令族：components、templates、preview、create、list、show、update、publish、versions、enabled、run、runs、result、export、events、cancel、accounts、account、monitor、risk-reset。运行示例见[策略工坊](strategy_composition.md)。`pipeline run` 等待真实终态，`--format jsonl` 或 `--stream` 显示实际事件；JSON配合 `--output` 只保存一次最终结果。参数请求使用 `--file`，不是CLI连接用的 `--config`。

可以将 `egs/config/platform/cli.example.yaml` 复制为项目内的 `egs/config/platform/cli.yaml`，分别保存多个 context；不提供配置时读取样例默认值。优先级为命令行、`ALL_IN_ONE_CLI_*` 环境、context 和样例配置。代理凭证通过 context 的 `authorization_env` 引用 `.env`，不写在 YAML 中。

使用 `aiquant api operations --format json` 查看完整契约；`aiquant api describe "backtest run"` 查看一个命令；业务参数以该命令的 `--help` 为准。模型地址用 `--model-base-url`，JSON 配置对象用 `--request-config`，避免与客户端的 `--base-url`、`--config` 混淆。

通用调用示例为 `aiquant api call --method GET --path /backtests/42`，请求字段通过 `--file` 或 `--set` 提供；它和语义命令共用确认、禁用及业务失败规则。历史 CLI 策略生成模拟器、券商事件注入和人工标错操作已明确禁用。

## 请求文件与参数

回测请求 YAML 使用现有 API 字段，至少包含 strategy_id、symbols、start_date、end_date。常用可选字段为 engine、initial_capital、commission_rate、order_type、price_adjustment、lot_size、max_position_count、max_position_weight、slippage_rate、parameter_profile 和 params。

`--file` 是整个请求，`--params-file` 只表示策略参数，`--parameter-profile` 是服务端已登记的方案 ID。完整方案 YAML 不能直接塞进 params。修改学习率使用 `--set params.model_params.learning_rate=0.03`，不会覆盖同级其他模型设置；列表替换整个列表。

CLI 本地覆盖顺序为 --file → --params-file → --set → 显式业务字段选项；服务端再解析命名方案与已保存默认值。--config 控制客户端连接，--request-config 才是业务 JSON 配置对象；二者均不修改后端行情模式。

默认值由服务端解析，CLI 不复制或猜测数据库默认值。发送前可以用 `--dry-run` 查看请求；该选项不执行后端参数验证、回测或工具调用。

完整请求和参数文件可使用 `--file -`、`--params-file -` 从标准输入读取；同一命令只允许一个参数消费标准输入。日期写成带引号的字符串，零和 false 会保留。尚未实现的日期/排序筛选会报错，避免静默忽略。`kb search` 只返回受 page-size 限制的检索结果，不支持自动翻页。

## 脚本与长任务

脚本使用 JSON 获取固定 code、message、data、meta 字段，通过进程退出码判断命令是否成功。原始 HTTP 200 不代表成功；执行结果 blocked 或 failed 会非零退出。读取一份失败任务记录本身仍可成功，任务状态保留在 data 中。

当前回测、Qlib、多 Agent 主要为同步接口：命令会等待最终响应，不提供虚假的后台任务 ID。超时或 Ctrl+C 后服务端可能继续执行，不能盲目重复提交。JSONL 只输出真实收到的状态和消息，未产生 token 时不会输出假进度。

| 退出码 | 含义 |
| --- | --- |
| 0 | 请求成功；模拟来源仍会标明 |
| 2 | 输入、配置或精确确认不满足 |
| 3 | HTTP、连接、断流或协议错误 |
| 4 | 超时，执行结果可能未知 |
| 5 | 业务失败或执行 failed |
| 6 | 能力缺失、blocked 或被禁用 |
| 7 | require-real 或 fail-on-verdict 条件不满足 |
| 130 | 用户中断，服务端可能继续执行 |

`--all --max-items 1000` 遍历支持分页的接口，按 ID 去重，结果 meta 会标注截断及非一致性快照。`--output` 只允许写入本项目；已有文件需要 `--overwrite`。CSV 目前只导出 trades，嵌套结果用 JSON；公式样式字符串添加单引号，避免电子表格执行公式。

## AI 会话、附件与事件

先执行 `aiquant ai session create --title ETF研究`，取得 data.id，然后使用 `aiquant ai ask --session-id 8 --backend codex --message-file egs/config/cli/prompts/question.txt --attachment doc/strategies/etf_strategy_design.md --format jsonl`。附件可重复指定；文件先经 multipart 上传，后端只接受返回的附件标识。图片会传给实际支持图片的后台。

`aiquant ai session show 8` 读取持久消息；`aiquant ai session list` 查看会话。后台的模型参数为 `--model-name`，模型 API 配置 ID 为 `--model-id`，思考强度为 `--reasoning-effort`。Codex 的状态、消息和动作来源于本地真实进程；GenericAgent 当前仅提供已完成阶段和最终消息，不承诺逐 token。多 Agent 复核同样可以加 `--format jsonl`。

mock 服务默认不启动真实 Codex；如需显式验收，在启动服务的环境中设置 `ALL_IN_ONE_ENABLE_REAL_CLI=true`。真实模型缺失、Trae/WorkBuddy 未接协议、Qlib 环境不完整均如实失败。断流先查会话/报告，不重发原消息。

## 数据来源和操作边界

图形工坊对应的查询为 `pipeline nodes <运行ID> --after 0`、`pipeline layout show <方案ID>`。保存布局使用 `pipeline layout save <方案ID> --file <请求文件>`，文件包含 definition_digest、layout 与 revision；修订号从show读取。保存坐标不发布计算版本，nodes只读取近期节点预览，完整事件使用 `pipeline events`。

`--require-real` 用于拒绝模拟数据/模型；它不会把 US 模拟行情自动升级成真实行情。ETF 的缺失规模、成交额或官方基准数据仍保持缺失，CLI 不改写策略能力。

删除、重置和覆盖需要确认精确对象，非交互调用通过 `--yes --confirm-id 对象标识` 明确确认；普通查询不需要确认。实盘启动和恢复还需开启允许交易操作的上下文，并通过服务端验证；停止和暂停直接执行。

`model chat` 是普通模型问答，`ai ask` 才使用 AI 工作台后台与会话。旧策略生成模拟器不能当作真实 Codex 后台，Trae/WorkBuddy 在没有真实协议时继续报告不可用。

配置凭证来自项目 .env，密钥不放在普通请求文件、命令行参数或日志中。服务端返回的文件路径不代表客户端已下载文件，导出要通过明确 output 生成客户端产物。
