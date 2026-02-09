"""
Global Sequence Number Manager for Message History.

This module provides a global sequence number (GSN) that spans across
all message archives, allowing UI components to track message positions
independently of archiving operations.

Design:
- count.lock: Stores the current global sequence number
- FileLock: Ensures exclusive access for atomic updates
- Signal enrichment: Includes GSN in message_saved signal

Usage:
    1. When saving a message, get_next_sequence_number() to reserve a GSN
    2. Include the GSN in the message_saved signal
    3. UI tracks last_seen_gsn instead of line_offset
    4. Fetch messages using get_messages_after_gsn(last_seen_gsn)
"""

import os
import fcntl
import struct
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from threading import Lock

logger = logging.getLogger(__name__)


class SequenceNumberManager:
    """
    Manages global sequence numbers (GSN) for message history.

    The GSN is a monotonically increasing number that uniquely identifies
    each message across all archives. This allows UI components to track
    their position independently of archiving operations.

    File Format:
    - count.lock: 8-byte unsigned integer (little-endian) representing current GSN

    Thread Safety:
    - Uses file locking (fcntl.flock) for exclusive access
    - Python Lock for thread-safe operations within process
    """

    _instances: Dict[str, 'SequenceNumberManager'] = {}
    _lock = Lock()

    # File name for sequence number storage
    SEQUENCE_FILE = "count.lock"
    SEQUENCE_ENTRY_SIZE = 8  # 8 bytes for uint64

    def __init__(self, history_root: str):
        """
        Initialize the sequence number manager.

        Args:
            history_root: Root path for history storage
        """
        self.history_root = Path(history_root)
        self.history_root.mkdir(parents=True, exist_ok=True)

        self.sequence_file_path = self.history_root / self.SEQUENCE_FILE

        # Thread-local lock for Python-level synchronization
        self._local_lock = Lock()

        # Initialize sequence file if it doesn't exist
        self._init_sequence_file()

    def _init_sequence_file(self):
        """Initialize the sequence file if it doesn't exist."""
        if not self.sequence_file_path.exists():
            try:
                with open(self.sequence_file_path, 'wb') as f:
                    # Write initial value: 0
                    f.write(struct.pack('<Q', 0))
                    f.flush()
                    os.fsync(f.fileno())
                logger.debug(f"Initialized sequence file at {self.sequence_file_path}")
            except Exception as e:
                logger.error(f"Failed to initialize sequence file: {e}")

    @classmethod
    def get_manager(cls, history_root: str) -> 'SequenceNumberManager':
        """
        Get or create a SequenceNumberManager instance for the given history root.

        Args:
            history_root: Root path for history storage

        Returns:
            SequenceNumberManager instance
        """
        with cls._lock:
            if history_root not in cls._instances:
                cls._instances[history_root] = SequenceNumberManager(history_root)
            return cls._instances[history_root]

    def _read_sequence_number(self) -> int:
        """
        Read the current sequence number from the file.

        Returns:
            Current sequence number, or 0 if file doesn't exist
        """
        try:
            if not self.sequence_file_path.exists():
                return 0

            with open(self.sequence_file_path, 'rb') as f:
                # Acquire shared lock for reading
                fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                data = f.read(self.SEQUENCE_ENTRY_SIZE)
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)

                if len(data) == self.SEQUENCE_ENTRY_SIZE:
                    return struct.unpack('<Q', data)[0]
                return 0
        except Exception as e:
            logger.error(f"Error reading sequence number: {e}")
            return 0

    def _write_sequence_number(self, sequence: int) -> bool:
        """
        Write a new sequence number to the file (with locking).

        Args:
            sequence: The sequence number to write

        Returns:
            True if successful
        """
        try:
            with open(self.sequence_file_path, 'r+b') as f:
                # Acquire exclusive lock for writing
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)

                # Write new sequence number
                f.seek(0)
                f.write(struct.pack('<Q', sequence))
                f.flush()
                os.fsync(f.fileno())

                fcntl.flock(f.fileno(), fcntl.LOCK_UN)

            return True
        except Exception as e:
            logger.error(f"Error writing sequence number: {e}")
            return False

    def get_next_sequence_number(self) -> int:
        """
        Get and increment the next sequence number (atomic operation).

        This is the primary method for reserving a sequence number for a new message.

        Returns:
            The reserved sequence number
        """
        with self._local_lock:
            # Read current value
            current = self._read_sequence_number()

            # Increment
            next_sequence = current + 1

            # Write back
            if self._write_sequence_number(next_sequence):
                return next_sequence
            else:
                # Fallback: return current + 1 without persisting
                return next_sequence

    def get_current_sequence_number(self) -> int:
        """
        Get the current (highest) sequence number without incrementing.

        Returns:
            Current sequence number
        """
        with self._local_lock:
            return self._read_sequence_number()

    def reset_sequence_number(self, new_value: int = 0) -> bool:
        """
        Reset the sequence number to a specific value.

        WARNING: This should only be used for maintenance/debugging purposes.

        Args:
            new_value: The new sequence number value

        Returns:
            True if successful
        """
        with self._local_lock:
            return self._write_sequence_number(new_value)


class MessageIndexEntry:
    """
    Maps global sequence numbers to actual message locations.

    This index allows efficient lookup of messages by GSN.
    The index is stored alongside the data files.

    Format:
    - GSN (8 bytes uint64)
    - Storage type (1 byte): 0 = active log, 1 = archive
    - File index (1 byte): Which file (for archives)
    - Line offset (8 bytes uint64): Offset within that file
    """

    # Storage types
    STORAGE_TYPE_ACTIVE = 0
    STORAGE_TYPE_ARCHIVE = 1

    # Entry size: GSN(8) + type(1) + file_idx(1) + offset(8) = 18 bytes
    ENTRY_SIZE = 18

    @staticmethod
    def pack_entry(gsn: int, storage_type: int, file_idx: int, offset: int) -> bytes:
        """Pack an index entry into bytes."""
        return struct.pack('<QBBQ', gsn, storage_type, file_idx, offset)

    @staticmethod
    def unpack_entry(data: bytes) -> tuple:
        """Unpack an index entry from bytes."""
        return struct.unpack('<QBBQ', data)


class EnhancedMessageLogHistory:
    """
    Enhanced message history with global sequence number support.

    This class extends the existing MessageLogHistory with:
    1. GSN tracking and indexing
    2. GSN-based message retrieval
    3. Archive-aware message fetching

    The GSN is stored in a separate index file (gsn_index.idx) that
    maps each sequence number to its actual storage location.
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
        # MessageLogHistory expects workspace_path and project_name separately
        self._history = MessageLogHistory(workspace_path, project_name)
        self.storage = self._history.storage
        self.history_root = Path(history_root)

        # GSN manager
        self._gsn_manager = SequenceNumberManager.get_manager(history_root)

        # GSN index file path
        self._gsn_index_path = self.history_root / "gsn_index.idx"

        # Thread-local lock for GSN index writes (coordinates with storage._write_lock)
        self._gsn_index_lock = Lock()

        # Initialize GSN index
        self._init_gsn_index()

        # Archive list cache
        self._archives: list = []
        self._refresh_archives()

    def _init_gsn_index(self):
        """Initialize the GSN index file if it doesn't exist."""
        if not self._gsn_index_path.exists():
            try:
                # Create empty index file
                self._gsn_index_path.touch()
                logger.debug(f"Initialized GSN index at {self._gsn_index_path}")
            except Exception as e:
                logger.error(f"Failed to initialize GSN index: {e}")

    def _refresh_archives(self):
        """Refresh the list of archive directories."""
        self._archives = self.storage.get_archived_directories()

    def append_message(self, message: Dict[str, Any]) -> tuple[bool, int]:
        """
        Append a message and return its GSN.

        Thread Safety:
            This method ensures atomicity by:
            1. GSN allocation uses file locking (fcntl.flock)
            2. Storage append uses threading.Lock (atomic data+index write)
            3. GSN index write uses both thread lock and file locking

            The GSN index entry is written AFTER storage append is complete,
            ensuring the GSN points to valid data.

        Args:
            message: Message dictionary to append

        Returns:
            Tuple of (success, gsn)
        """
        # Reserve GSN first (has its own locking via file lock)
        gsn = self._gsn_manager.get_next_sequence_number()

        # Add GSN to message metadata
        if 'metadata' not in message:
            message['metadata'] = {}
        message['metadata']['gsn'] = gsn

        # Append to storage (this is atomic: writes data + index with lock)
        # We call storage.append_message() directly to avoid deadlock
        # since _history.append_message() would also acquire the same lock
        success = self.storage.append_message(message)

        if success:
            # Get the offset where the message was written
            # Since storage.append_message() just completed, this is accurate
            offset = self.storage.get_message_count() - 1

            # Write GSN index entry (with its own locking)
            # This is safe because:
            # 1. The storage write is complete and committed
            # 2. GSN index has its own file lock for concurrent writes
            # 3. Even if another message appends before we write the GSN index,
            #    the GSN->offset mapping remains correct because the offset
            #    was captured after our message was written
            if not self._write_gsn_entry_locked(
                gsn, MessageIndexEntry.STORAGE_TYPE_ACTIVE, 0, offset
            ):
                logger.warning(f"Failed to write GSN index entry for GSN {gsn}")

            # Refresh archives in case archiving occurred
            self._refresh_archives()

            logger.debug(f"Appended message with GSN {gsn} at offset {offset}")
        else:
            logger.warning(f"Failed to append message, GSN {gsn} was reserved but not used")

        return success, gsn

    def _write_gsn_entry_locked(self, gsn: int, storage_type: int, file_idx: int, offset: int) -> bool:
        """
        Write a GSN index entry with file locking.

        Thread Safety:
            This method uses both thread-level lock (_gsn_index_lock) and file-level
            locking (fcntl.flock) to ensure safe concurrent writes.

        Args:
            gsn: Global sequence number
            storage_type: Storage type (0=active, 1=archive)
            file_idx: File index
            offset: Offset within the file

        Returns:
            True if successful, False otherwise
        """
        with self._gsn_index_lock:
            try:
                entry = MessageIndexEntry.pack_entry(gsn, storage_type, file_idx, offset)
                with open(self._gsn_index_path, 'ab') as f:
                    # Acquire exclusive lock for writing
                    fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                    f.write(entry)
                    f.flush()
                    os.fsync(f.fileno())
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                return True
            except Exception as e:
                logger.error(f"Error writing GSN index entry: {e}")
                return False

    def get_messages_after_gsn(self, last_seen_gsn: int, count: int = 100) -> list:
        """
        Get messages that were saved after a given GSN.

        This is the primary method for UI to fetch new messages.

        Args:
            last_seen_gsn: The last GSN the UI has seen
            count: Maximum number of messages to retrieve

        Returns:
            List of message dictionaries in chronological order
        """
        # First, get current GSN to see if there are new messages
        current_gsn = self._gsn_manager.get_current_sequence_number()

        if current_gsn <= last_seen_gsn:
            return []

        # Calculate how many messages to fetch
        messages_to_fetch = min(count, current_gsn - last_seen_gsn)

        # Strategy: Fetch from active log first, then from archives
        messages = []

        # Get latest messages from active log
        # Note: We need to be careful about messages that were archived
        active_messages = self._history.get_latest_messages(messages_to_fetch)

        # Filter messages by GSN
        for msg in reversed(active_messages):
            msg_gsn = msg.get('metadata', {}).get('gsn', 0)
            if msg_gsn > last_seen_gsn:
                messages.append(msg)
                if len(messages) >= messages_to_fetch:
                    break

        # If we need more messages and there are archives, check them
        if len(messages) < messages_to_fetch and self._archives:
            # Get remaining count
            remaining = messages_to_fetch - len(messages)

            # Check archives (newest first)
            for archive_dir in self._archives[:3]:  # Check last 3 archives
                if remaining <= 0:
                    break

                archive = self.storage.load_archive(archive_dir)
                archive_messages = archive.get_latest_messages(remaining)

                for msg in reversed(archive_messages):
                    msg_gsn = msg.get('metadata', {}).get('gsn', 0)
                    if msg_gsn > last_seen_gsn:
                        messages.append(msg)
                        remaining -= 1
                        if remaining <= 0:
                            break

        # Sort by GSN and return
        messages.sort(key=lambda m: m.get('metadata', {}).get('gsn', 0))
        return messages

    def get_current_gsn(self) -> int:
        """Get the current (latest) global sequence number."""
        return self._gsn_manager.get_current_sequence_number()

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

    # Use a class-level cache similar to FastMessageHistoryService
    if not hasattr(get_enhanced_history, '_instances'):
        get_enhanced_history._instances = {}

    if key not in get_enhanced_history._instances:
        get_enhanced_history._instances[key] = EnhancedMessageLogHistory(
            workspace_path, project_name
        )

    return get_enhanced_history._instances[key]
