"""Read-only verification of interpreter isolation, package origins and declared versions."""

import os
import sys
import tomllib
from importlib import metadata
from pathlib import Path
from time import perf_counter
from typing import Any

import yaml
from dotenv import dotenv_values
from loguru import logger
from packaging.requirements import Requirement

from .config import PROJECT_ROOT


def _requirements(cfg: dict[str, Any]) -> list[str]:
    lines = []
    if cfg["project_dependencies"]:
        lines.extend(
            tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["dependencies"]
        )
    for name in cfg["requirements"]:
        lines.extend((PROJECT_ROOT / name).read_text(encoding="utf-8").splitlines())
    return [line for line in lines if line.strip() and not line.lstrip().startswith("#")]


def _environment_errors(prefix: Path, cfg: dict[str, Any], minimum: list[int]) -> tuple[list[str], bool]:
    errors = []
    if sys.version_info[:2] < tuple(minimum):
        errors.append("Python版本低于支持基线")
    expected = Path(cfg["directory"])
    if not expected.is_absolute():
        expected = PROJECT_ROOT / expected
    if prefix != expected.resolve():
        errors.append("当前解释器不是此角色配置的项目环境")
    file = prefix / "pyvenv.cfg"
    inherited = not file.is_file() or "include-system-site-packages = true" in file.read_text(encoding="utf-8").lower()
    if inherited:
        errors.append("环境继承了基础包或不是独立虚拟环境")
    return errors, inherited


def _installed_requirement(line: str, prefix: Path) -> tuple[dict[str, Any] | None, str]:
    req = Requirement(line)
    if req.marker and not req.marker.evaluate():
        return None, ""
    try:
        dist = metadata.distribution(req.name)
    except metadata.PackageNotFoundError:
        return None, f"{req.name}未安装"
    satisfied = req.specifier.contains(dist.version)
    origin = Path(str(dist.locate_file(""))).resolve()
    result = {
        "name": req.name,
        "version": dist.version,
        "declared": str(req.specifier),
        "origin": str(origin),
        "satisfied": satisfied,
    }
    error = "" if satisfied and origin.is_relative_to(prefix) else f"{req.name}版本或安装来源不符合声明"
    return result, error


def inspect_runtime(role: str = "web") -> dict[str, Any]:
    config = yaml.safe_load((PROJECT_ROOT / "egs/config/operations/runtime_environments.yaml").read_text(encoding="utf-8"))
    if role not in config["environments"]:
        raise ValueError("未知运行环境")
    cfg = config["environments"][role]
    if cfg.get("directory_env"):
        local_env = dotenv_values(PROJECT_ROOT / ".env")
        selected = os.environ.get(cfg["directory_env"]) or local_env.get(cfg["directory_env"])
        if selected:
            cfg = {**cfg, "directory": selected}
    prefix = Path(sys.prefix).resolve()
    errors, inherited = _environment_errors(prefix, cfg, config["minimum_python"])
    declared = []
    for line in _requirements(cfg):
        row, error = _installed_requirement(line, prefix)
        if row:
            declared.append(row)
        if error:
            errors.append(error)
    outside = [
        dist.metadata["Name"]
        for dist in metadata.distributions()
        if not Path(str(dist.locate_file(""))).resolve().is_relative_to(prefix)
    ]
    if outside:
        errors.append("存在项目环境之外的可见分发包")
    return {
        "role": role,
        "executable": sys.executable,
        "prefix": str(prefix),
        "python": sys.version.split()[0],
        "include_system_site_packages": inherited,
        "declared": declared,
        "external_distributions": sorted(set(outside)),
        "errors": errors,
        "passed": not errors,
    }


def enforce_startup_runtime() -> dict[str, Any]:
    """Check once per launcher invocation, before announcing a usable service."""
    started = perf_counter()
    config = yaml.safe_load((PROJECT_ROOT / "egs/config/operations/runtime_environments.yaml").read_text(encoding="utf-8"))["startup"]
    env = dotenv_values(PROJECT_ROOT / ".env")
    mode = os.environ.get("ALL_IN_ONE_RUNTIME_MODE", env.get("ALL_IN_ONE_RUNTIME_MODE") or config["mode"])
    role = os.environ.get("ALL_IN_ONE_RUNTIME_ROLE", env.get("ALL_IN_ONE_RUNTIME_ROLE") or config["role"])
    if mode not in {"strict", "warn"}:
        raise SystemExit("ALL_IN_ONE_RUNTIME_MODE 只支持 strict / warn")
    report = inspect_runtime(str(role))
    elapsed = (perf_counter() - started) * 1000
    if report["passed"]:
        logger.info("启动环境预检通过 | role={} executable={} elapsed_ms={:.1f}", role, sys.executable, elapsed)
    else:
        logger.warning(
            "启动环境预检失败 | mode={} role={} executable={} errors={}", mode, role, sys.executable, report["errors"]
        )
        if mode == "strict":
            raise SystemExit("环境不符合声明，已停止启动；请使用项目配置的独立环境，详情运行 egs/entrypoints/check_runtime.py")
        logger.warning("显式兼容调试模式：带上述环境偏差继续启动，不表示依赖安全或兼容验证通过")
    return {**report, "mode": mode, "elapsed_ms": elapsed}
