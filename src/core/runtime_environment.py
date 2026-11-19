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

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

from .config import PROJECT_ROOT
from .paths import INSTALLED, RESOURCE_ROOT


def _requirements(cfg: dict[str, Any]) -> list[str]:
    lines = []
    if cfg["project_dependencies"]:
        if INSTALLED:
            lines.extend(metadata.requires("b001-all-in-one") or [])
        else:
            lines.extend(
                tomllib.loads((RESOURCE_ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["dependencies"]
            )
    for name in cfg["requirements"]:
        lines.extend((RESOURCE_ROOT / name).read_text(encoding="utf-8").splitlines())
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
        errors.append("Python is below the supported baseline")
    expected = Path(cfg["directory"])
    if not expected.is_absolute():
        expected = PROJECT_ROOT / expected
    if INSTALLED and cfg.get("project_dependencies") and not cfg.get("explicit_directory"):
        expected = prefix
    conda = _is_conda_environment(prefix, cfg)
    conda_base = conda and (
        prefix.name.lower() in cfg["conda_base_names"]
        or any((prefix / marker).exists() for marker in cfg["conda_base_markers"])
    )
    if prefix != expected.resolve() and (not conda or cfg.get("explicit_directory")):
        errors.append("Interpreter does not match the configured role environment")
    if conda_base:
        errors.append("Conda base/root is not supported; select a dedicated project environment in PyCharm")
    file = prefix / "pyvenv.cfg"
    inherited = (
        "include-system-site-packages = true" in file.read_text(encoding="utf-8").lower() if file.is_file() else False
    )
    if not conda and not file.is_file():
        errors.append("Environment lacks isolated interpreter metadata (pyvenv.cfg)")
    if inherited:
        errors.append("Environment inherits system packages")
    return errors, inherited


def _installed_requirement(line: str, prefix: Path) -> tuple[dict[str, Any] | None, str]:
    req = Requirement(line)
    if req.marker and not req.marker.evaluate():
        return None, ""
    try:
        dist = metadata.distribution(req.name)
    except metadata.PackageNotFoundError:
        return None, f"{req.name} is not installed"
    satisfied = req.specifier.contains(dist.version)
    origin = Path(str(dist.locate_file(""))).resolve()
    result = {
        "name": req.name,
        "version": dist.version,
        "declared": str(req.specifier),
        "origin": str(origin),
        "satisfied": satisfied,
    }
    error = (
        ""
        if satisfied and origin.is_relative_to(prefix)
        else f"{req.name} differs from the tested version or package origin"
    )
    return result, error


def _runtime_mode(config: dict[str, Any], mode: str | None = None) -> str:
    """Resolve explicit, process, local dotenv, then YAML mode selection."""
    local_env = dotenv_values(PROJECT_ROOT / ".env")
    selected = mode or os.environ.get("ALL_IN_ONE_RUNTIME_MODE") or local_env.get("ALL_IN_ONE_RUNTIME_MODE")
    selected = selected or config["startup"]["mode"]
    if selected == "warn":
        selected = "non-strict"
    if selected not in {"strict", "non-strict"}:
        raise ValueError("ALL_IN_ONE_RUNTIME_MODE must be strict / non-strict (warn is a legacy alias)")
    return str(selected)


def inspect_runtime(role: str = "web", mode: str | None = None) -> dict[str, Any]:
    config = yaml.safe_load(
        (PROJECT_ROOT / "egs/config/operations/runtime_environments.yaml").read_text(encoding="utf-8")
    )
    mode = _runtime_mode(config, mode)
    if role not in config["environments"]:
        raise ValueError("Unknown runtime role")
    cfg = {**config.get("isolation", {}), **config["environments"][role]}
    if cfg.get("directory_env"):
        local_env = dotenv_values(PROJECT_ROOT / ".env")
        selected = os.environ.get(cfg["directory_env"]) or local_env.get(cfg["directory_env"])
        if selected:
            cfg = {**cfg, "directory": selected, "explicit_directory": True}
    prefix = Path(sys.prefix).resolve()
    errors, inherited = _environment_errors(prefix, cfg, cfg.get("minimum_python", config["minimum_python"]))
    warnings: list[str] = []
    location_warning = "Interpreter does not match the configured role environment"
    if mode != "strict" and cfg.get("project_dependencies") and location_warning in errors:
        errors.remove(location_warning)
        warnings.append(location_warning)
    upper = config.get("maximum_python_exclusive")
    if upper and sys.version_info[: len(upper)] >= tuple(upper):
        errors.append("Python exceeds the verified support range")
    declared = []
    for line in _requirements(cfg):
        row, error = _installed_requirement(line, prefix)
        if row:
            declared.append(row)
        if error:
            if error.endswith(" is not installed"):
                errors.append(error)
            else:
                warnings.append(error)
    outside = [
        dist.metadata["Name"]
        for dist in metadata.distributions()
        if not Path(str(dist.locate_file(""))).resolve().is_relative_to(prefix)
        and not (
            not INSTALLED
            and dist.metadata["Name"].lower().replace("_", "-") == "b001-all-in-one"
            and Path(str(dist.locate_file(""))).resolve() == RESOURCE_ROOT.resolve()
        )
    ]
    if outside:
        warnings.append("External distributions are visible outside the selected environment")
    if mode == "strict":
        errors.extend(warnings)
        warnings = []
    return {
        "mode": mode,
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
    )
    env = dotenv_values(PROJECT_ROOT / ".env")
    role = os.environ.get("ALL_IN_ONE_RUNTIME_ROLE", env.get("ALL_IN_ONE_RUNTIME_ROLE") or config["startup"]["role"])
    try:
        mode = _runtime_mode(config)
        report = inspect_runtime(str(role))
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    mode = report.get("mode", mode)
    elapsed = (perf_counter() - started) * 1000
    if report.get("warnings"):
        logger.warning(
            "Runtime package differences | role={} count={} | Run check_runtime.py for details",
            role,
            len(report["warnings"]),
        )
        logger.debug("Runtime package differences | details={}", report["warnings"])
    if report["passed"]:
        logger.info("Runtime preflight passed | mode={} role={}", mode, role)
        logger.debug("Runtime interpreter | executable={} elapsed_ms={:.1f}", sys.executable, elapsed)
    else:
        logger.warning(
            "Runtime preflight failed | mode={} role={} executable={} errors={}",
            mode,
            role,
            sys.executable,
            report["errors"],
        )
        raise SystemExit(
            "Runtime requirements are incomplete; startup stopped. Inspect with egs/entrypoints/check_runtime.py --mode "
            + str(mode)
        )
    return {**report, "mode": mode, "elapsed_ms": elapsed}
