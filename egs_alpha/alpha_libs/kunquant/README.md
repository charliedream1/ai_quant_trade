# 1. 简介

KunQuant 是一个金融表达式和因子的**编译器、优化器和执行器**，能够将 Alpha101、Alpha158 等因子表达式编译为高度优化的 C++ 代码执行，性能远超 Pandas 实现。

- Github | https://github.com/Menooker/KunQuant
- PyPI | https://pypi.org/project/KunQuant/
- 协议 | MIT

## 1.1 性能对比

以 Alpha001~Alpha101 为例（64 只股票、260 行数据）：

| 实现方式 | 耗时 | 加速比 |
|----------|------|--------|
| Pandas 基础实现 | 6.138s | 1x |
| KunQuant 单线程 | 0.083s | 74x |
| KunQuant 4线程 | 0.027s | 227x |

更大规模测试（Alpha101，1024 只股票，2600 天）：

| 后端 | 耗时 |
|------|------|
| KunQuant 32线程 CPU | 1.04s |
| KunQuant-MLIR RTX5080 GPU | 0.22s |

## 1.2 特点

- 支持 Alpha101（WorldQuant）和 Alpha158（Qlib）因子集
- 批处理模式和流式模式
- 支持单精度/双精度浮点
- x86 和 ARM CPU 均支持，跨 Linux/Windows/macOS
- 支持 Nvidia GPU 后端（KunQuant-MLIR）

# 2. 安装

```sh
pip install KunQuant
```

# 3. 快速使用

详见 [kunquant_demo.py](kunquant_demo.py)，使用 akshare 获取数据后用 KunQuant 高性能计算 Alpha101 因子。

# 参考
[1] KunQuant 文档, https://pypi.org/project/KunQuant/
[2] Alpha101 论文, https://arxiv.org/pdf/1601.00991
