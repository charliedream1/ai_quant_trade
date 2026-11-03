# PandaQuantFlow 图形编排核查

2026-10-23核查，Codex。用户约束：本项目继续使用Gradio。本轮仅阅读官方仓库、源码和组件文档，没有安装运行Panda、迁入其代码或验证其收益/生产可靠性。

## 核查版本与证据边界

对象为 [PandaAI-Tech/panda_quantflow](https://github.com/PandaAI-Tech/panda_quantflow)。GitHub API本次返回main为提交 `688b90e74a738b84567efe622a2d9c1e5ce10e00`，提交日期2025-08-14。以下具体源码链接固定到此提交，避免把未来主分支变化当成本次结论。

README介绍的是数据处理、特征、模型、因子和回测节点串接的研究工作流，与本项目策略工坊有较大交集。README中部分LLM、交易通道能力仍列为规划，不能从介绍推断它们已全部可用。实际运行链路以源码核查为限。

## 从源码确认的机制

| 机制 | 官方源码依据 | 对本项目的价值 |
| --- | --- | --- |
| 节点统一契约 | [BaseWorkNode](https://github.com/PandaAI-Tech/panda_quantflow/blob/688b90e74a738b84567efe622a2d9c1e5ce10e00/src/panda_plugins/base/base_work_node.py)要求输入模型、输出模型和运行方法，并提供节点日志及说明元数据 | 组件目录同时描述参数、数据类型、帮助、状态，避免靠节点名称猜输入 |
| 节点分组与注册 | [work_node_registery.py](https://github.com/PandaAI-Tech/panda_quantflow/blob/688b90e74a738b84567efe622a2d9c1e5ce10e00/src/panda_plugins/base/work_node_registery.py)记录名称、分组、类型及颜色 | 工坊左侧按规则/模型/融合/Agent/Portfolio/Risk分组搜索 |
| 手填值与连线分开 | [WorkNodeModel](https://github.com/PandaAI-Tech/panda_quantflow/blob/688b90e74a738b84567efe622a2d9c1e5ce10e00/src/panda_server/models/work_node_model.py)分别保存静态输入、节点位置和输出引用 | 参数表单不覆盖上游绑定；布局独立于策略计算定义 |
| 连线有字段含义 | [LinkModel](https://github.com/PandaAI-Tech/panda_quantflow/blob/688b90e74a738b84567efe622a2d9c1e5ce10e00/src/panda_server/models/link_model.py)描述来源/目标节点与字段及状态 | 候选、评分、决定、权重需要可辨认端口，资金预算也要与评分融合区分 |
| 业务模型与画布关系 | [WorkflowModel](https://github.com/PandaAI-Tech/panda_quantflow/blob/688b90e74a738b84567efe622a2d9c1e5ce10e00/src/panda_server/models/workflow_model.py)同时含nodes、links和litegraph，注释明确说明早期冗余与解耦目标 | 本项目以既有方案定义为计算依据，画布库序列化不能变成第二套执行标准 |
| 运行与结果定位 | [WorkflowRunModel](https://github.com/PandaAI-Tech/panda_quantflow/blob/688b90e74a738b84567efe622a2d9c1e5ce10e00/src/panda_server/models/workflow_run_model.py)保存运行/成功/失败节点、通过连线和结果对象引用 | 点击节点定位真实事件和中间结果，用运行ID、子策略路径和日期区分 |
| 分层依赖执行 | [run_workflow_utils.py](https://github.com/PandaAI-Tech/panda_quantflow/blob/688b90e74a738b84567efe622a2d9c1e5ce10e00/src/panda_server/utils/run_workflow_utils.py)有拓扑分层、参数构造、结果保存和错误说明 | 借鉴可观察性；该后台主路径逐层逐节点等待，不把“可并行分层”说成实际节点并发 |

本项目已有冻结版本和模型/数据时点边界应继续保持。Panda的 [workflow_run_logic.py](https://github.com/PandaAI-Tech/panda_quantflow/blob/688b90e74a738b84567efe622a2d9c1e5ce10e00/src/panda_server/logic/workflow_run_logic.py)仍有运行期间再次保存导致版本不一致的TODO，不能照搬其保存/运行语义。

## 前端实际情况

[服务入口](https://github.com/PandaAI-Tech/panda_quantflow/blob/688b90e74a738b84567efe622a2d9c1e5ce10e00/src/panda_server/main.py)以FastAPI挂载 `panda_web` 静态内容，独立页面覆盖quantflow/charts。公开目录主要是构建后的JS/CSS及编辑器资源；本次全树检索未发现配套Vue/Svelte/React工程源文件和package.json。

[index.html](https://github.com/PandaAI-Tech/panda_quantflow/blob/688b90e74a738b84567efe622a2d9c1e5ce10e00/src/panda_web/index.html)加载 `main-CZkS48P-.js`；该入口的构建内容包含Vue依赖和LiteGraph内容，并映射到 `Quantflow-CGol03Rc.js`。工作流包存在LGraphCanvas调用、类型配色以及保存/导入/导出/运行/停止和日志界面标识。这与Python模型的LiteGraph字段相互印证。

这些证据可确认技术路线，不能代替实际UI试用。本轮未验证其点击节点跳上下游、子图面包屑、缩略图或所有端口约束均可用；本项目这些交互属于拟新增需求。

## 引入方式判断

建议参考Panda的量化工作流组织与节点证据机制，在本项目的Gradio工坊实现一个专用交互组件，复用现有编译、执行、风控、版本和SSE服务。

| 路线 | 适合程度 | 原因 |
| --- | --- | --- |
| Gradio原生表单加只读关系图 | 可作为兼容视图 | 初始成本低，但上下游定位、端口连线、子策略展开仍需交互组件 |
| Gradio自定义组件＋Svelte Flow | 推荐先验证 | [Gradio组件](https://gradio.app/guides/frontend)使用Svelte；[Svelte Flow](https://svelteflow.dev/)提供节点、连线、视口、缩略图和子流程基础，适合DOM参数/帮助与主题联动 |
| Gradio内嵌LiteGraph组件 | 备选 | 与Panda画布思路接近，[LiteGraph](https://github.com/jagenjo/litegraph.js)可绘制Canvas及序列化图，但DOM属性面板、可访问性、Gradio事件同步和图数据适配仍需实现 |
| 整体迁入Panda页面/执行器 | 不采用 | 不满足继续使用Gradio的界面约束，也会重复模型/账本/风控、存储和运行体系 |

Panda的 [pyproject.toml](https://github.com/PandaAI-Tech/panda_quantflow/blob/688b90e74a738b84567efe622a2d9c1e5ce10e00/pyproject.toml)要求Python≥3.12与NumPy<2，本项目模型环境实测Python3.11、NumPy2.4.6，不能视为直接可安装的插件。其 [LICENSE](https://github.com/PandaAI-Tech/panda_quantflow/blob/688b90e74a738b84567efe622a2d9c1e5ce10e00/LICENSE)为AGPL-3.0，而README末尾写GPLV3，记录此差异，当前方案不复制其实现。Svelte Flow和上游LiteGraph各自许可需在锁定版本时独立核查。

当前Gradio依赖声明为6.16.0，`.venv-models`实测6.3.0；两者不能混作同一已验收环境。先验证目标版本下组件生命周期、选择事件和数据回传，再决定库版本。本轮不调整包或环境。

## 对应设计

正式方案见项目 `doc/15_gradio_visual_strategy_editor_design.md`，状态为待确认。范围包括真正的连线图、节点参数与上下游跳转、子策略展开、Portfolio/Risk的明确可视化、执行证据和草稿/布局分离；训练、行情、Agent调用只由显式执行触发。
