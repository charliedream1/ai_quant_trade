# 期货数据接口示例

基于 AKShare 获取国内期货市场数据，无需额外 API Key。

## 覆盖数据

| 数据 | 接口 | 说明 |
|------|------|------|
| 主力连续日K线 | `futures_main_sina` | 主力合约连续行情 |
| 单合约历史K线 | `futures_zh_daily_sina` | 指定合约历史数据 |
| 主力合约列表 | `futures_display_main_sina` | 全市场主力合约清单 |

## 期货代码说明

新浪期货代码格式：`品种字母+月份`，例如：
- `V0`：PVC 主力连续
- `V2409`：PVC 2024年9月合约
- `RB0`：螺纹钢主力连续
- `CU0`：沪铜主力连续

## 安装

```bash
pip install akshare
```

## 运行

```bash
python futures_demo.py
```
