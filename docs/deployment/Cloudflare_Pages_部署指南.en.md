# Cloudflare Pages Deployment Guide for Mainland China

This guide explains how to deploy this project's documentation site to
**Cloudflare Pages** so that users in mainland China can access it more
smoothly.

If you only want the simplest option and do not care about mainland China
access speed, see option A, GitHub Pages, in the
[Publishing Guide](发布操作指南.md). Choose one of the two deployment options. You
can also deploy both if you want two entry points.

---

## Why Choose Cloudflare Pages for Mainland China Access

| Comparison | GitHub Pages | Cloudflare Pages |
|---|---|---|
| Mainland China access speed | Average, depends on GitHub CDN and may fluctuate | Faster, backed by Cloudflare edge network |
| Monthly bandwidth | 100 GB, may be throttled after limit | Unlimited |
| DDoS protection | None | Built in for free |
| Commercial use | Ambiguous | Explicitly allowed |
| Custom domain | Supported | Supported, up to 100 per project |
| Cost | Free | Free |

**Conclusion**: if most readers are in mainland China, Cloudflare Pages usually
provides a better experience.

---

## Prerequisites

- Admin permission for the GitHub repository `charliedream1/ai_quant_trade`, so
  Cloudflare can be authorized to read it.
- An email address for Cloudflare registration. The free plan is enough and does
  not require a credit card.
- The code is ready: [`mkdocs.yml`](https://github.com/charliedream1/ai_quant_trade/blob/master/mkdocs.yml)
  and [`.cloudflare/scripts/build.sh`](https://github.com/charliedream1/ai_quant_trade/blob/master/.cloudflare/scripts/build.sh)
  are already configured.

---

## Deployment Steps

### Step 1: Register a Cloudflare Account

1. Open https://dash.cloudflare.com/sign-up
2. Register with an email and password.
3. Verify the email address.

If you already have an account, log in at https://dash.cloudflare.com/.

### Step 2: Create a Pages Project

1. After logging in, choose **Workers & Pages** in the left sidebar.
2. Click **Create** -> choose the **Pages** tab -> **Connect to Git**.

### Step 3: Authorize Cloudflare to Access GitHub

1. Click **Connect to Git**. A GitHub authorization page opens.
2. Choose the authorization scope:
   - **Only select repositories**: recommended. Select only `ai_quant_trade`.
   - **All repositories**: not recommended.
3. Click **Install & Authorize**.
4. Return to Cloudflare. When `ai_quant_trade` appears in the repository list,
   click **Begin setup**.

### Step 4: Fill in Project Configuration

Use the following values. Each item matters:

| Setting | Value |
|---|---|
| **Project name** | `ai-quant-trade-docs`; can be customized and becomes part of the domain |
| **Production branch** | `master` |
| **Framework preset** | `None` |
| **Build command** | `bash .cloudflare/scripts/build.sh` |
| **Build output directory** | `site` |
| **Environment variables** | `PYTHON_VERSION` = `3.11` |

Example:

```text
Project name:           ai-quant-trade-docs
Production branch:      master
Framework preset:       None
Build command:          bash .cloudflare/scripts/build.sh
Build output directory: site
```

### Step 5: Deploy

1. Click **Save and Deploy**.
2. Watch the real-time build log. It usually takes 3-5 minutes.
3. A green **Success** status means deployment succeeded.

### Step 6: Visit the Documentation Site

After deployment succeeds, Cloudflare assigns a free domain:

> https://ai-quant-trade-docs.pages.dev/

The `ai-quant-trade-docs` part comes from the project name entered in step 4.

---

## Ongoing Maintenance

After configuration, every push to the `master` branch automatically triggers
Cloudflare to:

1. Pull the latest code.
2. Run `bash .cloudflare/scripts/build.sh`.
3. Deploy the generated `site/` directory to the global CDN.

No manual work is required. Build history and logs are available from the
**Deployments** tab in the Pages project.

---

## Optional: Bind a Custom Domain

If you own a domain, such as `docs.yourdomain.com`, binding it looks more
professional:

1. Pages project -> **Custom domains** -> **Set up a custom domain**.
2. Enter your domain, for example `docs.yourdomain.com`.
3. Cloudflare asks you to add a CNAME record:
   - Type: `CNAME`
   - Name: `docs`
   - Target: `ai-quant-trade-docs.pages.dev`
4. If the domain is already managed by Cloudflare, DNS is usually configured
   automatically.
5. HTTPS certificates are issued automatically and usually become active in
   5-10 minutes.

---

## Relationship with GitHub Pages

The two deployment methods do not conflict. You can:

- Use only Cloudflare Pages, recommended for mainland China users.
- Use only GitHub Pages.
- Deploy both from the same `master` branch.

Choose one unless you intentionally need two domains. If most users are in
mainland China, choose Cloudflare Pages. If most users are overseas, GitHub
Pages is usually enough.

---

## Common Issues

??? question "Build fails during pip install"
    The build script includes mirror fallback. It uses the official PyPI source
    first, then falls back to the Tsinghua mirror. If it still fails, add
    `PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple` under Pages ->
    Settings -> Environment variables, then redeploy.

??? question "Build fails because Python is wrong or mkdocs is missing"
    Add this environment variable under Pages -> Settings -> Environment
    variables:

    - `PYTHON_VERSION` = `3.11`

    Save and redeploy. Cloudflare Pages includes Python by default, but the
    version may be too old.

??? question "xxx.pages.dev cannot be opened or is slow"
    1. Confirm the latest deployment is successful.
    2. First-time DNS propagation for `.pages.dev` may take 1-2 minutes.
    3. If it remains inaccessible, the local network provider may restrict
       `.pages.dev`. Bind a custom domain to solve this.

??? question "Deployment succeeded but the page is still old"
    Cloudflare CDN cache usually updates within 1-5 minutes. Force refresh with
    `Ctrl+F5` on Windows or `Cmd+Shift+R` on macOS.

??? question "The build log shows mkdocs warnings"
    Warnings do not necessarily block deployment. Only errors fail the build.
    Seeing `Documentation built in X seconds` means the build succeeded.

??? question "I want to change theme color or navigation"
    Edit [`mkdocs.yml`](https://github.com/charliedream1/ai_quant_trade/blob/master/mkdocs.yml)
    and push the change. Cloudflare rebuilds automatically.

??? question "The project name is wrong"
    Cloudflare Pages project names cannot be renamed after creation. Delete the
    project and recreate it. This does not affect the GitHub repository.

---

## Troubleshooting Checklist

When deployment fails, check these items in order:

1. **Is the GitHub repository up to date?** Confirm `master` contains
   `.cloudflare/scripts/build.sh` and `mkdocs.yml`.
2. **Build logs**: Cloudflare Dashboard -> Pages -> your project ->
   Deployments -> failed deployment -> inspect the error near the end.
3. **Can it build locally?**
   ```bash
   pip install mkdocs mkdocs-material mkdocs-static-i18n pymdown-extensions
   bash .cloudflare/scripts/build.sh
   ```
4. **Environment variables**: confirm `PYTHON_VERSION=3.11` is configured.

---

## Related Files

| File | Purpose |
|---|---|
| [`mkdocs.yml`](https://github.com/charliedream1/ai_quant_trade/blob/master/mkdocs.yml) | Main documentation site configuration |
| [`.cloudflare/scripts/build.sh`](https://github.com/charliedream1/ai_quant_trade/blob/master/.cloudflare/scripts/build.sh) | Cloudflare build script with mirror fallback |
| [`.cloudflare/wrangler.toml`](https://github.com/charliedream1/ai_quant_trade/blob/master/.cloudflare/wrangler.toml) | Optional CLI deployment config |

If you run into issues, open an issue at
https://github.com/charliedream1/ai_quant_trade/issues.
