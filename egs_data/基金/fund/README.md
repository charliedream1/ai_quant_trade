# 基金数据接口示例

基于 AKShare + efinance 获取公募基金数据，无需额外 API Key。

## 覆盖数据

| 数据 | 接口 | 说明 |
|------|------|------|
| 开放式基金净值 | `fund_open_fund_info_em` | 单位/累计净值走势 |
| 基金排行 | `fund_open_fund_rank_em` | 全市场基金业绩排行 |
| 基金持仓 | `fund_portfolio_hold_em` | 股票持仓明细 |
| ETF 历史行情 | `fund_etf_hist_em` | ETF K线（需东财可访问） |
| 基金净值(efinance) | `ef.fund.get_quote_history` | efinance 备选方案 |

## 安装

```bash
pip install akshare efinance
```

## 运行

```bash
python fund_demo.py
```
