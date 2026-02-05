"""
Agent Chat History module.

Provides rolling message history management for agent conversations.
"""

import os
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from pathlib import Path

from agent.chat.history.storage import MessageStorage
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

        # Update cache
        if message.message_id in self._cache:
            # Reload from file to get updated content
            loaded = self.storage.load_message(Path(file_path))
            if loaded:
                self._cache[message.message_id] = loaded

        return file_path

    def get_latest_message_info(self) -> Optional[Dict[str, Any]]:
        """
        Get information about the most recent message.

        Returns:
            Dictionary with message_id, timestamp, and file_path, or None if no messages exist
        """
        return self.storage.get_latest_message_info()

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

        # Search for the message file
        if date_str:
            # Search specific date directory
            date = datetime.strptime(date_str, "%Y%m%d")
            files = self.storage.list_message_files(date)

            for file_path in files:
                if message_id in file_path.stem:
                    loaded = self.storage.load_message(file_path)
                    if loaded and loaded.get('metadata', {}).get('message_id') == message_id:
                        self._cache[message_id] = loaded
                        return loaded
        else:
            # Search recent dates (last 7 days)
            for days_ago in range(7):
                date = datetime.now() - timedelta(days=days_ago)
                files = self.storage.list_message_files(date)

                for file_path in files:
                    if message_id in file_path.stem:
                        loaded = self.storage.load_message(file_path)
                        if loaded and loaded.get('metadata', {}).get('message_id') == message_id:
                            self._cache[message_id] = loaded
                            return loaded

        return None

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
        result = []

        # Find the reference message
        reference = self.get_message(message_id, date_str)
        if not reference:
            return result

        ref_timestamp = reference['metadata'].get('timestamp')
        if not ref_timestamp:
            return result

        ref_datetime = datetime.fromisoformat(ref_timestamp)

        # Search backwards from the reference date
        days_to_search = 7  # Search up to 7 days back

        for days_ago in range(days_to_search + 1):
            search_date = ref_datetime - timedelta(days=days_ago)
            files = self.storage.list_message_files(search_date)

            if days_ago == 0:
                # On the same day, filter files before the reference timestamp
                ref_timestamp_int = int(ref_datetime.timestamp())
                files = [f for f in files if self._get_file_timestamp(f) < ref_timestamp_int]

            # Process files in reverse order (newest first)
            for file_path in reversed(files):
                if len(result) >= count:
                    break

                loaded = self.storage.load_message(file_path)
                if loaded:
                    result.insert(0, loaded)  # Insert at beginning to maintain order

            if len(result) >= count:
                break

        return result[-count:]  # Return the most recent N messages

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
        result = []

        # Find the reference message
        reference = self.get_message(message_id, date_str)
        if not reference:
            return result

        ref_timestamp = reference['metadata'].get('timestamp')
        if not ref_timestamp:
            return result

        ref_datetime = datetime.fromisoformat(ref_timestamp)

        # Search forward from the reference date
        days_to_search = 7  # Search up to 7 days forward

        for days_ahead in range(days_to_search + 1):
            search_date = ref_datetime + timedelta(days=days_ahead)
            files = self.storage.list_message_files(search_date)

            if days_ahead == 0:
                # On the same day, filter files after the reference timestamp
                ref_timestamp_int = int(ref_datetime.timestamp())
                files = [f for f in files if self._get_file_timestamp(f) > ref_timestamp_int]

            # Process files in order (oldest first)
            for file_path in files:
                if len(result) >= count:
                    break

                loaded = self.storage.load_message(file_path)
                if loaded:
                    result.append(loaded)

            if len(result) >= count:
                break

        return result[:count]  # Return the first N messages

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
        result = []
        target_count = count

        # Search from most recent date backwards
        for days_ago in range(30):  # Search up to 30 days back
            date = datetime.now() - timedelta(days=days_ago)
            files = self.storage.list_message_files(date)

            # Process files in reverse order (newest first)
            for file_path in reversed(files):
                if len(result) >= target_count:
                    break

                loaded = self.storage.load_message(file_path)
                if loaded:
                    result.append(loaded)

            if len(result) >= target_count:
                break

        return result[:target_count]

    def get_messages_by_date(self, date: datetime) -> List[Dict[str, Any]]:
        """
        Get all messages for a specific date.

        Args:
            date: The date to retrieve messages for

        Returns:
            List of message dictionaries for that date
        """
        files = self.storage.list_message_files(date)
        result = []

        for file_path in files:
            loaded = self.storage.load_message(file_path)
            if loaded:
                result.append(loaded)

        return result

    def _get_file_timestamp(self, file_path: Path) -> int:
        """
        Extract timestamp from a message file path.

        Args:
            file_path: Path to the message file

        Returns:
            UTC timestamp in seconds, or 0 if extraction fails
        """
        try:
            name = file_path.stem
            timestamp_str = name.split('_')[0]
            return int(timestamp_str)
        except (ValueError, IndexError):
            return 0

    def clear_cache(self):
        """Clear the internal message cache."""
        self._cache.clear()
