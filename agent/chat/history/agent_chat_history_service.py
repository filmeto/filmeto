"""
Fast Message History Service using MessageLogStorage.

This service provides high-performance message history access using:
- File cursor positioning for O(1) random access
- Single-line JSON format for efficient parsing
- Active log + archive files for management
- Pure synchronous API for Qt compatibility
- Global Sequence Number (GSN) for archive-aware tracking

Design: UI reads from storage as single source of truth.

Enhanced Signal:
    The message_saved signal now includes:
    - workspace_path: Path to workspace
    - project_name: Name of project
    - message_id: ID of the saved message
    - gsn: Global sequence number for archive-aware tracking
    - current_gsn: Current (latest) GSN in the system
"""

import logging
import blinker
from typing import Dict, List, Optional, Tuple

from agent.chat.history.agent_chat_storage import MessageLogHistory
from agent.chat.agent_chat_message import AgentMessage

logger = logging.getLogger(__name__)


# Signal emitted when a message is successfully saved to storage
# Args: sender, workspace_path (str), project_name (str), message_id (str), gsn (int), current_gsn (int)
message_saved = blinker.Signal()


class FastMessageHistoryService:
    """
    Fast message history service using MessageLogStorage.

    This is a drop-in replacement for AgentChatHistoryService with
    significantly better performance for large message histories.

    Enhanced with Global Sequence Number (GSN) support for archive-aware
    message tracking.
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

        After successfully writing to storage, emits a message_saved signal
        that UI components can listen to for refresh.

        The enhanced signal includes GSN information for archive-aware tracking.

        Args:
            workspace_path: Path to workspace
            project_name: Name of project
            message: The AgentMessage to add

        Returns:
            True if successful
        """
        # Import here to avoid circular dependency
        from agent.chat.history.global_sequence_manager import get_enhanced_history

        # Convert AgentMessage to dict format
        message_dict = cls._message_to_dict(message)

        # Use enhanced history to get GSN support
        enhanced_history = get_enhanced_history(workspace_path, project_name)
        success, gsn = enhanced_history.append_message(message_dict)

        # Emit signal after successful storage write
        # UI should listen to this signal and refresh from storage
        if success:
            try:
                current_gsn = enhanced_history.get_current_gsn()

                message_saved.send(
                    cls,
                    workspace_path=workspace_path,
                    project_name=project_name,
                    message_id=message.message_id,
                    gsn=gsn,
                    current_gsn=current_gsn
                )
                logger.debug(f"Emitted message_saved signal for {message.message_id}, GSN: {gsn}, Current: {current_gsn}")
            except Exception as e:
                logger.error(f"Error emitting message_saved signal: {e}")

        return success

    @classmethod
    def _message_to_dict(cls, message: AgentMessage) -> dict:
        """Convert AgentMessage to dictionary for storage."""
        # The UI expects data in a specific format with nested metadata
        # We store flattened and maintain compatibility
        serialized_content = cls._serialize_content(message.structured_content)

        # Derive message_type from structured_content for storage compatibility
        message_type_value = "text"  # Default
        if message.structured_content:
            message_type_value = message.structured_content[0].content_type.value

        # Create the dict format that matches what the UI expects from AgentChatHistory
        return {
            "message_id": message.message_id,
            "message_type": message_type_value,
            "sender_id": message.sender_id,
            "sender_name": message.sender_name,
            "timestamp": message.timestamp.isoformat(),
            "metadata": {
                "message_id": message.message_id,
                "message_type": message_type_value,
                "sender_id": message.sender_id,
                "sender_name": message.sender_name,
                **(message.metadata or {})
            },
            "structured_content": serialized_content,
            # Also include 'content' for UI compatibility
            "content": serialized_content,
        }

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

    # ==================== GSN-based methods ====================

    @classmethod
    def get_messages_after_gsn(
        cls,
        workspace_path: str,
        project_name: str,
        last_seen_gsn: int,
        count: int = 100
    ) -> List[dict]:
        """
        Get messages that were saved after a given GSN.

        This is the primary method for UI components to fetch new messages
        in an archive-aware manner. The GSN (Global Sequence Number) is
        maintained across all archives, so this method works correctly
        even after archiving operations.

        Args:
            workspace_path: Path to workspace
            project_name: Name of project
            last_seen_gsn: The last GSN the UI has seen
            count: Maximum number of messages to retrieve

        Returns:
            List of message dictionaries in chronological order
        """
        from agent.chat.history.global_sequence_manager import get_enhanced_history

        enhanced_history = get_enhanced_history(workspace_path, project_name)
        return enhanced_history.get_messages_after_gsn(last_seen_gsn, count)

    @classmethod
    def get_current_gsn(
        cls,
        workspace_path: str,
        project_name: str
    ) -> int:
        """
        Get the current (latest) global sequence number.

        Args:
            workspace_path: Path to workspace
            project_name: Name of project

        Returns:
            Current GSN
        """
        from agent.chat.history.global_sequence_manager import get_enhanced_history

        enhanced_history = get_enhanced_history(workspace_path, project_name)
        return enhanced_history.get_current_gsn()

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
