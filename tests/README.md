# 测试目录分类说明

本目录按功能边界组织测试，避免新增用例继续堆放在根目录。

| 目录 | 用途 |
|------|------|
| `api/` | FastAPI 路由、WebSocket、跨模块端到端冒烟测试 |
| `agent/` | LLM 客户端、问答链路、环境变量导入与脱敏测试 |
| `core/` | 配置、日志、缓存、数据库和文件存储等核心能力测试 |
| `data/` | 行情/新闻/研报/论文等数据源和 fallback 测试 |
| `engine/` | 市场分析、关系图谱、回测、模拟盘、实盘等引擎测试 |
| `frontend/` | Gradio 页面结构、前端回调服务、Plotly/Pandas 展示测试 |
| `strategy/` | 策略库、策略校验、CLI 构建器测试 |

根目录仅保留 `conftest.py` 和本说明文件。

## 页面巡检工具

`frontend/page_audit_runner.py` 是 Playwright 页面巡检脚本，不作为 pytest 用例自动收集。它用于启动本地服务后逐页点击 Gradio 标签、执行关键按钮、生成截图和 JSON 结果。
