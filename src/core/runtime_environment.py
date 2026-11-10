"""Read-only verification of interpreter isolation, package origins and declared versions."""

import os
import sys
from importlib import metadata
from pathlib import Path
from time import perf_counter
from typing import Any

import yaml
from dotenv import dotenv_values
from loguru import logger
from packaging.requirements import Requirement
from packaging.version import InvalidVersion, Version

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

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


def _is_conda_environment(prefix: Path, cfg: dict[str, Any]) -> bool:
    """Return whether the prefix contains Conda metadata."""
    if not cfg.get("allow_conda"):
        return False
    metadata_path = Path(str(cfg.get("conda_metadata", "conda-meta/history")))
    return (prefix / metadata_path).is_file()


def _environment_errors(prefix: Path, cfg: dict[str, Any], minimum: list[int]) -> tuple[list[str], bool]:
    errors = []
    if sys.version_info[: len(minimum)] < tuple(minimum):
        errors.append("Python版本低于支持基线")
    expected = Path(cfg["directory"])
    if not expected.is_absolute():
        expected = PROJECT_ROOT / expected
    conda = _is_conda_environment(prefix, cfg)
    conda_base = conda and (
        prefix.name.lower() in cfg["conda_base_names"]
        or any((prefix / marker).exists() for marker in cfg["conda_base_markers"])
    )
    if prefix != expected.resolve() and (not conda or cfg.get("explicit_directory")):
        errors.append("当前解释器不是此角色配置的项目环境")
    if conda_base:
        errors.append("Conda base/root is not supported; select a dedicated project environment in PyCharm")
    file = prefix / "pyvenv.cfg"
    inherited = (
        "include-system-site-packages = true" in file.read_text(encoding="utf-8").lower()
        if file.is_file()
        else False
    )
    if not conda and not file.is_file():
        errors.append("环境缺少独立解释器配置（pyvenv.cfg）")
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
    compatible = True
    exact_versions = [item.version for item in req.specifier if item.operator == "=="]
    if exact_versions:
        try:
            compatible = Version(dist.version).major == Version(exact_versions[0]).major
        except InvalidVersion:
            compatible = True
    result = {
        "name": req.name,
        "version": dist.version,
        "declared": str(req.specifier),
        "origin": str(origin),
        "satisfied": satisfied,
        "compatible": compatible,
    }
    error = "" if satisfied and origin.is_relative_to(prefix) else f"{req.name}版本或安装来源不符合声明"
    return result, error


def inspect_runtime(role: str = "web") -> dict[str, Any]:
    config = yaml.safe_load(
        (PROJECT_ROOT / "egs/config/operations/runtime_environments.yaml").read_text(encoding="utf-8")
    )
    if role not in config["environments"]:
        raise ValueError("未知运行环境")
    cfg = {**config.get("isolation", {}), **config["environments"][role]}
    if cfg.get("directory_env"):
        local_env = dotenv_values(PROJECT_ROOT / ".env")
        selected = os.environ.get(cfg["directory_env"]) or local_env.get(cfg["directory_env"])
        if selected:
            cfg = {**cfg, "directory": selected, "explicit_directory": True}
    prefix = Path(sys.prefix).resolve()
    errors, inherited = _environment_errors(prefix, cfg, cfg.get("minimum_python", config["minimum_python"]))
    warnings: list[str] = []
    upper = config.get("maximum_python_exclusive")
    if upper and sys.version_info[: len(upper)] >= tuple(upper):
        errors.append("Python版本超出已验证支持范围")
    declared = []
    for line in _requirements(cfg):
        row, error = _installed_requirement(line, prefix)
        if row:
            declared.append(row)
        if error:
            if error.endswith("未安装"):
                errors.append(error)
            elif row and not row.get("compatible", True):
                errors.append(f"{row['name']}主版本与声明不兼容")
            else:
                warnings.append(error)
    outside = [
        dist.metadata["Name"]
        for dist in metadata.distributions()
        if not Path(str(dist.locate_file(""))).resolve().is_relative_to(prefix)
    ]
    if outside:
        warnings.append("存在项目环境之外的可见分发包（仅作提示，不阻断启动）")
    return {
        "role": role,
        "executable": sys.executable,
        "prefix": str(prefix),
        "python": sys.version.split()[0],
        "include_system_site_packages": inherited,
        "declared": declared,
        "external_distributions": sorted(set(outside)),
        "errors": errors,
        "warnings": warnings,
        "passed": not errors,
    }


def enforce_startup_runtime() -> dict[str, Any]:
    """Check once per launcher invocation, before announcing a usable service."""
    started = perf_counter()
    config = yaml.safe_load(
        (PROJECT_ROOT / "egs/config/operations/runtime_environments.yaml").read_text(encoding="utf-8")
    )["startup"]
    env = dotenv_values(PROJECT_ROOT / ".env")
    mode = os.environ.get("ALL_IN_ONE_RUNTIME_MODE", env.get("ALL_IN_ONE_RUNTIME_MODE") or config["mode"])
    role = os.environ.get("ALL_IN_ONE_RUNTIME_ROLE", env.get("ALL_IN_ONE_RUNTIME_ROLE") or config["role"])
    if mode not in {"strict", "warn"}:
        raise SystemExit("ALL_IN_ONE_RUNTIME_MODE 只支持 strict / warn")
    report = inspect_runtime(str(role))
    elapsed = (perf_counter() - started) * 1000
    if report.get("warnings"):
        logger.warning("启动环境预检提示 | role={} warnings={}", role, report["warnings"])
    if report["passed"]:
        logger.info("启动环境预检通过 | role={} executable={} elapsed_ms={:.1f}", role, sys.executable, elapsed)
    else:
        logger.warning(
            "启动环境预检失败 | mode={} role={} executable={} errors={}", mode, role, sys.executable, report["errors"]
        )
        if mode == "strict":
            raise SystemExit(
                "环境不符合声明，已停止启动；请使用项目配置的独立环境，详情运行 egs/entrypoints/check_runtime.py"
            )
        logger.warning("显式兼容调试模式：带上述环境偏差继续启动，不表示依赖安全或兼容验证通过")
    return {**report, "mode": mode, "elapsed_ms": elapsed}
