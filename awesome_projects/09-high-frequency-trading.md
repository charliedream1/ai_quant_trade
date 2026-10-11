# High-Frequency Trading

## Crypto

- **[hummingbot](https://github.com/hummingbot/hummingbot)** — High-frequency quant bot with market-making, cross-market arbitrage and funding-rate arbitrage strategies; asyncio-based, TUI + Streamlit dashboard.
  - Metadata: Language: Python · Stars: 20,241 · License: APACHE-2.0 · Maintenance: Active (last push 2026-09-28)
  - Docs/Homepage: https://hummingbot.org
  - Value: Useful for latency-sensitive simulation or execution research; production use needs strict risk controls.

## Low-Latency Engines

- **[quant](https://github.com/wuledan/quant)** — Microsecond-level factor DAG computation engine built with topological-sort wave parallelism.
  - Metadata: Language: C++ · Stars: 11 · License: Not specified · Maintenance: Active (last push 2026-06-01)
  - Docs/Homepage: -
  - Value: Useful for latency-sensitive simulation or execution research; production use needs strict risk controls.

- **[hftbacktest](https://github.com/nkaz001/hftbacktest)** — High-frequency trading and market-making backtester with queue-position and latency modeling for L2/L3 order book data.
  - Metadata: Language: Rust · Stars: 4,875 · License: MIT · Maintenance: Recent (last push 2025-12-23)
  - Docs/Homepage: -
  - Value: Valuable for crypto market-making research where order-book realism matters more than daily-bar convenience.

- **[NautilusTrader](https://github.com/nautechsystems/nautilus_trader)** — Rust-native event-driven trading engine for deterministic backtesting and live execution.
  - Metadata: Language: Rust · Stars: 29,839 · License: LGPL-3.0 · Maintenance: Active (last push 2026-10-11)
  - Docs/Homepage: https://nautilustrader.io
  - Value: Suitable for low-latency architecture evaluation across simulation and production paths.

## Order Book and Low-Latency Research

- **[HFT-LOB-Trading-ML](https://github.com/rorysroes/SGX-Full-OrderBook-Tick-Data-Trading-Strategy)** — High-frequency trading (HFT) strategies using ML on full orderbook tick data.
  - Metadata: Language: Jupyter Notebook · Stars: 2,045 · License: Not specified · Maintenance: Stale (last push 2022-08-28)
  - Docs/Homepage: -
  - Value: Useful as a shortlist source for the Trading layer; verify fit before production adoption.

- **[libtrading](https://github.com/libtrading/libtrading)** — Ultra low-latency trading connectivity library (C/C++).
  - Metadata: Language: C · Stars: 739 · License: Other/Custom · Maintenance: Inactive (last push 2020-12-17)
  - Docs/Homepage: http://libtrading.org
  - Value: Useful as a shortlist source for the Deployment layer; verify fit before production adoption.

## Inference Deployment

- **[onnxruntime](https://github.com/microsoft/onnxruntime)** — Cross-platform ML inferencing/training accelerator.
  - Metadata: Language: C++ · Stars: 22,049 · License: MIT · Maintenance: Active (last push 2026-10-11)
  - Docs/Homepage: https://onnxruntime.ai
  - Value: Useful as a shortlist source for the Deployment layer; verify fit before production adoption.

- **[TensorRT](https://github.com/NVIDIA/TensorRT)** — NVIDIA GPU deep learning inference acceleration.
  - Metadata: Language: C++ · Stars: 13,391 · License: APACHE-2.0 · Maintenance: Active (last push 2026-09-23)
  - Docs/Homepage: https://developer.nvidia.com/tensorrt
  - Value: Useful as a shortlist source for the Deployment layer; verify fit before production adoption.

- **[MNN](https://github.com/alibaba/MNN)** — Alibaba lightweight DL inference (CPU/GPU/NPU).
  - Metadata: Language: C++ · Stars: 16,171 · License: APACHE-2.0 · Maintenance: Active (last push 2026-09-30)
  - Docs/Homepage: -
  - Value: Useful as a shortlist source for the Deployment layer; verify fit before production adoption.

- **[bolt](https://github.com/huawei-noah/bolt)** — Huawei CPU DL acceleration (ARM/X86, edge).
  - Metadata: Language: C++ · Stars: 955 · License: MIT · Maintenance: Recent (last push 2025-04-11)
  - Docs/Homepage: https://huawei-noah.github.io/bolt/
  - Value: Useful as a shortlist source for the Deployment layer; verify fit before production adoption.
