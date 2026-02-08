"""
Message Log Storage - High-performance message history storage.

Design:
1. current/ directory: Contains data.log (messages) and index.idx (8-byte offsets)
2. history/ directory: Contains archived message directories
3. Write: threading.Lock protects "write data + write index" critical section
4. Read: os.pread for concurrent lock-free reads by offset
5. Count: index file size / 8 = committed line count (O(1))
6. Archive: Rename current/ to history/YYYY_MM_DD_HH_MM_SS_mmm/ when full
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
    MAX_MESSAGES = 200  # Maximum messages before archiving
    CURRENT_DIR = "current"
    HISTORY_DIR = "history"
    DATA_FILE = "data.log"
    INDEX_FILE = "index.idx"
    ARCHIVE_PREFIX = ""


class MessageLogStorage:
    """
    High-performance message log storage with log + index file structure.

    Structure:
    - current/
      - data.log: One JSON message per line
      - index.idx: 8-byte unsigned int (offset in data.log) per line
    - history/
      - YYYY_MM_DD_HH_MM_SS_mmm/
        - data.log
        - index.idx

    Performance:
    - Write: Single lock protects data+index write (avoids interleaving)
    - Read: os.pread for lock-free concurrent reads
    - Count: index file size / 8 (O(1))
    - Archive: Atomic directory rename
    """

    def __init__(self, history_root: str):
        """
        Initialize message log storage.

        Args:
            history_root: Root path for history storage
        """
        self.history_root = Path(history_root)
        self.history_root.mkdir(parents=True, exist_ok=True)

        # Current directory (contains data.log and index.idx)
        self.current_dir = self.history_root / Constants.CURRENT_DIR
        self.history_dir = self.history_root / Constants.HISTORY_DIR
        self.history_dir.mkdir(exist_ok=True)

        self.data_path = self.current_dir / Constants.DATA_FILE
        self.index_path = self.current_dir / Constants.INDEX_FILE

        # Write lock (protects data + index write)
        self._write_lock = threading.Lock()

        # Cache for line count
        self._line_count: int = 0
        self._count_lock = threading.Lock()

        # Initialize current directory
        self._init_current_directory()

    def _init_current_directory(self):
        """Initialize current directory if it doesn't exist."""
        if not self.current_dir.exists():
            self.current_dir.mkdir(parents=True, exist_ok=True)
            # Create empty files
            self.data_path.write_bytes(b"")
            self.index_path.write_bytes(b"")
            self._line_count = 0
        else:
            # Ensure both files exist
            if not self.data_path.exists():
                self.data_path.write_bytes(b"")
            if not self.index_path.exists():
                self.index_path.write_bytes(b"")
            # Get line count from index file size
            self._line_count = self._get_line_count_from_index()

    def _get_line_count_from_index(self) -> int:
        """Get line count from index file size (O(1))."""
        try:
            return self.index_path.stat().st_size // 8
        except OSError:
            return 0

    def _escape_message(self, message: Dict[str, Any]) -> str:
        """
        Escape message to single-line JSON format.

        Args:
            message: Message dictionary to escape

        Returns:
            Single-line JSON string with all special characters properly escaped
        """
        json_str = json.dumps(message, ensure_ascii=False, separators=(',', ':'))

        # Validate round-trip
        try:
            parsed = json.loads(json_str)
            if parsed != message:
                logger.warning(f"Round-trip validation failed: {message} != {parsed}")
                json_str = json.dumps(message, ensure_ascii=False)
        except json.JSONDecodeError as e:
            logger.warning(f"Generated invalid JSON: {e}")
            json_str = json.dumps(message, ensure_ascii=False)

        return json_str

    def _unescape_message(self, line: str) -> Optional[Dict[str, Any]]:
        """
        Unescape message from single-line JSON format.

        Args:
            line: Single-line JSON string to parse

        Returns:
            Parsed message dictionary, or None if parsing fails
        """
        line = line.strip()
        if not line:
            return None

        try:
            return json.loads(line)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse message line: {e}. Line preview: {line[:100]}")
            return None

    def _write_index_entry(self, offset: int):
        """
        Write an 8-byte offset to the index file.

        Args:
            offset: Byte offset in data file
        """
        # Pack as unsigned long long (8 bytes, little-endian)
        packed = struct.pack('<Q', offset)
        with open(self.index_path, 'ab') as f:
            f.write(packed)

    def _read_index_entry(self, line_index: int) -> Optional[int]:
        """
        Read an 8-byte offset from the index file.

        Args:
            line_index: Line index to read

        Returns:
            Byte offset in data file, or None if read fails
        """
        try:
            with open(self.index_path, 'rb') as f:
                f.seek(line_index * 8)
                data = f.read(8)
                if len(data) == 8:
                    return struct.unpack('<Q', data)[0]
        except OSError as e:
            logger.error(f"Failed to read index entry at {line_index}: {e}")
        return None

    def _read_data_line(self, offset: int) -> Optional[str]:
        """
        Read a line from data file starting at offset.

        Args:
            offset: Byte offset in data file

        Returns:
            Line content, or None if read fails
        """
        try:
            with open(self.data_path, 'rb') as f:
                f.seek(offset)
                line_bytes = f.readline()
                if line_bytes and line_bytes.endswith(b'\n'):
                    return line_bytes.decode('utf-8').strip()
        except OSError as e:
            logger.error(f"Failed to read data line at offset {offset}: {e}")
        return None

    def _pread_line(self, line_index: int) -> Optional[str]:
        """
        Read a line using os.pread (lock-free, doesn't move file pointer).

        Args:
            line_index: Line index to read

        Returns:
            Line content, or None if read fails
        """
        offset = self._read_index_entry(line_index)
        if offset is None:
            return None

        try:
            with open(self.data_path, 'rb') as f:
                # Read until newline or EOF
                chunk_size = 4096
                data = b""
                file_offset = offset

                while True:
                    chunk = os.pread(f.fileno(), chunk_size, file_offset)
                    if not chunk:
                        break
                    data += chunk
                    if b'\n' in chunk:
                        # Extract only the first line
                        data = data.split(b'\n', 1)[0] + b'\n'
                        break
                    file_offset += len(chunk)

                if data and data.endswith(b'\n'):
                    return data.decode('utf-8').strip()
        except OSError as e:
            logger.error(f"Failed to pread line at index {line_index}: {e}")
        return None

    def append_message(self, message: Dict[str, Any]) -> bool:
        """
        Append a message to the log.

        Args:
            message: Message dictionary to append

        Returns:
            True if successful
        """
        try:
            # Escape message to single line
            line = self._escape_message(message) + '\n'
            line_bytes = line.encode('utf-8')

            # Acquire write lock to protect data + index write
            with self._write_lock:
                # Check if we need to archive BEFORE writing (at MAX_MESSAGES)
                with self._count_lock:
                    should_archive = (self._line_count >= Constants.MAX_MESSAGES)

                if should_archive:
                    self._archive_current()

                # Get current offset
                with open(self.data_path, 'ab') as f:
                    offset = f.tell()

                    # Write data
                    f.write(line_bytes)
                    f.flush()
                    os.fsync(f.fileno())

                # Write index entry
                self._write_index_entry(offset)

                # Update line count
                with self._count_lock:
                    self._line_count += 1

            return True

        except Exception as e:
            logger.error(f"Error appending message: {e}", exc_info=True)
            return False

    def get_message_count(self) -> int:
        """
        Get total message count.

        Returns:
            Number of messages in current log
        """
        with self._count_lock:
            return self._line_count

    def get_messages(self, start: int, count: int) -> List[Dict[str, Any]]:
        """
        Get messages by range using index file.

        Args:
            start: Starting line index (0-based)
            count: Number of messages to retrieve

        Returns:
            List of message dictionaries
        """
        if start < 0 or count <= 0:
            return []

        messages = []

        with self._count_lock:
            end = min(start + count, self._line_count)

        try:
            for i in range(start, end):
                # Use pread for lock-free concurrent reads
                line = self._pread_line(i)
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
            List of messages, most recent first
        """
        with self._count_lock:
            total = self._line_count

        if total == 0:
            return []

        start = max(0, total - count)
        messages = self.get_messages(start, count)
        return list(reversed(messages))

    def _archive_current(self):
        """Archive current directory to history directory."""
        try:
            # Create archive name
            timestamp = datetime.now().strftime("%Y_%m_%d_%H_%M_%S_%f")[:-3]
            archive_name = timestamp

            # Archive path
            archive_path = self.history_dir / archive_name

            # Rename current directory to archive (atomic on Unix)
            if self.current_dir.exists():
                self.current_dir.rename(archive_path)

            # Create new current directory
            self._init_current_directory()

            logger.info(f"Archived messages to {archive_name}")

        except Exception as e:
            logger.error(f"Error archiving messages: {e}", exc_info=True)

    def get_archived_directories(self) -> List[Path]:
        """Get list of archived directories sorted by timestamp (newest first)."""
        try:
            archives = list(self.history_dir.glob("*"))
            archives.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            return [a for a in archives if a.is_dir()]
        except Exception as e:
            logger.error(f"Error listing archives: {e}")
            return []

    def load_archive(self, archive_path: Path) -> 'MessageLogArchive':
        """Load an archive for reading."""
        return MessageLogArchive(archive_path)

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
    Read-only access to archived message logs.

    Uses the same log + index structure as active log.
    """

    def __init__(self, archive_dir: Path):
        """
        Initialize archive reader.

        Args:
            archive_dir: Path to the archive directory
        """
        self.archive_dir = archive_dir
        self.data_path = archive_dir / Constants.DATA_FILE
        self.index_path = archive_dir / Constants.INDEX_FILE

        # Get line count from index file size
        self._line_count = self._get_line_count_from_index()

    def _get_line_count_from_index(self) -> int:
        """Get line count from index file size."""
        try:
            return self.index_path.stat().st_size // 8
        except OSError:
            return 0

    def get_line_count(self) -> int:
        """Get total line count in archive."""
        return self._line_count

    def get_messages(self, start: int, count: int) -> List[Dict[str, Any]]:
        """Get messages from archive by range."""
        if start < 0 or count <= 0:
            return []

        if start >= self._line_count:
            return []

        messages = []
        end = min(start + count, self._line_count)

        try:
            for i in range(start, end):
                offset = self._read_index_entry(i)
                if offset is not None:
                    line = self._read_data_line(offset)
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

    def _read_index_entry(self, line_index: int) -> Optional[int]:
        """Read an 8-byte offset from the index file."""
        try:
            with open(self.index_path, 'rb') as f:
                f.seek(line_index * 8)
                data = f.read(8)
                if len(data) == 8:
                    return struct.unpack('<Q', data)[0]
        except OSError:
            pass
        return None

    def _read_data_line(self, offset: int) -> Optional[str]:
        """Read a line from data file starting at offset."""
        try:
            with open(self.data_path, 'rb') as f:
                f.seek(offset)
                line_bytes = f.readline()
                if line_bytes and line_bytes.endswith(b'\n'):
                    return line_bytes.decode('utf-8').strip()
        except OSError:
            pass
        return None


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

        # Messages were loaded in reverse order (archives first), reverse back
        return list(reversed(messages))

    def append_message(self, message: Dict[str, Any]) -> bool:
        """Append a new message to the active log."""
        result = self.storage.append_message(message)
        if result:
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
        Attempt to recover from corrupted storage.

        Returns:
            True if recovery was successful, False otherwise
        """
        try:
            logger.info(f"Recovering storage for project '{self.project_name}'")
            # Reinitialize current directory
            self.storage._init_current_directory()
            self._refresh_archives()
            logger.info(f"Recovery completed for project '{self.project_name}'")
            return True
        except Exception as e:
            logger.error(f"Error during recovery: {e}")
            return False
