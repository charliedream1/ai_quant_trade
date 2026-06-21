# 1. 简介

gplearn 是一个基于 Python 的**遗传编程**（Genetic Programming）库，提供 scikit-learn 风格的 API。在量化投资中，它被广泛用于**符号回归**自动挖掘 Alpha 因子表达式。

- 文档 | https://gplearn.readthedocs.io/
- Github | https://github.com/trevorstephens/gplearn
- Stars | 1.5k+
- 协议 | BSD-3-Clause

## 1.1 原理

遗传编程模拟生物进化过程来搜索最优的数学表达式：

1. **初始化**：随机生成一组因子表达式（个体），如 `(close - open) / volume`
2. **适应度评估**：用 IC、收益率等指标评估每个表达式的优劣
3. **选择**：保留适应度高的个体（锦标赛选择）
4. **遗传操作**：
   - **交叉**：交换两个表达式的子树
   - **变异**：随机修改表达式的某部分
   - **繁殖**：直接复制优秀个体
5. **迭代**：重复 2-4 步，直到找到满意的因子表达式

## 1.2 特点

- scikit-learn 风格 API，易于上手
- 支持自定义算子函数（可加入量化专用算子如 ts_rank、ts_mean 等）
- 生成的表达式**可解释**（树结构可视化）
- 支持 SymbolicRegressor、SymbolicTransformer、SymbolicClassifier

## 1.3 量化中的应用

gplearn 在量化中的典型用法：
- **特征工程**：自动搜索 OHLCV 数据的最佳非线性组合
- **因子挖掘**：以 IC 为适应度，自动生成有效因子表达式
- **策略优化**：搜索最优的交易信号公式

# 2. 安装

```sh
pip install gplearn
```

# 3. 快速使用

详见 [gplearn_demo.py](gplearn_demo.py)，使用 akshare 获取数据后用遗传规划自动挖掘因子。

# 参考
[1] gplearn 文档, https://gplearn.readthedocs.io/
[2] 基于遗传规划自动挖掘因子, https://www.joinquant.com/view/community/detail/3c8e3fade8c0a22f
