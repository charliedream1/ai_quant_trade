# 项目工作约定

本仓库是一体化量化平台的后续开发根目录。以当前仓库为工作目录，不再回写旧money_maker中的all_in_one副本。

- 开发前查看doc、docs、changelog和Git历史，先说明修改计划；已经确认的范围继续完成，不重复申请确认。
- 源码在src，样例/入口和YAML配置在egs，环境密钥仅存本地.env或.llm_env。使用Loguru；模型走普通OpenAI兼容生成、json_repair及传统ReAct。
- 公开使用和原理文档分别在docs/usage、docs/principles；平台入口在docs/platform；正式设计在doc，设计文档不写实现代码。根README提供近期更新、src能力与GIF概览，完整操作和原理继续链接到docs。
- mkdocs.yml发布整合文档站；mkdocs.platform.yml构建应用内帮助站。不得发布docs/audit、私有运行数据、密钥或环境目录。
- 保留Windows/Linux兼容；不修改Conda或项目外的包。项目环境使用.venv-secure、.venv-qlib-secure、.venv-image-secure；文档发布环境为.venv-docs。
- 完成修改后执行适用的单元/集成、Ruff、mypy和安全检查，同步设计/使用文档及按月内周划分的changelog，停止自己启动的服务。
- 删除文件前取得用户明确确认。自动审批拒绝后记录原文原因和实际状态，不重试或绕过。不要修改docs下task开头的Markdown。
- 提交只包括本任务改动，保留已有未提交工作。私有环境、数据与工具随本地迁移保留，不能提交到Git。
