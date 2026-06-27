# egs_skill 目录说明

本目录用于存放与"券商研报分析"相关的参考 Skill、调研资料与自研 Skill 工程。

## 一、已下载的参考 Skill

### A股智能分析助手 (china-stock-analyst)

- **本地路径**：`./china-stock-analyst/`
- **GitHub 仓库**：https://github.com/wjt0321/china-stock-analyst
- **TRAE 论坛发布页**：https://forum.trae.cn/t/topic/17068
- **作者**：幕后猪脚（GitHub: wjt0321）
- **License**：MIT
- **版本**：v3.1.0（截至克隆时）

### 用途定位

本仓库作为"券商研报分析 Skill"的**架构参考样本**，重点借鉴其：

1. `SKILL.md` 作为 Claude Code / TRAE Skill 入口的写法
2. `agents/` 多专家角色并行协作（Team-First）的设计模式
3. `scripts/` 中数据采集、路由、质量门禁的工程化思路
4. `tests/` 回归测试与质量保证机制
5. `plugins/` 插件化扩展机制

### 核心结构速览

```
china-stock-analyst/
├── SKILL.md                 # Skill 入口（TRAE/Claude Code 实际加载点）
├── agents/                  # 8 位专家角色定义（基本面/技术/量化/风险/宏观/行业/消息/审计）
├── scripts/                 # Python 辅助脚本（数据采集、路由、回测、质量门禁）
├── plugins/                 # 插件化扩展（资金流、技术指标）
├── assets/                  # 报告模板
├── references/              # 估值模型说明
├── tests/                   # 回归测试
└── stock-reports/           # 历史报告样例
```

### 关键设计借鉴点

| 设计点 | 借鉴价值 |
|---|---|
| 数据真实性审计前置（`run_data_auditor`） | 研报场景同样需要"研报时效性 + 来源权威性"前置校验 |
| Team-First 并行架构 | 多研报对比、多机构观点汇总可复用此模式 |
| 数据源优先级策略（Web Search > 结构化 API） | 研报场景：聚合平台 > 公众号 > 官网 |
| JSON Schema 约束输出 | 研报结构化提取可参考其 evidences 字段设计 |
| 报告质量门禁（`report_quality_gate.py`） | 研报分析结论的合规性校验 |

## 二、待自研 Skill

### 券商研报分析 Skill（broker-research-analyst）

- **预计路径**：`./broker-research-analyst/`（待创建）
- **状态**：方案设计阶段
- **方案文档**：见 `./PROPOSAL.md`

## 三、克隆方法

如需重新克隆参考 Skill：

```bash
cd /workspace/egs_skill
git clone https://github.com/wjt0321/china-stock-analyst.git
```

## 四、免责声明

- 参考 Skill 版权归原作者所有（MIT License），仅作架构学习与设计参考
- 自研 Skill 中**不直接复制**其业务逻辑代码，仅借鉴工程结构与设计模式
- 研报内容版权归原作者机构所有，本 Skill 仅做信息聚合与分析辅助，不构成投资建议
