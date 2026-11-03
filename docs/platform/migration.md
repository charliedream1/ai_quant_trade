# 新仓库入口与文档维护

2026-10-31，平台后续开发目录为当前仓库根目录。旧all_in_one已归档提交并推送，保留为迁移来源。本文是新目录的使用说明，不修改历史验收结果。

## 启动

在仓库根目录执行，Linux将Scripts/python.exe替换为bin/python并按固定版本重建环境：

```text
.venv-secure/Scripts/python.exe -B egs/check_runtime.py --role web
.venv-secure/Scripts/python.exe -B start.py --host 127.0.0.1 --port 8000
```

默认使用当前根目录的egs配置和本地.env/.llm_env。迁移保留私有设置与正式数据，不把它们提交到Git。模型、图片和Qlib环境的说明见[环境安装](../usage/installation.md)；已知依赖公告不会因复制仓库消失。

复核补充：AI新会话默认项目名由`egs/ai_workbench_presets.yaml`的`workspace.default_project`统一提供，当前为`ai_quant_trade`；侧栏、自动会话和项目输入框共享此值，已有会话或用户显式项目名不重写。外部缠论适配为可选能力，`chan_analyzer_root`示例默认留空，需要时登记实际路径，不再隐式指向旧仓库。

## 文档位置

| 内容 | 位置与用途 |
| --- | --- |
| 平台首页 | [平台概览](index.md)，代替旧all_in_one根README |
| 具体操作与截图 | [使用文档](../usage/README.md) |
| 计算、架构与边界 | [原理文档](../principles/README.md) |
| 设计 | 仓库doc目录，保留编号及相对引用 |
| 原仓库文档 | 环境配置、常见问题、社区和部署目录继续保留 |
| 历史报告 | docs/audit，仅本地核查，不发布到站点 |

根README保持原仓库内容，没有被平台README覆盖。原docs/index.md作为整合首页，新增量化工作台入口；源平台首页归入platform。周日志重名时保留目标文件，源同名日志在changelog/platform归档。

后续按用户要求，新仓库的中英文根README增加近期日志、src能力独立章节和实际操作GIF，保留原资源目录介绍；它们提供概览和文档导航，完整安装、使用及原理仍维护在docs中，没有重新复制旧all_in_one的README。

## 发布和应用内帮助

对外站点使用Material及中英语言选择，新平台页面暂以中文回退。使用独立文档环境：

```text
.venv-docs/Scripts/python.exe -m pip install -r requirements-docs.txt
.venv-docs/Scripts/python.exe zz_scripts/check_docs_publish_scope.py
.venv-docs/Scripts/python.exe zz_scripts/check_docs_build.py
.venv-docs/Scripts/python.exe -m mkdocs build --strict
```

应用内帮助单独使用mkdocs.platform.yml，由业务环境的MkDocs构建，无需安装Material。手动校验命令为：

```text
.venv-secure/Scripts/python.exe -m mkdocs build --strict -f mkdocs.platform.yml --site-dir data/help_site
```

两套配置共享使用/原理内容和配图，保留/usage、/principles等原路径。GitHub Pages、Cloudflare和Read the Docs使用根站点配置，当前迁移只校验构建，没有自动发布新内容。

## 开发与迁移边界

启动程序、测试与CLI均在新根目录运行；现有项目环境的入口已重定位，优先使用完整的项目Python路径。旧测试缓存、下载缓存与审批受阻目录留在原位置；历史冻结文件中的旧绝对路径是当时记录，不能直接视为新目录运行证据。

环境复核包含主要命令、版本化pip入口及标准激活文件，Python官方模板已重新生成，7套项目环境的脚本均不再引用旧项目路径。当前支持的隔离角色仍为`.venv-secure`、`.venv-qlib-secure`和`.venv-image-secure`；保留的旧环境不等于它们已通过同一隔离标准，业务模型角色继续使用`.venv-secure`。

目标仓库原有未提交资料保留。源仓库已完成commit/push，目标迁移改动留待审阅；后续提交须只选本任务文件，不能直接把已有未跟踪资料一并加入。
