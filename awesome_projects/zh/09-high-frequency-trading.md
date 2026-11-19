# 高频交易

[English](../en/09-high-frequency-trading.md) | [中文](../zh/09-high-frequency-trading.md) | [分类目录](README.md) | [语言入口](../README.md)

## 加密货币

- **[hummingbot](https://github.com/hummingbot/hummingbot)** — 高频量化交易机器人，包含做市、跨市场套利与资金费率套利策略，基于 asyncio，提供终端界面与 Streamlit 看板。
  - 元数据： 语言： Python · 星标数： 20,241 · 许可证： APACHE-2.0 · 维护状态： 活跃 (最近推送 2026-09-28)
  - 文档／主页： https://hummingbot.org
  - 使用点评：可用于对延迟敏感的模拟或执行研究；生产应用需要严格的风险控制。

## 低延迟引擎

- **[quant](https://github.com/wuledan/quant)** — 采用拓扑排序波次并行的微秒级因子 DAG 计算引擎。
  - 元数据： 语言： C++ · 星标数： 11 · 许可证： 未注明 · 维护状态： 活跃 (最近推送 2026-06-01)
  - 文档／主页： -
  - 使用点评：可用于对延迟敏感的模拟或执行研究；生产应用需要严格的风险控制。

- **[hftbacktest](https://github.com/nkaz001/hftbacktest)** — 针对 L2/L3 订单簿数据的高频交易与做市回测器，支持排队位置和延迟建模。
  - 元数据： 语言： Rust · 星标数： 4,875 · 许可证： MIT · 维护状态： 近期维护 (最近推送 2025-12-23)
  - 文档／主页： -
  - 使用点评：适合更重视真实订单簿行为、而非日线数据便利性的加密货币做市研究。

- **[NautilusTrader](https://github.com/nautechsystems/nautilus_trader)** — Rust 原生事件驱动交易引擎，支持确定性回测与实盘执行。
  - 元数据： 语言： Rust · 星标数： 29,839 · 许可证： LGPL-3.0 · 维护状态： 活跃 (最近推送 2026-10-11)
  - 文档／主页： https://nautilustrader.io
  - 使用点评：适合评估贯穿模拟与生产执行链路的低延迟架构。

## 订单簿与低延迟研究

- **[HFT-LOB-Trading-ML](https://github.com/rorysroes/SGX-Full-OrderBook-Tick-Data-Trading-Strategy)** — 基于完整订单簿逐笔数据，使用机器学习研究高频交易策略。
  - 元数据： 语言： Jupyter Notebook · 星标数： 2,045 · 许可证： 未注明 · 维护状态： 较久未更新 (最近推送 2022-08-28)
  - 文档／主页： -
  - 使用点评：可作为交易层的候选资源；生产采用前需验证适配性。

- **[libtrading](https://github.com/libtrading/libtrading)** — 超低延迟交易连接库，使用 C/C++。
  - 元数据： 语言： C · 星标数： 739 · 许可证： 其他／自定义 · 维护状态： 不活跃 (最近推送 2020-12-17)
  - 文档／主页： http://libtrading.org
  - 使用点评：可作为部署层的候选资源；生产采用前需验证适配性。

## 推理部署

- **[onnxruntime](https://github.com/microsoft/onnxruntime)** — 跨平台机器学习推理与训练加速器。
  - 元数据： 语言： C++ · 星标数： 22,049 · 许可证： MIT · 维护状态： 活跃 (最近推送 2026-10-11)
  - 文档／主页： https://onnxruntime.ai
  - 使用点评：可作为部署层的候选资源；生产采用前需验证适配性。

- **[TensorRT](https://github.com/NVIDIA/TensorRT)** — NVIDIA GPU 深度学习推理加速工具。
  - 元数据： 语言： C++ · 星标数： 13,391 · 许可证： APACHE-2.0 · 维护状态： 活跃 (最近推送 2026-09-23)
  - 文档／主页： https://developer.nvidia.com/tensorrt
  - 使用点评：可作为部署层的候选资源；生产采用前需验证适配性。

- **[MNN](https://github.com/alibaba/MNN)** — 阿里巴巴轻量级深度学习推理框架，支持 CPU/GPU/NPU。
  - 元数据： 语言： C++ · 星标数： 16,171 · 许可证： APACHE-2.0 · 维护状态： 活跃 (最近推送 2026-09-30)
  - 文档／主页： -
  - 使用点评：可作为部署层的候选资源；生产采用前需验证适配性。

- **[bolt](https://github.com/huawei-noah/bolt)** — 华为面向 CPU 的深度学习加速工具，支持 ARM/X86 与边缘计算。
  - 元数据： 语言： C++ · 星标数： 955 · 许可证： MIT · 维护状态： 近期维护 (最近推送 2025-04-11)
  - 文档／主页： https://huawei-noah.github.io/bolt/
  - 使用点评：可作为部署层的候选资源；生产采用前需验证适配性。
