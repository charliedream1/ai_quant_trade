"""AI workbench callback boundary."""

from .base import DomainHandler


class AIHandler(DomainHandler):
    domain = "ai"
    allowed_methods = frozenset(
        {
            "ai_capability_catalog",
            "ai_console_file_preview",
            "ai_console_load_session",
            "ai_console_model_choices",
            "ai_console_new_session",
            "ai_console_project_tree",
            "ai_console_send_stream",
            "ai_console_sessions",
            "ai_expert_catalog",
            "ai_expert_detail",
            "ai_expert_to_task_state",
            "ai_job_catalog",
            "ai_job_template_cards",
            "ai_job_template_form",
            "ai_team_cards",
            "ai_team_catalog",
            "ai_team_detail",
            "ai_team_to_task_state",
            "ai_workbench_brief",
            "ai_workbench_chat",
            "ai_workbench_context",
            "ai_workbench_header",
            "ai_workbench_nav",
            "ai_workbench_overview",
            "ai_workbench_state",
            "create_job",
            "dashboard_market",
            "dashboard_market_brief",
            "insight_history",
            "insight_open",
            "insight_run",
            "job_action",
            "job_histories",
            "jobs",
            "kb_categories",
            "kb_qa",
            "kb_search",
            "mcp_action",
            "mcp_call",
            "mcp_servers",
            "research_team_model_choices",
            "research_team_review",
            "skill_action",
            "skills",
        }
    )
