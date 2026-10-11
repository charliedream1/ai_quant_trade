# -*- coding: utf-8 -*-
"""配置模块测试"""
import os
import tempfile


from excel_monitor.config_loader import AppConfig, load_config


def test_default_config():
    """测试默认配置"""
    cfg = AppConfig()
    assert cfg.refresh_interval == 3
    assert cfg.excel_template == "看盘模板.xlsx"
    assert "上证指数" in cfg.market_indices
    assert len(cfg.watch_stocks) > 0


def test_sheet_names():
    """测试 Sheet 名称映射"""
    cfg = AppConfig()
    assert cfg.sheets["market_overview"] == "大盘"
    assert cfg.sheets["detailed_quotes"] == "详细行情"
    assert cfg.sheets["news"] == "新闻"
    assert cfg.sheets["custom_watch"] == "个性定制看盘"


def test_custom_watch_columns():
    """测试定制看盘列"""
    cfg = AppConfig()
    assert "代码" in cfg.custom_watch_columns
    assert "名称" in cfg.custom_watch_columns


def test_alert_columns():
    """测试预警条件列配置"""
    cfg = AppConfig()
    assert "涨跌幅下限" in cfg.alert_columns
    assert "涨跌幅上限" in cfg.alert_columns
    assert "价格下限" in cfg.alert_columns
    assert "价格上限" in cfg.alert_columns
    assert len(cfg.alert_columns) == 4


def test_alert_popup_default_enabled():
    """测试预警弹窗默认开启"""
    cfg = AppConfig()
    assert cfg.alert_popup_enabled is True


def test_config_reload_interval_default():
    """测试配置重载间隔默认值"""
    cfg = AppConfig()
    assert cfg.config_reload_interval == 5


def test_config_sheet_name():
    """测试配置 Sheet 名称"""
    cfg = AppConfig()
    assert cfg.sheets["config"] == "配置"


def test_load_config_from_yaml():
    """测试从 YAML 文件加载配置"""
    yaml_content = """
refresh_interval: 10
news_max_rows: 100
watch_stocks:
  - "测试股票A"
  - "测试股票B"
"""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False, encoding="utf-8"
    ) as f:
        f.write(yaml_content)
        tmp_path = f.name

    try:
        cfg = load_config(tmp_path)
        assert cfg.refresh_interval == 10
        assert cfg.news_max_rows == 100
        assert cfg.watch_stocks == ["测试股票A", "测试股票B"]
        # 未覆盖的字段应保持默认值
        assert cfg.excel_template == "看盘模板.xlsx"
    finally:
        os.unlink(tmp_path)


def test_load_config_missing_file_returns_defaults():
    """测试文件不存在时返回默认配置"""
    cfg = load_config("/nonexistent/path.yaml")
    assert cfg.refresh_interval == 3
    assert cfg.excel_template == "看盘模板.xlsx"
