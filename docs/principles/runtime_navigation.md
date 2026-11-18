# 运行隔离与入口整合

环境可复现需要同时核对解释器、实际包版本、安装来源和传递依赖。虚拟环境若继承基础site-packages，清单中的版本可能没有实际生效，审计也会包含其他项目使用的库。项目内独立环境、固定哈希及启动前预检共同约束这个边界。

Web、模型和Qlib是不同依赖集合。当前验收将Web/CPU模型组合安装在同一个独立环境，Qlib信号分析通过单独解释器进程执行，避免Pandas等版本冲突。模型依赖按需加载不等于已隔离到另一个进程；完整QlibWorkflow也不能由信号分析结果替代。

版本告警与实际可利用性需要分别记录。先核对公告条件和调用入口，再决定升级、隔离或限制。当前Pillow受Gradio约束仍有告警，不能通过忽略记录或破坏依赖一致性来取得清零结果。锁文件固定的是经过验证的组合，不是永久安全承诺。

## 一个职责对应一个完整编辑入口

研报、论文与知识资料共用检索/入库组件；RAG共享会话、引用及模型失败状态。因子监控与挖掘共用同一研究页面。AI中的轻量操作从同一服务读取状态，完整编辑回到系统管理或资料库。

回测入口可以不同，但任务ID、参数快照、执行成本及结果来源保持唯一。一键回测提交后跳到同一结果页，图形画布保留节点过程。归因统一按来源与账户标识读取，回测、模拟和实盘的账本不合并。

## 兼容路由与按需构建

旧模块和视图在进入页面前归一化；研报/论文子页、任务ID和分析来源显式传递。页面组件完成挂载后才选择子页，防止首次加载时丢失目标；同一导航事件只应用一次输入，避免后台更新覆盖用户的新编辑。

一级入口整合保留模块延迟构建及浏览器缓存上限。相同组件源码可以复用，历史接口可以保留，但不在主导航中复制完整表单。减少菜单和控件只能说明结构收敛，性能仍须用配置体积、构建时间、切换及后台任务验证。

操作配图见[统一入口指南](../usage/navigation_and_environment.md)，环境复现见[依赖安装](../usage/installation.md)。

## 自动预检与图片入口

预检接入三个正常启动入口，先验证解释器、声明版本、继承配置及包来源，再打印可用地址。默认Web角色避免把可选训练依赖变为所有功能的前提；严格模式失败即退出，兼容调试必须显式选择warn并保留偏差。帮助和远程客户端查询保持离线可用。

图片校验通过项目内Pillow13独立进程执行，Web只读取受限字节和校验结果，不使用Pillow12解码。按批传递有界内容，实际格式、完整解码、像素、帧和内存估算均校验；父进程对整批设置超时。通过后的内容快照供API编码或CLI副本使用，原文件变化不会换入未校验字节。此隔离减少业务图片入口风险，不等同于操作系统沙箱或主Gradio依赖告警清零。

## 定位状态与只读报告

每个模块/视图拥有独立的上下文、嵌套页签、冻结版本和定位序号。上下文白名单在导航YAML声明；普通切页只取目标自己的状态，历史跳转重建相应定位。子页共享嵌入式/独立窗口定位程序，挂载等待有上限，切页立即取消旧观察器与延迟动作，重复消息不会覆盖已应用字段。

报告库只在首次进入、显式刷新或筛选时读取目录，不增加轮询或模型调用。筛选保留有效选择，时间按时区排序；异常记录和损坏事件行跳过并记日志。原状态、HTML可用性和过程可用性分开显示，文件缺失既不生成替代报告，也不产生有效下载链接。

## Page-owned work

Each top-level document creates an unpredictable capability and increasing
navigation revision. Same-origin activation invalidates earlier revisions;
deactivation cannot affect a newer revision or another document. The bounded
registry retains cancellation tombstones and expires abandoned owners.

An early script runs before Gradio hydration and attaches ownership to its
requests. The shell signals backend cancellation before waiting for iframe
navigation. Cached frames keep their inputs, suppress hidden timer work, abort
obsolete direct reads and use Gradio's cancellation protocol to close queued SSE
streams. This avoids an upstream async-generator failure seen with abrupt SSE
disconnects. Callbacks also validate the revision before publishing results.

Explicit transient callbacks execute through trusted local IPC in a bounded
process pool. Only registered method names and server-preprocessed arguments
cross the pipe; no network endpoint accepts pickled content. Styling is converted
to Gradio table metadata instead of serializing closures. Homepage callbacks
run independently; OS-locked JSON observations preserve account/news reuse across workers.
Equivalent in-flight reads maintain consumer sets across document lifetimes.
The last consumer stops the worker and its owned descendants, releases file locks
and clears only that worker's model concurrency leases. RPM history is retained.

Rule and model graph creators register cancellation ownership separately from
viewers. Model graph resolution and source acquisition use the same hard-stop
boundary; its CLI keeps the established native cancellation protocol. Saved
results remain immutable. Independent accepted backtests, research campaigns,
schedules and trading services are outside this page cancellation registry.

Cancellation cannot roll back committed writes or model usage already consumed.
A hard worker exit can interrupt an SDK's buffered observation export; complete
remote token accounting after an interrupted response cannot be guaranteed.
For configuration and user behavior, see [page navigation](../usage/page_navigation.md).

## Research subviews and observable work

Stock technical/financial subviews share identity but have separate transient
lifetimes. Navigation invalidates the backend revision and posts a revision-bound
deactivation message to the old iframe. Pool warmup never waits for its condition
on the event-loop caller. Callback and worker stage events use distinct English
INFO records; automatic polling stays DEBUG. A worker reports stages over its
private pipe rather than copying prompts or source content into progress logs.

News classifications use versioned metadata beside the original records, with
independent geography and subject plus inspectable inclusion reasons. These rules
describe relevance, not predicted prices. Notification day windows use original
occurrence time converted from the configured local timezone; read state remains
client-specific, and unresolved critical history remains separately visible.

## Incremental section delivery

Eligible multi-output reads publish bounded indexed sections through the existing
owned-worker pipe. Each consumer advances its own cursor; leaving one window does
not stop another window's shared source. Independent sources can finish in any
order, and dependent views use their original shared snapshot. A section is sent
when ready instead of waiting for the final tuple. Normal service/API return
contracts and committed-job lifecycles remain unchanged.

The UI callback queue carries cumulative updates, preserving completed tables,
charts and citations while another section loads or fails. Each generator retains
one context even if the SDK advances it on different executor threads. Closing it
releases its subscription and keeps the existing last-consumer process cancellation.
Section state labels and output counts are configured in
`egs/config/ui/page_work.yaml`. Composite writes retain their transaction boundary.
The homepage uses the established independent account, market, local-task and
news callback groups for SDK compatibility. Its two large read groups are excluded
from section streaming until full-page parity is verified on both installations.
No-op SDK updates remain control messages, and emitted update dictionaries are
copied because postprocessing consumes their value fields.

## Page-bound Skill evidence

Explicit page analysis consumes bounded server-completed rule observations. It
does not trust browser-submitted fact bundles or automatically acquire sources on
entry. Snapshots are isolated by database, page capability/revision and market;
matching page controls must retain their original scope. Original measurements,
resource hashes, model selection and missing-evidence labels stay inspectable.

Page-created reports own their cancellation lifetime; saved report viewers do not
restart producers. Current-observation commentary is separate from strict
historical research admission. HTML findings are escaped and previewed in the
existing sandbox, and downloads use the immutable insight-artifact API. See
[page Skill analysis](../usage/page_skill_analysis.md) for tasks and limits.
