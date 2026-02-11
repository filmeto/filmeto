"""
Global Sequence Number Manager for Message History - Optimized Version.

This module provides a global sequence number (GSN) that spans across
all message archives, allowing UI components to track message positions
independently of archiving operations.

Optimized Design:
- No separate GSN index file needed (GSN stored in message metadata)
- Minimal file locking (only for GSN counter, not for index writes)
- Atomic GSN allocation with retry-based contention handling
- Simpler code with better performance

Usage:
    1. When saving a message, get_next_gsn() to reserve a GSN
    2. Include the GSN in the message's metadata
    3. UI tracks last_seen_gsn instead of line_offset
    4. Fetch messages using get_messages_after_gsn(last_seen_gsn)
"""

import os
import struct
import logging
import threading
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class GSNManager:
    """
    Optimized Global Sequence Number manager.

    Uses atomic file operations with minimal locking overhead.
    GSN is stored directly in message metadata - no separate index file needed.

    Thread Safety:
        - Uses file locking for GSN allocation (cross-process safe)
        - No additional index locking needed
    """

    _instances: Dict[str, 'GSNManager'] = {}
    _class_lock = threading.Lock()

    # File name for sequence number storage
    SEQUENCE_FILE = "gsn_counter.lock"
    ENTRY_SIZE = 8  # 8 bytes for uint64

    def __init__(self, history_root: str):
        """
        Initialize the GSN manager.

        Args:
            history_root: Root path for history storage
        """
        self.history_root = Path(history_root)
        self.history_root.mkdir(parents=True, exist_ok=True)

        self.sequence_file_path = self.history_root / self.SEQUENCE_FILE

        # Thread-local lock for coordinating within the same process
        self._local_lock = threading.Lock()

        # Initialize sequence file if it doesn't exist
        self._init_sequence_file()

    def _init_sequence_file(self):
        """Initialize the sequence file if it doesn't exist."""
        if not self.sequence_file_path.exists():
            try:
                with open(self.sequence_file_path, 'wb') as f:
                    f.write(struct.pack('<Q', 0))
                    f.flush()
                    os.fsync(f.fileno())
                logger.debug(f"Initialized GSN counter at {self.sequence_file_path}")
            except Exception as e:
                logger.error(f"Failed to initialize GSN counter: {e}")

    @classmethod
    def get_manager(cls, history_root: str) -> 'GSNManager':
        """
        Get or create a GSNManager instance for the given history root.

        Args:
            history_root: Root path for history storage

        Returns:
            GSNManager instance
        """
        with cls._class_lock:
            if history_root not in cls._instances:
                cls._instances[history_root] = GSNManager(history_root)
            return cls._instances[history_root]

    def get_next_gsn(self) -> int:
        """
        Get and increment the next GSN.

        Uses file locking for atomic read-modify-write operation.
        This is safe across processes and threads.

        Returns:
            The reserved GSN
        """
        with self._local_lock:
            try:
                # Read-modify-write with file locking
                with open(self.sequence_file_path, 'r+b') as f:
                    # Acquire exclusive lock
                    fcntl.flock(f.fileno(), fcntl.LOCK_EX)

                    # Read current value
                    f.seek(0)
                    data = f.read(self.ENTRY_SIZE)
                    current = struct.unpack('<Q', data)[0] if len(data) == self.ENTRY_SIZE else 0

                    # Increment
                    next_gsn = current + 1

                    # Write back
                    f.seek(0)
                    f.write(struct.pack('<Q', next_gsn))
                    f.flush()
                    os.fsync(f.fileno())

                    # Release lock (happens automatically on context exit)

                return next_gsn

            except Exception as e:
                logger.error(f"Error allocating GSN: {e}")
                # Fallback: return current + 1 (may cause duplicates in rare cases)
                return self._read_current_gsn() + 1

    def _read_current_gsn(self) -> int:
        """
        Read the current GSN without incrementing (no lock for read-only).

        Returns:
            Current GSN, or 0 if file doesn't exist
        """
        try:
            if not self.sequence_file_path.exists():
                return 0
            with open(self.sequence_file_path, 'rb') as f:
                data = f.read(self.ENTRY_SIZE)
                return struct.unpack('<Q', data)[0] if len(data) == self.ENTRY_SIZE else 0
        except Exception:
            return 0

    def get_current_gsn(self) -> int:
        """
        Get the current (highest) GSN without incrementing.

        Uses file locking for consistent read.

        Returns:
            Current GSN
        """
        with self._local_lock:
            try:
                with open(self.sequence_file_path, 'rb') as f:
                    fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                    f.seek(0)
                    data = f.read(self.ENTRY_SIZE)
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                    return struct.unpack('<Q', data)[0] if len(data) == self.ENTRY_SIZE else 0
            except Exception:
                return 0


# Import fcntl after defining the class to avoid issues at module level
import fcntl


class EnhancedMessageLogHistory:
    """
    Enhanced message history with GSN support - Optimized Version.

    Key improvements:
    - No separate GSN index file (GSN stored in message metadata)
    - Simpler concurrency model (no GSN index locking)
    - Better performance (fewer file operations)

    The GSN is stored in the message's metadata field, making it
    immediately available when messages are read from storage.
    """

    def __init__(self, workspace_path: str, project_name: str):
        """
        Initialize enhanced message history.

        Args:
            workspace_path: Path to workspace
            project_name: Name of the project
        """
        self.workspace_path = workspace_path
        self.project_name = project_name

        # Build history root path
        history_root = os.path.join(
            workspace_path,
            "projects",
            project_name,
            "agent",
            "history"
        )

        # Import here to avoid circular dependency
        from agent.chat.history.agent_chat_storage import MessageLogHistory

        # Use the existing MessageLogHistory for storage
        self._history = MessageLogHistory(workspace_path, project_name)
        self.storage = self._history.storage
        self.history_root = Path(history_root)

        # GSN manager
        self._gsn_manager = GSNManager.get_manager(str(self.history_root))

        # Archive list cache
        self._archives: List[Path] = []
        self._refresh_archives()

    def _refresh_archives(self):
        """Refresh the list of archive directories."""
        self._archives = self.storage.get_archived_directories()

    def append_message(self, message: Dict[str, Any]) -> tuple[bool, int]:
        """
        Append a message and return its GSN.

        Optimized: No separate GSN index write needed.

        Thread Safety:
            - GSN allocation uses file locking (cross-process safe)
            - Storage append uses thread locking (in-process safe)
            - No additional locking needed

        Args:
            message: Message dictionary to append

        Returns:
            Tuple of (success, gsn)
        """
        # Allocate GSN (uses file locking for atomicity)
        gsn = self._gsn_manager.get_next_gsn()

        # Add GSN to message metadata
        if 'metadata' not in message:
            message['metadata'] = {}
        message['metadata']['gsn'] = gsn

        # Append to storage (has its own locking)
        # No separate GSN index write needed - GSN is in the message!
        success = self.storage.append_message(message)

        if success:
            # Refresh archives in case archiving occurred
            self._refresh_archives()
            logger.debug(f"Appended message with GSN {gsn}")
        else:
            logger.warning(f"Failed to append message, GSN {gsn} was reserved but not used")

        return success, gsn

    def get_messages_after_gsn(self, last_seen_gsn: int, count: int = 100) -> List[Dict[str, Any]]:
        """
        Get messages that were saved after a given GSN.

        Optimized: Filters messages by GSN from metadata.

        Args:
            last_seen_gsn: The last GSN the UI has seen
            count: Maximum number of messages to retrieve

        Returns:
            List of message dictionaries in chronological order
        """
        # First check if there are any new messages at all
        current_gsn = self._gsn_manager.get_current_gsn()
        if current_gsn <= last_seen_gsn:
            return []

        # Calculate how many messages we might need to fetch
        # Fetch more than requested because some might have GSN <= last_seen_gsn
        fetch_count = min(count * 2, current_gsn - last_seen_gsn + 10)

        messages = []

        # Get messages from active log first
        active_messages = self._history.get_latest_messages(fetch_count)

        # Filter by GSN
        for msg in active_messages:
            msg_gsn = msg.get('metadata', {}).get('gsn', 0)
            if msg_gsn > last_seen_gsn:
                messages.append(msg)

        # If we need more messages and there are archives, check them
        if len(messages) < count and self._archives:
            remaining = count - len(messages)

            # Check archives (newest first)
            for archive_dir in self._archives[:3]:  # Check last 3 archives
                if remaining <= 0:
                    break

                archive = self.storage.load_archive(archive_dir)
                archive_messages = archive.get_latest_messages(remaining)

                for msg in archive_messages:
                    msg_gsn = msg.get('metadata', {}).get('gsn', 0)
                    if msg_gsn > last_seen_gsn:
                        messages.append(msg)
                        remaining -= 1
                        if remaining <= 0:
                            break

        # Sort by GSN and limit
        messages.sort(key=lambda m: m.get('metadata', {}).get('gsn', 0))
        return messages[:count]

    def get_current_gsn(self) -> int:
        """Get the current (latest) global sequence number."""
        return self._gsn_manager.get_current_gsn()

    def get_messages_before_gsn(self, max_gsn: int, count: int = 100) -> List[Dict[str, Any]]:
        """
        Get messages with GSN less than or equal to max_gsn (older messages).

        This method is used for loading older messages when scrolling up.

        Args:
            max_gsn: The maximum GSN to fetch (exclusive boundary - messages with GSN < max_gsn)
            count: Maximum number of messages to retrieve

        Returns:
            List of message dictionaries in chronological order (oldest first)
        """
        if max_gsn <= 0:
            # No GSN reference, fall back to latest messages
            return self._history.get_latest_messages(count)

        messages = []
        seen_gsns = set()

        # Calculate fetch range - we need messages with GSN < max_gsn
        # Fetch more than needed because we'll filter by GSN
        fetch_count = count * 3

        # Get messages from active log
        active_messages = self._history.get_latest_messages(fetch_count)

        # Filter by GSN (< max_gsn) and track oldest
        for msg in active_messages:
            msg_gsn = msg.get('metadata', {}).get('gsn', 0)
            if 0 < msg_gsn < max_gsn and msg_gsn not in seen_gsns:
                messages.append(msg)
                seen_gsns.add(msg_gsn)

        # If we need more messages and there are archives, check them
        if len(messages) < count and self._archives:
            remaining = count - len(messages)

            # Check archives (oldest first for older messages)
            for archive_dir in reversed(self._archives):
                if remaining <= 0:
                    break

                archive = self._history.storage.load_archive(archive_dir)
                if not archive:
                    continue

                archive_count = archive.get_line_count()
                if archive_count == 0:
                    continue

                # Fetch messages from archive
                fetch_from_archive = min(archive_count, remaining * 2)
                start = max(0, archive_count - fetch_from_archive)
                archive_messages = archive.get_messages(start, fetch_from_archive)

                # Filter by GSN
                for msg in reversed(archive_messages):
                    msg_gsn = msg.get('metadata', {}).get('gsn', 0)
                    if 0 < msg_gsn < max_gsn and msg_gsn not in seen_gsns:
                        messages.append(msg)
                        seen_gsns.add(msg_gsn)
                        remaining -= 1
                        if remaining <= 0:
                            break

        # Sort by GSN to get chronological order
        messages.sort(key=lambda m: m.get('metadata', {}).get('gsn', 0))

        # Return only the requested count
        return messages[:count]

    # Delegate methods to underlying history
    def get_latest_messages(self, count: int = 20) -> list:
        """Get latest messages from active log."""
        return self._history.get_latest_messages(count)

    def get_messages_after(self, line_offset: int, count: int) -> list:
        """Get messages after a line offset in active log."""
        return self._history.get_messages_after(line_offset, count)

    def get_messages_before(self, line_offset: int, count: int) -> list:
        """Get messages before a line offset."""
        return self._history.get_messages_before(line_offset, count)

    def get_total_count(self) -> int:
        """Get total message count."""
        return self._history.get_total_count()

    def get_latest_line_offset(self) -> int:
        """Get the current line offset in active log."""
        return self._history.get_latest_line_offset()

    def invalidate_cache(self):
        """Invalidate caches."""
        self._history.invalidate_cache()
        self._refresh_archives()


# Class-level cache for enhanced history instances
_enhanced_history_instances: Dict[str, EnhancedMessageLogHistory] = {}
_enhanced_history_lock = threading.Lock()


def get_enhanced_history(workspace_path: str, project_name: str) -> EnhancedMessageLogHistory:
    """
    Get or create an EnhancedMessageLogHistory instance.

    Args:
        workspace_path: Path to workspace
        project_name: Name of project

    Returns:
        EnhancedMessageLogHistory instance
    """
    key = f"{workspace_path}||{project_name}"

    with _enhanced_history_lock:
        if key not in _enhanced_history_instances:
            _enhanced_history_instances[key] = EnhancedMessageLogHistory(
                workspace_path, project_name
            )
        return _enhanced_history_instances[key]
