# 1. 简介

World Bank Open Data API 是世界银行提供的免费全球经济数据接口，
覆盖全球 200+ 国家的经济、社会、人口等指标，无需 API Key。

- 官网: https://data.worldbank.org/
- API文档: https://datahelpdesk.worldbank.org/knowledgebase/articles/889392
- 指标查询: https://data.worldbank.org/indicator

优点：
* 完全免费，无需注册和 API Key
* 覆盖全球 200+ 国家
* 数据权威，来源可靠

缺点：
* 数据更新频率较低（年度数据为主）
* 部分指标数据不完整
* 接口响应较慢

# 2. 安装

```shell
pip install wbdata
```

或使用 pandas_datareader：
```shell
pip install pandas-datareader
```

# 3. 常用指标

| 指标代码 | 说明 |
|----------|------|
| NY.GDP.MKTP.CD | GDP（美元） |
| NY.GDP.PCAP.CD | 人均GDP（美元） |
| SP.POP.TOTL | 总人口 |
| SP.POP.GROW | 人口增长率 |
| FP.CPI.TOTL | 消费者物价指数 |
| NE.IMP.GNFS.CD | 商品和服务进口 |
| NE.EXP.GNFS.CD | 商品和服务出口 |
| GC.TAX.TOTL.GD.ZS | 税收占GDP比例 |
| SL.UEM.TOTL.ZS | 失业率 |
| NY.GNS.ICTR.ZS | 总储蓄占GDP比例 |

# 4. 国家代码

| 代码 | 国家 |
|------|------|
| CHN | 中国 |
| USA | 美国 |
| JPN | 日本 |
| DEU | 德国 |
| GBR | 英国 |
| FRA | 法国 |
| IND | 印度 |
| BRA | 巴西 |
| RUS | 俄罗斯 |

# 5. 注意事项
* 无需 API Key
* 数据多为年度，更新有延迟
* 可通过 pandas_datareader 或 wbdata 包获取
