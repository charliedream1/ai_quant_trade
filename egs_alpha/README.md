# 因子库

本目录收集了量化投资中常用的 Alpha 因子相关开源工具，分为三大类：

## 目录结构

```
egs_alpha/
├── alpha_libs/          # 因子库：现成的因子计算工具
│   ├── alpha101/        # WorldQuant 101 Alphas
│   ├── stockstats/      # 技术指标库
│   ├── ta_lib/          # TA-Lib 150+ 技术指标
│   ├── qlib_alpha158/   # Qlib Alpha158/Alpha360 因子集
│   └── kunquant/        # KunQuant 高性能因子执行器
├── auto_alpha/          # 自动因子挖掘
│   ├── tsfresh/         # tsfresh 自动时间序列特征提取
│   ├── alphagen/        # AlphaGen 强化学习因子挖掘
│   └── gplearn/         # gplearn 遗传规划因子挖掘
└── alpha_analysis/      # 因子分析评估
    ├── alphalens/        # alphalens 因子分析（Quantopian）
    ├── alphalens_modify/ # alphalens 现代化分支
    └── jqfactor_analyzer/ # 聚客单因子分析工具
```

## 工具速览

| 工具 | 类型 | Stars | 说明 |
|------|------|-------|------|
| [alpha101](alpha_libs/alpha101) | 因子库 | 181 | WorldQuant 101 经典量价因子 |
| [stockstats](alpha_libs/stockstats) | 因子库 | - | 技术指标计算（RSI/MACD/KDJ等） |
| [ta_lib](alpha_libs/ta_lib) | 因子库 | - | 150+ 技术分析指标 |
| [qlib_alpha158](alpha_libs/qlib_alpha158) | 因子库 | 16k | 微软 Qlib 内置 158/360 因子集 |
| [kunquant](alpha_libs/kunquant) | 因子库 | - | Alpha101/158 高性能 C++ 执行器 |
| [tsfresh](auto_alpha/tsfresh) | 自动挖掘 | 7.1k | 自动提取 5000+ 时间序列特征 |
| [alphagen](auto_alpha/alphagen) | 自动挖掘 | 691 | RL 自动生成公式化 Alpha（KDD 2023） |
| [gplearn](auto_alpha/gplearn) | 自动挖掘 | 1.5k+ | 遗传规划符号回归挖掘因子 |
| [alphalens](alpha_analysis/alphalens) | 因子分析 | 3.8k | 因子分析 tear sheet 标准工具 |
| [alphalens_modify](alpha_analysis/alphalens_modify) | 因子分析 | - | alphalens 现代化分支 |
| [jqfactor_analyzer](alpha_analysis/jqfactor_analyzer) | 因子分析 | - | 聚宽 A 股专用因子分析 |
