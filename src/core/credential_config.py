"""External connection credentials live as environment references, never public JSON."""

import hashlib

from src.core.env_file import resolve_env_value, save_env_value
from src.core.redaction import MASK, SENSITIVE


def preserve_configuration(incoming, existing):
    if incoming == MASK or isinstance(incoming, str) and incoming.startswith("****"):
        return existing
    if isinstance(incoming, dict):
        prior = existing if isinstance(existing, dict) else {}
        return {**prior, **{key: preserve_configuration(value, prior.get(key)) for key, value in incoming.items()}}
    return incoming


def protect_configuration(value, namespace: str, path: str = ""):
    if isinstance(value, dict):
        if set(value) == {"$credential"}:
            return value
        result = {}
        for key, item in value.items():
            field = path + "/" + key
            if SENSITIVE.search(key) and isinstance(item, str) and item and not key.lower().endswith("_env"):
                digest = hashlib.sha256(field.encode()).hexdigest()[:16].upper()
                name = "MCP_" + namespace.upper() + "_" + digest + "_TOKEN"
                save_env_value(name, item)
                result[key] = {"$credential": name}
            else:
                result[key] = protect_configuration(item, namespace, field)
        return result
    if isinstance(value, list):
        return [protect_configuration(item, namespace, path + "/" + str(index)) for index, item in enumerate(value)]
    return value


def resolve_configuration(value):
    if isinstance(value, dict):
        if set(value) == {"$credential"}:
            name = str(value["$credential"])
            if not name.startswith("MCP_"):
                raise ValueError("非法连接凭据引用")
            return resolve_env_value(name)
        return {key: resolve_configuration(item) for key, item in value.items()}
    if isinstance(value, list):
        return [resolve_configuration(item) for item in value]
    return value
