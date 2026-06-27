# 券商研报分析 Skill 设计方案（PROPOSAL）

> Skill 名称：`broker-research-analyst`
> 作者：egs_skill 项目
> 状态：方案设计阶段（待评审 → 实施）
> 参考样本：`./china-stock-analyst/`（A股智能分析助手，MIT）

---

## 一、需求与目标

### 1.1 核心痛点

- 券商研报散落在东方财富、同花顺、慧博、新浪、各机构公众号等多个渠道，检索成本高
- 研报 PDF 篇幅长（10-50 页），散户"看不懂、看不完、抓不住重点"
- 多份研报观点不一致时，缺乏对比与仲裁机制
- 研报有时效性，旧报告容易误导决策
- 研报存在推荐倾向（卖方利益冲突），需要风险识别

### 1.2 目标用户

- 散户投资者（看研报但时间有限）
- 投研助理 / 行业研究员（需要快速汇总机构观点）
- 个人量化研究者（需要结构化研报数据做因子）

### 1.3 Skill 定位

聚焦"**研报获取 → 结构化提取 → 多机构观点对比 → 风险识别 → 决策辅助**"全链路，
不做行情预测、不做交易信号生成（避免与 `china-stock-analyst` 重叠）。

---

## 二、数据源可行性分析（爬取方案 vs 现成接口）

### 2.1 方案对比矩阵

| 数据源 | 获取方式 | 成本 | 稳定性 | 覆盖面 | 推荐度 |
|---|---|---|---|---|---|
| **东方财富研报中心** | 公开 JSON 接口（`reportapi.eastmoney.com`） | 免费 | 高 | 全市场券商 | ⭐⭐⭐⭐⭐ |
| **AKShare `stock_research_report_em`** | Python 库封装东方财富接口 | 免费 | 中（依赖 AKShare 维护） | 个股研报 | ⭐⭐⭐⭐ |
| **`eastmoney-reports` PyPI 包** | 第三方 CLI 工具（manymore13/eastmoney） | 免费 | 中 | 行业/策略/宏观/个股 | ⭐⭐⭐⭐ |
| **新浪财经研报** | HTML 页面解析 | 免费 | 中 | 全市场 | ⭐⭐⭐ |
| **慧博投研资讯** | 网页解析（部分需登录） | 免费+付费 | 中低 | 全市场+深度报告 | ⭐⭐⭐ |
| **券商官方公众号** | 微信公众号文章抓取（合规风险高） | 免费 | 低 | 单家机构 | ⭐⭐（不建议） |
| **东方财富妙想 API**（`mkapi2.dfcfs.com`） | 官方 API（需 APIKey） | 免费+付费 | 高 | 资讯+研报摘要 | ⭐⭐⭐⭐ |
| **Wind / Bloomberg 终端** | 商业 API | 数万元/年 | 极高 | 全市场 | ⭐（成本高，个人不推荐） |

### 2.2 推荐数据源策略（三层金字塔）

**主路径（默认）**：
- 东方财富研报中心公开接口 → 获取研报列表 + 元数据（标题/机构/分析师/评级/目标价/日期）
- PDF 全文通过 `pdf.dfcfw.com` 公开链接下载

**辅路径（补强）**：
- AKShare `stock_research_report_em` 接口 → 个股维度的研报聚合
- `eastmoney-reports` 库 → 批量按行业/类型下载

**兜底路径**：
- WebSearch（TRAE 内置）→ 抓取最新研报摘要、机构观点
- 公众号文章通过 WebSearch 间接获取（不直接爬微信，规避合规风险）

### 2.3 关键接口示例（已验证可用）

```python
# 东方财富研报列表接口（公开 JSON）
# GET https://reportapi.eastmoney.com/report/list?
#   industryCode=*&pageSize=50&pageNo=1&beginTime=2026-06-01
#   &endTime=2026-06-27&fields=&qType=0&orgCode=&author=
# 返回：标题、机构、分析师、评级、目标价、PDF链接、发布时间

# AKShare 个股研报
import akshare as ak
df = ak.stock_research_report_em(symbol="600519")  # 茅台研报列表

# eastmoney-reports 库
# pip install eastmoney-reports
# 命令行：eastmoney query -i 1046 -s 5  # 查询游戏行业最近5篇研报
# 命令行：eastmoney download -i 1046 -o ./reports/  # 批量下载PDF
```

### 2.4 合规与风控边界

- ✅ 只抓取**公开网页**的研报元数据与公开 PDF
- ✅ 遵守 robots.txt，控制请求频率（建议 ≤1 req/s）
- ✅ 不绕过登录墙、不抓取付费内容
- ❌ 不直接爬微信公众号（合规风险，改用 WebSearch 间接获取）
- ❌ 不 redistribute 原文 PDF，仅本地缓存 + 摘要引用
- ⚠️ 研报版权归原作者机构所有，输出必须标注来源

---

## 三、架构设计（借鉴 china-stock-analyst 模式）

### 3.1 目录结构

```
broker-research-analyst/
├── SKILL.md                    # Skill 入口（TRAE/Claude Code 加载点）
├── README.md                   # 安装与使用说明
├── agents/                     # 多专家角色定义
│   ├── report-fetcher.md          # 研报获取与去重
│   ├── report-auditor.md          # 研报时效性与来源校验
│   ├── fundamental-extractor.md   # 基本面观点提取
│   ├── rating-extractor.md        # 评级/目标价/盈利预测提取
│   ├── risk-spotter.md            # 风险提示与利益冲突识别
│   ├── consensus-aggregator.md    # 多机构观点聚合与分歧识别
│   ├── industry-view-extractor.md # 行业/宏观观点提取
│   └── supervisor.md              # 主管仲裁与报告生成
├── scripts/                    # Python 辅助脚本
│   ├── eastmoney_adapter.py        # 东方财富研报接口适配
│   ├── akshare_adapter.py          # AKShare 研报接口适配
│   ├── pdf_downloader.py           # PDF 批量下载与缓存
│   ├── pdf_parser.py               # PDF 文本抽取（pdfplumber）
│   ├── report_router.py            # 统一路由调度
│   ├── report_quality_gate.py      # 质量门禁
│   ├── generate_report.py          # Markdown 报告生成
│   └── config_loader.py            # 配置加载
├── assets/
│   └── 研报分析模板.md             # 输出报告模板
├── references/
│   ├── 评级体系说明.md             # 买入/增持/中性等评级映射
│   └── 机构白名单.md               # 主流券商与分析师识别
├── cache/                      # 本地研报缓存（gitignore）
├── tests/                      # 回归测试
├── config/
│   └── settings.json
├── .env.example
└── requirements.txt
```

### 3.2 运行链路（Team-First，借鉴参考 Skill）

```
1. report_auditor        → 校验请求合法性（股票代码/行业/时间范围）
2. report_fetcher        → 多源并发拉取研报列表 + 去重
3. pdf_downloader        → 下载 PDF 到本地缓存
4. pdf_parser            → 抽取正文文本
5. fundamental_extractor → 提取基本面观点（并行）
6. rating_extractor      → 提取评级/目标价/盈利预测（并行）
7. industry_view_extractor → 提取行业/宏观观点（并行）
8. risk_spotter          → 识别风险提示与利益冲突（并行）
9. consensus_aggregator  → 多机构观点聚合，标记分歧与共识
10. supervisor           → 仲裁 + 生成最终报告
```

### 3.3 输出 JSON Schema（约束 LLM 输出）

```json
{
  "schema_version": "v1",
  "agent": "broker-research-analyst",
  "subject": "600519 贵州茅台",
  "report_count": 8,
  "time_range": "2026-03-01 ~ 2026-06-27",
  "consensus": {
    "rating_distribution": {"买入": 5, "增持": 2, "中性": 1},
    "avg_target_price": 1850.0,
    "target_price_range": [1700, 2100],
    "eps_forecast_2026": 65.2,
    "eps_forecast_2027": 72.8
  },
  "divergence": [
    {"topic": "高端酒需求韧性", "consensus": "看好", "dissent": "1家谨慎"}
  ],
  "key_evidences": [
    {"conclusion": "...", "value": "...", "source": "中信证券-2026-06-15", "url": "..."}
  ],
  "risk_warnings": ["渠道库存压力", "消费降级风险", "税收政策变动"],
  "conflict_of_interest": "卖方机构普遍偏乐观，注意评级倾向",
  "decision_hint": "观察",
  "confidence": "中"
}
```

---

## 四、核心功能大纲

### 4.1 功能矩阵

| 功能 | 输入 | 输出 | 优先级 |
|---|---|---|---|
| **个股研报汇总** | 股票代码 | 多机构评级/目标价/盈利预测聚合 | P0 |
| **行业研报追踪** | 行业名称/代码 | 行业观点、景气度判断、龙头推荐 | P0 |
| **研报结构化提取** | 单篇研报 PDF | 评级、目标价、核心逻辑、风险点 | P0 |
| **多机构观点对比** | 标的 + 时间范围 | 共识点、分歧点、置信度 | P1 |
| **研报时效性校验** | 标的 | 标记过期报告、最新报告高亮 | P1 |
| **风险与利益冲突识别** | 研报集合 | 卖方倾向性提示、风险点汇总 | P1 |
| **研报日报/周报** | 日期范围 | 当日/当周热门研报 Top N | P2 |
| **分析师跟踪** | 分析师姓名 | 其历史研报命中率、新财富排名 | P2 |

### 4.2 触发示例（SKILL.md 中的 prompt 示例）

```text
请汇总 600519（茅台）最近3个月的券商研报观点
请对比中信、中金、华泰对新能源车行业的最新观点
分析这份研报 PDF：./reports/xxx.pdf，提取核心逻辑与风险
请输出本周电力行业的研报热度榜
分析师张三的历史研报准确率如何？
```

---

## 五、关键技术决策

### 5.1 数据采集层

- **主用**：东方财富 `reportapi.eastmoney.com` JSON 接口（无需 Key，稳定）
- **补强**：AKShare `stock_research_report_em`、`stock_analyst_rank_em`（分析师排名）
- **PDF 下载**：`pdf.dfcfw.com` 公开链接，本地缓存 + LRU 淘汰
- **PDF 解析**：`pdfplumber`（中文支持好）+ 兜底 `PyPDF2`

### 5.2 LLM 编排层

- 借鉴参考 Skill 的 **Team-First 并行** 模式
- 每个专家 Agent 用独立 `agents/*.md` 定义角色 + JSON Schema 约束输出
- 主管 Agent 负责仲裁与最终报告渲染

### 5.3 质量门禁层（借鉴参考 Skill 的 `report_quality_gate.py`）

- 研报时效性校验：默认仅采用 3 个月内报告，超期标记
- 来源权威性校验：机构白名单（中信/中金/华泰/国君/海通/广发等）
- 评级一致性校验：评级与目标价方向是否矛盾
- 利益冲突提示：卖方研报普遍偏多，强制标注倾向性

### 5.4 缓存与存储

- 本地缓存目录 `cache/`，按 `机构_标的_日期.pdf` 命名
- 元数据存 SQLite（`cache/reports.db`），支持快速检索
- 缓存默认 30 天过期，可配置

---

## 六、与参考 Skill 的差异化定位

| 维度 | china-stock-analyst | broker-research-analyst（本 Skill） |
|---|---|---|
| 数据源 | AKShare 行情 + 东方财富妙想 API | 东方财富研报接口 + AKShare 研报接口 |
| 分析对象 | 股票本身（量价/资金/财报） | **券商研报内容本身** |
| 输出 | 短线交易信号 + 营收质量评分 | 研报观点聚合 + 多机构共识/分歧 |
| 时间维度 | 实时 + 历史回测 | 研报发布时间窗口（通常 1-3 个月） |
| 风控重点 | 数据真实性、价格锚点 | 研报时效性、卖方利益冲突 |
| 互补关系 | 提供交易决策 | 提供**机构观点参考**，可与前者联动 |

**联动建议**：两者可串联使用——先用本 Skill 汇总机构研报观点，再用 `china-stock-analyst` 做量价验证，形成"机构观点 + 市场信号"双轨研判。

---

## 七、实施路线图

### Phase 1：MVP（最小可用）
- 搭建目录骨架与 SKILL.md
- 实现东方财富研报列表接口适配
- 实现单只股票研报汇总（P0 功能 1）
- 输出基础 Markdown 报告

### Phase 2：结构化提取
- PDF 下载与解析
- 评级/目标价/盈利预测提取 Agent
- 多机构观点聚合

### Phase 3：风险与对比
- 时效性校验、利益冲突识别
- 多机构分歧点识别
- 行业研报追踪

### Phase 4：增强
- 分析师跟踪、研报日报/周报
- 与 `china-stock-analyst` 联动接口
- 回归测试套件

---

## 八、风险与未决问题

1. **东方财富接口变更风险**：公开接口可能随时调整，需做接口适配层隔离
2. **PDF 解析准确率**：研报排版复杂（表格、图表），中文字段提取需调优
3. **卖方倾向性**：研报普遍偏乐观，需在输出中显著标注，避免误导
4. **合规边界**：仅做信息聚合与分析辅助，明确"不构成投资建议"
5. **分析师识别**：同名分析师去重需要执业证书编号辅助

---

## 九、参考资源

- 参考 Skill：`./china-stock-analyst/`（GitHub: wjt0321/china-stock-analyst）
- 东方财富研报中心：https://data.eastmoney.com/report/
- AKShare 文档：https://akshare.akfamily.xyz/
- eastmoney-reports 库：https://pypi.org/project/eastmoney-reports/
- 东方财富妙想 API：https://mkapi2.dfcfs.com
- TRAE Skill 论坛：https://forum.trae.cn/
