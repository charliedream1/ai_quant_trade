"""Every new-session entry uses YAML while existing explicit project labels survive."""

from src.agent.workspace import AIWorkspaceService, workspace_config
from src.frontend.features.ai_console_actions import ConsoleActions
from src.frontend.services import FrontendService


def test_sidebar_and_automatic_chat_share_configured_project(client, monkeypatch):
    policy = {**workspace_config(), "default_project": "configured-project"}
    monkeypatch.setattr("src.agent.workspace.workspace_config", lambda: policy)
    service = FrontendService()
    sidebar = ConsoleActions(service)._ai_console_new_from_sidebar()
    assert AIWorkspaceService().detail(sidebar[6])["project_name"] == "configured-project"

    messages = list(service.ai_console_send_stream(0, "检查当前项目", [], "generic_agent"))
    assert AIWorkspaceService().detail(messages[-1][0])["project_name"] == "configured-project"


def test_explicit_project_is_preserved(client):
    service = FrontendService()
    _, identifier, _, _ = service.ai_console_new_session("保留用户命名", "user-project")
    assert AIWorkspaceService().detail(identifier)["project_name"] == "user-project"
