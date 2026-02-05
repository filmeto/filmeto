"""
Agent Chat History Service module.

Provides singleton-style service for managing AgentChatHistory instances
at workspace+project_name granularity.
"""

import logging
from typing import Dict, Optional

from agent.chat.history.agent_chat_history import AgentChatHistory
from agent.chat.agent_chat_message import AgentMessage

logger = logging.getLogger(__name__)


class AgentChatHistoryService:
    """
    Service for managing AgentChatHistory instances.

    Provides static methods for accessing history instances
    at workspace+project_name granularity.
    """

    # Class-level storage for history instances
    _instances: Dict[str, AgentChatHistory] = {}

    @classmethod
    def _make_key(cls, workspace_path: str, project_name: str) -> str:
        """
        Create a unique key for workspace+project combination.

        Args:
            workspace_path: Path to the workspace
            project_name: Name of the project

        Returns:
            Unique key string
        """
        return f"{workspace_path}||{project_name}"

    @classmethod
    def get_history(cls, workspace_path: str, project_name: str) -> AgentChatHistory:
        """
        Get or create an AgentChatHistory instance for a workspace+project.

        Args:
            workspace_path: Path to the workspace
            project_name: Name of the project

        Returns:
            AgentChatHistory instance
        """
        key = cls._make_key(workspace_path, project_name)

        if key not in cls._instances:
            cls._instances[key] = AgentChatHistory(workspace_path, project_name)
            logger.debug(f"Created AgentChatHistory for {project_name} in {workspace_path}")

        return cls._instances[key]

    @classmethod
    def add_message(
        cls,
        workspace_path: str,
        project_name: str,
        message: AgentMessage,
        append_content: bool = True
    ) -> str:
        """
        Add a message to the history for a workspace+project.

        Args:
            workspace_path: Path to the workspace
            project_name: Name of the project
            message: The AgentMessage to add
            append_content: Whether to append content to existing file

        Returns:
            Path to the saved file
        """
        history = cls.get_history(workspace_path, project_name)
        return history.add_message(message, append_content=append_content)

    @classmethod
    def get_latest_message_info(
        cls,
        workspace_path: str,
        project_name: str
    ) -> Optional[dict]:
        """
        Get information about the most recent message.

        Args:
            workspace_path: Path to the workspace
            project_name: Name of the project

        Returns:
            Dictionary with message_id, timestamp, and file_path, or None
        """
        history = cls.get_history(workspace_path, project_name)
        return history.get_latest_message_info()

    @classmethod
    def get_message(
        cls,
        workspace_path: str,
        project_name: str,
        message_id: str,
        date_str: Optional[str] = None
    ) -> Optional[dict]:
        """
        Get a specific message by ID.

        Args:
            workspace_path: Path to the workspace
            project_name: Name of the project
            message_id: The message ID to retrieve
            date_str: Optional date string (yyyyMMdd) to narrow search

        Returns:
            Dictionary containing metadata and content, or None
        """
        history = cls.get_history(workspace_path, project_name)
        return history.get_message(message_id, date_str)

    @classmethod
    def get_messages_before(
        cls,
        workspace_path: str,
        project_name: str,
        message_id: str,
        count: int = 20,
        date_str: Optional[str] = None
    ) -> list:
        """
        Get N messages before a given message ID.

        Args:
            workspace_path: Path to the workspace
            project_name: Name of the project
            message_id: The reference message ID
            count: Number of messages to retrieve
            date_str: Optional date string (yyyyMMdd) to narrow search

        Returns:
            List of message dictionaries
        """
        history = cls.get_history(workspace_path, project_name)
        return history.get_messages_before(message_id, count, date_str)

    @classmethod
    def get_messages_after(
        cls,
        workspace_path: str,
        project_name: str,
        message_id: str,
        count: int = 20,
        date_str: Optional[str] = None
    ) -> list:
        """
        Get N messages after a given message ID.

        Args:
            workspace_path: Path to the workspace
            project_name: Name of the project
            message_id: The reference message ID
            count: Number of messages to retrieve
            date_str: Optional date string (yyyyMMdd) to narrow search

        Returns:
            List of message dictionaries
        """
        history = cls.get_history(workspace_path, project_name)
        return history.get_messages_after(message_id, count, date_str)

    @classmethod
    def get_messages_around(
        cls,
        workspace_path: str,
        project_name: str,
        message_id: str,
        before_count: int = 10,
        after_count: int = 10,
        date_str: Optional[str] = None
    ) -> dict:
        """
        Get messages around a given message ID.

        Args:
            workspace_path: Path to the workspace
            project_name: Name of the project
            message_id: The reference message ID
            before_count: Number of messages before to retrieve
            after_count: Number of messages after to retrieve
            date_str: Optional date string (yyyyMMdd) to narrow search

        Returns:
            Dictionary with 'before', 'current', and 'after' keys
        """
        history = cls.get_history(workspace_path, project_name)
        return history.get_messages_around(message_id, before_count, after_count, date_str)

    @classmethod
    def get_latest_messages(
        cls,
        workspace_path: str,
        project_name: str,
        count: int = 20
    ) -> list:
        """
        Get the N most recent messages.

        Args:
            workspace_path: Path to the workspace
            project_name: Name of the project
            count: Number of messages to retrieve

        Returns:
            List of message dictionaries, most recent first
        """
        history = cls.get_history(workspace_path, project_name)
        return history.get_latest_messages(count)

    @classmethod
    def get_messages_by_date(
        cls,
        workspace_path: str,
        project_name: str,
        date
    ) -> list:
        """
        Get all messages for a specific date.

        Args:
            workspace_path: Path to the workspace
            project_name: Name of the project
            date: The datetime object for the date

        Returns:
            List of message dictionaries for that date
        """
        history = cls.get_history(workspace_path, project_name)
        return history.get_messages_by_date(date)

    @classmethod
    def clear_cache(cls, workspace_path: str, project_name: str):
        """
        Clear the internal cache for a specific history instance.

        Args:
            workspace_path: Path to the workspace
            project_name: Name of the project
        """
        history = cls.get_history(workspace_path, project_name)
        history.clear_cache()

    @classmethod
    def clear_all_caches(cls):
        """Clear all internal caches."""
        for history in cls._instances.values():
            history.clear_cache()

    @classmethod
    def remove_history(cls, workspace_path: str, project_name: str):
        """
        Remove a history instance from the service.

        Args:
            workspace_path: Path to the workspace
            project_name: Name of the project
        """
        key = cls._make_key(workspace_path, project_name)
        if key in cls._instances:
            del cls._instances[key]
            logger.debug(f"Removed AgentChatHistory for {project_name} in {workspace_path}")
