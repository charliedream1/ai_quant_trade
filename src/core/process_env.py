"""Child processes inherit an explicit environment, rather than all platform keys."""

import os

from src.core.security_config import security_config


def process_environment(provider: str = "", supplied: dict | None = None) -> dict[str, str]:
    policy = security_config()["process"]
    names = set(policy["inherited_names"]) | set(policy["provider_names"].get(provider, []))
    if provider == "model":
        names.update(policy["model_names"])
    environment = {
        key: value
        for key, value in os.environ.items()
        if key.upper() in {name.upper() for name in names}
        or any(key.startswith(prefix) for prefix in policy["inherited_prefixes"])
    }
    environment.update(PYTHONUTF8="1", PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1")
    if provider in {"strategy", "document", "image"}:
        environment = {key: value for key, value in environment.items() if not key.upper().endswith("PROXY")}
    environment.update({str(key): str(value) for key, value in (supplied or {}).items()})
    return environment
