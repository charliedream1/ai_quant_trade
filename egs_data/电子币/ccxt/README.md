# 1. 简介

CCXT（CryptoCurrency eXchange Trading Library）是目前最全的加密货币交易所统一接口库，
支持 100+ 交易所的行情、交易、订单簿等数据获取，开源免费。

- GitHub: https://github.com/ccxt/ccxt
- 文档: https://docs.ccxt.com/

优点：
* 完全免费，开源
* 支持 100+ 交易所，统一接口格式
* 支持 Python/JavaScript/PHP 多语言
* 无需注册交易所即可获取公开行情数据

缺点：
* 私有接口（交易、账户）需要交易所 API Key
* 部分交易所存在地域限制
* 免费接口有频率限制

# 2. 安装

```shell
pip install ccxt
```

# 3. 支持的主要交易所

| 交易所 | 代码 | 说明 |
|--------|------|------|
| Binance | binance | 币安，全球最大 |
| OKX | okx | 欧易 |
| Bybit | bybit | bybit |
| Gate | gate | Gate.io |
| Kraken | kraken | 美国 |
| Coinbase | coinbase | 美国 |
| Huobi | huobi | 火币（已更名HTX） |
| Bitfinex | bitfinex | |
| Kucoin | kucoin | |

# 4. 常用接口

| 方法 | 说明 |
|------|------|
| fetch_ticker | 获取最新行情 |
| fetch_ohlcv | 获取K线数据 |
| fetch_order_book | 获取订单簿 |
| fetch_tickers | 批量获取行情 |
| load_markets | 加载交易对列表 |

# 5. 注意事项
* 公开行情接口无需 API Key
* 各交易所频率限制不同，建议间隔大于 1 秒
* 国内访问部分交易所需要代理
* timeframe 格式：1m/5m/15m/30m/1h/4h/1d/1w/1M
