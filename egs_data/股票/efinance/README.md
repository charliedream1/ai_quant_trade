# 1. 简介

efinance 是一个基于东方财富网的免费金融数据获取库，接口简洁易用，
主要覆盖股票、基金、债券等行情数据。

- GitHub: https://github.com/Micro-sheep/efinance
- 文档: https://github.com/Micro-sheep/efinance/wiki

优点：
* 完全免费，无需注册
* 接口简洁，返回 DataFrame 格式，使用方便
* 支持股票、基金、债券等多种标的

缺点：
* 无大盘指数接口
* 数据源单一（东方财富），稳定性依赖东财网站
* 更新频率不如 akshare 活跃

# 2. 安装

```shell
pip install efinance
```

# 3. 接口列表

## 3.1 股票数据
| 接口 | 说明 |
|------|------|
| ef.stock.get_quote_history | 股票历史行情 |
| ef.stock.get_realtime_quotes | 股票实时行情 |
| ef.stock.get_base_info | 个股基本信息 |
| ef.stock.get_belong_board | 所属板块 |

## 3.2 基金数据
| 接口 | 说明 |
|------|------|
| ef.fund.get_quote_history | 基金历史净值 |
| ef.fund.get_realtime_info | 基金实时信息 |
| ef.fund.get_base_info | 基金基本信息 |

## 3.3 债券数据
| 接口 | 说明 |
|------|------|
| ef.stock.get_quote_history | 可转债行情（传入债券代码） |

# 4. 注意事项
* 可转债代码与股票代码格式相同，通过 klt 参数区分周期
* klt 参数：5/15/30/60分钟，101日，102周
