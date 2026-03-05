"""
Filmeto Agent Utilities Module

Contains utility functions used by FilmetoAgent for text extraction,
content processing, and helper operations.
"""
from typing import Optional, Any

from agent.chat.agent_chat_message import AgentMessage
from agent.chat.agent_chat_types import ContentType
from agent.chat.content import TextContent


def extract_text_content(message: AgentMessage) -> str:
    """Extract text content from a message's structured_content."""
    if not message.structured_content:
        return ""
    for sc in message.structured_content:
        if sc.content_type == ContentType.TEXT and isinstance(sc, TextContent):
            return sc.text
    return ""


def truncate_text(text: Optional[str], limit: int = 160) -> str:
    """Truncate text to specified limit with ellipsis."""
    if text is None:
        return ""
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def get_workspace_path_safe(workspace: Any) -> str:
    """Safely extract workspace path from workspace object."""
    if workspace is None:
        return "none"
    if hasattr(workspace, "workspace_path"):
        return workspace.workspace_path
    if hasattr(workspace, "path"):
        return str(workspace.path)
    return str(id(workspace))


def get_project_from_workspace(workspace: Any, project_name: str) -> Any:
    """Get project object from workspace by name."""
    if workspace is None:
        return None

    # Try to get project by name
    if hasattr(workspace, "get_project"):
        # First try to get current project
        project = workspace.get_project()
        if project:
            # Check if it matches the requested name
            proj_name = None
            if hasattr(project, "project_name"):
                proj_name = project.project_name
            elif hasattr(project, "name"):
                proj_name = project.name
            elif isinstance(project, str):
                proj_name = project

            if proj_name == project_name:
                return project

    # Try to get from project manager
    if hasattr(workspace, "project_manager") and workspace.project_manager:
        if hasattr(workspace.project_manager, "ensure_projects_loaded"):
            workspace.project_manager.ensure_projects_loaded()

        if hasattr(workspace, "get_projects"):
            projects = workspace.get_projects()
            if projects and project_name in projects:
                return projects[project_name]

    # Fallback: return None and let agent handle it
    return None


def resolve_project_name(project: Any) -> Optional[str]:
    """Resolve project name from project object."""
    if project is None:
        return None
    if hasattr(project, "project_name"):
        return project.project_name
    if hasattr(project, "name"):
        return project.name
    if isinstance(project, str):
        return project
    return None
