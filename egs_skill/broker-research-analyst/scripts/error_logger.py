"""错误日志记录器

记录报告生成全流程中的错误、警告、降级事件，写入日志文件，便于追溯。
所有日志同时输出到控制台（LOGGER）和文件（error.log）。
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

LOGGER = logging.getLogger(__name__)


@dataclass
class ErrorEntry:
    """单条错误/警告记录"""
    timestamp: str
    stage: str          # 发生阶段：fetch/quality_gate/download/parse/image/generate/validate/hallucination
    level: str          # ERROR / WARNING / INFO
    message: str
    context: dict = field(default_factory=dict)  # 附加上下文（如 info_code、pdf_path 等）

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ErrorLog:
    """错误日志集合"""
    entries: list[ErrorEntry] = field(default_factory=list)
    log_file_path: str = ""

    def add(self, stage: str, level: str, message: str, **context):
        """添加一条记录"""
        entry = ErrorEntry(
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            stage=stage,
            level=level,
            message=message,
            context=context,
        )
        self.entries.append(entry)
        # 同时输出到 logger
        if level == "ERROR":
            LOGGER.error("[%s] %s | %s", stage, message, context)
        elif level == "WARNING":
            LOGGER.warning("[%s] %s | %s", stage, message, context)
        else:
            LOGGER.info("[%s] %s | %s", stage, message, context)

    def add_error(self, stage: str, message: str, **context):
        self.add(stage, "ERROR", message, **context)

    def add_warning(self, stage: str, message: str, **context):
        self.add(stage, "WARNING", message, **context)

    def add_info(self, stage: str, message: str, **context):
        self.add(stage, "INFO", message, **context)

    @property
    def error_count(self) -> int:
        return sum(1 for e in self.entries if e.level == "ERROR")

    @property
    def warning_count(self) -> int:
        return sum(1 for e in self.entries if e.level == "WARNING")

    def save(self, log_dir: str = "./cache/logs", filename: str = "") -> str:
        """保存日志到文件

        :param log_dir: 日志目录
        :param filename: 文件名（空则按时间自动生成）
        :return: 日志文件路径
        """
        log_dir = Path(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        if not filename:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"error_{ts}.log"
        path = log_dir / filename
        self.log_file_path = str(path)

        # 写入文本日志（人类可读）
        lines = [
            f"# 错误日志 - 生成于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"# 总记录数: {len(self.entries)}（错误 {self.error_count}，警告 {self.warning_count}）",
            "=" * 70,
            "",
        ]
        for e in self.entries:
            ctx_str = " ".join(f"{k}={v}" for k, v in e.context.items()) if e.context else ""
            lines.append(f"[{e.timestamp}] [{e.level}] [{e.stage}] {e.message}")
            if ctx_str:
                lines.append(f"  上下文: {ctx_str}")
        path.write_text("\n".join(lines), encoding="utf-8")

        # 同时写 JSON 版本（机器可读，便于后续分析）
        json_path = path.with_suffix(".json")
        # 转换非 JSON 可序列化对象（如 PosixPath）
        def _safe_json(obj):
            if isinstance(obj, dict):
                return {k: _safe_json(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [_safe_json(v) for v in obj]
            if isinstance(obj, Path):
                return str(obj)
            return obj
        json_path.write_text(
            json.dumps([_safe_json(e.to_dict()) for e in self.entries],
                       ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        LOGGER.info("错误日志已保存: %s（错误 %d，警告 %d）",
                    path, self.error_count, self.warning_count)
        return str(path)

    def summary(self) -> dict:
        """返回日志摘要"""
        from collections import Counter
        stage_counts = Counter(e.stage for e in self.entries)
        level_counts = Counter(e.level for e in self.entries)
        return {
            "total": len(self.entries),
            "errors": self.error_count,
            "warnings": self.warning_count,
            "by_stage": dict(stage_counts),
            "by_level": dict(level_counts),
            "log_file": self.log_file_path,
        }
