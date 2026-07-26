# 1. 简介

雪球网是国内领先的投资者社区，用户可发布投资观点、讨论股票、分享策略。
雪球的数据对市场情绪分析有较高参考价值。

- 官网: https://xueqiu.com/
- pysnowball: https://github.com/zhangyongjiezf/pysnowball

优点：
* 投资者社区质量较高，有专业投资者参与
* 数据丰富：帖子内容、阅读量、评论数、用户信息
* pysnowball 封装了认证流程

缺点：
* 需要登录获取 Cookie（xq_a_token）
* 反爬较强：需完整 Cookie、UA 校验、Referer 校验
* 未登录限流 15 次/分钟

# 2. 安装

```shell
pip install pysnowball
```

# 3. 获取 Cookie

1. 访问 https://xueqiu.com/ 并登录
2. 打开浏览器开发者工具（F12）
3. 在 Application -> Cookies 中找到 `xq_a_token`
4. 复制 token 值

# 4. pysnowball 接口

| 方法 | 说明 |
|------|------|
| set_token | 设置 Cookie token |
|.stock_detail | 股票详情 |
|.timeline | 雪球动态 |
|.quotec | 股票行情 |
|.follows | 关注列表 |
|.followers | 粉丝列表 |

# 5. 注意事项
* xq_a_token 有效期约 7 天，过期需重新获取
* 未登录访问会被限流（15次/分钟）
* 建议调用间隔大于 3 秒
* 也可直接使用 requests 调用雪球 API（需设置完整 Cookie 和 Headers）
