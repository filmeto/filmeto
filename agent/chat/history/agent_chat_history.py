"""
Agent Chat History module.

Provides rolling message history management for agent conversations.
"""

import os
from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path

from agent.chat.history.agent_chat_history_storage import MessageStorage
from agent.chat.history.agent_chat_history_paths import parse_message_filename
from agent.chat.agent_chat_message import AgentMessage

logger = __import__('logging').getLogger(__name__)


class MessageCursor:
    """
    Cursor for navigating through message history.
    """

    def __init__(self, message_id: str, timestamp: int, date_str: str, position: int = 0):
        """
        Initialize cursor.

        Args:
            message_id: The message ID
            timestamp: UTC timestamp in seconds
            date_str: Date string (yyyyMMdd format)
            position: Position in the file list for that date
        """
        self.message_id = message_id
        self.timestamp = timestamp
        self.date_str = date_str
        self.position = position


class AgentChatHistory:
    """
    Manages agent chat history with rolling message retrieval.

    Provides methods to:
    - Get latest message info
    - Get N messages before/after a given message ID
    - Add new messages to history
    """

    def __init__(self, workspace_path: str, project_name: str):
        """
        Initialize agent chat history.

        Args:
            workspace_path: Path to the workspace
            project_name: Name of the project
        """
        self.workspace_path = workspace_path
        self.project_name = project_name

        # Build history root path: workspace/projects/{project_name}/agent/history
        history_root = os.path.join(
            workspace_path,
            "projects",
            project_name,
            "agent",
            "history"
        )

        self.storage = MessageStorage(history_root)
        self._cache: Dict[str, Dict[str, Any]] = {}

    def add_message(self, message: AgentMessage, append_content: bool = True) -> str:
        """
        Add a message to history.

        Args:
            message: The AgentMessage to add
            append_content: Whether to append content to existing file (for same message_id)

        Returns:
            Path to the saved file
        """
        file_path = self.storage.save_message(message, append_content=append_content)

        loaded = self.storage.load_message(Path(file_path))
        if loaded:
            self._cache[message.message_id] = loaded

        return file_path

    def _load_messages_from_files(self, files: List[Path]) -> List[Dict[str, Any]]:
        result: List[Dict[str, Any]] = []
        for file_path in files:
            loaded = self.storage.load_message(file_path)
            if loaded:
                message_id = loaded.get("metadata", {}).get("message_id")
                if message_id:
                    self._cache[message_id] = loaded
                result.append(loaded)
        return result

    def _find_message_index(self, files: List[Path], message_id: str) -> Optional[int]:
        for index in range(len(files) - 1, -1, -1):
            parsed = parse_message_filename(files[index])
            if parsed and parsed.message_id == message_id:
                return index
        return None

    def get_latest_message_info(self) -> Optional[Dict[str, Any]]:
        """
        Get information about the most recent message.

        Returns:
            Dictionary with message_id, timestamp, and file_path, or None if no messages exist
        """
        return self.storage.get_latest_message_info()

    def get_latest_message_id(self) -> Optional[str]:
        """Get the most recent message ID."""
        info = self.get_latest_message_info()
        return info.get("message_id") if info else None

    def get_latest_message_timestamp(self) -> Optional[int]:
        """Get the most recent message timestamp (UTC seconds)."""
        info = self.get_latest_message_info()
        return info.get("timestamp") if info else None

    def get_message(self, message_id: str, date_str: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get a specific message by ID.

        Args:
            message_id: The message ID to retrieve
            date_str: Optional date string (yyyyMMdd) to narrow search

        Returns:
            Dictionary containing metadata and content, or None if not found
        """
        # Check cache first
        if message_id in self._cache:
            return self._cache[message_id]
        file_path = None
        if date_str:
            try:
                date = datetime.strptime(date_str, "%Y%m%d")
                file_path = self.storage.find_message_file(message_id, date)
            except ValueError:
                file_path = None

        if file_path is None:
            file_path = self.storage.find_message_file(message_id)

        if not file_path:
            return None

        loaded = self.storage.load_message(file_path)
        if loaded:
            self._cache[message_id] = loaded
        return loaded

    def get_messages_before(
        self,
        message_id: str,
        count: int = 20,
        date_str: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get N messages before a given message ID.

        Args:
            message_id: The reference message ID
            count: Number of messages to retrieve
            date_str: Optional date string (yyyyMMdd) to narrow search

        Returns:
            List of message dictionaries (excluding the reference message)
        """
        if count <= 0:
            return []

        files = self.storage.list_all_message_files()
        index = self._find_message_index(files, message_id)
        if index is None:
            return []

        start = max(0, index - count)
        slice_files = files[start:index]
        return self._load_messages_from_files(slice_files)

    def get_messages_after(
        self,
        message_id: str,
        count: int = 20,
        date_str: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get N messages after a given message ID.

        Args:
            message_id: The reference message ID
            count: Number of messages to retrieve
            date_str: Optional date string (yyyyMMdd) to narrow search

        Returns:
            List of message dictionaries (excluding the reference message)
        """
        if count <= 0:
            return []

        files = self.storage.list_all_message_files()
        index = self._find_message_index(files, message_id)
        if index is None:
            return []

        slice_files = files[index + 1:index + 1 + count]
        return self._load_messages_from_files(slice_files)

    def get_messages_around(
        self,
        message_id: str,
        before_count: int = 10,
        after_count: int = 10,
        date_str: Optional[str] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get messages around a given message ID.

        Args:
            message_id: The reference message ID
            before_count: Number of messages before to retrieve
            after_count: Number of messages after to retrieve
            date_str: Optional date string (yyyyMMdd) to narrow search

        Returns:
            Dictionary with 'before', 'current', and 'after' keys
        """
        return {
            'before': self.get_messages_before(message_id, before_count, date_str),
            'current': self.get_message(message_id, date_str),
            'after': self.get_messages_after(message_id, after_count, date_str)
        }

    def get_latest_messages(self, count: int = 20) -> List[Dict[str, Any]]:
        """
        Get the N most recent messages.

        Args:
            count: Number of messages to retrieve

        Returns:
            List of message dictionaries, most recent first
        """
        if count <= 0:
            return []

        files = self.storage.list_all_message_files()
        if not files:
            return []

        latest_files = files[-count:]
        return self._load_messages_from_files(list(reversed(latest_files)))

    def get_messages_by_date(self, date: datetime) -> List[Dict[str, Any]]:
        """
        Get all messages for a specific date.

        Args:
            date: The date to retrieve messages for

        Returns:
            List of message dictionaries for that date
        """
        files = self.storage.list_message_files(date)
        return self._load_messages_from_files(files)

    def clear_cache(self):
        """Clear the internal message cache."""
        self._cache.clear()
