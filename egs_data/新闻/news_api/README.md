# 1. 简介

NewsAPI.org 是一个提供全球新闻数据的 API 服务，覆盖 150,000+ 新闻源，
支持 55 个国家、14 种语言，适合获取国际财经新闻。

- 官网: https://newsapi.org/
- API文档: https://newsapi.org/docs
- Python SDK: https://pypi.org/project/newsapi-python/

优点：
* 免费层：100请求/天，100条结果/请求
* 覆盖 150,000+ 全球新闻源
* 支持 14 种语言，55 个国家
* 接口简单，返回 JSON

缺点：
* 免费版禁止商用
* 文章延迟 24 小时（免费层限制）
* /v2/everything 仅可搜索近 1 个月的文章

# 2. 安装

```shell
pip install newsapi-python
```

# 3. 获取 API Key

1. 访问 https://newsapi.org/
2. 注册免费 Developer 账户
3. 在 Account 获取 API Key

# 4. 常用接口

| 接口 | 说明 |
|------|------|
| /v2/top-headlines | 头条新闻 |
| /v2/everything | 搜索所有新闻 |
| /v2/sources | 新闻源列表 |

# 5. 查询参数

## /v2/top-headlines
| 参数 | 说明 |
|------|------|
| country | 国家代码（如 us, cn） |
| category | 类别（business, technology, science） |
| q | 搜索关键词 |
| pageSize | 每页数量（最大100） |
| page | 页码 |

## /v2/everything
| 参数 | 说明 |
|------|------|
| q | 搜索关键词 |
| from | 开始日期 YYYY-MM-DD |
| to | 结束日期 YYYY-MM-DD |
| sortBy | 排序（relevancy, popularity, publishedAt） |
| language | 语言（en, zh, ...） |

# 6. 注意事项
* 免费层 100请求/天
* 免费版文章延迟 24 小时
* /v2/everything 仅可搜索近 1 个月
* 禁止商用
