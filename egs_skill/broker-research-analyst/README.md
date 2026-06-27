# 券商研报分析 Skill（broker-research-analyst）

> 聚焦"研报获取 → 结构化提取 → 多机构观点对比 → 风险识别 → 决策辅助"全链路的 TRAE / Claude Code Skill。

## 核心特性

| 特性 | 说明 |
|---|---|
| 🔌 **免费数据源** | 东方财富研报中心公开接口，无需 API Key |
| 📊 **结构化提取** | 评级、目标价、EPS/PE 预测自动归一化 |
| 👥 **多专家并行** | 6 位 Agent（审计/评级/基本面/风险/共识/主管）协同 |
| 🛡️ **质量门禁** | 时效性 + 机构白名单 + 卖方利益冲突识别 |
| 📄 **PDF 解析** | pdfplumber 抽取正文，识别投资要点/盈利预测/风险提示段落 |
| 📝 **报告生成** | 自动产出 Markdown 报告，含明细表与免责声明 |

## 快速开始

### 安装依赖

```bash
cd broker-research-analyst
pip install -r requirements.txt
```

### 个股研报汇总

```bash
# 生成茅台研报分析报告（不下载 PDF）
python scripts/report_router.py stock --code 600519 --name 贵州茅台 --days 90 \
    --output ./cache/600519_研报分析.md

# 下载 PDF 并解析（用于 LLM 深度分析）
python scripts/report_router.py stock --code 600519 --name 贵州茅台 --days 90 \
    --download --output ./cache/600519_研报分析.md
```

### 行业研报追踪

```bash
python scripts/report_router.py industry --code 473 --name 证券 --days 30 \
    --output ./cache/证券行业_研报.md
```

### 仅查看研报列表（JSON）

```bash
python scripts/eastmoney_adapter.py --code 600519 --type 0 --days 90 --size 20
```

## 目录结构

```
broker-research-analyst/
├── SKILL.md                    # Skill 入口（TRAE/Claude Code 加载点）
├── agents/                     # 6 位专家 Agent 定义
│   ├── report-auditor.md          # 请求审计与路由
│   ├── rating-extractor.md        # 评级/目标价/EPS提取
│   ├── fundamental-extractor.md   # 基本面观点提取
│   ├── risk-spotter.md            # 风险与利益冲突识别
│   ├── consensus-aggregator.md    # 共识与分歧聚合
│   └── supervisor.md              # 主管仲裁与报告生成
├── scripts/                    # Python 辅助脚本
│   ├── eastmoney_adapter.py       # 东方财富研报接口适配（主数据源）
│   ├── pdf_downloader.py          # PDF 批量下载与缓存
│   ├── pdf_parser.py              # PDF 文本抽取与段落识别
│   ├── report_quality_gate.py     # 质量门禁（时效/白名单/利益冲突）
│   ├── generate_report.py         # Markdown 报告生成
│   └── report_router.py           # 统一路由调度（主入口）
├── assets/
│   └── 研报分析模板.md
├── references/
│   ├── 评级体系说明.md
│   └── 机构白名单.md
├── config/
│   └── settings.json
├── tests/
│   └── test_adapter.py
├── cache/                      # 本地缓存（gitignore）
├── .env.example
├── .gitignore
└── requirements.txt
```

## 数据源

### 主数据源：东方财富研报中心

- **列表接口**：`https://reportapi.eastmoney.com/report/list`
- **PDF 下载**：`https://pdf.dfcfw.com/pdf/H3_{infoCode}_1.pdf`
- **覆盖**：全市场券商研报（个股/行业/策略/宏观）
- **费用**：免费，无需 API Key
- **频率限制**：建议请求间隔 ≥ 1 秒

### 辅助数据源

- AKShare `stock_research_report_em`（个股研报聚合）
- WebSearch（兜底，抓取最新研报摘要）

## 运行链路

```
用户请求
  ↓
report-auditor        → 校验请求、路由 stock/industry/strategy
  ↓
report_router.py      → 拉取研报元数据 + 质量门禁
  ↓
[并行]
  rating-extractor       → 评级/目标价/EPS
  fundamental-extractor  → 核心逻辑/看多看空
  risk-spotter           → 风险/利益冲突
  ↓
consensus-aggregator   → 共识与分歧聚合
  ↓
supervisor             → 仲裁 + 生成最终报告
```

## 质量门禁规则

1. **时效性**：发布日期 ≤ 90 天（可配置）
2. **机构权威性**：主流券商白名单（25 家，可关闭）
3. **利益冲突识别**：买入/增持占比 > 80% 且无减持/卖出 → 标记"卖方普遍偏多"

## 与 china-stock-analyst 的关系

| 维度 | china-stock-analyst | broker-research-analyst |
|---|---|---|
| 分析对象 | 股票本身（量价/资金/财报） | 券商研报内容本身 |
| 输出 | 短线交易信号 | 机构观点聚合 |
| 互补 | 提供交易决策 | 提供机构观点参考 |

两者可串联：先用本 Skill 汇总机构研报观点，再用 `china-stock-analyst` 做量价验证。

## 合规与免责

- 仅抓取公开网页研报元数据与公开 PDF，不绕过登录墙
- 不爬微信公众号（合规风险，改用 WebSearch 间接获取）
- 研报版权归原作者机构所有，输出必须标注来源
- **本 Skill 仅作信息聚合与分析辅助，不构成任何投资建议**

## License

MIT
