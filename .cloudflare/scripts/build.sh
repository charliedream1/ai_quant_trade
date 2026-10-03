#!/usr/bin/env bash
# Cloudflare Pages 构建脚本
# 用于 Cloudflare Pages 控制台「构建命令」配置：bash .cloudflare/scripts/build.sh
# 也可本地执行验证：bash .cloudflare/scripts/build.sh
#
# 针对国内访问场景优化：
# - 默认用官方 PyPI，失败时自动回退清华镜像源（提升构建稳健性）
# - 安装超时保护，避免卡死
set -e

DEPS="mkdocs>=1.6 mkdocs-material>=9.5 mkdocs-material-extensions>=1.3 pymdown-extensions>=10.7"

echo "==> 安装 Python 依赖（MkDocs Material）"
# 优先官方源（Cloudflare 构建环境在海外，官方源通常最快）
if ! pip install --no-cache-dir --timeout 60 $DEPS; then
  echo "==> 官方源失败，回退清华镜像源"
  pip install --no-cache-dir --timeout 60 \
    -i https://pypi.tuna.tsinghua.edu.cn/simple \
    $DEPS
fi

echo "==> 依赖版本："
pip show mkdocs mkdocs-material 2>/dev/null | grep -E "^Name|^Version" || true

echo "==> 校验文档站发布范围"
python zz_scripts/check_docs_publish_scope.py

echo "==> 构建文档站到 site/ 目录"
mkdocs build --clean

echo "==> 构建完成，产物在 site/"
ls -la site/ | head -10
