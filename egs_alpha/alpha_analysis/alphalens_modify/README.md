# 1. 简介

alphalens-modify 是 alphalens 的现代化分支，修复了原版在新版 Python 环境下的兼容性问题，并增加了中文支持和更友好的接口。适合在 Python 3.12+ 环境下使用。

- Github | https://github.com/GenjiYin/alphalens-modify
- PyPI | https://pypi.org/project/alphalens-modify/
- 协议 | Apache-2.0

## 1.1 与原版 alphalens 的区别

| 特性 | alphalens (原版) | alphalens-modify |
|------|------------------|------------------|
| Python 版本 | 3.6-3.8 | 3.12+ |
| 依赖更新 | 旧版 pandas/numpy | 兼容新版 |
| 中英文 | 仅英文 | 中文友好 |
| 维护状态 | 已停止维护 | 活跃维护 |

## 1.2 核心功能

与原版一致，提供：
- IC（信息系数）分析与可视化
- 累计收益分析
- 分组（分位数）收益分析
- 因子换手率分析
- 行业/板块分组分析

# 2. 安装

```sh
pip install alphalens-modify
```

# 3. 快速使用

详见 [alphalens_modify_demo.py](alphalens_modify_demo.py)，使用 akshare 获取数据后做因子分析。

接口与原版 alphalens 基本一致，只需将 `import alphalens` 改为 `import alphalens_modify as al`。

# 参考
[1] alphalens-modify PyPI, https://pypi.org/project/alphalens-modify/
[2] alphalens-modify Github, https://github.com/GenjiYin/alphalens-modify
