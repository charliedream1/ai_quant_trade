# 量化关系图谱参考资料

## 金融相关性网络

| 资料 | 类型 | 项目用途 |
|------|------|----------|
| [Hierarchical structure in financial markets](https://arxiv.org/abs/cond-mat/9802256) | 论文 | 使用收益率相关矩阵和层次结构理解股票聚类，为“收益相关”关系类型提供理论参考 |
| [On the shortest spanning subtree of a graph and the traveling salesman problem](https://www.ams.org/journals/proc/1956-007-01/S0002-9939-1956-0078686-7/) | 论文 | 最小生成树方法可用于从高密度相关矩阵中提取更可读的骨干网络 |
| [NetworkX minimum_spanning_tree](https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.tree.mst.minimum_spanning_tree.html) | 官方文档 | 后续若引入相关性骨干图，可用 NetworkX 做 MST 计算和验证 |

## 股票多关系建模

| 资料 | 类型 | 项目用途 |
|------|------|----------|
| [Temporal Relational Ranking for Stock Prediction](https://arxiv.org/abs/1809.09441) | 论文 | 说明行业、股东、供应链等关系可作为股票预测的多关系输入，支撑本项目多关系图谱分层 |
| [Plotly Network Graphs](https://plotly.com/python/network-graphs/) | 官方文档 | 当前 Gradio 前端直接渲染 Plotly Figure，用于关系图谱节点、边和 hover 信息展示 |

## 本项目关系类型映射

| 关系类型 | 数据含义 | 当前落地 |
|----------|----------|----------|
| 行业 | 同行业、板块成分 | 已支持筛选和摘要 |
| 概念 | 共同题材、主题投资概念 | 已支持筛选和摘要 |
| 产业链 | 上下游、供应链、客户/供应商 | 已预留关系类型 |
| 股东/机构 | 共同股东、机构持仓、基金重仓 | 已预留关系类型 |
| 新闻共现 | 同一新闻/事件中共同出现 | 已预留关系类型 |
| 收益相关 | 收益率相关、联动关系 | 已预留关系类型 |

更完整的方案说明见 `doc/data/relation_graph_research.md`。
