# 1. 简介

jqfactor_analyzer 是聚宽（JoinQuant）开源的单因子分析工具，专为 A 股市场设计，是国内量化研究中最常用的因子分析工具之一。

- Github | https://github.com/JoinQuant/jqfactor_analyzer
- 文档 | https://github.com/JoinQuant/jqfactor_analyzer
- 协议 | Apache-2.0

## 1.1 核心功能

| 功能 | 说明 |
|------|------|
| **因子收益分析** | 分位数组合收益、累计收益曲线 |
| **IC 分析** | IC 时间序列、IC 均值、ICIR、IC 衰减 |
| **因子换手率** | 因子稳定性、自相关性 |
| **因子分布** | 因子值分布、偏度、峰度 |
| **行业/市值中性化** | 控制行业和市值暴露后的因子表现 |
| **因子覆盖度** | 因子有效值占比 |

## 1.2 特点

- 专为 **A 股市场**设计，内置行业分类
- 支持**行业中性化**和**市值中性化**
- 与聚宽数据生态兼容（也支持自定义数据）
- 中文文档和输出，对国内用户友好
- 输出图表风格符合国内量化研究习惯

## 1.3 与 alphalens 对比

| 特性 | alphalens | jqfactor_analyzer |
|------|-----------|-------------------|
| 市场适配 | 通用 | A 股专用 |
| 行业分类 | 需自定义 | 内置申万行业 |
| 中性化 | 不支持 | 支持行业/市值中性化 |
| 语言 | 英文 | 中文友好 |
| 数据格式 | MultiIndex | DataFrame |

# 2. 安装

```sh
pip install jqfactor_analyzer
```

# 3. 快速使用

详见 [jqfactor_analyzer_demo.py](jqfactor_analyzer_demo.py)，使用 akshare 获取数据后做因子分析。

# 参考
[1] jqfactor_analyzer Github, https://github.com/JoinQuant/jqfactor_analyzer
[2] 聚宽因子分析文档, https://www.joinquant.com/help/api/help#JQfactor_analyzer
