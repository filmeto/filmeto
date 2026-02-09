"""
Message Log Storage - High-performance message history storage.

Design:
1. current/data.log - Current active message data
2. current/index.idx - Fixed 8-byte offsets for fast O(1) access
3. history_YYYY_MM_DD_HH_MM_SS_mmm/ - Archived message directories

Index file format:
- Fixed 8-byte unsigned integers (little-endian)
- Position N (byte N*8) contains the offset of message N in data.log
- Line N can be read by reading offset at index[N*8] and index[(N+1)*8]

Concurrent strategy:
- Write: threading.Lock protects "write data + write index" critical section
- Read: os.pread() for concurrent offset-based reading (no lock needed)
- Count: O(1) by index file size / 8
"""

import os
import json
import logging
import struct
import threading
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)


class Constants:
    """Constants for message log storage."""
    MAX_MESSAGES = 200  # Maximum messages in active log
    ARCHIVE_THRESHOLD = 100  # Archive oldest N/2 when MAX is reached
    CURRENT_DIR = "current"
    DATA_LOG = "data.log"
    INDEX_FILE = "index.idx"
    ARCHIVE_PREFIX = "history_"
    INDEX_ENTRY_SIZE = 8  # 8 bytes per offset (uint64)


class MessageLogStorage:
    """
    High-performance message log storage with separate data and index files.

    Format:
    - current/data.log: JSON message data, one per line
    - current/index.idx: Fixed 8-byte offsets for O(1) random access

    Performance optimizations:
    - Separate index file for O(1) position lookup
    - os.pread() for lock-free concurrent reads
    - threading.Lock for atomic write operations
    - Directory-based archiving
    """

    def __init__(self, history_root: str):
        """
        Initialize message log storage.

        Args:
            history_root: Root path for history storage
        """
        self.history_root = Path(history_root)
        self.history_root.mkdir(parents=True, exist_ok=True)

        self.current_dir = self.history_root / Constants.CURRENT_DIR
        self.data_log_path = self.current_dir / Constants.DATA_LOG
        self.index_path = self.current_dir / Constants.INDEX_FILE

        # Write lock for atomic "write data + write index" operations
        self._write_lock = threading.Lock()

        # Initialize current directory
        self._init_current_directory()

        # Cached line count (updated on writes)
        self._line_count: int = self._load_line_count()

    def _init_current_directory(self):
        """Initialize the current directory if it doesn't exist."""
        if not self.current_dir.exists():
            self.current_dir.mkdir(parents=True, exist_ok=True)

        # Initialize data log if not exists
        if not self.data_log_path.exists():
            self.data_log_path.write_bytes(b"")

        # Initialize index file if not exists
        if not self.index_path.exists():
            self.index_path.write_bytes(b"")

    def _load_line_count(self) -> int:
        """Load line count from index file size (O(1) operation)."""
        try:
            index_size = self.index_path.stat().st_size
            return index_size // Constants.INDEX_ENTRY_SIZE
        except Exception:
            return 0

    def _append_index(self, offset: int):
        """
        Append an offset to the index file.

        Args:
            offset: Byte offset in data.log
        """
        # Pack offset as 8-byte little-endian unsigned integer
        packed = struct.pack('<Q', offset)
        with open(self.index_path, 'ab') as f:
            f.write(packed)
            f.flush()
            os.fsync(f.fileno())

    def _get_offset(self, line_index: int) -> Optional[int]:
        """
        Get the byte offset for a given line index using pread.

        Args:
            line_index: Line index (0-based)

        Returns:
            Byte offset in data.log, or None if index out of range
        """
        if line_index < 0:
            return None

        offset_position = line_index * Constants.INDEX_ENTRY_SIZE

        try:
            with open(self.index_path, 'rb') as f:
                # Use pread to read without moving file pointer
                data = os.pread(f.fileno(), Constants.INDEX_ENTRY_SIZE, offset_position)
                if len(data) != Constants.INDEX_ENTRY_SIZE:
                    return None
                return struct.unpack('<Q', data)[0]
        except Exception:
            return None

    def _get_offsets(self, start: int, count: int) -> List[int]:
        """
        Get multiple byte offsets using pread.

        Args:
            start: Starting line index
            count: Number of offsets to retrieve

        Returns:
            List of byte offsets
        """
        offsets = []
        for i in range(start, start + count):
            offset = self._get_offset(i)
            if offset is None:
                break
            offsets.append(offset)
        return offsets

    def _escape_message(self, message: Dict[str, Any]) -> str:
        """Escape message to single-line JSON format."""
        json_str = json.dumps(message, ensure_ascii=False, separators=(',', ':'))
        # Validate that the JSON can be parsed back
        try:
            json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.warning(f"Generated invalid JSON, attempting to fix: {e}")
            json_str = json.dumps(message, ensure_ascii=False)
        return json_str

    def _unescape_message(self, line: str) -> Optional[Dict[str, Any]]:
        """Unescape message from single-line JSON format."""
        line = line.strip()
        if not line:
            return None
        try:
            return json.loads(line)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse message line: {e}. Line preview: {line[:100]}")
            return None

    def _read_line_at_offset(self, offset: int) -> Optional[str]:
        """
        Read a single line starting at the given offset using pread.

        Args:
            offset: Byte offset in data.log

        Returns:
            Line content (without newline), or None if read fails
        """
        try:
            with open(self.data_log_path, 'rb') as f:
                # Read a reasonable chunk (max 64KB per line)
                chunk = os.pread(f.fileno(), 65536, offset)
                if not chunk:
                    return None

                # Find the newline
                newline_pos = chunk.find(b'\n')
                if newline_pos == -1:
                    # No newline found, read until EOF
                    return chunk.decode('utf-8').strip()

                line_bytes = chunk[:newline_pos]
                return line_bytes.decode('utf-8').strip()
        except Exception as e:
            logger.error(f"Error reading line at offset {offset}: {e}")
            return None

    def append_message(self, message: Dict[str, Any]) -> bool:
        """
        Append a message to the log.

        This method is thread-safe. The write lock ensures atomic
        "write data + write index" operations.

        Args:
            message: Message dictionary to append

        Returns:
            True if successful
        """
        with self._write_lock:
            try:
                # Escape message to single line
                line = self._escape_message(message) + '\n'
                line_bytes = line.encode('utf-8')

                # Get current data.log size (offset for this message)
                with open(self.data_log_path, 'rb') as f:
                    offset = f.seek(0, os.SEEK_END)

                # Append to data.log
                with open(self.data_log_path, 'ab') as f:
                    f.write(line_bytes)
                    f.flush()
                    os.fsync(f.fileno())

                # Append offset to index
                self._append_index(offset)

                # Update cached line count
                self._line_count += 1

                # Check if we need to archive (only when exceeding MAX_MESSAGES)
                if self._line_count > Constants.MAX_MESSAGES:
                    self._archive_old_messages()

                return True

            except Exception as e:
                logger.error(f"Error appending message: {e}", exc_info=True)
                return False

    def get_message_count(self) -> int:
        """
        Get total message count (O(1) operation).

        Returns:
            Number of messages in the active log
        """
        return self._line_count

    def get_messages(self, start: int, count: int) -> List[Dict[str, Any]]:
        """
        Get messages by range using index-based lookups.

        This method uses os.pread() for lock-free concurrent reads.

        Args:
            start: Starting line index (0-based)
            count: Number of messages to retrieve

        Returns:
            List of message dictionaries
        """
        if start < 0 or count <= 0:
            return []

        if start >= self._line_count:
            return []

        end = min(start + count, self._line_count)
        messages = []

        try:
            # Get offsets for all requested lines
            offsets = self._get_offsets(start, end - start)

            for i, offset in enumerate(offsets):
                line = self._read_line_at_offset(offset)
                if line:
                    msg = self._unescape_message(line)
                    if msg:
                        messages.append(msg)

        except Exception as e:
            logger.error(f"Error reading messages: {e}")

        return messages

    def get_latest_messages(self, count: int = 20) -> List[Dict[str, Any]]:
        """
        Get latest N messages.

        Args:
            count: Number of latest messages to retrieve

        Returns:
            List of message dictionaries, most recent first
        """
        if self._line_count == 0:
            return []

        start = max(0, self._line_count - count)
        messages = self.get_messages(start, count)
        return list(reversed(messages))

    def _archive_old_messages(self):
        """
        Archive oldest MAX_MESSAGES messages to keep current directory small.

        Creates a new history directory with the archived messages and
        resets the current directory with remaining messages.

        Note: This method should only be called while holding _write_lock.
        """
        try:
            # When count exceeds MAX_MESSAGES, archive MAX_MESSAGES oldest messages
            # This leaves only the newest messages in current
            messages_to_archive = min(Constants.MAX_MESSAGES, self._line_count)

            # Read oldest messages to archive
            old_messages = self.get_messages(0, messages_to_archive)

            if not old_messages:
                return

            # Create archive directory
            timestamp = datetime.now().strftime("%Y_%m_%d_%H_%M_%S_%f")[:-3]
            archive_dir = self.history_root / f"{Constants.ARCHIVE_PREFIX}{timestamp}"
            archive_dir.mkdir(parents=True, exist_ok=True)

            archive_data_path = archive_dir / Constants.DATA_LOG
            archive_index_path = archive_dir / Constants.INDEX_FILE

            # Write archived data.log
            with open(archive_data_path, 'w', encoding='utf-8') as f:
                for msg in old_messages:
                    line = self._escape_message(msg) + '\n'
                    f.write(line)
                f.flush()
                os.fsync(f.fileno())

            # Write archived index.idx
            with open(archive_index_path, 'wb') as f:
                offset = 0
                for msg in old_messages:
                    line = self._escape_message(msg) + '\n'
                    packed = struct.pack('<Q', offset)
                    f.write(packed)
                    offset += len(line.encode('utf-8'))
                f.flush()
                os.fsync(f.fileno())

            # Calculate remaining messages
            remaining_start = messages_to_archive
            remaining_count = self._line_count - remaining_start

            # Create new current directory
            new_current_dir = self.history_root / f"{Constants.CURRENT_DIR}.new"
            new_current_dir.mkdir(parents=True, exist_ok=True)

            new_data_path = new_current_dir / Constants.DATA_LOG
            new_index_path = new_current_dir / Constants.INDEX_FILE

            # Write remaining messages to new current
            remaining_messages = self.get_messages(remaining_start, remaining_count)

            with open(new_data_path, 'w', encoding='utf-8') as f:
                for msg in remaining_messages:
                    line = self._escape_message(msg) + '\n'
                    f.write(line)
                f.flush()
                os.fsync(f.fileno())

            with open(new_index_path, 'wb') as f:
                offset = 0
                for msg in remaining_messages:
                    line = self._escape_message(msg) + '\n'
                    packed = struct.pack('<Q', offset)
                    f.write(packed)
                    offset += len(line.encode('utf-8'))
                f.flush()
                os.fsync(f.fileno())

            # Atomic rename: replace old current with new
            # First remove old current directory
            import shutil
            if self.current_dir.exists():
                shutil.rmtree(self.current_dir)
            new_current_dir.replace(self.current_dir)

            # Update cached line count
            self._line_count = remaining_count

            logger.info(f"Archived {len(old_messages)} messages to {archive_dir.name}")

        except Exception as e:
            logger.error(f"Error archiving messages: {e}", exc_info=True)

    def get_archived_directories(self) -> List[Path]:
        """Get list of archived directories sorted by timestamp (newest first)."""
        try:
            archives = list(self.history_root.glob(f"{Constants.ARCHIVE_PREFIX}*"))
            archives = [a for a in archives if a.is_dir()]
            archives.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            return archives
        except Exception as e:
            logger.error(f"Error listing archives: {e}")
            return []

    def load_archive(self, archive_dir: Path) -> 'MessageLogArchive':
        """Load an archive directory for reading."""
        return MessageLogArchive(archive_dir)

    def get_total_count(self) -> int:
        """Get total message count including archives."""
        active_count = self.get_message_count()
        archive_count = 0
        for archive_dir in self.get_archived_directories():
            archive = self.load_archive(archive_dir)
            archive_count += archive.get_line_count()
        return active_count + archive_count


class MessageLogArchive:
    """
    Read-only access to archived message log directories.

    Uses the same index-based reading logic as active log.
    """

    def __init__(self, archive_dir: Path):
        """
        Initialize archive reader.

        Args:
            archive_dir: Path to the archive directory
        """
        self.archive_dir = archive_dir
        self.data_log_path = archive_dir / Constants.DATA_LOG
        self.index_path = archive_dir / Constants.INDEX_FILE
        self._line_count: int = self._load_line_count()

    def _load_line_count(self) -> int:
        """Load line count from index file size (O(1) operation)."""
        try:
            index_size = self.index_path.stat().st_size
            return index_size // Constants.INDEX_ENTRY_SIZE
        except Exception:
            return 0

    def get_line_count(self) -> int:
        """Get total line count in archive."""
        return self._line_count

    def _get_offset(self, line_index: int) -> Optional[int]:
        """Get the byte offset for a given line index."""
        if line_index < 0:
            return None

        offset_position = line_index * Constants.INDEX_ENTRY_SIZE

        try:
            with open(self.index_path, 'rb') as f:
                data = os.pread(f.fileno(), Constants.INDEX_ENTRY_SIZE, offset_position)
                if len(data) != Constants.INDEX_ENTRY_SIZE:
                    return None
                return struct.unpack('<Q', data)[0]
        except Exception:
            return None

    def _read_line_at_offset(self, offset: int) -> Optional[str]:
        """Read a single line starting at the given offset using pread."""
        try:
            with open(self.data_log_path, 'rb') as f:
                chunk = os.pread(f.fileno(), 65536, offset)
                if not chunk:
                    return None

                newline_pos = chunk.find(b'\n')
                if newline_pos == -1:
                    return chunk.decode('utf-8').strip()

                line_bytes = chunk[:newline_pos]
                return line_bytes.decode('utf-8').strip()
        except Exception:
            return None

    def get_messages(self, start: int, count: int) -> List[Dict[str, Any]]:
        """Get messages from archive by range."""
        if start < 0 or count <= 0:
            return []

        if start >= self._line_count:
            return []

        end = min(start + count, self._line_count)
        messages = []

        try:
            for i in range(start, end):
                offset = self._get_offset(i)
                if offset is None:
                    break

                line = self._read_line_at_offset(offset)
                if line:
                    try:
                        msg = json.loads(line)
                        messages.append(msg)
                    except json.JSONDecodeError:
                        pass

        except Exception as e:
            logger.error(f"Error reading archive: {e}")

        return messages

    def get_latest_messages(self, count: int = 20) -> List[Dict[str, Any]]:
        """Get latest N messages from archive (most recent first)."""
        if self._line_count == 0:
            return []

        start = max(0, self._line_count - count)
        messages = self.get_messages(start, count)
        return list(reversed(messages))


class MessageLogHistory:
    """
    Message log history manager combining active log and archives.

    Manages seamless loading across active log and archive directories.
    """

    def __init__(self, workspace_path: str, project_name: str):
        """
        Initialize message log history.

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

        self.storage = MessageLogStorage(history_root)

        # Archive list cache
        self._archives: List[Path] = []
        self._refresh_archives()

    def _refresh_archives(self):
        """Refresh the list of archive directories."""
        self._archives = self.storage.get_archived_directories()

    def get_total_count(self) -> int:
        """Get total message count across all files."""
        return self.storage.get_total_count()

    def get_latest_messages(self, count: int = 20) -> List[Dict[str, Any]]:
        """
        Get latest N messages from active log.

        Args:
            count: Number of messages to retrieve

        Returns:
            List of messages, most recent first
        """
        return self.storage.get_latest_messages(count)

    def get_messages_after(self, line_offset: int, count: int) -> List[Dict[str, Any]]:
        """
        Get messages after a given position in active log.

        Args:
            line_offset: Line offset in active log
            count: Number of messages to retrieve

        Returns:
            List of messages in chronological order
        """
        active_count = self.storage.get_message_count()

        if line_offset >= active_count:
            return []

        end = min(line_offset + count, active_count)
        return self.storage.get_messages(line_offset, end - line_offset)

    def get_messages_before(self, line_offset: int, count: int) -> List[Dict[str, Any]]:
        """
        Get messages before a given position.

        First tries active log, then archives if needed.

        Args:
            line_offset: Starting line offset (exclusive)
            count: Number of messages to retrieve

        Returns:
            List of messages in chronological order
        """
        messages = []
        remaining = count

        # First get from active log
        if line_offset > 0:
            start = max(0, line_offset - remaining)
            from_active = self.storage.get_messages(start, line_offset - start)

            if from_active:
                messages.extend(from_active)
                remaining -= len(from_active)

        # If we still need more, get from archives
        if remaining > 0 and self._archives:
            for archive_dir in self._archives:
                archive = self.storage.load_archive(archive_dir)
                archive_count = archive.get_line_count()

                if archive_count > 0:
                    start = max(0, archive_count - remaining)
                    from_archive = archive.get_messages(start, remaining)

                    if from_archive:
                        messages.extend(reversed(from_archive))
                        remaining -= len(from_archive)

                    if remaining <= 0:
                        break

        # Messages were loaded in reverse order, reverse back
        return list(reversed(messages))

    def append_message(self, message: Dict[str, Any]) -> bool:
        """Append a new message to the active log."""
        result = self.storage.append_message(message)
        if result:
            # Refresh archives in case archiving occurred
            self._refresh_archives()
        return result

    def get_latest_line_offset(self) -> int:
        """Get the current line offset (total messages in active log)."""
        return self.storage.get_message_count()

    def invalidate_cache(self):
        """Invalidate all caches."""
        self._refresh_archives()

    def recover_from_corruption(self) -> bool:
        """
        Attempt to recover from corrupted data files.

        Since the new design uses separate index and data files with
        os.pread for reading, corruption is less likely. This method
        rebuilds the index file from the data log if needed.

        Returns:
            True if recovery was successful, False otherwise
        """
        try:
            logger.info(f"Attempting to recover storage for project '{self.project_name}'")
            history_root = self.storage.history_root
            data_path = self.storage.data_log_path
            index_path = self.storage.index_path

            # Rebuild index from data.log
            if data_path.exists():
                offsets = []
                offset = 0

                with open(data_path, 'rb') as f:
                    while True:
                        line_start = f.tell()
                        line = f.readline()
                        if not line:
                            break

                        # Only add complete lines ending with newline
                        if line.endswith(b'\n'):
                            offsets.append(line_start)
                            offset = f.tell()

                # Write rebuilt index
                with open(index_path, 'wb') as f:
                    for off in offsets:
                        packed = struct.pack('<Q', off)
                        f.write(packed)
                    f.flush()
                    os.fsync(f.fileno())

                # Update cached line count
                self.storage._line_count = len(offsets)

                logger.info(f"Recovery completed: rebuilt index with {len(offsets)} entries")
                return True

        except Exception as e:
            logger.error(f"Error during recovery: {e}")
            return False
