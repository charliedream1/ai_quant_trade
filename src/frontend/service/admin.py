"""Admin frontend service callbacks."""

from __future__ import annotations

from src.agent.model_catalog import (
    create_model,
    delete_model,
    get_model,
    list_models,
    set_default,
    test_model,
    update_model,
)

from .foundation import (
    SYSTEM_LAKE_COLUMNS,
    SYSTEM_SETTING_COLUMNS,
    SYSTEM_STORAGE_COLUMNS,
    Any,
    MarketDataLake,
    MCPServiceManager,
    SchedulerService,
    SkillManager,
    _calendar_range_text,
    compact_json,
    delete_env_value,
    env_status,
    escape,
    global_settings_payload,
    go,
    import_env_file,
    masked_env_rows,
    parse_csv,
    parse_json,
    pd,
    require_id,
    require_text,
    runtime_storage_rows,
    save_global_settings,
    to_frame,
    trading_calendar_alerts,
    trading_calendar_status,
)
from .visuals import model_stat_figure


class AdminServiceMixin:
    """Callbacks owned by the admin frontend domain."""

    def jobs(self) -> pd.DataFrame:
        return to_frame(SchedulerService().list(page=1, page_size=100))

    def create_job(self, name: str, job_type: str, cron: str, params: str, enabled: bool) -> tuple[str, pd.DataFrame]:
        item = SchedulerService().create(
            {
                "name": require_text(name, "任务名称"),
                "job_type": require_text(job_type, "任务类型"),
                "cron": require_text(cron, "Cron 表达式"),
                "target": parse_json(params, "任务参数"),
                "enabled": bool(enabled),
            }
        )
        return (f"任务已创建，ID={item['job_id']}", self.jobs())

    def job_action(self, job_id: Any, action: str) -> tuple[str, pd.DataFrame, pd.DataFrame]:
        value = require_id(job_id, "任务 ID")
        service = SchedulerService()
        if action == "trigger":
            result = service.trigger(value)
        elif action == "enable":
            result = service.enable(value, True)
        elif action == "disable":
            result = service.enable(value, False)
        elif action == "delete":
            service.delete(value)
            result = {"job_id": value, "deleted": True}
        else:
            raise ValueError("不支持的任务操作")
        histories = [] if action == "delete" else service.histories(value, page=1, page_size=100)
        return (compact_json(result), self.jobs(), to_frame(histories))

    def job_histories(self, job_id: Any) -> pd.DataFrame:
        return to_frame(SchedulerService().histories(require_id(job_id, "任务 ID"), page=1, page_size=100))

    def system_runtime_status(self) -> str:
        from src.scheduler import scheduler_runtime

        scheduler = scheduler_runtime.status()
        calendar = trading_calendar_status()
        alerts = trading_calendar_alerts(status=calendar)
        scheduler_label = "运行中" if scheduler.get("running") else "未运行"
        calendar_status = str(calendar.get("status") or "unknown")
        calendar_label = {"ok": "正常", "missing": "文件缺失", "missing_market": "缺少市场", "error": "解析异常"}.get(
            calendar_status, calendar_status
        )
        range_text = _calendar_range_text(calendar)
        updated_at = str(calendar.get("updated_at") or "未记录")
        path = escape(str(calendar.get("path") or "-"))
        source = escape(str(calendar.get("source") or "-"))
        metric = f"节假日 {int(calendar.get('holiday_count') or 0)} 个，补班交易日 {int(calendar.get('trading_day_count') or 0)} 个"
        message = str(calendar.get("message") or "")
        message_html = f"<br><small>{escape(message)}</small>" if message else ""
        alerts_html = ""
        if alerts:
            alert_summary = "；".join(
                f"{str(item.get('title') or item.get('code') or '告警')}：{str(item.get('message') or '')}"
                for item in alerts[:3]
            )
            alerts_html = (
                f"<br><small>系统告警：{escape(alert_summary)}{(escape('；...') if len(alerts) > 3 else '')}</small>"
            )
        return f"**运行状态**  ·  调度器 `{scheduler_label}`（{scheduler.get('backend', '-')}，任务 {scheduler.get('job_count', 0)} 个）  ·  交易日历 `{calendar_label}`  ·  系统告警 `{len(alerts)}` 条\n\n<small>文件：{path}；市场：{escape(str(calendar.get('market') or '-'))}；来源：{source}；覆盖：{escape(range_text)}；更新：{escape(updated_at)}；{escape(metric)}</small>{message_html}{alerts_html}"

    def settings(self) -> tuple[Any, ...]:
        payload = global_settings_payload()
        values = payload["values"]
        return (
            values.get("data_dir") or "",
            values.get("db_path") or "",
            values.get("document_storage_dir") or "",
            values.get("market_parquet_dir") or "",
            values.get("duckdb_path") or "",
            float(values.get("data_timeout_seconds") or 12.0),
            int(values.get("data_http_retries") or 0),
            int(values.get("data_cache_ttl_seconds") or 300),
            values.get("trading_calendar_path") or "",
            values.get("scheduler_executors_path") or "",
            to_frame(payload.get("rows") or [], SYSTEM_SETTING_COLUMNS),
            to_frame(runtime_storage_rows(), SYSTEM_STORAGE_COLUMNS),
            to_frame(MarketDataLake().status_rows(), SYSTEM_LAKE_COLUMNS),
        )

    def save_settings_form(
        self,
        data_dir: str,
        db_path: str,
        document_storage_dir: str,
        market_parquet_dir: str,
        duckdb_path: str,
        data_timeout_seconds: Any,
        data_http_retries: Any,
        data_cache_ttl_seconds: Any,
        trading_calendar_path: str,
        scheduler_executors_path: str,
    ) -> tuple[Any, ...]:
        payload = {
            "data_dir": require_text(data_dir, "数据根目录"),
            "db_path": require_text(db_path, "SQLite 主库路径"),
            "document_storage_dir": require_text(document_storage_dir, "文档存储目录"),
            "market_parquet_dir": require_text(market_parquet_dir, "Parquet 行情湖目录"),
            "duckdb_path": require_text(duckdb_path, "DuckDB 查询库路径"),
            "data_timeout_seconds": float(data_timeout_seconds or 0),
            "data_http_retries": int(data_http_retries or 0),
            "data_cache_ttl_seconds": int(data_cache_ttl_seconds or 0),
            "trading_calendar_path": require_text(trading_calendar_path, "交易日历路径"),
            "scheduler_executors_path": require_text(scheduler_executors_path, "自定义执行体白名单"),
        }
        result = save_global_settings(payload)
        overrides = result.get("env_overrides") or []
        suffix = f"；当前进程环境变量覆盖：{', '.join(overrides)}" if overrides else ""
        return (f"系统设置已保存到 `egs/config.yaml`，重启后全部生效{suffix}。", *self.settings())

    def models(self) -> pd.DataFrame:
        return to_frame(list_models())

    def models_with_stats(self) -> tuple[pd.DataFrame, go.Figure]:
        frame = self.models()
        return (frame, model_stat_figure(frame))

    def model_form(self, model_id: Any) -> tuple[Any, ...]:
        item = get_model(require_id(model_id, "模型 ID"))
        return (
            item.get("name") or "",
            item.get("base_url") or "",
            "",
            item.get("api_key_env") or "",
            item.get("model_name") or "",
            item.get("level") or "fast",
            ", ".join(item.get("purpose") or []),
            float(item.get("temperature") or 0.2),
            int(item.get("max_tokens") or 1200),
            float(item.get("timeout_seconds") or 60),
            item.get("system_prompt") or "",
        )

    def create_model(
        self,
        name: str,
        base_url: str,
        api_key: str,
        api_key_env: str,
        model_name: str,
        level: str,
        purpose: str,
        temperature: Any,
        max_tokens: Any,
        timeout_seconds: Any,
        system_prompt: str,
    ) -> tuple[str, pd.DataFrame]:
        item = create_model(
            {
                "name": require_text(name, "配置名称"),
                "base_url": require_text(base_url, "Base URL"),
                "api_key": str(api_key or "").strip(),
                "api_key_env": str(api_key_env or "").strip(),
                "model_name": require_text(model_name, "模型名称"),
                "level": level or "fast",
                "purpose": parse_csv(purpose),
                "temperature": float(temperature if temperature is not None else 0.2),
                "max_tokens": int(max_tokens or 1200),
                "timeout_seconds": float(timeout_seconds or 60),
                "system_prompt": str(system_prompt or "").strip(),
            }
        )
        return (f"模型配置已创建，ID={item['model_id']}", self.models())

    def update_model(
        self,
        model_id: Any,
        name: str,
        base_url: str,
        api_key: str,
        api_key_env: str,
        model_name: str,
        level: str,
        purpose: str,
        temperature: Any,
        max_tokens: Any,
        timeout_seconds: Any,
        system_prompt: str,
    ) -> tuple[str, pd.DataFrame]:
        payload = {
            "name": require_text(name, "配置名称"),
            "base_url": require_text(base_url, "Base URL"),
            "api_key_env": str(api_key_env or "").strip(),
            "model_name": require_text(model_name, "模型名称"),
            "level": level or "fast",
            "purpose": parse_csv(purpose),
            "temperature": float(temperature if temperature is not None else 0.2),
            "max_tokens": int(max_tokens or 1200),
            "timeout_seconds": float(timeout_seconds or 60),
            "system_prompt": str(system_prompt or "").strip(),
        }
        if str(api_key or "").strip():
            payload["api_key"] = str(api_key).strip()
        item = update_model(require_id(model_id, "模型 ID"), payload)
        return (f"模型配置已更新，ID={item['model_id']}", self.models())

    def model_action(self, model_id: Any, action: str, level: str) -> tuple[str, pd.DataFrame]:
        value = require_id(model_id, "模型 ID")
        if action == "test":
            result = test_model(value)
        elif action == "default":
            result = set_default(value, {"level": level or "fast"})
        elif action in {"enable", "disable"}:
            result = update_model(value, {"enabled": action == "enable"})
        elif action == "delete":
            result = delete_model(value)
        else:
            raise ValueError("不支持的模型操作")
        return (compact_json(result), self.models())

    def environment_variables(self) -> pd.DataFrame:
        return to_frame(masked_env_rows(), ["name", "value", "source"])

    def check_environment_variable(self, name: str) -> tuple[str, pd.DataFrame]:
        result = env_status(require_text(name, "变量名"))
        state = "已配置" if result["configured"] else "未配置"
        locations = "、".join(result.get("locations") or []) or "-"
        return (
            f"环境变量 `{result['name']}` {state}；来源：{locations}；值：`{result.get('masked_value') or '-'}`",
            self.environment_variables(),
        )

    def delete_environment_variable(self, name: str) -> tuple[str, pd.DataFrame]:
        result = delete_env_value(require_text(name, "变量名"))
        message = "已删除" if result["deleted"] else "未找到可删除项"
        return (f"{message}环境变量 `{result['name']}`。", self.environment_variables())

    def import_environment(self, file_path: str, overwrite: bool) -> tuple[str, pd.DataFrame]:
        if not file_path:
            raise ValueError("请选择环境变量文件")
        result = import_env_file(file_path, overwrite=bool(overwrite))
        status = f"已导入 {len(result['imported'])} 个变量，跳过 {len(result['skipped'])} 个；模型密钥立即生效，服务端口和数据目录等运行参数需重启后生效。"
        return (status, self.environment_variables())

    def mcp_servers(self) -> pd.DataFrame:
        rows = MCPServiceManager().list()
        columns = [
            "ID",
            "名称",
            "传输",
            "启用",
            "状态",
            "工具数",
            "失败冷却",
            "剩余秒",
            "失败次数",
            "最近探测",
            "最近调用",
            "调用状态",
            "错误摘要",
        ]
        display_rows = []
        for item in rows:
            probe = item.get("last_probe") or {}
            call = item.get("last_call") or {}
            display_rows.append(
                {
                    "ID": item.get("server_id"),
                    "名称": item.get("name"),
                    "传输": item.get("transport"),
                    "启用": "是" if item.get("enabled") else "否",
                    "状态": item.get("status"),
                    "工具数": item.get("tool_count", 0),
                    "失败冷却": "是" if item.get("cooldown") else "否",
                    "剩余秒": item.get("cooldown_remaining_seconds", 0),
                    "失败次数": item.get("failure_count", 0),
                    "最近探测": probe.get("checked_at") or "未探测",
                    "最近调用": call.get("tool_name") or "未调用",
                    "调用状态": "成功"
                    if call.get("success") is True
                    else "失败"
                    if call.get("success") is False and call.get("checked_at")
                    else "未调用",
                    "错误摘要": item.get("last_failure_reason") or call.get("error") or probe.get("error") or "",
                }
            )
        return to_frame(display_rows, columns)

    def create_mcp(
        self, name: str, service_type: str, transport: str, config: str, enabled: bool
    ) -> tuple[str, pd.DataFrame]:
        payload = parse_json(config, "MCP 连接参数")
        payload.update(
            {
                "name": require_text(name, "MCP 名称"),
                "service_type": service_type or "自定义",
                "transport": transport or "stdio",
                "enabled": bool(enabled),
            }
        )
        item = MCPServiceManager().create(payload)
        return (f"MCP 服务已创建，ID={item['server_id']}", self.mcp_servers())

    def mcp_action(self, server_id: Any, action: str) -> tuple[str, pd.DataFrame]:
        value = require_id(server_id, "MCP 服务 ID")
        service = MCPServiceManager()
        if action == "test":
            result = service.test(value)
        elif action == "enable":
            result = service.enable(value, True)
        elif action == "disable":
            result = service.enable(value, False)
        elif action == "delete":
            service.delete(value)
            result = {"server_id": value, "deleted": True}
        else:
            raise ValueError("不支持的 MCP 操作")
        return (compact_json(result), self.mcp_servers())

    def mcp_call(self, server_id: Any, tool_name: str, arguments: Any) -> tuple[str, pd.DataFrame]:
        value = require_id(server_id, "MCP 服务 ID")
        name = require_text(tool_name, "MCP 工具名")
        params = parse_json(arguments, "MCP 工具参数")
        if not isinstance(params, dict):
            raise ValueError("MCP 工具参数必须是 JSON 对象")
        result = MCPServiceManager().call_tool(value, name, params)
        return (compact_json(result), self.mcp_servers())

    def skills(self) -> pd.DataFrame:
        return to_frame(SkillManager().list())

    def create_skill(
        self, name: str, description: str, source: str, param_schema: str, params: str
    ) -> tuple[str, pd.DataFrame]:
        item = SkillManager().create(
            {
                "name": require_text(name, "Skill 名称"),
                "description": str(description or "").strip(),
                "source": str(source or "用户登记").strip(),
                "param_schema": parse_json(param_schema, "参数 schema"),
                "params": parse_json(params, "默认参数"),
            }
        )
        return (f"Skill 已登记，ID={item['skill_id']}；仅保存参数契约，不执行上传代码。", self.skills())

    def skill_action(self, skill_id: Any, action: str, params: str) -> tuple[str, pd.DataFrame]:
        value = require_id(skill_id, "Skill ID")
        service = SkillManager()
        if action == "enable":
            result = service.enable(value, True)
        elif action == "disable":
            result = service.enable(value, False)
        elif action == "params":
            result = service.params(value, parse_json(params, "Skill 参数"))
        elif action == "run":
            result = service.run(value, parse_json(params, "Skill 参数"))
        else:
            raise ValueError("不支持的 Skill 操作")
        return (compact_json(result), self.skills())
