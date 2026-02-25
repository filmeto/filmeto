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
        Get messages with GSN less than max_gsn (older messages).

        This method is used for loading older messages when scrolling up.

        IMPORTANT: A single message_id can have multiple log entries (e.g., llm_output,
        tool_call, skill, thinking, etc.), each with its own GSN. We return ALL log entries
        and let the MessageBuilder handle grouping by message_id.

        Optimized Strategy (single-pass with early termination):
        1. Traverse data sources from newest to oldest (active log -> recent archives)
        2. Collect ALL entries for message_ids where ANY entry has GSN < max_gsn
        3. Stop early once we have enough qualified message_ids

        Args:
            max_gsn: The maximum GSN to fetch (exclusive boundary - messages with GSN < max_gsn)
            count: Maximum number of UNIQUE message_ids to retrieve

        Returns:
            List of ALL log entry dictionaries for the retrieved message_ids,
            sorted by GSN (oldest first). May return more entries than 'count'
            because each message_id can have multiple log entries.
        """
        if max_gsn <= 0:
            # No GSN reference, fall back to latest messages
            return self._history.get_latest_messages(count)

        # Fetch multiplier: accounts for entries with GSN >= max_gsn being filtered out
        FETCH_MULTIPLIER = 3

        # Data structures for single-pass collection
        # message_entries: maps message_id -> list of all its entries
        # qualified_ids: message_ids that have at least one entry with GSN < max_gsn
        message_entries: Dict[str, List[Dict[str, Any]]] = {}
        qualified_ids: set[str] = set()
        seen_gsns: set[int] = set()

        def process_message(msg: Dict[str, Any]) -> None:
            """Process a single message entry."""
            msg_gsn = msg.get('metadata', {}).get('gsn', 0)
            msg_id = msg.get('message_id', '')

            if not msg_id or msg_gsn <= 0:
                return

            # Skip duplicates
            if msg_gsn in seen_gsns:
                return
            seen_gsns.add(msg_gsn)

            # Collect entry (we need all entries for each message_id)
            if msg_id not in message_entries:
                message_entries[msg_id] = []
            message_entries[msg_id].append(msg)

            # Mark as qualified if GSN < max_gsn
            if msg_gsn < max_gsn:
                qualified_ids.add(msg_id)

        # Process active log first (newest messages)
        active_messages = self._history.get_latest_messages(count * FETCH_MULTIPLIER)
        for msg in active_messages:
            process_message(msg)

        # Early termination: check if we have enough qualified IDs from active log
        if len(qualified_ids) < count and self._archives:
            # Process archives from newest to oldest (recent archives first)
            # Note: self._archives is ordered [oldest, ..., newest], so reversed() gives [newest, ..., oldest]
            for archive_dir in reversed(self._archives):
                if len(qualified_ids) >= count:
                    # Early termination: we have enough qualified IDs
                    break

                archive = self._history.storage.load_archive(archive_dir)
                if not archive:
                    continue

                archive_count = archive.get_line_count()
                if archive_count == 0:
                    continue

                # Fetch in chunks from the END of archive (newest entries first)
                # This is more efficient because we want messages with GSN close to max_gsn
                CHUNK_SIZE = 500
                for end_pos in range(archive_count - 1, -1, -CHUNK_SIZE):
                    if len(qualified_ids) >= count:
                        break

                    start_pos = max(0, end_pos - CHUNK_SIZE + 1)
                    chunk_size = end_pos - start_pos + 1
                    archive_messages = archive.get_messages(start_pos, chunk_size)

                    # Process in reverse order (newest first within chunk)
                    for msg in reversed(archive_messages):
                        process_message(msg)
                        if len(qualified_ids) >= count:
                            break

        # If no qualified messages found, return empty
        if not qualified_ids:
            return []

        # Select message_ids to return (limit by count)
        # Sort qualified_ids by their minimum GSN to get oldest first
        id_min_gsn = {
            msg_id: min(e.get('metadata', {}).get('gsn', 0) for e in entries)
            for msg_id, entries in message_entries.items()
            if msg_id in qualified_ids
        }
        selected_ids = sorted(qualified_ids, key=lambda mid: id_min_gsn.get(mid, 0))[:count]

        # Collect all entries for selected message_ids
        all_entries = []
        for msg_id in selected_ids:
            all_entries.extend(message_entries.get(msg_id, []))

        # Sort by GSN for final chronological order
        all_entries.sort(key=lambda m: m.get('metadata', {}).get('gsn', 0))

        return all_entries

    # Delegate methods to underlying history
    def get_latest_messages(self, count: int = 20) -> list:
        """
        Get latest messages from active log and archives.

        Returns messages from both active log and archives in reverse
        chronological order (most recent first). The UI layer is
        responsible for grouping messages by message_id.

        Note: This method does NOT deduplicate by message_id because the
        same message_id can have multiple content entries (e.g., skill
        progress updates) that should all be returned.

        Args:
            count: Number of messages to retrieve

        Returns:
            List of messages, most recent first
        """
        messages = []
        remaining = count

        # First get from active log
        active_messages = self._history.get_latest_messages(remaining)
        messages.extend(active_messages)
        remaining = count - len(active_messages)

        # If we need more messages, get from archives (newest first)
        if remaining > 0 and self._archives:
            for archive_dir in self._archives:
                if remaining <= 0:
                    break

                archive = self._history.storage.load_archive(archive_dir)
                archive_messages = archive.get_latest_messages(remaining)
                messages.extend(archive_messages)
                remaining = count - len(messages)

                if remaining <= 0:
                    break

        return messages

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
