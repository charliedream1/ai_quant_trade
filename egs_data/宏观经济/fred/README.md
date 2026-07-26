# 1. 简介

FRED（Federal Reserve Economic Data）是美国圣路易斯联邦储备银行维护的免费宏观经济数据库，
包含数十万条美国及全球经济指标时间序列，是获取宏观经济数据的首选免费源。

- 官网: https://fred.stlouisfed.org/
- API文档: https://fred.stlouisfed.org/docs/api/fred/

优点：
* 完全免费，数据权威
* 覆盖美国及全球宏观经济指标
* 数据更新及时，历史数据长

缺点：
* 需要免费注册获取 API Key
* 主要覆盖美国数据，其他国家数据较少
* 有 API 调用频率限制（120次/分钟）

# 2. 安装

```shell
pip install fredapi
```

或使用 pandas_datareader（无需额外安装 fredapi）：
```shell
pip install pandas-datareader
```

# 3. 获取 API Key

1. 访问 https://fred.stlouisfed.org/
2. 注册免费账户
3. 进入 My Account -> API Keys
4. 申请 API Key（即时获取）

# 4. 常用指标

| 指标代码 | 说明 |
|----------|------|
| GDP | 美国GDP（季度） |
| CPIAUCSL | CPI消费者物价指数 |
| UNRATE | 失业率 |
| FEDFUNDS | 联邦基金利率 |
| GS10 | 10年期国债收益率 |
| GS2 | 2年期国债收益率 |
| DTWEXBGS | 美元指数 |
| M2SL | M2货币供应量 |
| VIXCLS | VIX恐慌指数 |
| DGS10 | 10年期国债收益率（日频） |

# 5. 注意事项
* API Key 请妥善保管，不要上传到公开仓库
* 也可使用 pandas_datareader 无需 fredapi 包
* 数据频率：GDP为季度，CPI为月度，利率为日度
