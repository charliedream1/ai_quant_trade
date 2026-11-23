"""Human-readable labels for bounded workspace events."""

from .workspace_config import workspace_config


def action_label(method: str) -> str:
    policy = workspace_config()["logging"]
    return policy["actions"].get(method.rsplit(".", 1)[-1], policy["console"]["generic_action"])


def stage_label(stage: str) -> str:
    policy = workspace_config()["logging"]
    return policy["stages"].get(stage, policy["console"]["generic_stage"])


def event_label(event: str) -> str:
    return workspace_config()["logging"]["console"][event]
