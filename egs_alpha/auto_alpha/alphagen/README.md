# 1. 简介

AlphaGen 是一个基于**强化学习**自动生成公式化 Alpha 因子的工具，发表于 KDD 2023。它能够自动搜索并生成一组互补的 Alpha 因子表达式，同时支持 LLM 驱动的因子挖掘。

- 论文 | *Generating Synergistic Formulaic Alpha Collections via Reinforcement Learning* (KDD 2023)
- Github | https://github.com/RL-MLDM/alphagen
- Stars | 691
- 协议 | MIT

## 1.1 核心方法

AlphaGen 将 Alpha 因子挖掘建模为一个强化学习问题：
- **状态**：当前已生成的因子集合
- **动作**：生成一个新的因子表达式（由算子+特征组合而成）
- **奖励**：新生成因子的 IC（信息系数）减去与已有因子的相关性惩罚

通过 RL 智能体不断探索，生成一组**互补且有效**的因子集合。

## 1.2 仓库结构

| 目录 | 说明 |
|------|------|
| `/alphagen` | 基础数据结构和 Alpha 挖掘核心模块 |
| `/alphagen_qlib` | Qlib 数据接口 |
| `/alphagen_generic` | 基于 gplearn 的基线方法 |
| `/alphagen_llm` | LLM 驱动的 Alpha 生成 |
| `/gplearn`、`/dso` | 基线方法（遗传规划、深度符号回归） |

## 1.3 特点

- RL 自动挖掘因子，无需人工设计
- 生成的因子表达式可解释（公式形式）
- 支持多种基线对比（GP、DSO、LLM）
- 与 Qlib 数据生态兼容

# 2. 安装

```sh
git clone https://github.com/RL-MLDM/alphagen.git
cd alphagen
pip install -r requirements.txt
```

需要配合 Qlib 数据使用，请先按 Qlib 文档下载数据。

# 3. 快速使用

详见 [alphagen_demo.py](alphagen_demo.py)，演示 RL 因子挖掘的基本流程。

# 参考
[1] AlphaGen 论文, https://dl.acm.org/doi/10.1145/3580305.3599831
[2] AlphaGen Github, https://github.com/RL-MLDM/alphagen
