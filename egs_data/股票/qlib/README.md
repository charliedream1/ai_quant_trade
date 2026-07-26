# 1. 简介

Qlib 是微软开源的 AI 量化投研平台框架，内置数据下载功能，
支持中国和美国市场数据，数据通过雅虎财经获取。

- GitHub: https://github.com/microsoft/qlib
- 文档: https://qlib.readthedocs.io/

优点：
* 微软开源，框架完善，集数据+模型+回测于一体
* 数据格式经过处理，适合直接用于机器学习
* 支持中国(cn)和美国(us)两个市场

缺点：
* 数据通过雅虎财经获取，国内访问可能不稳定
* 数据质量适合研究，实盘建议更换更高质量数据源
* 框架较重，如果仅需要数据可单独使用数据模块

# 2. 安装

```shell
pip install pyqlib
```

# 3. 数据下载

首次使用需要下载数据到本地：

```shell
# 下载中国区数据
python -m qlib.run.get_data qlib_data --target_dir ~/.qlib/qlib_data/cn_data --region cn

# 下载美国区数据
python -m qlib.run.get_data qlib_data --target_dir ~/.qlib/qlib_data/us_data --region us
```

# 4. 数据说明

Qlib 将数据处理为二进制格式存储，通过统一接口访问：
* 股票代码格式：`SH601318`（沪市）、`SZ000001`（深市）
* 字段前缀 `$` 表示原始字段，如 `$close`、`$open`
* 支持表达式：`($close / $open - 1)` 计算涨跌幅
* 支持算子：`Mean($close, 5)` 计算5日均线

常用字段：
| 字段 | 说明 |
|------|------|
| $open | 开盘价 |
| $close | 收盘价 |
| $high | 最高价 |
| $low | 最低价 |
| $volume | 成交量 |
| $factor | 复权因子 |
| $change | 涨跌额 |

# 5. 注意事项
* 数据下载依赖网络，国内访问雅虎可能需要代理
* 数据默认不含分钟级数据，分钟数据需单独下载
* Qlib 的数据格式与普通 DataFrame 不同，需通过 D.features 接口获取
