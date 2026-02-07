"""
Agent Chat History module.

Provides rolling message history management for agent conversations
with LRU caching and efficient file list management.
"""

import os
from collections import OrderedDict
from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from agent.chat.history.agent_chat_history_storage import MessageStorage
from agent.chat.history.agent_chat_history_paths import parse_message_filename
from agent.chat.agent_chat_message import AgentMessage

logger = __import__('logging').getLogger(__name__)


class HistorySignals(QObject):
    """Signals for history update notifications."""
    message_added = Signal(str, str)  # workspace_path, project_name


# Global signals instance
_history_signals = HistorySignals()


def get_history_signals() -> HistorySignals:
    """Get the global history signals instance."""
    return _history_signals


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

    Features:
    - LRU cache for message data with bounded size
    - Cached file list to avoid repeated filesystem scans
    - Revision counter for efficient change detection
    - Cached latest message info
    """

    CACHE_MAX_SIZE = 200

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

        # LRU cache for loaded messages (OrderedDict for O(1) move-to-end)
        self._cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()

        # Cached sorted file list (invalidated on add_message)
        self._all_files_cache: Optional[List[Path]] = None

        # Monotonically increasing revision counter for change detection
        self._revision: int = 0

        # Cached latest message info (updated on add_message, lazy-loaded otherwise)
        self._latest_info_cache: Optional[Dict[str, Any]] = None

    @property
    def revision(self) -> int:
        """Monotonically increasing revision counter, incremented on each add_message call."""
        return self._revision

    def _cache_put(self, message_id: str, data: Dict[str, Any]):
        """Add item to LRU cache, evicting oldest entries if over capacity."""
        if message_id in self._cache:
            self._cache.move_to_end(message_id)
        self._cache[message_id] = data
        while len(self._cache) > self.CACHE_MAX_SIZE:
            self._cache.popitem(last=False)

    def _cache_get(self, message_id: str) -> Optional[Dict[str, Any]]:
        """Get item from cache and mark as recently used."""
        if message_id in self._cache:
            self._cache.move_to_end(message_id)
            return self._cache[message_id]
        return None

    def _invalidate_file_list_cache(self):
        """Invalidate the cached file list so it's rebuilt on next access."""
        self._all_files_cache = None
        # Also invalidate storage cache
        self.storage.invalidate_file_list_cache()

    def _get_all_files(self, force_refresh: bool = False) -> List[Path]:
        """Get all message files sorted by timestamp, using cache if available."""
        if self._all_files_cache is None or force_refresh:
            self._all_files_cache = self.storage.list_all_message_files(force_refresh=force_refresh)
        return self._all_files_cache

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
            self._cache_put(message.message_id, loaded)

        # Update latest info cache from the saved file
        parsed = parse_message_filename(Path(file_path))
        if parsed:
            new_info = {
                "message_id": parsed.message_id,
                "timestamp": parsed.timestamp,
                "file_path": str(file_path),
            }
            # Only update if this message is actually newer than the cached latest
            if (self._latest_info_cache is None
                    or parsed.timestamp >= self._latest_info_cache.get("timestamp", 0)):
                self._latest_info_cache = new_info

        # Incrementally update file list cache instead of invalidating
        # This avoids rescanning all directories on every add_message
        if self._all_files_cache is not None:
            # Remove old file with same message_id if exists
            self._all_files_cache = [f for f in self._all_files_cache
                                       if parse_message_filename(f).message_id != message.message_id
                                       if parse_message_filename(f)]
            # Add new file
            self._all_files_cache.append(Path(file_path))
            self._all_files_cache.sort(key=self.storage._get_file_timestamp)
        else:
            # Cache not initialized, will be built on demand
            pass

        # Increment revision to signal change
        self._revision += 1

        # Emit signal to notify listeners (e.g., UI components)
        get_history_signals().message_added.emit(self.workspace_path, self.project_name)

        return file_path

    def _load_messages_from_files(self, files: List[Path]) -> List[Dict[str, Any]]:
        """Load messages from file list with parallel loading optimization."""
        if not files:
            return []

        # Try to load as many as possible from cache first
        result: List[Dict[str, Any]] = []
        files_to_load: List[Path] = []

        for file_path in files:
            parsed = parse_message_filename(file_path)
            if parsed:
                cached = self._cache_get(parsed.message_id)
                if cached is not None:
                    result.append(cached)
                    continue

            files_to_load.append(file_path)

        # Batch load remaining files in parallel
        if files_to_load:
            # Use parallel loading for better performance
            try:
                loaded_batch = self.storage.load_messages_batch(files_to_load)

                # Map results back to original order
                loaded_dict: Dict[Path, Optional[Dict[str, Any]]] = dict(zip(files_to_load, loaded_batch))

                for file_path in files_to_load:
                    loaded = loaded_dict.get(file_path)
                    if loaded:
                        message_id = loaded.get("metadata", {}).get("message_id")
                        if message_id:
                            self._cache_put(message_id, loaded)
                        result.append(loaded)
                    else:
                        # Skip failed loads
                        pass
            except Exception as e:
                logger.error(f"Error in batch loading, falling back to sequential: {e}")
                # Fallback to sequential loading
                for file_path in files_to_load:
                    loaded = self.storage.load_message(file_path)
                    if loaded:
                        message_id = loaded.get("metadata", {}).get("message_id")
                        if message_id:
                            self._cache_put(message_id, loaded)
                        result.append(loaded)

        return result

    def _find_message_index(self, files: List[Path], message_id: str) -> Optional[int]:
        """Find the index of a message file in the sorted file list (searches from end)."""
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
        if self._latest_info_cache is not None:
            return self._latest_info_cache
        info = self.storage.get_latest_message_info()
        if info:
            self._latest_info_cache = info
        return info

    def get_latest_message_id(self) -> Optional[str]:
        """Get the most recent message ID."""
        info = self.get_latest_message_info()
        return info.get("message_id") if info else None

    def get_latest_message_timestamp(self) -> Optional[int]:
        """Get the most recent message timestamp (UTC milliseconds)."""
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
        cached = self._cache_get(message_id)
        if cached is not None:
            return cached

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
            self._cache_put(message_id, loaded)
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
            List of message dictionaries in chronological order (excluding the reference message)
        """
        if count <= 0:
            return []

        files = self._get_all_files()
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
            List of message dictionaries in chronological order (excluding the reference message)
        """
        if count <= 0:
            return []

        files = self._get_all_files()
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

        files = self._get_all_files()
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

    def get_message_count(self) -> int:
        """Get the total number of messages in history."""
        return len(self._get_all_files())

    def clear_cache(self):
        """Clear all internal caches."""
        self._cache.clear()
        self._all_files_cache = None
        self._latest_info_cache = None
