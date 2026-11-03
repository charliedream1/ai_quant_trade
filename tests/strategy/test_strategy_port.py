from pathlib import Path

from src.strategy.loader import StrategyLoader
from src.strategy.strategy_store import StrategyStore
from src.strategy.validator import StrategyValidator


def test_validator_accepts_class_and_function_ports():
    validator = StrategyValidator()

    class_code = Path("egs/strategy_examples/standard_port_strategy.py").read_text(encoding="utf-8")
    class_result = validator.validate_source(class_code)
    assert class_result["adapter_type"] == "class_port"
    assert class_result["entry_class"] == "StandardPortMomentumStrategy"
    assert "bar" in class_result["capabilities"]

    function_code = Path("egs/strategy_examples/function_signal_strategy.py").read_text(encoding="utf-8")
    function_result = validator.validate_source(function_code)
    assert function_result["adapter_type"] == "function_port"
    assert function_result["entry_func"] == "generate_signal"
    assert function_result["params_schema"][0]["name"] == "quantity"


def test_strategy_loader_dry_runs_egs_examples():
    loader = StrategyLoader()

    class_report = loader.dry_run("egs/strategy_examples/standard_port_strategy.py", symbols=["600519"])
    assert class_report["valid"] is True
    assert class_report["entry_name"] == "StandardPortMomentumStrategy"
    assert class_report["signal_count"] == 1

    function_report = loader.dry_run("egs/strategy_examples/function_signal_strategy.py", symbols=["300750"])
    assert function_report["valid"] is True
    assert function_report["adapter_type"] == "function_port"
    assert function_report["sample_signals"][0]["symbol"] == "300750"


def test_strategy_store_imports_example_and_reports_port(client):
    store = StrategyStore()

    item = store.import_example("egs/strategy_examples/function_signal_strategy.py", {"name": "function_port_test"})
    assert item["strategy_id"] > 0
    assert "函数端口" in item["interface_type"]

    detail = store.get(item["strategy_id"], include_code=True)
    assert detail["interface_report"]["valid"] is True
    assert detail["interface_report"]["validation"]["entry_func"] == "generate_signal"

    examples = store.examples()
    assert any(example["path"].endswith("function_signal_strategy.py") for example in examples)
