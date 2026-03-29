"""
LLM Utilities

Utility functions for working with LLM responses.
"""
from typing import Any


def extract_content(response: Any) -> str:
    """
    Extract content from LLM response.

    Handles response objects with choices attribute and extracts
    the message content. Supports both regular content and reasoning_content
    for reasoning models.

    Args:
        response: The response object with choices attribute

    Returns:
        The extracted content as a string, or empty string if extraction fails.
    """
    # Handle response object with choices
    if hasattr(response, 'choices'):
        choices = response.choices
        if choices and len(choices) > 0:
            choice = choices[0]
            if hasattr(choice, 'message'):
                message = choice.message
                # First try to get regular content
                if hasattr(message, 'content') and message.content is not None:
                    return str(message.content)
                # Check for reasoning_content (for reasoning models like o1)
                if hasattr(message, 'reasoning_content') and message.reasoning_content:
                    return str(message.reasoning_content)
            # Fallback to text attribute (for some older response formats)
            text = getattr(choice, 'text', None)
            if text:
                return str(text)

    # Fallback: convert to string
    return str(response) if response else ""


def get_chat_service(workspace=None):
    """
    Get or create the server's ChatService instance.

    Args:
        workspace: Optional workspace instance

    Returns:
        ChatService instance or None if not available
    """
    try:
        from server.server import ServerManager
        from server.service.chat_service import ChatService
        from server.plugins.plugin_manager import PluginManager
        from pathlib import Path

        # Get workspace path
        workspace_path = None
        if workspace and hasattr(workspace, 'get_path'):
            workspace_path = workspace.get_path()
        elif workspace and hasattr(workspace, 'workspace_path'):
            workspace_path = workspace.workspace_path

        # Fallback to default workspace if not available
        if not workspace_path:
            project_root = Path(__file__).parent.parent
            workspace_path = str(project_root / "workspace")

        # Create plugin manager and server manager
        plugin_manager = PluginManager()
        plugin_manager.discover_plugins()
        server_manager = ServerManager(workspace_path, plugin_manager)

        # Create chat service
        return ChatService(server_manager)
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Failed to initialize ChatService: {e}")
        return None


def validate_llm_config(workspace=None) -> bool:
    """
    Validate if LLM service is properly configured.

    Args:
        workspace: Optional workspace instance

    Returns:
        True if properly configured, False otherwise
    """
    try:
        chat_service = get_chat_service(workspace)
        if chat_service is not None:
            # Refresh capabilities to get latest server status
            selection_svc = chat_service.selection_service
            if selection_svc and hasattr(selection_svc, '_capability_service'):
                selection_svc._capability_service.refresh_capabilities()

            # Check if there are any available chat capabilities
            from server.api.types import Capability
            capabilities = selection_svc._capability_service.get_capabilities_by_type(Capability.CHAT_COMPLETION)
            if capabilities:
                return True
    except Exception:
        pass

    return False