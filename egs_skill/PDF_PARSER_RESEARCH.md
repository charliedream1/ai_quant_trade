# PDF 转 Markdown 工具调研报告

> 调研背景：当前 broker-research-analyst skill 使用 `pdfplumber + PyPDF2` 解析研报 PDF，评估是否升级为 MarkItDown / MinerU / Marker 等新一代工具。
> 调研时间：2026-06-27

## 一、主流工具对比矩阵

| 维度 | pdfplumber（当前） | **MarkItDown** | **MinerU** | **Marker** |
|---|---|---|---|---|
| 开发方 | 社区 | **微软 AutoGen 团队** | 上海AI Lab (OpenDataLab) | EndlessAI |
| GitHub Star | 5k+ | **12.6 万** | 6 万+ | 1.8 万 |
| License | MIT | **MIT** | Apache 2.0（模型含 AGPL） | GPL（商用需授权） |
| 安装难度 | 简单（pip） | **极简（pip 一键）** | 中（需下载模型） | 中（需模型） |
| 是否需 GPU | 否 | **否** | 推荐 GPU（CPU 可跑但慢） | 推荐 GPU |
| 处理速度（12页PDF） | ~5 秒 | **4 秒** | 1262 秒（CPU）/ 快 3-5x（GPU） | 630 秒（CPU） |
| PDF 转换成功率 | 中（~60%） | **25%**（复杂/扫描件差） | **98.7%** | 90%+ |
| 中文支持 | 好 | 中 | **极好**（专为中文优化） | 弱（早期不支持中文） |
| 表格识别 | 中等 | 一般（样式丢失） | **极强**（HTML嵌入、跨页合并） | 一般 |
| 公式识别 | 不支持 | 差（乱码） | **强**（LaTeX，92.5%） | 强（LaTeX） |
| 扫描件 OCR | 不支持 | 需 Azure 付费 | **内置** | 内置 |
| 章节结构保留 | 弱 | 弱（纯文本） | **强**（标题层级） | 强 |
| 图片处理 | 提取文字 | 仅占位符 | 导出并关联说明 | 自动导出文件 |
| 多格式支持 | 仅 PDF | **14+ 格式**（Office/音频/图片） | PDF/DOCX/PPTX/XLSX | PDF/EPUB/MOBI |
| MCP 集成 | 无 | **有** | 有 | 无 |
| LLM 友好度 | 中 | **高**（专为 LLM 设计） | 高 | 高 |

## 二、券商研报场景适配性分析

### 2.1 研报 PDF 特征

- **语言**：中文为主
- **格式**：多数为文本型 PDF（非扫描件），少数深度报告含扫描图表
- **结构**：相对规范，含"投资要点/盈利预测/风险提示"等固定段落
- **关键内容**：
  - 文本段落（投资逻辑）→ 需段落级提取
  - **财务预测表格**（EPS/PE/营收预测）→ 需精准表格识别
  - 评级/目标价（散落正文）→ 需文本+上下文
- **篇幅**：10-50 页
- **公式**：罕见（金融研报基本无数学公式）

### 2.2 各工具适配评分（针对研报场景）

| 工具 | 适配度 | 理由 |
|---|---|---|
| pdfplumber | ⭐⭐⭐ | 中文OK、表格中等、轻量，但段落结构与复杂表格弱 |
| **MarkItDown** | ⭐⭐⭐⭐ | 轻量快、LLM友好、MIT、MCP集成；研报多为文本型PDF可规避其扫描件短板 |
| **MinerU** | ⭐⭐⭐⭐⭐ | 中文最强、表格HTML输出、章节结构保留，**财务预测表格提取最佳** |
| Marker | ⭐⭐ | 中文弱、GPL商用受限，不推荐 |

## 三、推荐方案：分层策略

不建议"一刀切"替换，采用**按需分层**策略最优：

### 方案 A：MarkItDown 为主 + pdfplumber 兜底（轻量推荐）⭐⭐⭐⭐

```
研报 PDF
  ↓
MarkItDown 转换（默认）  →  产出 LLM 友好的 Markdown
  ↓ 失败/表格复杂时
pdfplumber 兜底（现有逻辑）
```

**优点**：
- 安装极简（`pip install markitdown[pdf]`），无 GPU 依赖
- 12.6 万 Star，微软维护，稳定
- MIT 许可，商用无风险
- 专为 LLM 设计，输出 token 高效
- 有 MCP Server，可与 TRAE/Claude 原生集成

**缺点**：
- 复杂表格识别一般（财务预测表可能丢格式）
- 需 Azure Document Intelligence 才能处理扫描件（付费）

**适合**：MVP 阶段、轻量部署、多数文本型研报

### 方案 B：MinerU 为主（高精度推荐）⭐⭐⭐⭐⭐

```
研报 PDF
  ↓
MinerU 解析  →  产出 Markdown + HTML 表格
  ↓
LLM 基于 结构化 Markdown 做观点提取
```

**优点**：
- 中文研报解析最强（专为中文优化）
- **财务预测表格 → HTML 嵌入**，合并单元格、跨页表格完整保留
- 章节层级保留，"投资要点/盈利预测/风险提示"段落精准定位
- 内置 OCR，扫描件也能处理
- 准确率 98.7%

**缺点**：
- CPU 慢（12 页需 21 分钟），**需 GPU 才实用**（推荐 8GB+ 显存）
- 模型大（首次下载 GB 级）
- 部署复杂度高
- 模型 AGPL 协议（代码 Apache 2.0，但模型权重有 AGPL 限制）

**适合**：有 GPU 服务器、追求极致解析质量、商业化产品

### 方案 C：分层混合（企业级推荐）⭐⭐⭐⭐⭐

```
研报 PDF
  ↓
快速判断：是否含复杂表格/扫描图表？
  ├─ 否 → MarkItDown（快、轻）  → 90% 研报走此路
  └─ 是 → MinerU（精、重）      → 10% 复杂研报走此路
  ↓
统一输出 Markdown + 结构化字段
```

**优点**：兼顾速度与精度，按需调度
**缺点**：需维护两套解析器，复杂度最高

## 四、对当前 Skill 的改造建议

### 4.1 短期（MVP 增强）：方案 A

改造 `scripts/pdf_parser.py`，将 MarkItDown 作为主解析器，pdfplumber 作为兜底：

```python
# 优先级：MarkItDown > pdfplumber > PyPDF2
def parse_pdf(file_path):
    try:
        from markitdown import MarkItDown
        md = MarkItDown()
        result = md.convert(str(file_path))
        return ParsedReport(full_text=result.text_content, ...)
    except Exception:
        # 回退到现有 pdfplumber 逻辑
        return _try_pdfplumber(file_path)
```

**改动量**：小（仅 pdf_parser.py 一个文件）
**收益**：LLM 友好度提升、段落结构更清晰、社区维护更好
**风险**：低（pdfplumber 兜底，不会比现在差）

### 4.2 中期（精度提升）：方案 B/C

当确认有 GPU 资源时，集成 MinerU 处理复杂表格：

```python
# 检测到表格密集型研报时调用 MinerU
def parse_pdf_with_mineru(file_path):
    import mineru
    result = mineru.parse(str(file_path))
    # result.markdown 含 HTML 表格，财务预测表完整保留
    return ParsedReport(full_text=result.markdown, tables=result.tables, ...)
```

**改动量**：中（新增 mineru_adapter.py，路由层增加判断）
**收益**：财务预测表格提取准确率从 ~60% → 98%+
**前提**：需 GPU 环境

### 4.3 推荐决策路径

```
是否立即改造？
  ├─ 是 → 采用方案 A（MarkItDown 为主 + pdfplumber 兜底）
  │       改动小、收益明确、风险低
  └─ 否 → 保持现状，待以下条件触发再升级：
          - 实测 pdfplumber 对财务表格丢失率 > 30%
          - 获得 GPU 服务器资源
          - 此时直接上方案 C（MinerU + MarkItDown 分层）
```

## 五、关键验证点（改造前需实测）

建议在改造前，用 3-5 篇真实研报 PDF 实测以下指标：

1. **段落完整性**：投资要点/盈利预测/风险提示段落是否完整提取
2. **表格保真度**：财务预测表（EPS/PE 多年数据）是否能正确识别行列
3. **评级/目标价**：散落正文的数字能否被上下文关联
4. **处理速度**：单篇研报解析耗时是否可接受（< 30 秒）
5. **失败率**：批量处理 20 篇研报的成功率

## 六、参考链接

- MarkItDown: https://github.com/microsoft/markitdown
- MinerU: https://github.com/opendatalab/MinerU
- Marker: https://github.com/VikParuchuri/marker
- MinerU 在线体验: https://mineru.opendatalab.org/
- MarkItDown MCP Server: https://github.com/microsoft/markitdown (含 mcp extras)

## 七、结论

**针对券商研报场景的明确建议**：

1. **首选 MarkItDown 作为默认解析器**（方案 A）：轻量、LLM友好、微软背书、MIT许可，与当前 skill 架构契合度高。研报多为文本型 PDF，可规避其扫描件短板。

2. **保留 pdfplumber 作为兜底**：现有逻辑不删，确保稳定性。

3. **MinerU 作为可选增强**：当用户有 GPU 且需要极致表格精度时（如提取复杂财务预测表），通过配置开关启用。不作为默认依赖，避免部署门槛过高。

4. **不推荐 Marker**：中文支持弱 + GPL 商用限制，与研报场景不匹配。

**一句话总结**：用 MarkItDown 升级主解析路径，pdfplumber 兜底，MinerU 按需启用——这是研报场景下速度、精度、部署成本的最优平衡。
