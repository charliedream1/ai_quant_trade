# yfinance / pandas_datareader 海外股票数据获取样例

本样例演示使用 [`yfinance`](https://github.com/ranaroussi/yfinance) 与 [`pandas_datareader`](https://pandas-datareader.readthedocs.io/) 获取海外股票、外汇、加密货币以及宏观经济（FRED / World Bank）数据。

## 环境依赖

见同目录 `requirements.txt`（版本已锁定为精确版本）。

```bash
pip install -r requirements.txt
```

## 样例文件

| 文件 | 说明 |
| --- | --- |
| `yfinance_data.py` | 使用 yfinance 获取美股（AAPL/TSLA）、A 股（000001.SZ）、外汇（USDCNY=X）、加密货币（BTC-USD）的实时与历史行情，以及多股票批量下载。 |
| `pandas_datareader_data.py` | 使用 pandas_datareader 从 Stooq、FRED、World Bank 等数据源获取行情与宏观数据。 |

## 运行方式

```bash
python yfinance_data.py
python pandas_datareader_data.py
```

## 说明

- yfinance 为非官方接口，调用频率过高可能被限流，建议加适当延时。
- pandas_datareader 部分数据源（如 World Bank、FRED）需要网络可访问对应站点。
