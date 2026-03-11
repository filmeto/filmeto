"""
Crew Member History Service - History storage for individual crew members.

Storage path: workspace/projects/{project}/agent/crews/{crew_member}/history

This service provides:
- Message storage for crew member conversations
- History query support (get latest, get after/before offset, get by GSN)
- Reuses MessageLogStorage for high-performance storage

Signal:
    crew_member_message_saved is emitted after a message is successfully
    written to storage. UI components (e.g. PrivateChatWidget) can listen
    to this signal to render system-routed messages in real-time.
    Args: sender, workspace_path (str), project_name (str),
          crew_title (str), message (dict)
"""

import logging
import os
import blinker
from pathlib import Path
from typing import Dict, List, Optional, Any
from threading import Lock

from agent.chat.history.agent_chat_storage import MessageLogStorage

logger = logging.getLogger(__name__)

# Signal emitted when a message is written to a crew member's private history.
crew_member_message_saved = blinker.Signal()


class CrewMemberHistoryService:
    """
    Singleton service to manage history storage for crew members.

    Each crew member has its own history storage under:
    workspace/projects/{project}/agent/crews/{crew_title}/history/
    """

    _instance = None
    _lock = Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(CrewMemberHistoryService, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._storages: Dict[str, MessageLogStorage] = {}
        self._initialized = True

    def _make_key(self, workspace_path: str, project_name: str, crew_title: str) -> str:
        """Create a unique key for workspace+project+crew_member combination."""
        return f"{workspace_path}||{project_name}||{crew_title}"

    def _get_history_root(self, workspace_path: str, project_name: str, crew_title: str) -> str:
        """Get the history root path for a crew member."""
        return os.path.join(
            workspace_path,
            "projects",
            project_name,
            "agent",
            "crews",
            crew_title,
            "history"
        )

    def get_storage(self, workspace_path: str, project_name: str, crew_title: str) -> MessageLogStorage:
        """Get or create a MessageLogStorage instance for a crew member."""
        key = self._make_key(workspace_path, project_name, crew_title)

        if key not in self._storages:
            history_root = self._get_history_root(workspace_path, project_name, crew_title)
            self._storages[key] = MessageLogStorage(history_root)
            logger.debug(f"Created MessageLogStorage for crew member: {crew_title}")

        return self._storages[key]

    def add_message(
        self,
        workspace_path: str,
        project_name: str,
        crew_title: str,
        message: Dict[str, Any]
    ) -> bool:
        """
        Add a message to crew member history.

        After a successful write, emits ``crew_member_message_saved`` so that
        open PrivateChatWidget instances can render the message immediately.

        Args:
            workspace_path: Path to workspace
            project_name: Name of project
            crew_title: Crew member's title (used as directory name)
            message: Message dictionary to store

        Returns:
            True if successful
        """
        storage = self.get_storage(workspace_path, project_name, crew_title)
        success = storage.append_message(message)
        if success:
            try:
                crew_member_message_saved.send(
                    self,
                    workspace_path=workspace_path,
                    project_name=project_name,
                    crew_title=crew_title,
                    message=message,
                )
            except Exception as e:
                logger.error(f"Error emitting crew_member_message_saved signal: {e}")
        return success

    def get_latest_messages(
        self,
        workspace_path: str,
        project_name: str,
        crew_title: str,
        count: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get the N most recent messages for a crew member.

        Args:
            workspace_path: Path to workspace
            project_name: Name of project
            crew_title: Crew member's title
            count: Number of messages to retrieve

        Returns:
            List of message dictionaries, most recent first
        """
        storage = self.get_storage(workspace_path, project_name, crew_title)
        return storage.get_latest_messages(count)

    def get_messages_after(
        self,
        workspace_path: str,
        project_name: str,
        crew_title: str,
        line_offset: int,
        count: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get N messages after a given line offset.

        Args:
            workspace_path: Path to workspace
            project_name: Name of project
            crew_title: Crew member's title
            line_offset: Line offset in active log
            count: Number of messages to retrieve

        Returns:
            List of message dictionaries in chronological order
        """
        storage = self.get_storage(workspace_path, project_name, crew_title)
        active_count = storage.get_message_count()

        if line_offset >= active_count:
            return []

        end = min(line_offset + count, active_count)
        return storage.get_messages(line_offset, end - line_offset)

    def get_messages_before(
        self,
        workspace_path: str,
        project_name: str,
        crew_title: str,
        line_offset: int,
        count: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get N messages before a given line offset.

        Args:
            workspace_path: Path to workspace
            project_name: Name of project
            crew_title: Crew member's title
            line_offset: Starting line offset (exclusive)
            count: Number of messages to retrieve

        Returns:
            List of message dictionaries in chronological order
        """
        storage = self.get_storage(workspace_path, project_name, crew_title)
        if line_offset <= 0:
            return []

        start = max(0, line_offset - count)
        messages = storage.get_messages(start, line_offset - start)
        return messages

    def get_total_count(
        self,
        workspace_path: str,
        project_name: str,
        crew_title: str
    ) -> int:
        """
        Get total message count for a crew member.

        Args:
            workspace_path: Path to workspace
            project_name: Name of project
            crew_title: Crew member's title

        Returns:
            Total number of messages
        """
        storage = self.get_storage(workspace_path, project_name, crew_title)
        return storage.get_total_count()

    def get_latest_line_offset(
        self,
        workspace_path: str,
        project_name: str,
        crew_title: str
    ) -> int:
        """
        Get the latest line offset (total messages in active log).

        Args:
            workspace_path: Path to workspace
            project_name: Name of project
            crew_title: Crew member's title

        Returns:
            Current line offset
        """
        storage = self.get_storage(workspace_path, project_name, crew_title)
        return storage.get_message_count()

    def clear_history(
        self,
        workspace_path: str,
        project_name: str,
        crew_title: str
    ) -> bool:
        """
        Clear all history for a crew member.

        Args:
            workspace_path: Path to workspace
            project_name: Name of project
            crew_title: Crew member's title

        Returns:
            True if successful
        """
        import shutil

        key = self._make_key(workspace_path, project_name, crew_title)

        # Remove from cache
        if key in self._storages:
            del self._storages[key]

        # Remove directory
        history_root = self._get_history_root(workspace_path, project_name, crew_title)
        if os.path.exists(history_root):
            try:
                shutil.rmtree(history_root)
                logger.info(f"Cleared history for crew member: {crew_title}")
                return True
            except Exception as e:
                logger.error(f"Error clearing history for {crew_title}: {e}")
                return False

        return True

    def remove_storage(self, workspace_path: str, project_name: str, crew_title: str):
        """Remove a storage instance from the cache."""
        key = self._make_key(workspace_path, project_name, crew_title)
        if key in self._storages:
            del self._storages[key]
            logger.debug(f"Removed storage for crew member: {crew_title}")


# Singleton instance
crew_member_history_service = CrewMemberHistoryService()
