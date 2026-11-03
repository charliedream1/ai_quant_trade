"""Capabilities describe installation, authentication and research eligibility separately."""

import hashlib
import json
import subprocess
from functools import lru_cache
from pathlib import Path

from src.agent.llm_client import LLMClient
from src.agent.qoder_cli import QoderCliRunner, authentication_status
from src.core.exceptions import BusinessError
from src.core.llm_config import llm_config

from .config import provider_config
from .native import executable, version


@lru_cache(maxsize=16)
def _protocol_probe(backend: str, path: str, size: int, modified: int, digest: str) -> dict:
    cfg = provider_config()
    profile = cfg["providers"][backend]
    details = {"version": version(backend), "strict_supported": profile["strict"]}
    if profile["strict"]:
        checked = subprocess.run(
            [path, "--help"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=cfg["defaults"]["probe_timeout_seconds"],
            check=False,
        )
        details["strict_supported"] = (
            checked.returncode == 0
            and any(value in details["version"] for value in profile.get("verified_versions", []))
            and all(flag in checked.stdout for flag in profile.get("required_flags", []))
        )
    return details


def provider_snapshot(selection: dict, *, client=None, probe: bool = False) -> dict:
    cfg = provider_config()
    backend = selection.get("backend") or cfg["defaults"]["backend"]
    if backend not in cfg["providers"]:
        raise ValueError(cfg["messages"]["unknown"] + ": " + str(backend))
    profile = cfg["providers"][backend]
    result = {
        "backend": backend,
        "protocol": profile["protocol"],
        "strict_supported": profile["strict"] if probe or backend == "api" else False,
        "strict_profile_implemented": profile["strict"],
        "model_name": selection.get("model_name") or "",
        "reasoning_effort": selection.get("reasoning_effort") or "",
        "authentication": "unknown",
        "model_available": "unknown",
        "installed": True,
        "research_mode": "strict",
        "enable_thinking": selection.get("enable_thinking"),
        "config_digest": hashlib.sha256(
            json.dumps(cfg, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest(),
    }
    if backend == "api":
        owned = client is None
        llm = client or LLMClient()
        try:
            if hasattr(llm, "_select_config"):
                model = llm._select_config(selection.get("model_id"))
                result.update({key: model.get(key) for key in ("id", "model_name", "base_url", "api_key_env")})
                result["model_id"] = model["id"]
                result["generation_settings"] = {
                    "temperature": model.get("temperature"),
                    "max_tokens": model.get("max_tokens"),
                    "timeout_seconds": model.get("timeout_seconds"),
                    "system_prompt_sha256": hashlib.sha256(
                        str(model.get("system_prompt") or llm_config()["system_prompt"]).encode()
                    ).hexdigest(),
                }
            else:
                result["injected_client"] = True
        except BusinessError as exc:
            result.update(
                model_id=selection.get("model_id"), configuration_available=False, configuration_error=str(exc)
            )
        finally:
            if owned:
                llm.session.close()
        return result
    path = executable(backend)
    result.update(executable=path, installed=bool(path), strict_reason=profile.get("strict_reason", ""), version="")
    if probe and path:
        try:
            info = Path(path).stat()
            result.update(_protocol_probe(backend, path, info.st_size, info.st_mtime_ns, result["config_digest"]))
            if backend == "qoder":
                state = authentication_status(QoderCliRunner())
                result["authentication"] = (
                    "authenticated"
                    if state.get("logged_in") is True
                    else "not_authenticated"
                    if state.get("logged_in") is False
                    else "unknown"
                )
        except (OSError, subprocess.SubprocessError, ValueError) as exc:
            result["probe_error"] = str(exc)
            result["strict_supported"] = False
    if path:
        info = Path(path).stat()
        result["executable_identity"] = {"path": path, "size": info.st_size, "mtime_ns": info.st_mtime_ns}
    return result


def provider_catalog(*, probe: bool = False) -> list[dict]:
    rows = []
    for backend, profile in provider_config()["providers"].items():
        try:
            row = provider_snapshot({"backend": backend}, probe=probe)
        except Exception as exc:
            row = {"backend": backend, "installed": backend == "api", "error": str(exc)}
        rows.append({"label": profile["label"], **row})
    return rows


def require_native(selection: dict, *, strict: bool = True) -> dict:
    state = provider_snapshot(selection, probe=True)
    messages = provider_config()["messages"]
    if not state["installed"]:
        raise ValueError(messages["missing"] + ": " + state["backend"])
    if strict and not state["strict_supported"]:
        raise ValueError(messages["strict"] + "；" + state["strict_reason"])
    if state.get("authentication") == "not_authenticated":
        raise ValueError(state["backend"] + "尚未登录；没有启动模型生成")
    return state


def check_identity(expected: dict | None, current: dict) -> None:
    if not expected or expected.get("configuration_available") is False or current.get("injected_client"):
        return
    for key in (
        "backend",
        "model_id",
        "generation_settings",
        "protocol",
        "model_name",
        "base_url",
        "api_key_env",
        "reasoning_effort",
        "enable_thinking",
        "config_digest",
        "executable_identity",
        "version",
    ):
        if key in expected and expected.get(key) != current.get(key):
            raise ValueError("生成后端与冻结身份不一致，请创建新研究：" + key)
