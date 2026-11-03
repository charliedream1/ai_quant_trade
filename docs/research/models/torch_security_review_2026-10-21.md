# Torch 告警触发路径与升级核查

2026-10-21，Codex。本轮范围为核实告警及可用方案，没有修改现用模型环境或 requirements-models.txt。

## 当前环境和代码路径

当前可选依赖固定 torch 2.9.1。pip-audit 仍报告四项漏洞，不能把模型回测通过当作漏洞已消除。审计原始结果见 [当前模型依赖](../../audit/platform_fix_2026-10-21/model_dependency_audit.json)。

本项目 `src/strategy/models/neural_backend.py:NeuralEnsemble` 在内存构建 Linear/ReLU 网络，以 AdamW 训练，从数值特征生成预测；没有提供权重文件导入入口。对当前 `src/strategy/models/` 静态检查，未发现 torch.load、torch.export.load、torch.jit.script 或 lstm_cell 的直接调用。因此下表所列触发入口不在当前 MLP 的显式调用链中；这是有限范围的代码分析，不证明整个 Torch 包或任意用户上传的 Python 策略安全。

| 告警 | 涉及路径 | 核查结论 |
| --- | --- | --- |
| CVE-2026-24747 / PYSEC-2026-2286 | weights_only 模型文件反序列化 | PyTorch 官方公告标明 2.9.1 及以下受影响，2.10.0 起修复；本项目当前 MLP 不读取此类权重文件 |
| CVE-2025-3000 / PYSEC-2025-194 | torch.jit.script | 当前审计记录修复版本为 2.13.0；当前 MLP 不使用 JIT，仍保留审计结果 |
| CVE-2025-3001 / PYSEC-2025-195 | lstm_cell 的非法权重尺寸 | 审计记录修复版本为 2.10.0，上游提供尺寸校验修复提交；当前 MLP 不使用 LSTM |
| CVE-2026-4538 / PYSEC-2026-139 | pt2 / torch.export.load | 上游相关 PR 已关闭，不能把关闭当作合并修复；当前审计记录没有明确修复版本，本项目没有 pt2 导入入口 |

来源：[PyTorch 权重加载公告](https://github.com/pytorch/pytorch/security/advisories/GHSA-63cw-57p8-fm3p)、[PyPA JIT 记录](https://github.com/pypa/advisory-database/blob/main/vulns/torch/PYSEC-2025-194.yaml)、[PyPA LSTM 记录](https://github.com/pypa/advisory-database/blob/main/vulns/torch/PYSEC-2025-195.yaml)、[LSTM 上游修复](https://github.com/pytorch/pytorch/commit/999d94b5ede5f4ec111ba7dd144129e2c2725b03)、[pt2 上游 PR](https://github.com/pytorch/pytorch/pull/176791)。

PyTorch 的[官方安全规范](https://github.com/pytorch/pytorch/security/policy)强调模型与其 Python 实现属于可执行程序；外部模型、TorchScript 或不可信权重需要按代码执行处理。当前没有权重导入功能，后续新增时应重新评审，不能只依赖 weights_only 参数。

## 可用候选方案

2026-10-21 查询 [PyPI 官方元数据](https://pypi.org/pypi/torch/json)，最新版本为 2.14.1，要求 Python ≥3.10，存在 CPython 3.11 的 Windows x64、Linux x64 和 Linux ARM64 wheel。候选单包 torch 2.14.1 的 pip-audit 返回无已知漏洞，原始结果见 [候选审计](../../audit/platform_fix_2026-10-21/torch_candidate_audit.json)。元数据及文件名证据见 [候选元数据](../../audit/platform_fix_2026-10-21/torch_candidate_metadata.json)。

候选扫描无告警仅表示当时漏洞数据库没有匹配项，不证明上述未知修复版本的记录已被上游明确解决，也不代替完整依赖解析、安装和功能验证。本轮没有安装 2.14.1，不能宣称其模型结果已通过。

建议下一步在项目内新建隔离环境安装候选版本，重新核对全量依赖审计与 Windows/Linux wheel 兼容性，执行 MLP 训练、样本外预测、日期隔离和真实行情回测，比较耗时与数值。验证通过后再同步实际测试可用的固定版本；当前 requirements-models.txt 继续反映已验证的 2.9.1。
