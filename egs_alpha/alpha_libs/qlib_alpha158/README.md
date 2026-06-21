# 1. 简介

Qlib 是微软开源的面向 AI 的量化投资平台，内置了业界著名的 **Alpha158** 和 **Alpha360** 两套标准因子集，是量化研究中使用最广泛的因子库之一。

- 主页 | https://qlib.readthedocs.io/
- Github | https://github.com/microsoft/qlib
- Stars | 16k+
- 协议 | MIT

## 1.1 Alpha158 与 Alpha360

| 因子集 | 因子数 | 说明 |
|--------|--------|------|
| Alpha158 | 158 | 覆盖趋势跟踪、均值回归、成交量、波动率、资金流向、复合指标六大维度 |
| Alpha360 | 360 | Alpha158 的扩展版，包含更全面的技术因子 |

Alpha158 因子分类：
- **趋势跟踪**：MA5-MA20、ROC10、ADX 等，捕捉动量
- **均值回归**：RSI6、BIAS10 等，识别超买超卖
- **成交量**：VOLUME-MA5、OBV 等，洞察资金流向
- **波动率**：ATR、STD 等，度量风险
- **复合指标**：KDJ、MACD 等

## 1.2 特点

- 因子经过严格的历史回测验证，开箱即用
- 内置数据预处理流程（ZScoreNorm、Fillna、CSZScoreNorm 等）
- 与 Qlib 的 ML 建模流程无缝衔接（LightGBM、XGBoost、LSTM、Transformer 等）
- 支持因子正交化、IC 分析、分层回测

# 2. 安装

```sh
pip install pyqlib
```

数据准备（以 A 股为例）：
```sh
python -c "from qlib.data.data import GetData; GetData().qlib_data(target_dir='~/.qlib/qlib_data/cn_data', region='cn')"
```

# 3. 快速使用

详见 [qlib_alpha158_demo.py](qlib_alpha158_demo.py)，使用 akshare 获取 A 股数据后调用 Alpha158 因子。

# 参考
[1] Qlib 官方文档, https://qlib.readthedocs.io/
[2] Qlib Alpha158 数据集解析, https://github.com/microsoft/qlib/blob/main/qlib/contrib/data/handler.py
