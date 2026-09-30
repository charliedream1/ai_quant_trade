# Cloudflare Pages 部署指南（国内访问专篇）

本文档专门介绍如何把本项目的文档站部署到 **Cloudflare Pages**，让**国内用户访问更快**。

如果你只关心最简单的方案（不在意国内速度），请看 [发布操作指南](发布操作指南.md) 的方案 A（GitHub Pages）。两者二选一即可，也可以同时部署。

---

## 为什么选 Cloudflare Pages（针对国内访问）

| 对比项 | GitHub Pages | Cloudflare Pages |
|---|---|---|
| 国内访问速度 | 一般（依赖 GitHub CDN，国内偶有波动） | **快**（Cloudflare 在国内有边缘节点） |
| 月度带宽 | 100GB（超限可能限速） | **无限** |
| DDoS 防护 | 无 | **免费内置** |
| 商业用途 | 灰色地带 | **明确允许** |
| 自定义域名 | 支持 | 支持（100 个/项目） |
| 费用 | 免费 | 免费 |

**结论**：如果你的文档站访问者主要在中国大陆，选 Cloudflare Pages 体验明显更好。

---

## 前置条件

- GitHub 仓库 `charliedream1/ai_quant_trade` 的 admin 权限（用于授权 Cloudflare 读取仓库）
- 一个邮箱（注册 Cloudflare 用，免费、无需信用卡）
- 代码已就绪：仓库根的 [`mkdocs.yml`](https://github.com/charliedream1/ai_quant_trade/blob/master/mkdocs.yml) 和 [`.cloudflare/scripts/build.sh`](https://github.com/charliedream1/ai_quant_trade/blob/master/.cloudflare/scripts/build.sh) 已配置好，你无需改代码

---

## 部署步骤（一次性，约 5-8 分钟）

### 步骤 1：注册 Cloudflare 账号

1. 打开 https://dash.cloudflare.com/sign-up
2. 填邮箱 + 密码注册（免费，不用绑卡）
3. 收验证邮件，点链接激活

> 已有账号直接登录 https://dash.cloudflare.com/

### 步骤 2：进入 Pages 创建项目

1. 登录后，在左侧导航选 **Workers & Pages**
2. 点 **Create** → 顶部选 **Pages** 标签 → **Connect to Git**

### 步骤 3：授权 Cloudflare 访问 GitHub

1. 点 **Connect to Git**，弹出 GitHub 授权页
2. 选择授权方式：
   - **Only select repositories**（推荐）：只授权 `ai_quant_trade` 这一个仓库
   - All repositories：授权所有仓库（不推荐）
3. 点 **Install & Authorize**
4. 回到 Cloudflare 页面，仓库列表里能看到 `ai_quant_trade`，点 **Begin setup**

### 步骤 4：填写项目配置（关键步骤）

按下表填写，**注意每一项都要对**：

| 配置项 | 填写内容 |
|---|---|
| **Project name** | `ai-quant-trade-docs`（可自定义，会成为域名一部分） |
| **Production branch** | `master` |
| **Framework preset** | `None`（保持默认） |
| **Build command** | `bash .cloudflare/scripts/build.sh` |
| **Build output directory** | `site` |
| **Environment variables**（点 + Add，可选但推荐） | `PYTHON_VERSION` = `3.11` |

填写示意：

```
Project name:          ai-quant-trade-docs
Production branch:     master
Framework preset:      None
Build command:         bash .cloudflare/scripts/build.sh
Build output directory: site
```

### 步骤 5：部署

1. 点 **Save and Deploy**
2. 进入构建页面，能看到实时日志，等 3-5 分钟
3. 看到绿色 **Success** 表示部署成功

### 步骤 6：访问文档站

部署成功后，Cloudflare 分配一个免费域名：

> https://ai-quant-trade-docs.pages.dev/

（域名里的 `ai-quant-trade-docs` 就是你在步骤 4 填的 Project name）

---

## 后续维护（全自动）

配置完成后，**以后每次 push 到 master 分支，Cloudflare 会自动**：

1. 拉取最新代码
2. 执行 `bash .cloudflare/scripts/build.sh`（安装 MkDocs + 构建站点）
3. 部署到全球 CDN

你无需任何手动操作。在 Pages 项目页的 **Deployments** 标签能查看每次部署记录与日志。

---

## 可选：绑定自己的域名

如果你有自定义域名（如 `docs.yourdomain.com`），绑定后访问更专业：

1. Pages 项目 → **Custom domains** → **Set up a custom domain**
2. 输入你的域名（如 `docs.yourdomain.com`）
3. Cloudflare 会提示你在域名 DNS 添加一条 CNAME 记录：
   - 类型：`CNAME`
   - 名称：`docs`
   - 目标：`ai-quant-trade-docs.pages.dev`
4. 如果你的域名也在 Cloudflare 管理，会自动配置，无需手动改 DNS
5. HTTPS 证书自动签发，约 5-10 分钟生效

---

## 与 GitHub Pages 的关系

两种方案**互不冲突**，可以：

- **只用 Cloudflare Pages**（推荐国内用户）：忽略 GitHub Pages，只用 `xxx.pages.dev` 域名
- **只用 GitHub Pages**：不创建 Cloudflare 项目即可
- **两个都部署**：从同一个 master 分支自动构建，两个域名都能访问（维护成本一样，只是多一个入口）

建议**只选一个**，避免维护两份认知负担。国内用户多就选 Cloudflare，海外用户多就选 GitHub Pages。

---

## 常见问题

??? question "构建失败：pip install 超时/网络错误"
    构建脚本已内置镜像源容错：官方源失败会自动回退清华源。若仍失败，在 Pages 项目 → Settings → Environment variables 加 `PIP_INDEX_URL` = `https://pypi.tuna.tsinghua.edu.cn/simple`，然后重新触发部署。

??? question "构建失败：Python 版本不对 / mkdocs 命令找不到"
    在 Pages 项目 → Settings → Environment variables 添加：
    - `PYTHON_VERSION` = `3.11`
    保存后重新部署。Cloudflare Pages 默认环境已含 Python，但版本可能较旧。

??? question "访问 xxx.pages.dev 打不开或很慢"
    1. 确认 Deployments 里最新部署是 Success 状态
    2. 国内首次解析 `.pages.dev` 域名偶有延迟，等 1-2 分钟或换网络/浏览器重试
    3. 若持续打不开，可能是当地运营商对 `.pages.dev` 有限制，建议绑自定义域名解决

??? question "部署成功了但页面是旧的"
    Cloudflare CDN 缓存通常 1-5 分钟更新。强制刷新：浏览器 `Ctrl+F5`（Win）/`Cmd+Shift+R`（Mac）。

??? question "构建日志显示 mkdocs build 警告"
    警告（WARNING/INFO）不影响部署，只有红色 ERROR 才会失败。看到 `Documentation built in X seconds` 即表示构建成功。

??? question "想改文档站主题色/导航"
    编辑仓库根的 [`mkdocs.yml`](https://github.com/charliedream1/ai_quant_trade/blob/master/mkdocs.yml)，push 后 Cloudflare 自动重新构建。

??? question "Project name 填错了想改"
    Cloudflare Pages 的 Project name 创建后不能改。删掉项目重建即可（不会影响 GitHub 仓库代码）。

---

## 故障排查清单

部署失败时按顺序检查：

1. **GitHub 仓库是否最新**：确认 `master` 分支有 `.cloudflare/scripts/build.sh` 和 `mkdocs.yml`
2. **构建日志**：Cloudflare Dashboard → Pages → 你的项目 → Deployments → 点失败的部署 → 看日志末尾的报错
3. **本地能否构建**：
   ```bash
   pip install mkdocs mkdocs-material pymdown-extensions
   bash .cloudflare/scripts/build.sh
   ```
4. **环境变量**：确认 `PYTHON_VERSION=3.11` 已设置

---

## 相关文件

| 文件 | 作用 |
|---|---|
| [`mkdocs.yml`](https://github.com/charliedream1/ai_quant_trade/blob/master/mkdocs.yml) | 文档站主配置 |
| [`.cloudflare/scripts/build.sh`](https://github.com/charliedream1/ai_quant_trade/blob/master/.cloudflare/scripts/build.sh) | Cloudflare 构建脚本（含镜像源容错） |
| [`.cloudflare/wrangler.toml`](https://github.com/charliedream1/ai_quant_trade/blob/master/.cloudflare/wrangler.toml) | CLI 手动部署配置（可选） |

如遇问题，可在 https://github.com/charliedream1/ai_quant_trade/issues 提 issue。
