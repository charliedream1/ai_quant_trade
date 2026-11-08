# 文档构建、预览与发布

## Local agent privacy

Both documentation configurations exclude local `.codex`, `.trae`, and
`.workbuddy` directories at any depth. Keep memories, sessions, authentication
state, and task transcripts local; do not copy them into public guide pages or
assets. Git and Docker have independent exclusion rules. Shared project skills
may be reviewed as source files, but local agent memory is never a publishing
input. Publication regression tests use synthetic markers only.

本仓库使用MkDocs。公开文档站和应用内帮助共享`docs/`正文，但使用不同配置、环境及输出目录；不能把其中一套的命令直接当作另一套。

## 1. 两套构建配置 {#configurations}

| 用途 | 配置 | 解释器/依赖 | 默认输出 |
| --- | --- | --- | --- |
| 仓库公开文档站 | `mkdocs.yml` | `.venv-docs`，安装`requirements-docs.txt` | `site/` |
| Gradio内帮助站 | `mkdocs.platform.yml` | `.venv-secure`中的MkDocs，无需Material | `data/help_site/` |
| 仅平台帮助的独立发布样例 | `egs/config/operations/mkdocs.publish.example.yaml` | 轻量MkDocs，继承`mkdocs.platform.yml` | `data/docs_publication/` |

公开站采用Material与中英语言选择，保留原仓库的环境/FAQ/部署资料及新的量化工作台。平台使用/原理指南目前以中文为主，在英文站有明确回退；三份根README的语言版本不等于全部使用指南已经翻译成三种语言。`scripts/docs/docs_language.py`提供语言根目录地图，并让语言菜单使用i18n生成的当前页面链接，避免深层sitemap请求404或切换后退回首页；该Hook仅用于公开站，不修改环境包。

MkDocs负责把Markdown构建成静态文件；Read the Docs是可承载MkDocs的构建/托管服务，两者并不互斥。[MkDocs部署说明](https://www.mkdocs.org/user-guide/deploying-your-docs/)、[Read the Docs配置](https://docs.readthedocs.com/platform/stable/config-file/v2.html#mkdocs)。内置的readthedocs主题只是样式，不等于内容已上线。

## 2. 维护分类与素材 {#sources-and-assets}

- `docs/usage/`：前提、页面入口、操作、核对、故障处理和截图；[工作台使用路线](workspace.md)串起第一次操作。
- `docs/principles/`：架构、数据时点、指标、模型、执行与风险口径；不复制长篇操作流程。
- `docs/platform/`：平台首页、仓库入口及维护说明。
- `doc/`：内部正式设计。`docs/audit/research/reference`、隐藏参考、task稿件和私有运行数据不发布。

页面截图位于`docs/usage/assets/screenshots/`，动图发布副本位于`docs/usage/assets/demos/`。使用相对链接并说明来源和模拟/真实口径；根README的`.README_images`不会自动进入MkDocs站点，发布所需素材必须在docs内。复制的GIF须与原摘要一致。

## 3. 安装公开站环境 {#installation}

在仓库根目录操作。首次创建独立环境，已有环境不必重复创建：

```text
python -m venv .venv-docs
.venv-docs/Scripts/python.exe -m pip install -r requirements-docs.txt
.venv-docs/Scripts/python.exe -m pip check
```

Linux创建时用python3，解释器路径为`.venv-docs/bin/python`。固定版本包括MkDocs、Material、i18n及构建工具；不需要安装Torch、Gradio、行情库或配置模型密钥来发布文档。

## 4. 严格构建与门禁 {#build}

公开站：

```text
.venv-docs/Scripts/python.exe scripts/docs/check_docs_publish_scope.py
.venv-docs/Scripts/python.exe scripts/docs/check_docs_build.py
.venv-docs/Scripts/python.exe -m mkdocs build --strict -f mkdocs.yml
```

输出`site/`。Windows和Linux均可按上述解释器替换方式使用。构建会清理目标生成目录，不能在里面保存手写资料；为避免覆盖既有站点，复核时可指定一个尚不存在的目录：

```text
.venv-docs/Scripts/python.exe -m mkdocs build --strict -f mkdocs.yml --site-dir .migration-records/docs-check-20261101/public
```

应用内帮助：

```text
.venv-secure/Scripts/python.exe -m mkdocs build --strict -f mkdocs.platform.yml --site-dir .migration-records/docs-check-20261101/help
```

正常运行时帮助构建器优先使用mkdocs.platform.yml，按设置写入data/help_site并挂到/help-docs。关闭自动构建后只复用已有产物，刷新浏览器不会编译源文档。发布样例继承轻量配置，填写真实site_url，路径相对样例文件所在目录解析。

仓库发布脚本也会执行门禁和生成站点扫描。PowerShell用`scripts/build_docs.ps1`，Linux/Git Bash用`scripts/build_docs.sh`；验证时加严格模式和新的输出目录：

```powershell
./scripts/build_docs.ps1 -Python .venv-docs/Scripts/python.exe -Strict -SiteDir .migration-records/docs-check-20261101/pipeline
```

```sh
bash scripts/build_docs.sh --python .venv-docs/bin/python --strict --site-dir .migration-records/docs-check-20261101/pipeline
```

## 5. 通过HTTP预览 {#preview}

公开站和应用服务使用不同端口。若使用MkDocs serve，先将终端临时目录设在项目内，不修改系统全局环境：

```powershell
New-Item -ItemType Directory -Path .migration-records/docs-preview-tmp -Force
$env:TEMP = (Resolve-Path .migration-records/docs-preview-tmp).Path
$env:TMP = $env:TEMP
.venv-docs/Scripts/python.exe -m mkdocs serve -f mkdocs.yml --dev-addr 127.0.0.1:8001
```

```sh
mkdir -p .migration-records/docs-preview-tmp
export TMPDIR="$PWD/.migration-records/docs-preview-tmp"
.venv-docs/bin/python -m mkdocs serve -f mkdocs.yml --dev-addr 127.0.0.1:8001
```

访问http://127.0.0.1:8001/，检查平台指南、GIF、原理页与搜索。也可以使用HTTP静态服务托管刚构建的输出目录。不要用file地址验收搜索。预览结束按Ctrl+C并确认端口释放。

## 6. 发布到托管站点 {#hosting}

| 目标 | 仓库配置 | 需要的实际发布条件 |
| --- | --- | --- |
| GitHub Pages | `.github/workflows/docs-pages.yml` | 文档及配置提交/push到master，Pages Source选GitHub Actions，构建/部署任务成功；输出site |
| Cloudflare Pages | `.cloudflare/scripts/build.sh` | 连接对应仓库和分支，构建命令运行该脚本，输出目录site，配置后触发成功构建 |
| Read the Docs | `.readthedocs.yml` | 导入仓库/版本，按MkDocs配置和requirements-docs安装并构建成功 |
| 自有静态服务器 | 任意完整MkDocs输出 | 上传HTML、搜索索引、CSS/JS、字体、图片及GIF，并映射实际访问前缀 |

根site_url默认是GitHub项目地址；切换托管域名时同步调整正式链接设置。实际子路径由HTTP服务器映射决定，需支持目录index.html及末尾斜杠。仅本地build通过不代表远端已更新；尚未提交/推送的内容不会由线上CI构建。上传、gh-deploy或触发外部发布需要明确选择目标，不在本地验证命令中自动执行。

## 7. 发布前逐项核对 {#verification}

1. 两套strict和发布门禁退出码均为0；不把生成了HTML当成通过。
2. 在根路径和实际前缀（如/ai_quant_trade/）访问首页、深层指南、原理、语言入口；图片/GIF、CSS/JS和搜索索引均可加载。
3. 在浏览器搜索“回测”和Codex，检查结果能跳转；GIF应播放而非缺图，源副本摘要一致。
4. 产物不包含audit、任务/研究稿、数据库、密钥、环境或源码目录。
5. 执行`tests/frontend/test_help_docs.py`等相关集成测试，检查UTF-8、链接和配图，记录当前实际结果并停止预览服务。

排障与使用说明见[工作台指南](workspace.md)和[故障排查](troubleshooting.md)。
