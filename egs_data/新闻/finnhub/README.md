# 1. 简介

Finnhub 是一个提供金融数据 API 的平台，免费层覆盖公司新闻、市场新闻、
基础情绪分析等，适合获取国际财经新闻。

- 官网: https://finnhub.io/
- API文档: https://finnhub.io/docs/api
- Python SDK: https://pypi.org/project/finnhub-python/

优点：
* 免费层：60请求/分钟，30请求/秒
* 覆盖公司新闻、市场新闻、情绪分析
* 支持 60+ 全球交易所
* 有官方 Python SDK

缺点：
* 需免费注册获取 API Key
* 实时 WebSocket 新闻流为付费功能
* 免费层覆盖美股为主，国际股票需付费

# 2. 安装

```shell
pip install finnhub-python
```

# 3. 获取 API Key

1. 访问 https://finnhub.io/
2. 注册免费账户
3. 在 Dashboard 获取 API Key（即时获取）

# 4. 常用接口

| 接口 | 说明 |
|------|------|
| /api/v1/news | 市场新闻（通用财经新闻） |
| /api/v1/company-news | 公司新闻（按股票） |
| /api/v1/news-sentiment | 新闻情绪分析 |
| /api/v1/company/basicfinancials | 基础财务数据 |

# 5. 注意事项
* 免费层限制：60请求/分钟
* 公司新闻需要指定日期范围
* 情绪分析返回 -1 到 1 之间的分数
