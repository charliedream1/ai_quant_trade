# 1. 简介

Alphalens 是 Quantopian 开源的 Python 因子分析库，用于评估 Alpha 因子的预测能力。它能生成专业的 "tear sheet"（因子分析报告），是量化研究中因子评估的事实标准工具。

- 文档 | http://quantopian.github.io/alphalens/
- Github | https://github.com/quantopian/alphalens
- Stars | 3.8k
- 协议 | Apache-2.0

## 1.1 核心功能

Alphalens 从四个维度分析因子：

| 分析维度 | 说明 |
|----------|------|
| **收益分析** | 不同分位数组合的收益表现、累计收益曲线 |
| **信息系数（IC）** | 因子值与未来收益的相关性，IC 均值、ICIR |
| **换手率分析** | 因子稳定性、调仓频率 |
| **分组分析** | 按行业/板块分组的因子表现 |

## 1.2 典型工作流

```
因子数据 + 价格数据
    ↓
get_clean_factor_and_forward_returns()  # 数据对齐+前向收益计算
    ↓
create_full_tear_sheet()  # 生成完整分析报告
    ↓
IC分析 / 分位组合收益 / 换手率 / 行业暴露
```

## 1.3 与其他工具配合

- **Zipline**：回测框架，生成因子信号
- **Pyfolio**：组合绩效分析
- **Alphalens**：因子有效性分析

# 2. 安装

```sh
pip install alphalens-reloaded  # 社区维护版本，兼容新版 Python
# 或
pip install alphalens  # 原版（可能依赖较旧）
```

> 注意：原版 alphalens 依赖较旧，建议使用 `alphalens-reloaded` 社区维护版本。

# 3. 快速使用

详见 [alphalens_demo.py](alphalens_demo.py)，使用 akshare 获取数据后做因子分析。

# 参考
[1] Alphalens 文档, http://quantopian.github.io/alphalens/
[2] Alphalens 示例, https://github.com/quantopian/alphalens/tree/master/alphalens/examples
