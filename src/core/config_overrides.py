"""Apply declared dotted-key overrides without mutating the caller's configuration."""

from copy import deepcopy

from loguru import logger


def override_config(configs, override_list):
    result = deepcopy(configs)
    for override in override_list:
        parts = override.split()
        if len(parts) != 2:
            logger.warning("Skipping malformed configuration override")
            continue
        keys, value = parts[0].split("."), parts[1]
        node = result
        try:
            for key in keys[:-1]:
                node = node[key]
            previous = node[keys[-1]]
            if isinstance(previous, bool):
                if value.lower() not in {"true", "false", "1", "0"}:
                    raise ValueError("Invalid boolean override")
                converted = value.lower() in {"true", "1"}
            else:
                converted = type(previous)(value)
            node[keys[-1]] = converted
        except (KeyError, TypeError, ValueError) as exc:
            logger.warning("Skipping invalid configuration override | error_type={}", type(exc).__name__)
    return result
