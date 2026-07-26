# 1. 简介

本目录提供财经新闻、舆情、研报数据的获取示例，基于 AKShare 的新闻接口，
覆盖个股新闻、财经快讯、新闻联播文字稿、微博舆情、新闻情绪指数等。

AKShare 是目前免费金融数据接口库中新闻覆盖最全的，无需 API Key，直接返回 DataFrame。

- AKShare 文档: https://akshare.akfamily.xyz/
- 新闻接口分类: https://akshare.akfamily.xyz/data/news.html

# 2. 接口分类

## 2.1 个股新闻
| 接口 | 说明 |
|------|------|
| stock_news_em | 个股新闻（东方财富） |
| stock_news_main_cx | 财新网主要财经新闻 |

## 2.2 财经快讯
| 接口 | 说明 |
|------|------|
| stock_info_global_cls | 财联社电报快讯 |
| stock_info_global_em | 东方财富全球财经快讯 |
| stock_info_global_sina | 新浪财经全球快讯 |
| stock_info_global_ths | 同花顺全球财经快讯 |
| stock_info_global_futu | 富途牛牛财经快讯 |

## 2.3 官方新闻
| 接口 | 说明 |
|------|------|
| news_cctv | 新闻联播文字稿 |
| news_economic_baidu | 百度财经新闻 |

## 2.4 舆情与情绪
| 接口 | 说明 |
|------|------|
| stock_js_weibo_report | 微博舆情报告 |
| index_news_sentiment_scope | 新闻情绪指数 |

## 2.5 期货新闻
| 接口 | 说明 |
|------|------|
| futures_news_shmet | 上海期货交易所新闻 |

# 3. 安装

```shell
pip install akshare --upgrade
```

# 4. 注意事项
* 新闻接口基于爬虫，调用间隔建议大于 1 秒
* 部分接口依赖数据源网站结构，可能随网站改版而失效
* news_cctv 的 date 参数格式为 YYYYMMDD
* stock_news_em 的 symbol 参数为6位股票代码
