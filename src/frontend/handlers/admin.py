"""Administration callback boundary."""

from .base import DomainHandler


class AdminHandler(DomainHandler):
    domain = "admin"
    allowed_methods = frozenset(
        {
            "check_environment_variable",
            "create_job",
            "create_mcp",
            "create_model",
            "create_skill",
            "delete_environment_variable",
            "environment_variables",
            "import_environment",
            "job_action",
            "job_histories",
            "jobs",
            "mcp_action",
            "mcp_call",
            "mcp_servers",
            "model_action",
            "model_form",
            "models_with_stats",
            "save_settings_form",
            "settings",
            "skill_action",
            "skills",
            "system_runtime_status",
            "update_model",
        }
    )
