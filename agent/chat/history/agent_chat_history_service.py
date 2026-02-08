"""
Fast Message History Service using MessageLogStorage.

This service provides high-performance message history access using:
- File cursor positioning for O(1) random access
- Single-line JSON format for efficient parsing
- Active log + archive files for management
- Pure synchronous API for Qt compatibility
"""

import logging
from typing import Dict, List

from agent.chat.history.agent_chat_storage import MessageLogHistory
from agent.chat.agent_chat_message import AgentMessage

logger = logging.getLogger(__name__)


class FastMessageHistoryService:
    """
    Fast message history service using MessageLogStorage.

    This is a drop-in replacement for AgentChatHistoryService with
    significantly better performance for large message histories.
    """

    # Class-level storage for history instances
    _instances: Dict[str, MessageLogHistory] = {}

    @classmethod
    def _make_key(cls, workspace_path: str, project_name: str) -> str:
        """Create a unique key for workspace+project combination."""
        return f"{workspace_path}||{project_name}"

    @classmethod
    def get_history(cls, workspace_path: str, project_name: str) -> MessageLogHistory:
        """Get or create a MessageLogHistory instance."""
        key = cls._make_key(workspace_path, project_name)

        if key not in cls._instances:
            cls._instances[key] = MessageLogHistory(workspace_path, project_name)
            logger.debug(f"Created MessageLogHistory for {project_name}")

        return cls._instances[key]

    @classmethod
    def add_message(
        cls,
        workspace_path: str,
        project_name: str,
        message: AgentMessage
    ) -> bool:
        """
        Add a message to history.

        Args:
            workspace_path: Path to workspace
            project_name: Name of project
            message: The AgentMessage to add

        Returns:
            True if successful
        """
        # Convert AgentMessage to dict format
        message_dict = cls._message_to_dict(message)
        history = cls.get_history(workspace_path, project_name)
        return history.append_message(message_dict)

    @classmethod
    def _message_to_dict(cls, message: AgentMessage) -> dict:
        """
        Convert AgentMessage to dictionary for storage.

        Creates a simple, non-redundant JSON structure:
        - Message properties are at top level only
        - metadata contains only user-defined metadata (not message properties)
        - structured_content is the single source of truth for message content
        """
        serialized_content = cls._serialize_content(message.structured_content)

        # Create clean dict without redundancy
        result = {
            "message_id": message.message_id,
            "sender_id": message.sender_id,
            "sender_name": message.sender_name,
            "timestamp": message.timestamp.isoformat(),
            "structured_content": serialized_content,
        }

        # Add user-defined metadata only (exclude message properties to avoid duplication)
        if message.metadata:
            # Filter out any keys that duplicate message properties
            excluded_keys = {"message_id", "sender_id", "sender_name", "timestamp"}
            filtered_metadata = {k: v for k, v in message.metadata.items() if k not in excluded_keys}
            if filtered_metadata:
                result["metadata"] = filtered_metadata

        return result

    @classmethod
    def _serialize_content(cls, content_list) -> List[dict]:
        """Serialize structured content to dict format."""
        result = []
        for content in content_list or []:
            if hasattr(content, "to_dict"):
                result.append(content.to_dict())
            elif hasattr(content, "__dict__"):
                result.append(content.__dict__)
            else:
                result.append({"content_type": str(content)})
        return result

    @classmethod
    def get_latest_messages(
        cls,
        workspace_path: str,
        project_name: str,
        count: int = 20
    ) -> List[dict]:
        """
        Get the N most recent messages.

        Args:
            workspace_path: Path to workspace
            project_name: Name of project
            count: Number of messages to retrieve

        Returns:
            List of message dictionaries, most recent first
        """
        history = cls.get_history(workspace_path, project_name)
        return history.get_latest_messages(count)

    @classmethod
    def get_messages_after(
        cls,
        workspace_path: str,
        project_name: str,
        line_offset: int,
        count: int = 20
    ) -> List[dict]:
        """
        Get N messages after a given line offset.

        Args:
            workspace_path: Path to workspace
            project_name: Name of project
            line_offset: Line offset in active log
            count: Number of messages to retrieve

        Returns:
            List of message dictionaries in chronological order
        """
        history = cls.get_history(workspace_path, project_name)
        return history.get_messages_after(line_offset, count)

    @classmethod
    def get_messages_before(
        cls,
        workspace_path: str,
        project_name: str,
        line_offset: int,
        count: int = 20
    ) -> List[dict]:
        """
        Get N messages before a given line offset.

        Args:
            workspace_path: Path to workspace
            project_name: Name of project
            line_offset: Starting line offset (exclusive)
            count: Number of messages to retrieve

        Returns:
            List of message dictionaries in chronological order
        """
        history = cls.get_history(workspace_path, project_name)
        return history.get_messages_before(line_offset, count)

    @classmethod
    def get_total_count(
        cls,
        workspace_path: str,
        project_name: str
    ) -> int:
        """
        Get total message count.

        Args:
            workspace_path: Path to workspace
            project_name: Name of project

        Returns:
            Total number of messages
        """
        history = cls.get_history(workspace_path, project_name)
        return history.get_total_count()

    @classmethod
    def get_latest_line_offset(
        cls,
        workspace_path: str,
        project_name: str
    ) -> int:
        """
        Get the latest line offset (total messages in active log).

        Args:
            workspace_path: Path to workspace
            project_name: Name of project

        Returns:
            Current line offset
        """
        history = cls.get_history(workspace_path, project_name)
        return history.get_latest_line_offset()

    @classmethod
    def clear_cache(cls, workspace_path: str, project_name: str):
        """Clear caches for a specific history instance."""
        history = cls.get_history(workspace_path, project_name)
        history.invalidate_cache()

    @classmethod
    def remove_history(cls, workspace_path: str, project_name: str):
        """Remove a history instance from the service."""
        key = cls._make_key(workspace_path, project_name)
        if key in cls._instances:
            del cls._instances[key]
            logger.debug(f"Removed MessageLogHistory for {project_name}")
