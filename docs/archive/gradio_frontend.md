# 模块化 Gradio 前端

平台采用 Gradio-first 路线。FastAPI 负责 REST API、WebSocket、静态资源、帮助文档和 Gradio ASGI 挂载，不再维护 Jinja2 业务页面。

完整整改计划和阶段状态见 [`gradio_modularization_plan.md`](gradio_modularization_plan.md)。

策略构建的预制策略已加入 LightGBM/XGBoost 截面选股和小型 MLP 融合，仍复用原有预览、参数与导入入口。模型一键回测自动选择开盘价，独立回测页需手动选择；结果说明展示真实训练和样本外预测次数。AI工作台的“工作流中心 / 专家团”新增多Agent回测复核，按四个角色渐进显示状态、只读证据工具和研究报告，不增加导航层级。

## 路由

| 路径 | 页面 |
|------|------|
| `/app/` | 持久工作台、同页模块切换和市场选择 |
| `/app/dashboard/` | 投研看板、账户和市场摘要、自定义看板 |
| `/app/market/` | 行情、因子、新闻、个股、关系图谱、资源池、推荐 |
| `/app/research/` | 研报、模型报告、论文 |
| `/app/strategy/` | 因子挖掘、Qlib、策略生命周期、预制/上传策略、CLI 构建 |
| `/app/simulation/` | 回测、参数比较、模拟交易、模拟归因 |
| `/app/live/` | 实盘配置、发布验证、风控、运行控制、归因 |
| `/app/ai/` | 主界面对话、自动化、MCP 服务、Skill、知识库、智能洞察、专家和闭环工作流 |
| `/app/knowledge/` | 本地知识、RAG、远程源、研报论文阅读、学习专栏 |
| `/app/admin/` | 帮助、任务、系统设置、环境变量、模型、MCP、Skill |
| `/legacy-app/` | 迁移期完整兼容界面 |

`/` 与 `/app` 重定向到 `/app/`；`/app/` 直接提供持久 Gradio 工作台。不带尾斜杠的模块地址会重定向到对应带尾斜杠地址。

## 运行模型

工作台壳和每个一级模块都是独立 `gr.Blocks`：

- FastAPI 启动时只注册 ASGI 包装器，不构建页面。
- 第一次访问某个模块时，只构建并缓存该模块，并在当前事件循环中启动该模块回调队列一次。
- 每个模块拥有独立 `/config`、组件树和事件依赖图。
- 模块间通过 URL、数据库 ID 或稳定业务键交接，不共享 Gradio 组件对象。
- 访问市场模块不会构建 AI、实盘、知识库或系统管理模块。
- 工作台首次打开只构建小型壳和默认看板；切换模块时在同一页面按需创建同源 iframe，最多保留最近三个模块实例。

旧单体包含 1,341 个组件、304 个依赖，配置约 1.31 MB。模块化后的单模块基线为 94 至 318 个组件、17 至 68 个依赖，配置约 0.14 至 0.38 MB。

## 代码结构

```text
src/frontend/
├── app.py                 兼容完整界面的组合工厂与公共导出
├── modular.py             独立模块 Blocks 工厂
├── mounting.py            按模块延迟构建、队列启动和 ASGI 挂载
├── shell.py               持久工作台、模块视图导航和有界 iframe 缓存
├── registry.py            模块元数据与稳定路径
├── navigation.py          跨 Gradio 应用导航
├── theme.py               CSS、浏览器 JS、主题和挂载选项
├── constants.py           前端任务选项和默认参数
├── common/
│   ├── callbacks.py       回调异常转换、operation_id 和耗时日志
│   └── components.py      Dataframe、Chatbot 等公共组件工厂
├── handlers/              九个业务域及悬浮助手的回调访问边界
├── service/               领域回调实现、共享展示转换与跨域契约
├── features/
│   ├── dashboard.py
│   ├── market.py
│   ├── research.py
│   ├── strategy.py
│   ├── simulation.py
│   ├── live.py
│   ├── ai.py
│   ├── knowledge.py
│   ├── admin.py
│   └── assistant.py
├── services.py            稳定导入与旧调用兼容门面
├── header.py
├── icons.py               本地彩色 SVG 导航图标
├── assets/styles/         持久壳与 AI 满屏布局的独立样式
├── assets/ai_console.js   AI 高度适配、工作栏和文件面板交互
└── i18n.py
```

`app.py` 不再声明全站组件，完整兼容界面也由相同的 feature renderer 组合生成。页面功能只维护一份。每个 feature 通过对应 handler 的精确方法白名单访问兼容服务，跨域回调访问会立即抛出错误。`service/` 按业务域保存实际回调实现，共享基础解析、图表和看板展示转换分别归档；明确复用的跨域工作流受独立类型契约约束。`services.py` 仅聚合这些实现并保留历史导入路径。

## 加载策略

- 页面构建只创建组件、轻量静态内容和事件绑定。
- 总览通过非排队 `load` 事件分段加载摘要、账户、市场和任务数据。
- 首页以单组指标、净值趋势、资金配置环图、板块样本热力和持仓浮动盈亏为主，十一类明细默认折叠、展开时补充低频数据；保留自定义仪表盘。`service/home_data.py` 让指标与持仓表共用估值；`home_charts.py`、`home_views.py`、`home_tables.py` 分别处理图形、摘要和语义色阶，参数在 `egs/config/ui/home_dashboard.yaml`。
- 首页样式位于 `assets/styles/home_dashboard.css`，仅首页模块与兼容单体加载；其同页入口交互位于 `assets/home_dashboard.js`。色阶使用主题表面计算渐变，覆盖斑马纹/悬浮背景，不丢失原始百分比和 ID。
- 因子、Qlib、回测、归因、知识源和 AI 能力状态通过页内刷新或标签首次选择加载。
- 市场资源池、AI 会话、项目目录和 Skill/MCP 状态不在 Blocks 构建阶段查询。
- AI 工作台主界面采用可收起的左侧工作区与满屏对话：主界面对话、自动化、MCP 服务、Skill 和知识库均在同一工作区切换，项目会话放在 AI 左栏下半部、进入时按需读取、点击可载入；输入区支持拖入文件/图片、文本附件提取、后台/模型/思考强度选择，Codex CLI 通过只读 JSONL 事件流回填状态和正文。Trae/WorkBuddy 在真实协议未配置时明确提示未接入。自动化可创建、开启和关闭；Skill 只登记安全参数契约。文件预览默认关闭；附件仅随用户显式发送进入模型上下文。
- 工作台壳只创建当前模块，切换后保留最近三个 iframe；模块服务端 Blocks 仍分别缓存，不重复构建。
- 工作台侧栏默认展开，支持收起为图标栏；主题由 `Settings.ui_theme` 控制，支持 `light`、`dark`、`system`，顶部按钮可在浏览器本地覆盖配置。蓝白渐变、圆角和层次阴影由共享 CSS 变量统一提供，模块 iframe 与工作台保持同一主题。
- 图表不携带默认空 Plotly payload，大表限制返回数量并提供详情入口。

AI 工作台整页无滚动，对话区伸展填满窗口剩余高度，长聊天、历史列表和工具表单独立滚动。主导航和 AI 工作栏均提供收起/展开按钮；小窗口导航改为可关闭抽屉，文件面板按需展开。壳顶部恢复原有三个项目/社区链接；导航使用 16px/14px 字号和本地彩色 SVG。通用表格换行规则不得覆盖工作台主容器，隐藏面板不能占用高度。暗色运行时同时同步主题属性和 Gradio 原生暗色类，关键样式使用稳定应用标识提高优先级，不依赖 Gradio 的版本类名。
- 回调统一记录实际服务方法、源码位置、operation_id 和耗时；超过 1500ms 记录为 WARNING。

## 公共交互

- 左侧折叠导航同时承载模块和模块一级页面，地址栏记录当前 `module` 与 `view`；浏览器前进、后退可恢复选择。
- 嵌入态隐藏子应用重复头部、模块导航、单模块根 Tab 和一级页面 Tab，只保留内容明细 Tab；独立直达模式继续显示完整导航。
- 右上角语言和市场按钮通过本地确定性词典与隐藏 Gradio 事件桥接器工作。
- 市场切换会清理对应日内缓存，首页分块刷新。隐藏市场桥接器初始不选中，确保缓存 Blocks 重新加载时仍触发后台同步，防止页面语言切回中文而行情仍是美股。
- 每个模块保留 AI 悬浮助手：模型问答、知识问答和 CLI 助手。
- 总览中的 AI 快捷入口在模块化页面中跳转 `/app/ai/`；兼容页面仍使用内部 Tab。

## 启动

```powershell
python start.py
```

启动后访问 `http://127.0.0.1:8000/app/`。本地直接访问时 `frontend_root_path` 保持空值；反向代理前缀通过 `ALL_IN_ONE_FRONTEND_ROOT_PATH` 配置。

## 验证

```powershell
python -m pytest tests/frontend/test_gradio_frontend.py -q
python -m pytest tests/frontend/test_frontend_handlers.py -q
python -m pytest tests/frontend/test_market_i18n_pages.py -q
python -m ruff check src/frontend src/api/app.py start.py
python -m ruff format --check src/frontend src/api/app.py start.py
```

模块契约测试覆盖路由、尾斜杠、关键组件、配置大小、表格样式、延迟构建隔离和队列只启动一次。页面浏览器巡检会等待回调队列真正空闲，默认入口应使用：

```powershell
python tests/frontend/page_audit_runner.py --base-url http://127.0.0.1:8000/app/dashboard/
python tests/frontend/workspace_shell_audit.py --base-url http://127.0.0.1:8000/app/
```

2026-10-12 队列生命周期修复后的全量模块化验收覆盖 49 个页面与悬浮窗场景，并完成九模块移动端和核心交易闭环实测；场景失败、console 错误、HTTP 5xx 和非受控横向溢出均为 0。报告见 `docs/audit/page_audit_2026-10-12-task14-queue-fix.json`、`page_audit_2026-10-12-task14-queue-fix-mobile.json` 和 `workflow_audit_2026-10-12-task14-queue-fix.json`。

2026-10-13 持久工作台验收在 1440×1000 视口连续切换看板、市场、AI、策略和仿真，顶层 URL 保持 `/app/`、活动 iframe 始终为一个、缓存不超过三个，嵌入态重复导航均隐藏，console 错误、HTTP 4xx/5xx 和横向溢出均为 0。报告见 `docs/audit/workspace_shell_audit_2026-10-13-task14.json`。
