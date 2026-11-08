"""Strategy frontend service callbacks."""

from __future__ import annotations

from typing import cast

from src.core.config import get_settings
from src.help_docs.links import handbook_markdown

from .backtest_quick import QuickBacktestMixin
from .composition import CompositionServiceMixin
from .contracts import CrossDomainCallbacks
from .foundation import (
    CLI_SESSION_COLUMNS,
    LEARNING_CATEGORY_CHOICES,
    LEARNING_COLUMNS,
    PROJECT_ROOT,
    STRATEGY_LIFECYCLE_COLUMNS,
    STRATEGY_PARAM_SCHEMA_COLUMNS,
    STRATEGY_VERSION_COMPARE_COLUMNS,
    Any,
    CliBuilder,
    Path,
    Repository,
    StrategyStore,
    StrategyValidator,
    _cache_badge,
    _daily_cached,
    _learning_entries,
    _schema_defaults,
    _strategy_param_rows,
    _strategy_param_value,
    compact_json,
    escape,
    go,
    json_loads,
    parse_csv,
    parse_json,
    pd,
    re,
    require_id,
    require_text,
    to_frame,
    ui_error_message,
    yaml,
)
from .visuals import (
    _format_display_time,
    _percent,
    _safe_float,
    format_cli_logs,
    strategy_stat_figure,
)


class StrategyServiceMixin(CompositionServiceMixin, QuickBacktestMixin):
    """Callbacks owned by the strategy frontend domain."""

    def preset_strategies(self) -> pd.DataFrame:
        rows = []
        for item in StrategyStore().examples():
            row = dict(item)
            capabilities = row.get("capabilities") or []
            row["capabilities"] = ", ".join(capabilities) if isinstance(capabilities, list) else str(capabilities)
            rows.append(row)
        return to_frame(rows, ["name", "path", "adapter_type", "entry", "capabilities", "valid", "error"])

    def learning_catalog(self, category: str, keyword: str) -> pd.DataFrame:
        category_value = str(category or "all")
        keyword_value = str(keyword or "").strip().lower()
        rows = []
        for entry in _learning_entries():
            if category_value not in {"", "all"} and entry["category_key"] != category_value:
                continue
            haystack = f"{entry['title']}\n{entry['summary']}\n{entry['path']}".lower()
            if keyword_value and keyword_value not in haystack:
                continue
            rows.append(
                {
                    "chapter_id": entry["chapter_id"],
                    "category": entry["category"],
                    "title": entry["title"],
                    "path": entry["path"],
                    "summary": entry["summary"],
                }
            )
        return to_frame(rows, LEARNING_COLUMNS)

    def learning_tree(self) -> list[dict[str, Any]]:
        """Return chapters grouped by category for the clickable learning directory."""
        groups: list[dict[str, Any]] = []
        entries = _learning_entries()
        for category_label, category_key in LEARNING_CATEGORY_CHOICES[1:]:
            choices = [
                (entry["title"], entry["chapter_id"]) for entry in entries if entry["category_key"] == category_key
            ]
            if choices:
                groups.append({"category_key": category_key, "category": category_label, "chapters": choices})
        return groups

    def learning_detail(self, chapter_id: Any, force_refresh: bool = False) -> str:
        value = require_id(chapter_id, "章节 ID")
        content, cache_hit, refreshed_at = _daily_cached(
            ("learning_detail", value),
            lambda: self._build_learning_detail(value),
            force_refresh=force_refresh,
        )
        return f"{content}\n\n> {_cache_badge(cache_hit, refreshed_at)}"

    def _build_learning_detail(self, chapter_id: int) -> str:
        entry = next((item for item in _learning_entries() if item["chapter_id"] == chapter_id), None)
        if entry is None:
            return "未找到学习章节"
        path = PROJECT_ROOT / entry["path"]
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            content = path.read_text(encoding="utf-8-sig")
        content = handbook_markdown(content, path, get_settings())
        relative = entry["path"]
        if len(content) > 24000:
            content = content[:24000] + "\n\n> 内容较长，页面已截断显示。"
        return f"> 来源：`{relative}`\n\n{content}"

    def strategies(self, keyword: str = "") -> pd.DataFrame:
        try:
            return to_frame(StrategyStore().list(keyword=str(keyword or "").strip() or None, page=1, page_size=100))
        except Exception as exc:
            return to_frame([{"状态": f"策略列表读取失败：{ui_error_message(exc)}"}])

    def strategies_with_stats(self, keyword: str = "") -> tuple[pd.DataFrame, go.Figure]:
        frame = self.strategies(keyword)
        return frame, strategy_stat_figure(frame)

    def strategy_lifecycle(self) -> tuple[str, str, pd.DataFrame]:
        repo = Repository()
        strategies = StrategyStore(repo=repo).list(page=1, page_size=200).get("items") or []
        rows: list[dict[str, Any]] = []
        for strategy in strategies:
            strategy_id = int(strategy["strategy_id"])
            latest_backtest = repo.db.query_one(
                """SELECT t.id AS task_id, t.status, t.created_at, t.started_at, t.finished_at, r.metrics
                   FROM backtest_tasks t
                   LEFT JOIN backtest_results r ON r.task_id = t.id
                   WHERE t.strategy_id = ?
                   ORDER BY COALESCE(t.finished_at, t.started_at, t.created_at) DESC, t.id DESC
                   LIMIT 1""",
                (strategy_id,),
            )
            backtest_count = int(
                repo.db.scalar("SELECT COUNT(*) FROM backtest_tasks WHERE strategy_id = ?", (strategy_id,)) or 0
            )
            finished_backtests = int(
                repo.db.scalar(
                    """SELECT COUNT(*)
                       FROM backtest_tasks
                       WHERE strategy_id = ? AND status IN ('finished', '完成', '已完成', 'success', 'completed')""",
                    (strategy_id,),
                )
                or 0
            )
            paper_count = int(
                repo.db.scalar("SELECT COUNT(*) FROM paper_accounts WHERE strategy_id = ?", (strategy_id,)) or 0
            )
            latest_paper = repo.db.query_one(
                """SELECT id, name, status, updated_at
                   FROM paper_accounts
                   WHERE strategy_id = ?
                   ORDER BY updated_at DESC, id DESC
                   LIMIT 1""",
                (strategy_id,),
            )
            live_count = int(
                repo.db.scalar("SELECT COUNT(*) FROM live_configs WHERE strategy_id = ?", (strategy_id,)) or 0
            )
            latest_live = repo.db.query_one(
                """SELECT id, name, status, updated_at
                   FROM live_configs
                   WHERE strategy_id = ?
                   ORDER BY updated_at DESC, id DESC
                   LIMIT 1""",
                (strategy_id,),
            )
            metrics = json_loads(latest_backtest.get("metrics"), {}) if latest_backtest else {}
            latest_return = (
                _percent(metrics.get("total_return"))
                if isinstance(metrics, dict) and metrics.get("total_return") is not None
                else "-"
            )
            latest_backtest_label = "-"
            if latest_backtest:
                latest_backtest_label = f"{latest_backtest.get('task_id')} / {latest_backtest.get('status', '-')}"
            stage = self._strategy_lifecycle_stage(
                str(strategy.get("status") or ""),
                finished_backtests,
                paper_count,
                live_count,
            )
            updated_candidates = [
                strategy.get("updated_at"),
                latest_backtest.get("finished_at") if latest_backtest else None,
                latest_backtest.get("created_at") if latest_backtest else None,
                latest_paper.get("updated_at") if latest_paper else None,
                latest_live.get("updated_at") if latest_live else None,
            ]
            updated_at = max(str(item) for item in updated_candidates if item) if any(updated_candidates) else "-"
            rows.append(
                {
                    "strategy_id": strategy_id,
                    "name": strategy.get("name") or "-",
                    "version": strategy.get("version") or "-",
                    "stage": stage,
                    "status": strategy.get("status") or "-",
                    "backtests": f"{finished_backtests}/{backtest_count}",
                    "latest_backtest": latest_backtest_label,
                    "latest_return": latest_return,
                    "paper_accounts": paper_count,
                    "live_configs": live_count,
                    "next_step": self._strategy_lifecycle_next_step(stage),
                    "updated_at": _format_display_time(updated_at),
                }
            )
        stage_order = ["草稿", "已验证", "已回测", "模拟盘", "实盘候选", "停用"]
        counts = {stage: sum(1 for row in rows if row["stage"] == stage) for stage in stage_order}
        summary = (
            "### 策略生命周期\n\n"
            f"共 `{len(rows)}` 个策略 · 实盘候选 `{counts['实盘候选']}` · "
            f"模拟盘 `{counts['模拟盘']}` · 待回测 `{counts['已验证']}` · 草稿 `{counts['草稿']}`\n\n"
            "> 阶段依据来自策略状态、最新回测、模拟账户和实盘配置；进入本页签或点击刷新时才读取。"
        )
        return summary, self._strategy_lifecycle_board(rows, counts), to_frame(rows, STRATEGY_LIFECYCLE_COLUMNS)

    @staticmethod
    def _strategy_lifecycle_stage(
        strategy_status: str,
        finished_backtests: int,
        paper_count: int,
        live_count: int,
    ) -> str:
        if strategy_status == "停用":
            return "停用"
        if live_count > 0:
            return "实盘候选"
        if paper_count > 0:
            return "模拟盘"
        if finished_backtests > 0:
            return "已回测"
        if strategy_status == "可用":
            return "已验证"
        return "草稿"

    @staticmethod
    def _strategy_lifecycle_next_step(stage: str) -> str:
        return {
            "草稿": "补齐策略接口并启用",
            "已验证": "启动离线回测并留存绩效",
            "已回测": "创建模拟账户进行在线仿真",
            "模拟盘": "观察成交、滑点和风控表现",
            "实盘候选": "发布前复核风控和资金上限",
            "停用": "确认停用原因并归档证据",
        }.get(stage, "补齐生命周期证据")

    @staticmethod
    def _strategy_lifecycle_board(rows: list[dict[str, Any]], counts: dict[str, int]) -> str:
        stage_specs = [
            ("草稿", "draft", "需求、代码或接口仍在准备中"),
            ("已验证", "verified", "策略已启用，等待离线回测"),
            ("已回测", "tested", "已有绩效证据，可进入模拟盘"),
            ("模拟盘", "paper", "在线仿真观察成交与风险"),
            ("实盘候选", "live", "具备发布配置，需要最后复核"),
            ("停用", "disabled", "已暂停，保留审计与复盘线索"),
        ]
        total = max(len(rows), 1)
        cards = []
        for stage, tone, description in stage_specs:
            names = [str(row["name"]) for row in rows if row["stage"] == stage][:2]
            examples = " / ".join(names) if names else "暂无策略"
            percent = int(counts.get(stage, 0) / total * 100)
            cards.append(
                "<article class='strategy-lifecycle-card stage-"
                + tone
                + "'><small>"
                + escape(stage)
                + "</small><strong>"
                + str(counts.get(stage, 0))
                + "</strong><p>"
                + escape(description)
                + "</p><div class='strategy-lifecycle-meter'><i style='width:"
                + str(percent)
                + "%'></i></div><span>"
                + escape(examples)
                + "</span></article>"
            )
        return (
            "<section class='ai-market-header'><span>Strategy Lifecycle</span>"
            "<strong>从策略构建到模拟盘、实盘候选的证据链</strong></section>"
            "<section class='strategy-lifecycle-board'>" + "".join(cards) + "</section>"
        )

    def strategy_detail(self, strategy_id: Any) -> tuple[str, str, str, str]:
        item = StrategyStore().get(require_id(strategy_id, "策略 ID"), include_code=True)
        meta = {key: value for key, value in item.items() if key not in {"code", "interface_report"}}
        return (
            item.get("code") or "",
            compact_json(meta),
            compact_json(item.get("default_params") or item.get("param_schema") or {}),
            compact_json(item.get("interface_report") or {}),
        )

    def strategy_version_compare(self, strategy_id: Any) -> tuple[str, pd.DataFrame]:
        value = require_id(strategy_id, "策略 ID")
        repo = Repository()
        selected = repo.get("strategies", value)
        rows = self._strategy_version_rows(repo, str(selected.get("name") or ""))
        if not rows:
            return "暂无可比较的同名策略版本", to_frame([], STRATEGY_VERSION_COMPARE_COLUMNS)
        return (
            f"策略版本对比已生成：`{selected.get('name')}` 共 {len(rows)} 个版本。",
            to_frame(rows, STRATEGY_VERSION_COMPARE_COLUMNS),
        )

    def strategy_quick_backtest(
        self,
        strategy_id: Any,
        symbols: str,
        start_date: str,
        end_date: str,
        capital: Any,
        params: str,
        engine: str = "auto",
        parameter_profile: str = "",
    ) -> tuple[str, int, pd.DataFrame, pd.DataFrame]:
        value = require_id(strategy_id, "策略 ID")
        strategy = StrategyStore().get(value, include_code=False)
        params_text = str(params or "").strip() or "{}"
        callbacks = cast(CrossDomainCallbacks, self)
        order_type = "open" if "模型策略" in (strategy.get("tags") or []) else "market"
        status, task_id, backtest_rows, _, _, _, _, _ = callbacks.create_backtest(
            value,
            symbols,
            start_date,
            end_date,
            capital,
            params_text,
            engine,
            order_type,
            "qfq",
            5,
            0.3,
            100,
            0.0,
            parameter_profile,
        )
        compare_rows = self._strategy_version_rows(Repository(), str(strategy.get("name") or ""))
        return (
            f"策略一键回测已完成。{status}",
            task_id,
            backtest_rows,
            to_frame(compare_rows, STRATEGY_VERSION_COMPARE_COLUMNS),
        )

    @staticmethod
    def _strategy_version_rows(repo: Repository, strategy_name: str) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        if not strategy_name:
            return rows
        strategies = repo.db.query(
            """SELECT *
               FROM strategies
               WHERE name = ?
               ORDER BY updated_at DESC, id DESC""",
            (strategy_name,),
        )
        for strategy in strategies:
            latest_backtest = repo.db.query_one(
                """SELECT t.id AS task_id, t.status, t.created_at, t.finished_at, r.metrics
                   FROM backtest_tasks t
                   LEFT JOIN backtest_results r ON r.task_id = t.id
                   WHERE t.strategy_id = ?
                   ORDER BY COALESCE(t.finished_at, t.created_at) DESC, t.id DESC
                   LIMIT 1""",
                (strategy["id"],),
            )
            metrics = json_loads(latest_backtest.get("metrics"), {}) if latest_backtest else {}
            params = json_loads(strategy.get("param_schema"), {})
            params_text = compact_json(params)
            if len(params_text) > 120:
                params_text = params_text[:117] + "..."
            rows.append(
                {
                    "策略ID": strategy["id"],
                    "版本": strategy.get("version") or "-",
                    "状态": strategy.get("status") or "-",
                    "接口类型": strategy.get("interface_type") or "-",
                    "来源": strategy.get("origin") or "-",
                    "最近回测": (
                        f"{latest_backtest.get('task_id')} / {latest_backtest.get('status')}"
                        if latest_backtest
                        else "-"
                    ),
                    "总收益": _percent(metrics.get("total_return")) if metrics else "-",
                    "最大回撤": _percent(metrics.get("max_drawdown")) if metrics else "-",
                    "夏普": round(_safe_float(metrics.get("sharpe")), 3) if metrics else "-",
                    "交易数": int(_safe_float(metrics.get("trade_count"))) if metrics else "-",
                    "默认参数": params_text,
                    "更新时间": _format_display_time(strategy.get("updated_at")),
                    "备注": "当前选中同名策略版本横向比较",
                }
            )
        return rows

    def strategy_example_detail(self, example_path: str) -> tuple[str, str]:
        detail = StrategyStore().example_detail(require_text(example_path, "示例策略"))
        meta = {key: value for key, value in detail.items() if key not in {"code", "intro"}}
        return detail.get("code") or "", compact_json(meta)

    def preset_strategy_detail(self, example_path: str) -> tuple[str, str, str, str]:
        detail = StrategyStore().example_detail(require_text(example_path, "预制策略"))
        intro = detail.get("intro") or {}
        intro_md = self._preset_intro_markdown(intro)
        params = intro.get("default_params")
        if not isinstance(params, dict) or not params:
            schema = (detail.get("validation") or {}).get("params_schema")
            params = _schema_defaults(schema)
        params_yaml = yaml.safe_dump(params or {}, allow_unicode=True, sort_keys=False)
        meta = {
            key: value
            for key, value in detail.items()
            if key not in {"code", "intro"} and not (key == "validation" and isinstance(value, dict))
        }
        meta["validation"] = {
            "valid": (detail.get("validation") or {}).get("valid"),
            "adapter_type": (detail.get("validation") or {}).get("adapter_type"),
            "entry_class": (detail.get("validation") or {}).get("entry_class"),
            "entry_func": (detail.get("validation") or {}).get("entry_func"),
        }
        return intro_md, detail.get("code") or "", params_yaml, compact_json(meta)

    @staticmethod
    def _preset_intro_markdown(intro: dict[str, Any]) -> str:
        if not intro:
            return "### 暂无介绍\n\n该预制策略尚未在 `egs/examples/strategy_examples/strategy_intros.yaml` 配置介绍。"
        parts = [f"### {intro.get('title', '预制策略')}"]
        tags = intro.get("tags") or []
        if isinstance(tags, list) and tags:
            parts.append("**标签：** " + " / ".join(str(tag) for tag in tags))
        if intro.get("intro"):
            parts.append(str(intro["intro"]).strip())
        if intro.get("suitable"):
            parts.append(f"**适用场景：** {intro['suitable']}")
        if intro.get("risk"):
            parts.append(f"**风险提示：** {intro['risk']}")
        return "\n\n".join(parts)

    def import_strategy_example(
        self, example_path: str, name: str, description: str, params_yaml: str = ""
    ) -> tuple[str, pd.DataFrame]:
        payload: dict[str, Any] = {
            "name": str(name or "").strip() or None,
            "description": str(description or "").strip(),
        }
        params_text = str(params_yaml or "").strip()
        if params_text:
            try:
                parsed = yaml.safe_load(params_text)
            except yaml.YAMLError as exc:
                raise ValueError(f"超参 YAML 格式有误：{exc}") from exc
            if not isinstance(parsed, dict):
                raise ValueError("超参 YAML 必须是键值对映射，例如 fast_window: 5")
            payload["default_params"] = parsed
        item = StrategyStore().import_example(require_text(example_path, "示例策略"), payload)
        return f"示例策略已导入，策略 ID={item['strategy_id']}", self.strategies()

    def strategy_param_schema_preview(self, params: str) -> tuple[str, str, pd.DataFrame]:
        parsed = parse_json(params, "默认参数")
        if not isinstance(parsed, dict):
            raise ValueError('默认参数必须是 JSON 对象，例如 {"fast_window": 5}')
        return (
            f"参数预览已生成，共 {len(parsed)} 个参数。",
            compact_json(parsed),
            to_frame(_strategy_param_rows(parsed), STRATEGY_PARAM_SCHEMA_COLUMNS),
        )

    def strategy_param_schema_add(
        self,
        params: str,
        name: str,
        param_type: str,
        default_value: str,
        description: str,
    ) -> tuple[str, str, pd.DataFrame]:
        parsed = parse_json(params, "默认参数")
        if not isinstance(parsed, dict):
            raise ValueError('默认参数必须是 JSON 对象，例如 {"fast_window": 5}')
        param_name = require_text(name, "参数名")
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", param_name):
            raise ValueError("参数名需使用字母、数字和下划线，并以字母或下划线开头")
        parsed[param_name] = _strategy_param_value(default_value, param_type)
        rows = _strategy_param_rows(parsed, {param_name: str(description or "").strip()})
        return (
            f"参数 `{param_name}` 已追加或更新。",
            compact_json(parsed),
            to_frame(rows, STRATEGY_PARAM_SCHEMA_COLUMNS),
        )

    def strategy_param_schema_extract(self, source: str, file_path: str | None) -> tuple[str, str, pd.DataFrame]:
        source_text = str(source or "")
        if file_path:
            source_text = Path(file_path).read_text(encoding="utf-8")
        validation = StrategyValidator().validate_source(require_text(source_text, "策略代码"))
        defaults = _schema_defaults(validation.get("params_schema"))
        if not defaults:
            return (
                "源码未声明 `params_schema` 或 `PARAMS_SCHEMA`，已生成空默认参数。",
                "{}",
                to_frame([], STRATEGY_PARAM_SCHEMA_COLUMNS),
            )
        return (
            f"已从源码提取 {len(defaults)} 个默认参数。",
            compact_json(defaults),
            to_frame(_strategy_param_rows(defaults), STRATEGY_PARAM_SCHEMA_COLUMNS),
        )

    def create_strategy(
        self,
        name: str,
        version: str,
        description: str,
        tags: str,
        params: str,
        code: str,
        file_path: str | None,
    ) -> tuple[str, pd.DataFrame]:
        source = str(code or "")
        if file_path:
            source = Path(file_path).read_text(encoding="utf-8")
        payload = {
            "name": require_text(name, "策略名称"),
            "version": str(version or "v1").strip() or "v1",
            "description": description or "",
            "tags": parse_csv(tags),
            "default_params": parse_json(params, "默认参数"),
            "code": require_text(source, "策略代码"),
        }
        item = StrategyStore().create(payload)
        return f"策略 {item['name']} {item['version']} 已入库，ID={item['strategy_id']}", self.strategies()

    def set_strategy_status(self, strategy_id: Any, enabled: bool) -> tuple[str, pd.DataFrame]:
        value = require_id(strategy_id, "策略 ID")
        item = StrategyStore().set_status(value, "可用" if enabled else "停用")
        return f"策略 {value} 状态已更新为 {item['status']}", self.strategies()

    def delete_strategy(self, strategy_id: Any) -> tuple[str, pd.DataFrame]:
        value = require_id(strategy_id, "策略 ID")
        StrategyStore().delete(value)
        return f"策略 {value} 已删除", self.strategies()

    def cli_build(self, cli_type: str, requirement: str) -> tuple[str, str, pd.DataFrame]:
        builder = CliBuilder()
        session = builder.create_session(
            {"cli_type": cli_type or "trae", "requirement": require_text(requirement, "策略需求")}
        )
        session_id = int(session["session_id"])
        log_data = builder.logs(session_id, 0, 500)
        log_text = format_cli_logs(log_data)
        return compact_json(session), log_text, to_frame([{"file": item} for item in session.get("artifacts") or []])

    def cli_build_with_sessions(self, cli_type: str, requirement: str) -> tuple[str, str, pd.DataFrame, pd.DataFrame]:
        session, logs, artifacts = self.cli_build(cli_type, requirement)
        return session, logs, artifacts, self.cli_sessions()

    def cli_sessions(self) -> pd.DataFrame:
        try:
            return to_frame(CliBuilder().list_sessions(page=1, page_size=50), CLI_SESSION_COLUMNS)
        except Exception as exc:
            return to_frame([{"status": f"CLI 会话读取失败：{ui_error_message(exc)}"}], CLI_SESSION_COLUMNS)

    def cli_retry(self, session_id: Any) -> tuple[str, str, pd.DataFrame, pd.DataFrame]:
        builder = CliBuilder()
        session = builder.retry_session(require_id(session_id, "CLI 会话 ID"))
        value = int(session["session_id"])
        log_text = format_cli_logs(builder.logs(value, 0, 500))
        return (
            compact_json(session),
            log_text,
            to_frame([{"file": item} for item in session.get("artifacts") or []]),
            self.cli_sessions(),
        )

    def import_cli_artifact(
        self, session_id: Any, artifact: str, name: str, description: str
    ) -> tuple[str, pd.DataFrame]:
        value = require_id(session_id, "会话 ID")
        result = CliBuilder().import_artifact(
            value,
            require_text(artifact, "产物路径"),
            require_text(name, "策略名称"),
            description or "",
            StrategyStore(),
        )
        return f"CLI 产物已导入，策略 ID={result.get('strategy_id', result.get('id'))}", self.strategies()
