"""Playwright page audit runner for the Gradio frontend."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from loguru import logger

try:
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
except ModuleNotFoundError:  # Browser tooling is optional outside page-audit runs.
    PlaywrightTimeoutError = TimeoutError

NAVIGATION_CONSOLE_NOISE = (
    "BodyStreamBuffer was aborted",
    "Unexpected error Connection errored out",
    "TypeError: Failed to fetch",
)

CLICK_EXACT = """
([text, index]) => {
  const visibleMatches = (selector) => Array.from(document.querySelectorAll(selector))
    .filter((button) => {
      const rect = button.getBoundingClientRect();
      const style = window.getComputedStyle(button);
      const centerX = rect.left + rect.width / 2;
      const centerY = rect.top + rect.height / 2;
      const topElement = document.elementFromPoint(centerX, centerY);
      return button.innerText.trim() === text
        && rect.width > 8
        && rect.height > 8
        && centerX >= 0
        && centerY >= 0
        && centerX <= window.innerWidth
        && centerY <= window.innerHeight
        && style.display !== 'none'
        && style.visibility !== 'hidden'
        && style.pointerEvents !== 'none'
        && topElement
        && (topElement === button || button.contains(topElement));
    });
  const tabMatches = visibleMatches('[role="tab"]');
  const buttons = tabMatches.length > 0 ? tabMatches : visibleMatches('button');
  if (!buttons[index]) {
    throw new Error(`visible button not found: ${text} #${index}, matches=${buttons.length}`);
  }
  buttons[index].scrollIntoView({block: 'center', inline: 'center'});
  buttons[index].click();
  return buttons.length;
}
"""

BODY_METRICS = """
() => {
  const body = document.body;
  const rect = body.getBoundingClientRect();
  const overflowing = Array.from(document.querySelectorAll('button, textarea, input, table, .dataframe'))
    .filter((el) => {
      const r = el.getBoundingClientRect();
      return r.width > 0 && r.height > 0 && (r.right > window.innerWidth + 6 || r.left < -6);
    }).length;
  const visibleText = body.innerText || '';
  return {
    textLength: visibleText.length,
    errorLike: /error|exception|traceback|失败|错误/i.test(visibleText),
    overflowCount: overflowing,
    scrollHeight: Math.round(body.scrollHeight),
    viewportHeight: window.innerHeight,
    bodyWidth: Math.round(rect.width),
  };
}
"""

OPEN_AI_PANEL = """
() => {
  const button = document.getElementById('ai-floating-button');
  if (!button) {
    throw new Error('AI floating button not found');
  }
  button.click();
}
"""

TAB_SELECTED = """
(text) => Array.from(document.querySelectorAll('[role="tab"]')).some((tab) => {
  const rect = tab.getBoundingClientRect();
  const style = window.getComputedStyle(tab);
  const centerX = rect.left + rect.width / 2;
  const centerY = rect.top + rect.height / 2;
  const topElement = document.elementFromPoint(centerX, centerY);
  return tab.innerText.trim() === text
    && tab.getAttribute('aria-selected') === 'true'
    && rect.width > 8
    && rect.height > 8
    && centerX >= 0
    && centerY >= 0
    && centerX <= window.innerWidth
    && centerY <= window.innerHeight
    && style.display !== 'none'
    && style.visibility !== 'hidden'
    && topElement
    && (topElement === tab || tab.contains(topElement));
})
"""

ELEMENT_CLICKABLE = """
(element) => {
  const rect = element.getBoundingClientRect();
  const style = window.getComputedStyle(element);
  const centerX = rect.left + rect.width / 2;
  const centerY = rect.top + rect.height / 2;
  const topElement = document.elementFromPoint(centerX, centerY);
  return rect.width > 8
    && rect.height > 8
    && centerX >= 0
    && centerY >= 0
    && centerX <= window.innerWidth
    && centerY <= window.innerHeight
    && style.display !== 'none'
    && style.visibility !== 'hidden'
    && style.pointerEvents !== 'none'
    && topElement
    && (topElement === element || element.contains(topElement));
}
"""

MAX_GATE_ITEMS = 20

SCENARIOS: list[dict[str, Any]] = [
    {
        "name": "01_dashboard",
        "tabs": ["投研看板", "总览"],
        "button": "刷新总览",
        "expect_text": ["账户总资产", "资金配置", "快照回撤", "完整数据与历史明细"],
    },
    {
        "name": "01_dashboard_ai_shortcut",
        "tabs": ["投研看板", "总览"],
        "link": "进入 AI 工作台",
        "expect_text": ["项目会话", "模型对话"],
        "wait_ms": 4500,
    },
    {"name": "02_market_overview", "tabs": ["投研看板", "市场分析", "行情看盘"], "button": "刷新行情"},
    {"name": "03_news_center", "tabs": ["投研看板", "市场分析", "新闻中心"], "button": "查询"},
    {"name": "04_stock_analysis", "tabs": ["投研看板", "市场分析", "个股分析"], "button": "分析"},
    {
        "name": "05_relation_graph",
        "tabs": ["投研看板", "市场分析", "关系图谱"],
        "clicks": ["查询关系"],
        "button": "导出图谱JSON",
        "expect_text": ["导出图谱JSON", "图谱导出文件路径"],
    },
    {
        "name": "06_stock_recommend",
        "tabs": ["投研看板", "市场分析", "股票推荐"],
        "clicks": ["生成推荐", "多组参数对比"],
        "button": "候选对比",
        "scroll_text": "多组参数横向对比",
        "expect_text": ["推荐模板库", "推荐候选验证", "生成条件模板", "多组参数对比", "推荐一键回测"],
    },
    {
        "name": "06_resource_pool",
        "tabs": ["投研看板", "市场分析", "资源池"],
        "button": "刷新",
        "expect_text": ["资源池列表", "手工输入标的", "CSV / Excel 导入"],
    },
    {"name": "07_report_search", "tabs": ["投研看板", "市场分析", "研报与模型分析", "研报检索"], "button": "检索"},
    {"name": "08_model_report", "tabs": ["投研看板", "市场分析", "研报与模型分析", "模型报告"], "button": "刷新列表"},
    {"name": "09_paper_search", "tabs": ["投研看板", "市场分析", "论文检索"], "button": "检索"},
    {
        "name": "10_strategy_lifecycle",
        "tabs": ["AI工作台", "模拟模块", "策略构建", "生命周期"],
        "button": "刷新生命周期",
        "expect_text": ["策略生命周期", "实盘候选"],
    },
    {
        "name": "10_strategy_library",
        "tabs": ["AI工作台", "模拟模块", "策略构建", "策略库"],
        "button": "刷新",
        "scroll_text": "策略版本对比",
        "expect_text": ["策略版本对比", "生成策略版本对比", "策略一键回测"],
    },
    {
        "name": "11_preset_strategy",
        "tabs": ["AI工作台", "模拟模块", "策略构建", "预制策略"],
        "button": "刷新预制策略",
    },
    {
        "name": "12_strategy_upload",
        "tabs": ["AI工作台", "模拟模块", "策略构建", "上传策略"],
        "clicks": ["查看示例"],
        "scroll_text": "参数 schema 辅助编辑",
        "expect_text": ["参数 schema 辅助编辑", "追加参数字段", "从源码提取参数"],
    },
    {
        "name": "13_cli_workbench",
        "tabs": ["AI工作台", "模拟模块", "策略构建", "CLI 工作台"],
        "textarea": "生成一个低换手趋势策略",
        "button": "生成策略",
        "scroll_text": "CLI 会话列表与失败重试",
        "expect_text": ["CLI 会话列表与失败重试", "刷新会话列表", "重试会话"],
    },
    {
        "name": "14_backtest",
        "tabs": ["AI工作台", "模拟模块", "策略仿真", "回测"],
        "button": "刷新任务",
        "scroll_text": "订单与组合约束",
        "expect_text": [
            "订单与组合约束",
            "复权方式",
            "单票最大权重",
            "回测证据与模拟衔接",
            "回测参数对比",
        ],
    },
    {
        "name": "15_paper_trading",
        "tabs": ["AI工作台", "模拟模块", "策略仿真", "模拟交易"],
        "text_control": "audit_paper",
        "button": "创建账户",
        "scroll_text": "撤销委托",
        "expect_text": ["撤单订单 ID", "撤销委托"],
    },
    {
        "name": "15_simulation_attribution",
        "tabs": ["AI工作台", "模拟模块", "模拟归因"],
        "button": "生成模拟归因",
    },
    {
        "name": "16_live",
        "tabs": ["AI工作台", "实盘模块", "发布策略"],
        "button": "刷新配置",
        "scroll_text": "发布验证门槛",
        "expect_text": [
            "风控阈值编辑",
            "通道适配器与事件",
            "写入通道事件",
            "发布验证门槛",
            "查看发布验证",
            "暂停",
            "恢复",
            "异常原因",
            "标记异常",
            "dry-run订单计划",
            "运行前风控",
            "运行状态机",
            "异常告警",
            "运行日志",
        ],
    },
    {
        "name": "16_live_attribution",
        "tabs": ["AI工作台", "实盘模块", "归因分析"],
        "button": "生成实盘归因",
    },
    {
        "name": "17_ai_console",
        "tabs": ["AI工作台", "主界面"],
        "expect_text": ["项目会话", "模型对话", "自动化", "MCP 服务", "Skill", "知识库"],
    },
    {"name": "17_ai_daily_market", "tabs": ["AI工作台", "智能洞察", "每日行情"], "button": "刷新每日行情"},
    {"name": "17_ai_data_qa", "tabs": ["AI工作台", "智能洞察", "问数"]},
    {"name": "17_ai_workbench_overview", "tabs": ["AI工作台", "工作流中心", "工作台总览"], "button": "刷新总览"},
    {
        "name": "17_ai_factor_mining",
        "tabs": ["AI工作台", "模拟模块", "因子挖掘"],
        "button": "刷新因子挖掘",
        "scroll_text": "候选风格暴露",
        "expect_text": ["候选分层收益", "候选风格暴露"],
    },
    {
        "name": "17_ai_qlib_workflow",
        "tabs": ["AI工作台", "模拟模块", "Qlib实验"],
        "button": "刷新Qlib状态",
        "expect_text": ["Qlib实验状态", "Qlib运行历史"],
    },
    {"name": "17_ai_workbench_task", "tabs": ["AI工作台", "工作流中心", "AI任务对话"]},
    {"name": "18_ai_workbench_experts", "tabs": ["AI工作台", "工作流中心", "专家助手"], "button": "刷新专家"},
    {"name": "19_ai_workbench_teams", "tabs": ["AI工作台", "工作流中心", "专家团"], "button": "刷新专家团"},
    {"name": "19_ai_workbench_jobs", "tabs": ["AI工作台", "工作流中心", "定时任务助手"], "button": "刷新任务"},
    {"name": "20_ai_workbench_workflow", "tabs": ["AI工作台", "工作流中心", "闭环流程"], "button": "生成闭环快照"},
    {
        "name": "20_local_kb",
        "tabs": ["知识库", "资料库", "本地知识库"],
        "button": "刷新分类",
        "scroll_text": "删除确认",
        "expect_text": ["删除确认", "知识文档"],
    },
    {
        "name": "21_kb_qa",
        "tabs": ["知识库", "资料库", "知识问答"],
        "expect_text": ["会话 ID", "清空当前会话", "保存会话信息", "问答会话"],
    },
    {"name": "22_remote_kb", "tabs": ["知识库", "资料库", "远程知识源"], "button": "刷新"},
    {"name": "22_knowledge_report_search", "tabs": ["知识库", "研报与论文", "研报检索"], "button": "检索"},
    {"name": "22_knowledge_paper_search", "tabs": ["知识库", "研报与论文", "论文检索"], "button": "检索"},
    {"name": "23_learning", "tabs": ["知识库", "学习专栏"], "button": "刷新当前章节"},
    {"name": "24_jobs", "tabs": ["帮助", "定时任务"], "button": "刷新任务"},
    {"name": "25_settings", "tabs": ["帮助", "系统配置", "系统设置"], "button": "刷新"},
    {"name": "26_environment", "tabs": ["帮助", "系统配置", "环境变量"], "button": "刷新"},
    {"name": "27_models", "tabs": ["帮助", "系统配置", "模型管理"], "button": "刷新"},
    {"name": "28_mcp", "tabs": ["帮助", "系统配置", "MCP 服务"], "button": "刷新"},
    {"name": "29_skills", "tabs": ["帮助", "系统配置", "Skill 配置"], "button": "刷新"},
    {"name": "30_help", "tabs": ["帮助", "帮助文档"], "expect_text": ["新窗口打开"]},
    {
        "name": "31_factor_monitor",
        "tabs": ["投研看板", "市场分析", "因子监控"],
        "button": "刷新监控",
        "scroll_text": "风格暴露",
        "expect_text": ["分层收益时序", "风格暴露"],
    },
]

AI_SCENARIOS: list[dict[str, Any]] = [
    {"name": "32_ai_model", "tabs": ["模型问答"]},
    {"name": "33_ai_kb", "tabs": ["知识问答"]},
    {"name": "34_ai_cli", "tabs": ["CLI 助手"], "textarea": "生成一个低换手趋势策略", "button": "生成策略"},
]


def scenario_module(name: str) -> str:
    if name.startswith("01_"):
        return "dashboard"
    if name.startswith(("02_", "03_", "04_", "05_", "06_", "31_")):
        return "market"
    if name.startswith(("07_", "08_", "09_")):
        return "research"
    if name.startswith(("10_", "11_", "12_", "13_")) or name in {
        "17_ai_factor_mining",
        "17_ai_qlib_workflow",
    }:
        return "strategy"
    if name.startswith(("14_", "15_")):
        return "simulation"
    if name.startswith("16_"):
        return "live"
    if name.startswith(("17_", "18_", "19_", "20_ai_")):
        return "ai"
    if name.startswith(("20_local_", "21_", "22_", "23_")):
        return "knowledge"
    if name.startswith(("24_", "25_", "26_", "27_", "28_", "29_", "30_")):
        return "admin"
    raise ValueError(f"未配置巡检模块：{name}")


def modular_tabs(scenario: dict[str, Any], module: str) -> list[str]:
    tabs = [str(tab) for tab in scenario.get("tabs", [])]
    if module == "market":
        return ["市场研究", *tabs[2:]]
    if module == "research":
        return ["研报论文", *tabs[2:]]
    if module == "strategy":
        if scenario["name"] in {"17_ai_factor_mining", "17_ai_qlib_workflow"}:
            return ["策略构建", tabs[-1]]
        return ["策略构建", "策略管理", *tabs[3:]]
    if module == "simulation":
        if scenario["name"] == "15_simulation_attribution":
            return ["策略仿真", "模拟归因"]
        return ["策略仿真", "回测与模拟", *tabs[3:]]
    if module == "live":
        return tabs[1:]
    return tabs


def module_url(base_url: str, module: str) -> str:
    parsed = urlsplit(base_url)
    marker = "/app/"
    marker_index = parsed.path.find(marker)
    if marker_index >= 0:
        app_path = parsed.path[: marker_index + len(marker)]
    else:
        app_path = f"{parsed.path.rstrip('/')}/app/"
    return urlunsplit((parsed.scheme, parsed.netloc, f"{app_path}{module}/", "", ""))


def safe_output(text: str) -> str:
    return text.encode("ascii", "backslashreplace").decode("ascii")


def record_http_error(response: Any, errors: list[str]) -> None:
    status = int(response.status)
    if status >= 500:
        errors.append(f"{status} {response.url}")


def collect_audit_failures(summary: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    for result in summary.get("results", []):
        name = str(result.get("name") or "unknown")
        if result.get("status") != "ok":
            errors = "; ".join(str(error) for error in result.get("errors", []))
            failures.append(f"{name}: {errors or 'scenario failed'}")
            continue
        metrics = result.get("metrics") or {}
        overflow_count = int(metrics.get("overflowCount") or 0)
        if overflow_count > 0:
            failures.append(f"{name}: horizontal overflow count {overflow_count}")
    for message in summary.get("console_errors", []):
        failures.append(f"console: {message}")
    for message in summary.get("http_errors", []):
        failures.append(f"http: {message}")
    return failures[:MAX_GATE_ITEMS]


def is_navigation_console_noise(message: str) -> bool:
    """Identify Gradio queue cancellation messages emitted while leaving a module."""
    return any(pattern in message for pattern in NAVIGATION_CONSOLE_NOISE)


def click_exact(page: Any, text: str, index: int = 0) -> int:
    for role in ("tab", "button"):
        locator = page.get_by_role(role, name=text, exact=True)
        visible_indices: list[int] = []
        for item_index in range(locator.count()):
            item = locator.nth(item_index)
            try:
                item.scroll_into_view_if_needed(timeout=5000)
            except Exception:
                pass
            box = item.bounding_box()
            if box and bool(item.evaluate(ELEMENT_CLICKABLE)):
                visible_indices.append(item_index)
        if visible_indices:
            if index >= len(visible_indices):
                raise RuntimeError(f"visible {role} not found: {text} #{index}, matches={len(visible_indices)}")
            target = locator.nth(visible_indices[index])
            target.scroll_into_view_if_needed(timeout=10000)
            box = target.bounding_box()
            if not box:
                raise RuntimeError(f"visible {role} lost bounding box before click: {text}")
            page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
            return len(visible_indices)
    return int(page.evaluate(CLICK_EXACT, [text, index]))


def click_tab_exact(page: Any, text: str) -> None:
    for _attempt in range(3):
        click_exact(page, text)
        settle(page)
        if bool(page.evaluate(TAB_SELECTED, text)):
            return
        page.wait_for_timeout(1200)
    raise RuntimeError(f"tab not selected after click: {text}")


def settle(page: Any) -> None:
    try:
        page.wait_for_load_state("networkidle", timeout=5000)
    except PlaywrightTimeoutError:
        pass
    page.wait_for_timeout(500)
    page.wait_for_function(
        "() => !/queue:\\s*\\d+\\/\\d+/i.test(document.body.innerText || '')",
        timeout=60000,
    )
    page.wait_for_timeout(700)


def fill_first_visible_control(page: Any, selector: str, value: str) -> None:
    controls = page.locator(selector)
    for index in range(controls.count()):
        control = controls.nth(index)
        box = control.bounding_box()
        if box and box["width"] > 8 and box["height"] > 8:
            control.fill(value)
            settle(page)
            return
    raise RuntimeError(f"visible control not found: {selector}")


def scroll_to_visible_text(page: Any, text: str) -> None:
    candidates = page.get_by_text(text, exact=False)
    for index in range(candidates.count()):
        candidate = candidates.nth(index)
        box = candidate.bounding_box()
        if box and box["width"] > 8 and box["height"] > 8:
            candidate.scroll_into_view_if_needed(timeout=10000)
            page.wait_for_timeout(700)
            return
    raise RuntimeError(f"visible text not found: {text}")


def run_scenario(page: Any, out_dir: Path, scenario: dict[str, Any]) -> dict[str, Any]:
    started = time.perf_counter()
    result: dict[str, Any] = {
        "name": scenario["name"],
        "module": scenario.get("module"),
        "tabs": scenario.get("tabs", []),
        "status": "ok",
        "errors": [],
    }
    try:
        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(300)
        for tab in scenario.get("tabs", []):
            click_tab_exact(page, str(tab))
        if scenario.get("textarea"):
            fill_first_visible_control(page, "textarea", str(scenario["textarea"]))
        if scenario.get("text_control"):
            fill_first_visible_control(page, "input[type='text'], textarea", str(scenario["text_control"]))
        for text in scenario.get("clicks", []):
            click_exact(page, str(text))
            settle(page)
        if scenario.get("link"):
            page.get_by_role("link", name=str(scenario["link"]), exact=False).click()
            settle(page)
        if scenario.get("button"):
            click_exact(page, str(scenario["button"]))
            settle(page)
        if scenario.get("wait_ms"):
            page.wait_for_timeout(int(scenario["wait_ms"]))
        if scenario.get("scroll_text"):
            scroll_to_visible_text(page, str(scenario["scroll_text"]))
        screenshot = out_dir / f"{scenario['name']}.png"
        page.screenshot(path=str(screenshot), full_page=False, timeout=60000)
        result["screenshot"] = screenshot.as_posix()
        result["metrics"] = page.evaluate(BODY_METRICS)
        overflow_count = int(result["metrics"].get("overflowCount") or 0)
        if overflow_count > 0:
            raise RuntimeError(f"horizontal overflow detected: {overflow_count}")
        visible_text = str(page.locator("body").inner_text(timeout=10000))
        missing_text = [text for text in scenario.get("expect_text", []) if str(text) not in visible_text]
        if missing_text:
            raise RuntimeError(f"expected text not visible: {', '.join(missing_text)}")
    except Exception as exc:
        result["status"] = "failed"
        result["errors"].append(str(exc))
        screenshot = out_dir / f"{scenario['name']}_failed.png"
        try:
            page.screenshot(path=str(screenshot), full_page=False, timeout=60000)
            result["screenshot"] = screenshot.as_posix()
        except Exception:
            pass
    result["duration_ms"] = round((time.perf_counter() - started) * 1000, 1)
    return result


def run_audit(base_url: str, out_dir: Path, scenario_names: set[str] | None = None) -> dict[str, Any]:
    try:
        from playwright.sync_api import sync_playwright
    except ModuleNotFoundError as exc:
        raise RuntimeError("运行页面审计前请安装 Playwright 并执行 playwright install chromium") from exc

    out_dir.mkdir(parents=True, exist_ok=True)
    scenarios = [scenario for scenario in SCENARIOS if not scenario_names or scenario["name"] in scenario_names]
    if scenario_names:
        missing = sorted(scenario_names - {scenario["name"] for scenario in scenarios})
        if missing:
            raise ValueError(f"未知巡检场景：{', '.join(missing)}")
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000}, device_scale_factor=1)
        console_errors: list[str] = []
        http_errors: list[str] = []
        navigation_in_progress = [False]
        navigation_noise_count = [0]

        def record_console_message(message: Any) -> None:
            if message.type != "error":
                return
            if navigation_in_progress[0] and is_navigation_console_noise(message.text):
                navigation_noise_count[0] += 1
                return
            console_errors.append(message.text)

        page.on("console", record_console_message)
        page.on("pageerror", lambda exc: console_errors.append(str(exc)))
        page.on("response", lambda response: record_http_error(response, http_errors))

        results: list[dict[str, Any]] = []
        current_module = ""
        for scenario in scenarios:
            module = scenario_module(str(scenario["name"]))
            if module != current_module:
                navigation_in_progress[0] = True
                try:
                    page.goto(module_url(base_url, module), wait_until="domcontentloaded", timeout=60000)
                    page.wait_for_selector("#main-navigation [role='tab']", timeout=60000)
                    page.wait_for_timeout(5000)
                    settle(page)
                finally:
                    navigation_in_progress[0] = False
                current_module = module
            modular_scenario = dict(scenario)
            modular_scenario["module"] = module
            modular_scenario["tabs"] = modular_tabs(scenario, module)
            results.append(run_scenario(page, out_dir, modular_scenario))

        if not scenario_names:
            navigation_in_progress[0] = True
            try:
                page.goto(module_url(base_url, "dashboard"), wait_until="domcontentloaded", timeout=60000)
                page.wait_for_selector("#ai-floating-button", timeout=60000)
                settle(page)
            finally:
                navigation_in_progress[0] = False
            page.evaluate(OPEN_AI_PANEL)
            settle(page)
            results.extend(run_scenario(page, out_dir, scenario) for scenario in AI_SCENARIOS)
        browser.close()
    return {
        "base_url": base_url,
        "results": results,
        "console_errors": console_errors[:MAX_GATE_ITEMS],
        "http_errors": http_errors[:MAX_GATE_ITEMS],
        "ignored_navigation_console_errors": navigation_noise_count[0],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit Gradio pages with Playwright.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8013/app/dashboard/")
    parser.add_argument("--out-dir", default="docs/audit/screenshots/2026-09-12")
    parser.add_argument("--json-out", default="docs/audit/page_audit_2026-09-12.json")
    parser.add_argument("--scenario", action="append", help="只运行指定场景名；可重复传入")
    args = parser.parse_args()

    summary = run_audit(args.base_url, Path(args.out_dir), set(args.scenario) if args.scenario else None)
    failures = collect_audit_failures(summary)
    if failures:
        summary["gate_failures"] = failures
    json_payload = json.dumps(summary, ensure_ascii=False, indent=2)
    Path(args.json_out).write_text(json_payload + "\n", encoding="utf-8")
    logger.info("{}", safe_output(json_payload))
    if failures:
        logger.error("页面巡检门禁失败：{}", safe_output("; ".join(failures)))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
