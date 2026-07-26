# Tushare 股票数据获取样例

本样例演示使用 [Tushare Pro](https://tushare.pro) 获取 A 股日线行情、交易日历等数据。

## 环境依赖

见同目录 `requirements.txt`（版本已锁定为精确版本）。

```bash
pip install -r requirements.txt
```

## 样例文件

| 文件 | 说明 |
| --- | --- |
| `tushare.ipynb` | 使用 Tushare Pro 接口获取股票日线行情、交易日历等数据的 Jupyter Notebook。 |

## 运行方式

```bash
jupyter notebook tushare.ipynb
```

## 说明

- Tushare Pro 为部分免费数据源，需在 [tushare.pro](https://tushare.pro) 注册并获取个人 API Token。
- Notebook 中通过 `from data.private.tushare_token import token` 读取本地 Token（项目内私有模块），
  运行前需将你自己的 Token 配置到该模块，或直接在 Notebook 中替换为 `ts.set_token('你的token')`。
- 免费额度有限，高频或高级接口需要积分（付费）。
