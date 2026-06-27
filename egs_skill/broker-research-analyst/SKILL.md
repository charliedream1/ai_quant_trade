---
name: broker-research-analyst
description: 券商研报分析助手，聚焦"研报获取→结构化提取→多机构观点对比→风险识别→决策辅助"。使用时机：汇总个股券商研报、追踪行业研报、对比多机构观点、识别卖方利益冲突、验证研报时效性。默认数据源为东方财富研报中心公开接口（无需 API Key）。
priority: primary
---

# 券商研报分析助手

## 适用场景

- 汇总某只股票的券商研报观点（评级、目标价、盈利预测）
- 追踪某行业的最新研报动态
- 对比多机构对同一标的的观点共识与分歧
- 识别卖方研报的利益冲突与乐观倾向
- 校验研报时效性，过滤过期报告

示例：

```text
请汇总 600519（茅台）最近3个月的券商研报观点
请对比中信、中金、华泰对新能源车行业的最新观点
分析这份研报 PDF：./reports/xxx.pdf，提取核心逻辑与风险
请输出本周电力行业的研报热度榜
```

## 运行原则

### 1. 数据源优先级

- **主路径**：东方财富研报中心公开接口（`reportapi.eastmoney.com`）
- **辅路径**：AKShare `stock_research_report_em`（个股研报聚合）
- **兜底**：WebSearch（抓取最新研报摘要、机构观点）
- **固定原则**：`eastmoney_api > akshare > websearch`

### 2. Team-First 编排

默认进入多专家并行分析链路：

1. `report-auditor` → 校验请求、路由 stock/industry/strategy
2. `report_router.py` → 拉取研报元数据 + 质量门禁
3. `rating-extractor` → 提取评级/目标价/EPS预测（并行）
4. `fundamental-extractor` → 提取核心逻辑/看多看空（并行）
5. `risk-spotter` → 识别风险与利益冲突（并行）
6. `consensus-aggregator` → 聚合共识与分歧
7. `supervisor` → 仲裁 + 生成最终报告

### 3. 风控优先

- 所有结论必须附证据链（来源机构 + 日期 + URL）
- 卖方利益冲突识别为高时，强制在报告显著位置 ⚠️ 标注
- 研报时效性校验：默认仅采用 90 天内报告
- 输出仅作决策辅助，不得表述为投资指令

## 工具能力

### 数据采集脚本（位于 `scripts/`）

| 脚本 | 功能 | 调用示例 |
|---|---|---|
| `eastmoney_adapter.py` | 东方财富研报列表抓取 | `python eastmoney_adapter.py --code 600519 --type 0 --days 90` |
| `pdf_downloader.py` | PDF 批量下载与缓存 | 由 report_router 内部调用 |
| `pdf_parser.py` | **PDF 解析（三层架构：MarkItDown → pdfplumber → PyPDF2）** | `python pdf_parser.py xxx.pdf --parser markitdown --sections` |
| `report_quality_gate.py` | 质量门禁（时效/白名单/利益冲突） | 由 report_router 内部调用 |
| `generate_report.py` | Markdown 报告生成 | 由 report_router 内部调用 |
| `report_router.py` | **统一路由调度（主入口）** | `python report_router.py stock --code 600519 --output report.md` |

### PDF 解析三层架构 + 图片提取

`pdf_parser.py` 采用主路径 + 兜底机制，任一文本解析器成功即返回：

1. **MarkItDown（微软，主路径）**：LLM 友好的 Markdown 输出，保留表格/标题结构，中文支持好
2. **pdfplumber（兜底 1）**：传统文本抽取，对部分 PDF 格式兼容性更好
3. **PyPDF2（兜底 2）**：最简纯文本，最后保障

**图片提取**（独立于文本解析，双层架构）：
- **主路径 PyMuPDF（fitz）**：速度快（20x）、用 xref 自动去重、保留原格式（JPEG/PNG）
- **兜底 pdfplumber**：当 PyMuPDF 不可用时降级，用内容哈希去重，转 PNG 保存
- **MarkItDown 不支持 PDF 图片提取**（源码层面不调用 page.images，传 llm_client 参数也无效），故不用于图片提取

提取研报中的图表图片（营收走势、毛利率趋势、批发价走势等），保存为本地文件，供 LLM 多模态分析。

- 自动过滤小图标（页眉 logo 等，宽度/高度 < 80px）
- 按 `{pdf名}_images/p{页码}_img{序号}.{ext}` 命名
- 图片路径写入 `ParsedReport.images`，供 LLM 多模态分析使用
- 可通过 `extract_imgs=False` 关闭
- 详细调研见 [PDF_IMAGE_RESEARCH.md](../PDF_IMAGE_RESEARCH.md)

可通过 `prefer_parser` 参数强制指定文本解析器，或在 `config/settings.json` 的 `pdf_parser.chain` 中调整优先级。

### 典型调用链

```bash
# 1. 个股研报汇总（不下载 PDF）
python scripts/report_router.py stock --code 600519 --name 贵州茅台 --days 90 --output ./cache/600519_研报分析.md

# 2. 个股研报汇总（下载 PDF 并解析，用于 LLM 深度分析）
python scripts/report_router.py stock --code 600519 --name 贵州茅台 --days 90 --download --output ./cache/600519_研报分析.md

# 3. 行业研报追踪
python scripts/report_router.py industry --code 473 --name 证券 --days 30 --output ./cache/证券行业_研报.md

# 4. 仅列出研报元数据（JSON，用于快速预览）
python scripts/report_router.py list --code 600519 --days 90 --size 20
```

## 多专家 Agent（位于 `agents/`）

| Agent | 职责 |
|---|---|
| `report-auditor.md` | 请求审计与路由 |
| `rating-extractor.md` | 评级/目标价/盈利预测提取 |
| `fundamental-extractor.md` | 核心逻辑/看多看空观点提取 |
| `risk-spotter.md` | 风险提示与卖方利益冲突识别 |
| `consensus-aggregator.md` | 多机构共识与分歧聚合 |
| `supervisor.md` | 主管仲裁与报告生成 |

## 数据源说明

### 东方财富研报接口（已验证可用）

- **列表接口**：`https://reportapi.eastmoney.com/report/list`
  - 参数：`code`（股票代码）、`industryCode`、`qType`（0个股/1行业/2策略/3宏观）、`beginTime`/`endTime`、`pageSize`
  - 返回：标题、机构、分析师、评级、EPS/PE预测、infoCode（PDF标识）
- **PDF 下载**：`https://pdf.dfcfw.com/pdf/H3_{infoCode}_1.pdf`
- **无需 API Key**，公开接口

### 质量门禁规则

- 时效性：发布日期 ≤ 90 天
- 来源权威性：机构白名单（中信/中金/华泰/国君/海通等 25 家主流券商）
- 利益冲突：买入/增持占比 > 80% 且无减持/卖出时，标记为"卖方普遍偏多"

## 重要约束

1. **合规边界**：仅抓取公开网页研报元数据与公开 PDF，不绕过登录墙，不爬微信公众号
2. **版权声明**：研报版权归原作者机构所有，输出必须标注来源
3. **免责声明**：所有报告必须包含"不构成投资建议"声明
4. **频率控制**：请求间隔 ≥ 1 秒，遵守 robots.txt

## 配置

环境变量见 `.env.example`，配置文件见 `config/settings.json`。

依赖安装：

```bash
pip install -r requirements.txt
```
