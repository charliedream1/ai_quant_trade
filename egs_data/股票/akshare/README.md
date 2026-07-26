# 1. 简介

AKShare 是目前最完善的免费 Python 金融数据接口库，通过爬虫方式获取各类金融数据，
覆盖股票、期货、期权、基金、外汇、债券、宏观经济、另类数据等多个领域。

- GitHub: https://github.com/akfamily/akshare
- 文档: https://akshare.akfamily.xyz/

优点：
* 完全免费，无需注册
* 数据覆盖面非常广，是目前免费库中最全的
* 接口丰富，持续更新维护

缺点：
* 基于爬虫获取数据，调用频率不宜过高，否则可能被封 IP
* 数据质量依赖数据源网站，可能存在少量缺失或延迟
* 部分接口依赖网站结构，网站改版可能导致接口失效

# 2. 安装

```shell
pip install akshare --upgrade
```

# 3. 接口分类

## 3.1 股票数据
| 接口 | 说明 |
|------|------|
| stock_zh_a_spot_em | A股实时行情（东财） |
| stock_zh_a_hist | A股历史K线（日/周/月/分钟） |
| stock_zh_a_hist_min_em | A股分钟数据（东财） |
| stock_zh_index_daily | 指数历史行情 |
| stock_individual_info_em | 个股基本信息 |
| stock_hsgt_north_net_flow_in_em | 北向资金流入 |
| stock_financial_report_sina | 财务报表（新浪） |
| stock_zh_a_st_em | ST股票列表 |

## 3.2 期货数据
| 接口 | 说明 |
|------|------|
| futures_zh_daily_sina | 期货日K线（新浪） |
| futures_foreign_hist | 外盘期货行情 |
| futures_main_sina | 主力合约 |

## 3.3 基金数据
| 接口 | 说明 |
|------|------|
| fund_open_fund_info_em | 开放式基金净值 |
| fund_etf_hist_em | ETF历史行情 |
| fund_portfolio_hold_em | 基金持仓 |

## 3.4 宏观经济
| 接口 | 说明 |
|------|------|
| macro_china_gdp | 中国GDP |
| macro_china_cpi | 中国CPI |
| macro_china_ppi | 中国PPI |
| macro_china_pmi | 中国PMI |
| macro_china_money_supply | 货币供应量 |
| macro_usa_gdp_monthly | 美国GDP |

## 3.5 外汇数据
| 接口 | 说明 |
|------|------|
| currency_boc_sina | 中国银行外汇牌价 |
| fx_spot_quote | 外汇实时报价 |

# 4. 注意事项
* 基于爬虫获取数据，建议调用间隔大于 1 秒
* 部分接口返回字段可能随数据源网站更新而变化
* 如遇接口报错，可查看 AKShare 官方文档确认接口是否已更新
