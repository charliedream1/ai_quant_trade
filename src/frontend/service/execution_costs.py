"""Execution preview and readable cost evidence without starting a backtest."""

import json

import yaml

from src.core.repository import Repository
from src.engine.backtest.capabilities import strategy_capability
from src.engine.execution.config import resolve_costs
from src.strategy.composition.validation import compile_plan
from src.strategy.parameters import StrategyParameters


class ExecutionCostsMixin:
    def execution_cost_preview(self, value, strategy_id=None, definition=None):
        try:
            legacy = {}
            if definition:
                legacy = compile_plan(yaml.safe_load(definition))["execution"]
            elif strategy_id:
                resolved = StrategyParameters().resolve(int(strategy_id), None, None)
                legacy = strategy_capability(int(strategy_id), resolved["resolved_params"], Repository())["execution"]
            result = resolve_costs(value, legacy)
            return json.dumps(result, ensure_ascii=False, indent=2), "已解析本次执行配置；未提交回测、未调用模型。"
        except Exception as exc:
            return "{}", f"执行配置无效：{exc}"


def cost_markdown(metrics):
    if not metrics.get("execution_costs"):
        if metrics.get("engine_mode") == "qlib_qrun":
            return "\n\nQlib费用以原生Workflow配置及其产物为准；未从指标摘要推造执行账本。"
        return "\n\n旧任务未保存完整成本拆分，保持原结果，不按新规则回算。"
    policy = metrics["execution_costs"]
    lines = [
        "\n\n#### 实际执行成本",
        f"费用方案 `{policy['profile']}` · 校验 `{policy['validation_mode']}` · 执行摘要 `{policy['sha256'][:12]}`",
        f"买/卖佣金 {policy['buy_commission_rate']:.4%} / {policy['sell_commission_rate']:.4%}，每外部订单最低 {policy['minimum_commission']:.2f} 元；税费按成交日期解析。",
        f"佣金 {metrics.get('commission_paid', 0):.2f} · 税 {metrics.get('tax_paid', 0):.2f} · 过户 {metrics.get('transfer_fee_paid', 0):.2f} · 其他 {metrics.get('other_fee_paid', 0):.2f} · 滑点归因 {metrics.get('slippage_cost', 0):.2f}",
        f"加回成本收益 {metrics.get('gross_return_before_costs', 0):.2%} · 净收益 {metrics.get('net_return', 0):.2%}；滑点已进入成交价格，不重复扣减。",
        "毛收益是保持实际成交不变加回成本的归因，不是另跑的零成本策略。",
    ]
    lines.extend("- " + gap for gap in metrics.get("execution_gaps", []))
    return "\n\n".join(lines)
