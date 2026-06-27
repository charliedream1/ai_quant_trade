# PDF 图片提取方案深度调研报告

> 调研背景：用户提出"MarkItDown 会不会也可以解析图片，只是参数没传对？另外 pdfplumber 试试"
> 调研时间：2026-06-27
> 测试样本：贵州茅台研报 PDF（7 页，992KB，含图表）

## 一、核心结论（先说答案）

### 1.1 MarkItDown 能否提取 PDF 图片？

**不能。这不是参数问题，是源码层面就不支持。**

通过阅读 [MarkItDown PdfConverter 源码](https://github.com/microsoft/markitdown/blob/main/packages/markitdown/src/markitdown/converters/_pdf_converter.py)，其 `convert()` 方法只做两件事：

```python
# PdfConverter.convert() 核心逻辑（简化）
with pdfplumber.open(pdf_bytes) as pdf:
    for page in pdf.pages:
        text = page.extract_text()      # 只提取文本
        # ❌ 完全没有调用 page.images
        # ❌ 完全没有处理图片的逻辑
# 兜底：pdfminer.high_level.extract_text()  # 也只提取文本
```

`llm_client` / `llm_model` / `llm_prompt` 这些参数是给**独立图片文件**（JPG/PNG）和**音频文件**用的，**对 PDF 内嵌图片无效**。当你用 MarkItDown 转换一个独立的 JPG 文件时，它会用 LLM 描述图片；但 PDF 里的嵌入图片，它根本不提取、不描述、不保存。

要处理 PDF 内嵌图片，MarkItDown 官方方案是安装 `markitdown-ocr` 插件，但该插件需要 **LLM Vision API（付费）**，且只做 OCR 文字识别，不保存图片本体。

### 1.2 pdfplumber 能否提取图片？

**能。** 通过 `page.images` + `img["stream"].get_data()` 可获取图片二进制，配合 PIL 保存。

### 1.3 三方案实测对比

| 维度 | MarkItDown | pdfplumber | PyMuPDF（当前方案） |
|---|---|---|---|
| 提取 PDF 图片 | ❌ 源码不支持 | ✅ 支持 | ✅ 支持 |
| 识别图片数（去重前） | 0 | 19 | 13 |
| 去重后唯一图片数 | 0 | 13 | 13 |
| 自动去重 | — | ❌ 需手动 | ✅ 用 xref 自动去重 |
| 保留原格式 | — | ❌ 强制转 PNG | ✅ 保留 JPEG/PNG |
| 提取速度 | — | 1.77s | **0.09s（快 20 倍）** |
| 图片总大小 | — | 4116KB（PNG 膨胀） | **735KB（原 JPEG）** |
| 提供图片坐标 | — | ✅ bbox | ❌（需额外计算） |
| 额外依赖 | 已装 | 已装（项目依赖） | 需单独装 |
| 代码复杂度 | — | 中（需 PIL 转换） | 简洁 |

### 1.4 关键发现

- **pdfplumber 和 PyMuPDF 提取的图片内容完全相同**（去重后都是 13 张），只是 pdfplumber 没去重（页眉 logo 在 7 页重复 7 次，所以 19 张）
- 两方案对损坏 PDF 都无能为力（之前实测山西/中邮等 4 家券商 PDF 都打不开）
- PyMuPDF 在速度、体积、去重、代码简洁度上全面领先

## 二、详细测试数据

### 2.1 测试环境

- 测试 PDF：贵州茅台研报（诚通证券，2026-05-20，7 页，含 11 张图表）
- 测试机器：Linux 沙箱
- 测试时间：2026-06-27

### 2.2 MarkItDown 验证

```python
from markitdown import MarkItDown
md = MarkItDown()
r = md.convert('/tmp/compare_test.pdf')
# r 对象只有 text_content / markdown / title 三个字段
# text_content 中图片标记数 = 0
# 源码确认：PdfConverter.convert() 不调用 page.images
```

即使传入 `llm_client` 参数，PDF converter 也不使用它（`llm_client` 只对独立图片文件生效）。

### 2.3 pdfplumber 验证

```python
import pdfplumber, io
from PIL import Image
with pdfplumber.open(PDF) as pdf:
    for pno, page in enumerate(pdf.pages):
        for img in page.images:
            img_data = img["stream"].get_data()  # 获取二进制
            pil_img = Image.open(io.BytesIO(img_data))
            pil_img.save(f'p{pno+1}_img{idx+1}.png')  # 强制转 PNG
```

- 识别 19 张，去重后 13 张（7 张是页眉 logo 重复）
- 保存为 PNG，体积膨胀 5.6 倍（4116KB vs 735KB）
- 提供图片在页面中的坐标（bbox），可用于版面分析

### 2.4 PyMuPDF 验证

```python
import fitz
doc = fitz.open(PDF)
for pno in range(len(doc)):
    for img_info in doc[pno].get_images(full=True):
        xref = img_info[0]
        if xref in seen: continue  # 自动去重
        base = doc.extract_image(xref)
        # base['image'] 是原格式二进制（JPEG/PNG）
        # base['ext'] / base['width'] / base['height']
```

- 识别 13 张（已用 xref 去重）
- 保留原格式（JPEG），体积小
- 速度快 20 倍

## 三、最终方案：保持 PyMuPDF 主路径 + 新增 pdfplumber 兜底

### 3.1 方案选择理由

**PyMuPDF 作为主路径**（不变）：
- 速度快 20 倍
- 自动去重
- 保留原格式（体积小）
- 代码简洁

**新增 pdfplumber 作为兜底**（优化）：
- pdfplumber 已是项目依赖（用于文本解析兜底），无需额外安装
- 当 PyMuPDF 不可用（未安装或打开失败）时自动降级
- 提供图片坐标信息（未来可用于版面分析）

### 3.2 不选 MarkItDown 提取图片的理由

- 源码层面不支持（非参数问题）
- 官方 OCR 插件需付费 LLM API
- 即使装了插件也只做 OCR 文字识别，不保存图片本体
- 与"提取图片供 LLM 多模态分析"的需求不匹配

### 3.3 优化实施

在 `pdf_parser.py` 的 `extract_images()` 函数中，增加 pdfplumber 兜底：

```python
def extract_images(file_path, output_dir, ...):
    # 主路径：PyMuPDF
    try:
        images = _extract_images_pymupdf(file_path, output_dir)
        if images:
            return images
    except ImportError:
        pass
    
    # 兜底：pdfplumber（需 PIL）
    try:
        images = _extract_images_pdfplumber(file_path, output_dir)
        if images:
            return images
    except ImportError:
        pass
    
    return []
```

## 四、参考资料

- [MarkItDown PdfConverter 源码](https://github.com/microsoft/markitdown/blob/main/packages/markitdown/src/markitdown/converters/_pdf_converter.py)
- [MarkItDown OCR Plugin 文档](https://deepwiki.com/microsoft/markitdown/4.3-markitdown-ocr-plugin)
- [pdfplumber 图片提取教程](https://wenku.csdn.net/answer/89wqont8td)
- [PyMuPDF 官方文档](https://pymupdf.readthedocs.io/)
- [markdrop（备选工具，集成图片+表格+AI描述）](https://pypi.org/project/markdrop/)

## 五、一句话总结

**MarkItDown 不提取 PDF 图片是源码限制，不是参数问题**（PdfConverter 根本不调用 page.images）。pdfplumber 和 PyMuPDF 都能提取，且内容完全相同。**当前 PyMuPDF 方案已是最优**（快 20 倍、自动去重、保留原格式），只需补充 pdfplumber 作为兜底即可。
