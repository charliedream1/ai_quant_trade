# 依赖安装与环境复现

Codex、Qoder、TRAE以及WorkBuddy/CodeBuddy的独立安装、登录、E盘路径和项目接入区别，见[AI CLI安装与接入](cli_installation.md)。这些工具不属于Python requirements，也不要求全部安装。

2026-10-26更新。推荐Python3.11+；本轮在Windows/Python3.11.14验证。Web与CPU模型使用项目内独立环境，Qlib信号分析使用另一套环境，均不继承Conda基础包。旧环境保留用于复现，不能将环境名或安装成功等同于安全验收。

## 已验证的环境与文件

| 文件/目录 | 用途 |
| --- | --- |
| `pyproject.toml`、`requirements.txt` | 固定基础直接依赖；requirements另含常用质量工具 |
| `requirements-models.txt` | LightGBM、XGBoost及CPU MLP所需直接依赖 |
| `uv.lock` | 包含传递依赖、平台条件及可选组的统一锁文件 |
| `egs/requirements/runtime.lock.txt` | Web基础运行依赖及哈希 |
| `egs/requirements/runtime-models.lock.txt` | Web与CPU模型组合依赖及哈希 |
| `egs/requirements/development.lock.txt` | 本轮实际测试的Web、模型及开发工具组合 |
| `egs/requirements/qlib.lock.txt` | 独立Qlib信号环境的传递依赖及哈希 |
| `egs/requirements/images.lock.txt` | Pillow13图片校验环境的传递依赖及哈希，与Web分开安装 |
| `.venv-secure`、`.venv-qlib-secure` | 本项目当前验收环境，不提交Git |
| `egs/runtime_environments.yaml` | 角色、目录、版本和来源预检规则 |

Qlib使用Pandas3.1，Web使用Pandas2.3.3，分别安装；不要把两套清单直接混装。模型在拟合时加载，基础启动不强制安装Torch。CPU Torch来自PyTorch官方索引，导出锁文件包含索引和包哈希。

## Windows：复现本轮完整开发环境

在项目根目录执行。先确认所选Python至少3.11；已有Conda时，可先激活合适环境再创建项目虚拟环境。不要使用system-site-packages，也不要修改Conda中的包源码。

```powershell
python --version
python -m venv .venv-secure --without-pip
$env:UV_CACHE_DIR = (Join-Path (Get-Location) '.uvc')
$env:TEMP = (Join-Path (Get-Location) '.uvc/tmp')
$env:TMP = $env:TEMP
New-Item -ItemType Directory -Path $env:TEMP -Force
uv pip install --python .venv-secure/Scripts/python.exe pip==26.2 setuptools==84.1.0 wheel==0.46.2
uv pip install --python .venv-secure/Scripts/python.exe --index-strategy unsafe-best-match --require-hashes --no-build-isolation -r egs/requirements/development.lock.txt
.venv-secure/Scripts/python.exe -B -m pip check
.venv-secure/Scripts/python.exe -B egs/check_runtime.py --role models
.venv-secure/Scripts/python.exe -B start.py --host 127.0.0.1 --port 8000
```

这里的两个索引分别是PyPI与PyTorch官方CPU索引；严格使用锁文件哈希核对下载内容。不要添加未知第三方索引。旧式jsonpath源码包在Windows下可能因构建缓存路径过长失败，因此使用项目根下较短的.uvc，并先安装已验证构建工具。未修改jsonpath或其他包源码。

如果只需要基础Web或Web加模型，将development.lock.txt分别换成runtime.lock.txt或runtime-models.lock.txt。基础环境预检使用role web，模型组合使用role models；开发工具按需另装，不假设每个环境都包含pytest。

## Linux入口

目录布局一致，解释器位于bin下。使用同一哈希清单和平台条件：

```bash
python3 --version
python3 -m venv .venv-secure --without-pip
export UV_CACHE_DIR="$PWD/.uvc"
export TMPDIR="$PWD/.uvc/tmp"
mkdir -p "$TMPDIR"
uv pip install --python .venv-secure/bin/python pip==26.2 setuptools==84.1.0 wheel==0.46.2
uv pip install --python .venv-secure/bin/python --index-strategy unsafe-best-match --require-hashes --no-build-isolation -r egs/requirements/development.lock.txt
.venv-secure/bin/python -B -m pip check
.venv-secure/bin/python -B egs/check_runtime.py --role models
.venv-secure/bin/python -B start.py --host 127.0.0.1 --port 8000
```

Linux尚未做本轮实机验收，需在目标机器完成相同回归。Windows遇到二进制DLL缺失时，先检查对应架构的Visual C++运行时和包版本；不要把外部环境包复制进来掩盖缺失。

## 独立Qlib环境

Windows示例；Linux将Scripts/python.exe换成bin/python。

```powershell
python -m venv .venv-qlib-secure --without-pip
uv pip install --python .venv-qlib-secure/Scripts/python.exe pip==26.2 setuptools==84.1.0 wheel==0.46.2
uv pip install --python .venv-qlib-secure/Scripts/python.exe --require-hashes -r egs/requirements/qlib.lock.txt
.venv-qlib-secure/Scripts/python.exe -B -m pip check
.venv-qlib-secure/Scripts/python.exe -B egs/check_runtime.py --role qlib
```

因子监控默认使用egs/factor_monitor.yaml中的.venv-qlib-secure。可在.env中通过ALL_IN_ONE_QLIB_PYTHON指定项目内其他解释器；环境变量优先，不要忽略旧覆盖值。此环境真实验证了Qlib信号分析；原生Workflow另需provider、Workflow YAML与qrun，不能由信号测试推断已完成模型Workflow训练。

## 固定版本与安全审计

<a id="image-validation"></a>

### 独立图片校验环境

图片附件需要项目内`.venv-image-secure`。文本附件不启动该进程；未安装图片环境时明确拒绝图片，不会回退到Web的旧Pillow解码。

```powershell
python -m venv .venv-image-secure --without-pip
uv pip install --python .venv-image-secure/Scripts/python.exe --require-hashes -r egs/requirements/images.lock.txt
.venv-image-secure/Scripts/python.exe -B egs/check_runtime.py --role image
.venv-image-secure/Scripts/python.exe -B -m pip check
```

Linux将创建命令中的python换为python3，解释器路径换为`.venv-image-secure/bin/python`。配置在`egs/image_validation.yaml`：JPEG/PNG/WebP真实格式必须与后缀一致，默认单帧、1600万像素、6400万解码字节，整批校验超时8秒；另受附件8文件/20MiB总量限制。不接受动画。校验程序每批启动一次，显式使用UTF-8。它是依赖及进程隔离，不是操作系统权限沙箱。

不要把images.txt或images.lock.txt装入Gradio环境，也不要强制升级主环境Pillow。两套环境的审计结果分别记录；增加新格式前需要同步白名单、测试和文档。

### 启动自动预检

`start.py`、`python -m src.main`及`aiquant system serve`会在打印可用地址前校验环境。默认`strict`，检查失败不启动监听；帮助及远程CLI查询不执行本地服务预检。规则在`egs/runtime_environments.yaml`，默认只检查Web角色，不因没有可选Torch而阻断规则策略。

确需排查兼容问题，可在`.env`显式设置`ALL_IN_ONE_RUNTIME_MODE=warn`，启动仍会列出所有偏差；这不表示安全验收通过。`ALL_IN_ONE_RUNTIME_ROLE=web|models`选择启动角色，日常保持`strict`。预检不安装包、不修改Conda、不自动切换解释器；它也不会每次回调都运行漏洞扫描。

### 审计结论的范围

最近一次业务环境审计（2026-10-31）为Pillow12.3.0的39条与pypdf6.21.2的7条，共46条；数量随公告数据库变化，不把历史37条当作当前结果。Gradio的Pillow约束及pypdf候选升级验证见[访问与依赖边界](access_and_execution.md)。Qlib环境当次未匹配已知漏洞，也不代表后续永远为0。

每次调整版本后都应运行pip check、pip-audit和对应功能回归；修改直接依赖时同时更新pyproject、requirements和锁文件。仅修改文本清单不会改变服务实际加载的版本，可用check_runtime检查解释器、版本、来源和基础包继承。

`uv sync --frozen`按项目环境管理规则执行；如需指定当前验收目录，可设置UV_PROJECT_ENVIRONMENT=.venv-secure，并显式选择models/dev。此操作可能移除锁文件外的包，执行前明确目标环境；旧环境仍需按项目规范确认后才能删除。

## 文档站独立环境

公开Material文档使用`.venv-docs`和根`requirements-docs.txt`，应用内轻量帮助使用业务环境的MkDocs与`mkdocs.platform.yml`。两套配置的安装、输出和发布步骤见[文档发布](documentation_publish.md)，不要沿用“根配置无需主题插件”的旧说明。

## 可选能力

TDX与观测仍为可选组，默认不启用；不要将本轮验证扩展为对所有可选能力的生产承诺。TDX历史依赖对HTTPX有约束，统一锁文件保留兼容解，当前固定版本已进入Web测试。

模型、Qlib和开发工具的环境不是用户业务数据目录。数据库、报告、模型产物和密钥分别按[配置说明](configuration.md)保存；运行服务时保留.env与.llm_env的既有优先级。Parlant继续按原项目本地源码加载，不通过pip安装。

页面入口与配图见[统一入口指南](navigation_and_environment.md)，当前系统边界见[风险说明](risk.md)。
