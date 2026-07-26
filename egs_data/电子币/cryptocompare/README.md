# 电子货币行情聚合接口示例

CryptoCompare 国际加密货币行情聚合 API，补充 CCXT（交易所直连）的数据维度。

## 与 CCXT 的区别

| 维度 | CCXT | CryptoCompare |
|------|------|---------------|
| 数据来源 | 单交易所直连 | 多交易所聚合 |
| 实时行情 | 支持 | 支持 |
| 市值排名 | 不擅长 | 支持（全市场排名） |
| 历史聚合 | 单交易所 | 多交易所加权 |
| API Key | 公开行情无需 | 免费层需注册 |

## 覆盖数据

| 数据 | 接口 | 说明 |
|------|------|------|
| 实时价格 | `/data/price` | 单币种兑多法币 |
| 市值排名 | `/data/top/mktcapfull` | 按市值排名 |
| 历史K线 | `/data/v2/histohour` | 历史 OHLCV |
| 新闻 | `/data/v2/news/` | 加密货币新闻 |

## 安装

```bash
pip install requests pandas
```

## 注册

免费 API Key 注册：https://min-api.cryptocompare.com/
