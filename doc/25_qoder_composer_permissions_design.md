# Qoder后端与输入区权限设计

2026-10-29补充：两处普通对话增加TRAE版本适配及CodeBuddy协议；WorkBuddy桌面标签不自动映射账户。Qoder严格研究角色使用独立空工具/空配置来源模式，不复用普通对话的读取和项目编辑能力；未登录及未核验版本在调用前如实阻断。

2026-10-28，Codex。状态：两处对话框、CLI适配和E盘安装完成，功能/页面已验收；真实模型回复仍需本人登录。官方对应产品为Qoder，实际安装命令为qodercli，保留qorder输入别名。本文不含实现代码。

## 一、现状和修改目标

| 项目 | 当前实际行为 | 本轮目标 |
| --- | --- | --- |
| Qoder | 工作台、悬浮对话均无适配，当前进程PATH未发现qoder/qodercli/qorder | 接入实际非交互CLI、消息流、模型、推理强度与权限，状态可核实 |
| 后端列表 | 模型API、Codex、Trae、WorkBuddy；后两者未接通真实对话 | 增加Qoder；未接通/未安装后端明确显示原因 |
| 输入区 | 附件在左，后台/模型/强度集中右侧，没有权限字段 | 左下后端→权限；右下模型→思考强度→发送；附件保留图标入口 |
| 快捷键 | Enter发送、Shift+Enter换行；Ctrl+Enter仍走发送 | Enter发送，Ctrl+Enter在光标处换行；保留Shift+Enter兼容 |
| 提示 | placeholder仍提示Shift+Enter；悬停说明相同 | 输入框内提示Enter发送、Ctrl+Enter换行及附件；输入后自动消失 |
| 模型 | 共用平台API模型名称列表 | 按后端提供有效模型，不把API模型ID误传给CLI |

核查位置：src/agent/workspace_backend.py:backend_events、src/strategy/codex_cli.py:CodexCliRunner.command/stream、src/frontend/common/composer.py:render_composer、assets/ai_console.js键盘事件、service/foundation.py后端与模型目录、service/ai.py:ai_console_send_stream。当前Codex命令固定read-only；权限选项必须真正传入并生效，不能只做装饰。

## 二、输入区交互

AI工作台和悬浮助手复用同一个Gradio输入区；独立CLI对话入口同步后端和快捷键，避免同名后端行为冲突。输入正文放在上层，紧凑工具栏分为左、右两个组，中间弹性留白。

左组依次为后端、访问权限；附件以加号或回形针按钮放在正文左缘，附件预览仍占独立条，不挤占选择器。右组依次为模型、思考强度、发送图标。工具栏在常用桌面宽度保持一行；窄窗口和悬浮窗压缩选择器、使用清晰菜单，不能出现裁字、遮挡或多层堆叠。

提示使用真正placeholder，默认文本为“输入消息，Enter发送，Ctrl+Enter换行；可拖入文件或图片”。有内容时自动隐藏，清空后恢复；提示不成为实际消息。按钮悬停说明同步，模型/权限菜单保留可访问名称。请求执行期间避免重复提交，拒绝或失败后保留可修改的内容。

Ctrl+Enter在选区处插入换行，不触发发送；普通Enter走与发送按钮相同的单次提交路径。中文输入法确认候选词、组合输入和长按重复事件不能误发送。保留Shift+Enter换行，兼容旧使用习惯；Alt/Meta组合不应意外提交。切页或重复挂载不重复绑定键盘监听。

## 三、后端与权限

新增独立Qoder适配器，配置和命令参数模板放YAML，执行路径、认证等环境配置从.env或已有环境读取。优先使用显式路径，再探测官方qoder及兼容qodercli；qorder作为输入别名，不假设本机有同名程序。Windows与Linux分别处理实际可执行形式，不引入bat脚本，不拼接用户文本到Shell命令。

Qoder采用官方print非交互模式和stream-json公开事件，支持模型、reasoning-effort、附件及权限参数；模型正文和工具状态映射到既有工作台事件。JSON内容使用json_repair处理并校验类型。流式表示按真实事件到达更新，不承诺CLI版本未提供的逐token输出；保留供应商错误、退出码、超时及停止结果，不用模拟日志兜底。

默认权限为只读。首期提供只读和项目读写两类能力；按后端可实现的档位显示说明、启用或禁用选项。Codex映射实际sandbox参数；Qoder组合其permission-mode及工具限制，并核验实际版本支持。模型API的GenericAgent当前只有项目读取工具，不假称获得了CLI写入能力。完全访问不作为默认值，也不为凑齐菜单绕过后端权限。

权限校验同时存在于前端、业务服务和API输入，未知权限拒绝，缺字段保持旧只读行为。所选权限与实际映射写入运行/消息元数据，不在模型提示词中口头承诺后就当作限制。Qoder工具权限并不等于操作系统文件沙箱；不能证明的范围如实说明，不能将dont_ask错误标成严格只读。不可用的权限或模型/强度组合执行前提示，不静默升级权限或忽略参数。

切换后端后同步模型、思考强度和权限选择；API使用平台已配置模型，CLI使用其实际支持的模型标识或默认模型。优先有界按需探测、会话缓存及手动刷新，不在页面初始加载反复请求模型服务。不支持某强度时禁用并解释，不能只改变显示文字。

## 四、范围和兼容

本轮主要覆盖AI工作台与悬浮对话的共享执行链，以及同一AI会话REST/CLI的权限参数。保留已有会话、附件/拖拽、文件预览和历史消息。旧调用未传权限时默认只读；旧模型API/Codex路径需要回归。

Skill报告、Alpha研究、策略回测及多Agent内部角色的后端扩展留在各自能力目录，本轮不自动将所有研究流程切到Qoder，不改变已验收研究纪律或账本。旧策略CLI产物模拟器仍明确属于模拟器，不能因为列表增加Qoder就宣称已支持真实生成。

若本机未安装Qoder或未认证，先完成可复核适配器、协议与页面验证，再记录缺失条件；不擅自在项目外安装或登录，也不用其他模型冒充Qoder验收。已有程序可配置路径时优先复用。真实冒烟只做一条简短消息和必要参数验证，不做效果迭代。

本轮用户随后明确授权E盘安装：从官方发行清单下载1.1.80 Windows原生包、核对SHA-256，程序位于E盘Tools/QoderCLI/1.1.80，运行配置同在E盘独立config，不运行会修改全局路径/创建bat的引导安装脚本。项目.env保存显式路径，不向源码写机器路径或密钥，不读取或迁移C盘个人认证。官方status返回未登录；不能宣称真实模型回复通过。

## 五、预计修改位置

| 范围 | 位置与用途 |
| --- | --- |
| 后端 | src/agent/workspace_backend.py、新Qoder适配模块、CodexCliRunner：实际命令、事件和权限传递 |
| 公共配置 | egs下新增/整理输入区及CLI能力YAML，认证/路径走.env；不新增硬编码提示词或测试数据 |
| UI | common/composer.py、assets/composer.js、assets/ai_console.js及样式；features/ai.py、assistant.py绑定权限回调 |
| 服务和API/CLI | service/ai.py、workspace.py及现有AI会话路由/命令：校验、后端选择、权限与元数据 |
| 文档 | 03/05及相关spec、AI工作台使用/原理、README和changelog；使用文档补当前真实页面图 |
| 测试 | 按agent/frontend/api/cli分类；协议进程夹具、真实命令参数、真实浏览器键盘及菜单行为 |

## 六、验证与交付

先做小范围单元/集成：后端归一化、只读默认、权限拒绝、参数映射、UTF-8/长提示输入、消息增量/完整块去重、空结果、无程序、认证失败、静默超时、取消与进程释放。验证API模型ID与CLI模型标识区分，不回退已有API/Codex会话和附件检查。

浏览器对工作台、悬浮窗分别模拟后端/权限/模型/强度切换、Enter单次发送、Ctrl+Enter及Shift+Enter换行、选区插入、中文输入法、placeholder消隐与恢复、附件图标及拖拽；亮暗色、不同窗口宽度截图逐张检查。记录首屏/切换与消息事件时延，探测不得拖慢首屏。

完成review后执行pytest、mypy、Ruff、pip-audit、Semgrep、Bandit及相关MkDocs构建，区分继承告警与本轮新增问题；真实Qoder需要程序和认证均可用才报告通过。保存正式证据，停止本轮测试服务并检查端口/子进程，临时文件另获确认后清理。

## 七、官方依据

- [Qoder CLI命令和参数](https://docs.qoder.com/cli/cli-reference)：print、stream-json、模型、reasoning-effort及权限/附件参数。
- [脚本调用](https://docs.qoder.com/cli/run-in-scripts)：非交互输出和权限行为；无人确认的动作会被拒绝。
- [权限说明](https://docs.qoder.com/cli/permissions)：模式、工具规则及边界，不能把不询问等同只读。
- [模型及思考强度](https://docs.qoder.com/cli/model)：不同模型可用等级不同，按实际后端能力显示。
- [安装与升级](https://docs.qoder.com/cli/installation)：官方命令qoder、兼容npm包与Windows/Linux能力；此轮仅查阅，不安装。
