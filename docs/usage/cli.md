# 命令行操作

2026-10-29：研究角色新增统一API/CLI选择；不用网页的十个本地研究Skill、按角色覆盖、项目级导出及严格研究可用性边界，见[Agent后端与原生Skills](agent_cli_skills.md)。程序安装与普通对话成功不等于历史研究资格已通过。

本页介绍平台自身CLI。Codex/Qoder等AI工具的安装和登录请看[AI CLI安装与接入](cli_installation.md)，两者用途不同。

平台支持用命令行操作策略、回测、模拟盘、ETF、因子、研究资料、知识库、任务、模型、MCP、Skill 和 AI 会话。CLI 连接已启动的后端，和网页复用业务规则。

在项目根目录执行 `python egs/cli.py --help`。完整命令表通过 `python egs/cli.py api operations --format json` 查看；例如 `python egs/cli.py backtest run --help` 查看回测字段。源码运行无需安装额外 CLI 框架。

远程令牌模式下，通过`authorization_env`指定的环境变量传递完整`Bearer `值，不放入URL或YAML。自定义策略运行前须登记当前SHA256复核，命令为`strategy review-source`；浏览器/CLI配合步骤与权限边界见[访问控制与源码运行](access_and_execution.md)。

## 策略和回测

| 步骤 | 命令示例 |
| --- | --- |
| 检查服务 | `python egs/cli.py system health --format json` |
| 查看示例 | `python egs/cli.py strategy examples list` |
| 导入 ETF 策略 | `python egs/cli.py strategy examples import --example egs/strategy_examples/etf_momentum_rotation_strategy.py --name ETF研究` |
| 启用刚创建的策略 | `python egs/cli.py strategy enable 12` |
| 预览有效参数 | `python egs/cli.py strategy params resolve 12 --parameter-profile etf_momentum.yaml:baseline --params-file egs/cli/params/etf.yaml` |
| 只预览请求 | `python egs/cli.py backtest run --file egs/cli/requests/etf_backtest.yaml --set strategy_id=12 --dry-run --format json` |
| 提交回测 | `python egs/cli.py backtest run --file egs/cli/requests/etf_backtest.yaml --set strategy_id=12` |
| 查看结果 | `python egs/cli.py backtest metrics 42 --format json` |
| 核对参数快照 | `python egs/cli.py backtest snapshot 42 --format json` |
| 查看曲线 | `python egs/cli.py backtest curve 42 --format json` |
| 查看成交和归因 | `python egs/cli.py backtest trades 42 --format json`；`python egs/cli.py backtest attribution 42 --format json` |
| 对比两个任务 | `python egs/cli.py backtest compare --ids 42,43 --format json` |
| 导出成交 | `python egs/cli.py backtest export 42 --output data/reports/42-trades.csv` |

12、42 是示例 ID，请替换为实际返回的 strategy_id、task_id。请求文件中的日期、股票池和执行假设需要自行核对；`--dry-run` 只检查本地请求拼装，不能证明策略可以运行。

ETF 研究快照和历史回测是不同操作，快照成功不表示回测通过。真实行情无请求日期内数据会报错；mock 曲线明确标记模拟来源。核对曲线日期、交易、费用与数据来源后，再考虑多 Agent 复核或模拟盘。策略参数的 YAML 继承、页面覆盖和模型策略要求见 [策略调参](strategy_parameters.md)，ETF 池和复核流程见 [ETF 研究](etf_research.md)。

## 请求和配置文件的区别

| 文件/选项 | 内容 |
| --- | --- |
| `egs/cli.yaml` / `--config` | 客户端地址、context、超时和输出，样例为 egs/cli.example.yaml |
| `--file` | 本次 API 完整请求，样例为 egs/cli/requests/etf_backtest.yaml |
| `--params-file` | 只有策略参数对象，样例为 egs/cli/params/etf.yaml |
| `--parameter-profile` | 服务端登记的方案 ID，如 etf_momentum.yaml:baseline |
| `--set` | 覆盖请求的一个字段，例如 strategy_id=12 或 params.top_n=2 |

本地拼装顺序为完整请求 → 参数文件 → --set → 显式业务选项；后端再按方案、默认值和单次参数解析最终生效配置。日期要写成 YAML 字符串，布尔值写 true/false，模型密钥不放进请求文件。客户端本地附件会上传；Qlib workflow/provider 等路径则属于服务端，不会自动上传。

## 连接、输出和失败

默认连接 `http://127.0.0.1:8000`；其他端口加 `--base-url http://127.0.0.1:8879`。多环境配置保存于 `egs/cli.yaml`，样例为 `egs/cli.example.yaml`。凭证引用 `.env` 中的环境变量。

脚本加 `--format json`；只有 AI 会话和多 Agent 支持真实事件 JSONL。stdout 输出结果，诊断日志走 stderr。退出码 2 表示输入，3 表示连接/协议，4 表示超时，5 表示业务失败，6 表示能力不可用，7 表示真实来源/复核结论条件不满足，130 表示中断。HTTP 200 不能单独证明成功。

同步请求超时后后端可能继续运行，CLI 不自动重试；先查已有任务或会话。`--require-real` 拒绝模拟来源和缺少来源证据的结果。`--all` 只适用于支持分页的接口，注意 meta.truncated。

## AI 工作台

先执行 `python egs/cli.py ai session create --title 研究会话`。拿到会话 ID 后执行 `python egs/cli.py ai ask --session-id 8 --backend codex --message 你好 --format jsonl`，通过 `ai session show 8` 查看留档。加 `--attachment 文件路径` 上传附件，重复指定可添加多个文件；模型和思考强度通过 `--model-name`、`--reasoning-effort` 设置。

GenericAgent 用 `--backend generic` 和可选 `--model-id`；只有实际可用的模型/CLI 才能返回真实结果。Trae/WorkBuddy 未接协议时返回不可用；旧策略构建模拟器不作为真实对话。

模型 API 的配置编号用 --model-id，本地 CLI 的模型名用 --model-name。mock 行情服务默认不运行真实 Codex，需要在服务环境设置 `ALL_IN_ONE_ENABLE_REAL_CLI=true` 后重启；real 仍需本地 CLI 和认证。工作台页面、Enter、附件限制和悬浮助手说明见 [AI 工作台](ai_workspace.md)。

删除与重置需要精确确认对象；非交互使用 `--yes --confirm-id ID`。实盘启动、恢复及风险参数修改还需要配置允许交易的 context，并通过既有后端验证。当前没有真实券商适配器。

完整命令见[命令参考](cli_reference.md)，协议见[CLI 原理](../principles/cli_protocol.md)；正式设计保留在项目 `doc/12_cli_interface_design.md`。`--output` 只能写入本项目，已有文件需 --overwrite；CSV 当前只导出成交，其他嵌套结果使用 JSON。
