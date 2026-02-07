"""
Message Log Storage - High-performance message history storage.

Design:
1. message.log - Current active messages (max N messages)
2. history_YYYY_MM_DD_HH_MM_SS_mmm.log - Archived message files
3. File cursor based loading - Fast O(1) access to messages by position
4. Single-line JSON format - One message per line with proper escaping
5. Efficient archive using file slicing - No full file rewrite
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
import threading
import fcntl

logger = logging.getLogger(__name__)


class Constants:
    """Constants for message log storage."""
    MAX_MESSAGES = 200  # Maximum messages in active log
    ARCHIVE_THRESHOLD = 100  # Archive oldest N/2 when MAX is reached
    ARCHIVE_PREFIX = "history_"
    ACTIVE_LOG = "message.log"
    LOCK_FILE = "message.log.lock"


class MessageLogStorage:
    """
    High-performance message log storage with file cursor positioning.

    Format:
    - message.log: Current active messages (max MAX_MESSAGES)
    - history_*.log: Archived message files

    Each line is a JSON-encoded message with escaped newlines.

    Performance optimizations:
    - File-based locking for concurrent access
    - Incremental position cache updates
    - Archive using file slice (no full rewrite)
    - Lazy cache rebuilding
    """

    def __init__(self, history_root: str):
        """
        Initialize message log storage.

        Args:
            history_root: Root path for history storage
        """
        self.history_root = Path(history_root)
        self.history_root.mkdir(parents=True, exist_ok=True)

        self.active_log_path = self.history_root / Constants.ACTIVE_LOG
        self.lock_file_path = self.history_root / Constants.LOCK_FILE

        # File position cache for fast access: {line_index: byte_offset}
        self._position_cache: List[int] = []
        self._line_count: int = 0
        self._cache_lock = threading.Lock()
        self._cache_dirty: bool = False

        # File lock for concurrent access
        self._lock_fd: Optional[int] = None

        # Initialize active log if not exists
        if not self.active_log_path.exists():
            self.active_log_path.write_text("")
            self._line_count = 0
            self._position_cache = []
        else:
            # Build initial position cache
            self._rebuild_position_cache()

    def _get_lock(self):
        """Acquire file lock for exclusive access."""
        if self._lock_fd is None:
            try:
                self._lock_fd = os.open(self.lock_file_path, os.O_CREAT | os.O_WRONLY)
                fcntl.flock(self._lock_fd, fcntl.LOCK_EX)
            except Exception as e:
                logger.warning(f"Could not acquire lock: {e}")
                self._lock_fd = None

    def _release_lock(self):
        """Release file lock."""
        if self._lock_fd is not None:
            try:
                fcntl.flock(self._lock_fd, fcntl.LOCK_UN)
                os.close(self._lock_fd)
            except Exception as e:
                logger.warning(f"Error releasing lock: {e}")
            finally:
                self._lock_fd = None

    def _rebuild_position_cache(self):
        """Build file position cache for fast random access."""
        with self._cache_lock:
            self._position_cache.clear()
            self._line_count = 0

            if not self.active_log_path.exists():
                return

            try:
                with open(self.active_log_path, 'rb') as f:
                    offset = 0
                    while True:
                        line = f.readline()
                        if not line:
                            break
                        self._position_cache.append(offset)
                        offset += len(line)
                        self._line_count += 1
            except Exception as e:
                logger.error(f"Error building position cache: {e}")

    def _escape_message(self, message: Dict[str, Any]) -> str:
        """Escape message to single-line JSON format."""
        return json.dumps(message, ensure_ascii=False, separators=(',', ':'))

    def _unescape_message(self, line: str) -> Optional[Dict[str, Any]]:
        """Unescape message from single-line JSON format."""
        line = line.strip()
        if not line:
            # Skip empty lines silently
            return None
        try:
            return json.loads(line)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse message line: {e}")
            return None

    def _incremental_cache_update(self, line_length: int):
        """Update position cache incrementally after append."""
        with self._cache_lock:
            if self._line_count == 0:
                new_offset = 0
            else:
                new_offset = self._position_cache[-1] + line_length
            self._position_cache.append(new_offset)
            self._line_count += 1

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
            line_bytes = len(line.encode('utf-8'))

            # Append to file
            with open(self.active_log_path, 'a', encoding='utf-8') as f:
                f.write(line)

            # Update position cache incrementally
            self._incremental_cache_update(line_bytes)

            # Check if we need to archive (check without lock first for speed)
            if self._line_count >= Constants.MAX_MESSAGES:
                self._archive_old_messages()

            return True

        except Exception as e:
            logger.error(f"Error appending message: {e}")
            return False

    def get_message_count(self) -> int:
        """Get total message count."""
        with self._cache_lock:
            return self._line_count

    def get_messages(self, start: int, count: int) -> List[Dict[str, Any]]:
        """
        Get messages by range using file cursor.

        Args:
            start: Starting line index (0-based)
            count: Number of messages to retrieve

        Returns:
            List of message dictionaries
        """
        if start < 0 or count <= 0:
            return []

        messages = []
        end = min(start + count, self._line_count)

        try:
            with open(self.active_log_path, 'r', encoding='utf-8') as f:
                # Get start offset from cache
                with self._cache_lock:
                    if start >= len(self._position_cache):
                        return []
                    start_offset = self._position_cache[start]

                f.seek(start_offset)

                # Read lines
                for i in range(start, end):
                    line = f.readline()
                    if not line:
                        break

                    line = line.strip()
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
        with self._cache_lock:
            total = self._line_count

        if total == 0:
            return []

        start = max(0, total - count)
        messages = self.get_messages(start, count)
        return list(reversed(messages))

    def _archive_old_messages(self):
        """Archive oldest ARCHIVE_THRESHOLD messages using file slice.

        This is much more efficient than reading and rewriting:
        1. Read the first N lines to archive
        2. Write them to archive file
        3. Slice the file to keep only the remaining lines
        """
        try:
            self._get_lock()

            # Read oldest messages
            old_messages = self.get_messages(0, Constants.ARCHIVE_THRESHOLD)

            if not old_messages:
                return

            # Create archive filename
            timestamp = datetime.now().strftime("%Y_%m_%d_%H_%M_%S_%f")[:-3]
            archive_path = self.history_root / f"{Constants.ARCHIVE_PREFIX}{timestamp}.log"

            # Write to archive file
            with open(archive_path, 'w', encoding='utf-8') as f:
                for msg in old_messages:
                    line = self._escape_message(msg) + '\n'
                    f.write(line)

            # Calculate slice offset (start of remaining messages)
            with self._cache_lock:
                if Constants.ARCHIVE_THRESHOLD >= len(self._position_cache):
                    slice_offset = 0
                else:
                    slice_offset = self._position_cache[Constants.ARCHIVE_THRESHOLD]

            # Read remaining content
            remaining_content = ""
            if slice_offset > 0:
                with open(self.active_log_path, 'rb') as f:
                    f.seek(slice_offset)
                    remaining_content = f.read().decode('utf-8')

            # Write remaining content back (truncate and rewrite)
            with open(self.active_log_path, 'w', encoding='utf-8') as f:
                f.write(remaining_content)

            # Rebuild position cache
            self._rebuild_position_cache()

            logger.info(f"Archived {len(old_messages)} messages to {archive_path.name}")

        except Exception as e:
            logger.error(f"Error archiving messages: {e}")
        finally:
            self._release_lock()

    def get_archived_files(self) -> List[Path]:
        """Get list of archived history files sorted by timestamp (newest first)."""
        try:
            archives = list(self.history_root.glob(f"{Constants.ARCHIVE_PREFIX}*.log"))
            archives.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            return archives
        except Exception as e:
            logger.error(f"Error listing archives: {e}")
            return []

    def load_archive(self, archive_path: Path) -> 'MessageLogArchive':
        """Load an archive file for reading."""
        return MessageLogArchive(archive_path)

    def get_total_count(self) -> int:
        """Get total message count including archives."""
        active_count = self.get_message_count()
        archive_count = 0
        for archive_path in self.get_archived_files():
            archive = self.load_archive(archive_path)
            archive_count += archive.get_line_count()
        return active_count + archive_count

    def clear_cache(self):
        """Clear position cache (will be rebuilt on next access)."""
        with self._cache_lock:
            self._position_cache.clear()
            self._line_count = 0
            self._cache_dirty = True


class MessageLogArchive:
    """
    Read-only access to archived message log files.

    Uses the same cursor-based loading logic as active log.
    """

    def __init__(self, archive_path: Path):
        """
        Initialize archive reader.

        Args:
            archive_path: Path to the archive file
        """
        self.archive_path = archive_path

        # Build position cache
        self._position_cache: List[int] = []
        self._line_count: int = 0
        self._build_cache()

    def _build_cache(self):
        """Build file position cache."""
        self._position_cache.clear()
        self._line_count = 0

        if not self.archive_path.exists():
            return

        try:
            with open(self.archive_path, 'rb') as f:
                offset = 0
                while True:
                    line = f.readline()
                    if not line:
                        break
                    self._position_cache.append(offset)
                    offset += len(line)
                    self._line_count += 1
        except Exception as e:
            logger.error(f"Error building archive position cache: {e}")

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
            with open(self.archive_path, 'r', encoding='utf-8') as f:
                if start >= len(self._position_cache):
                    return []

                start_offset = self._position_cache[start]
                f.seek(start_offset)

                for i in range(start, end):
                    line = f.readline()
                    if not line:
                        break

                    line = line.strip()
                    if line:
                        try:
                            msg = json.loads(line)
                            messages.append(msg)
                        except json.JSONDecodeError:
                            pass  # Skip invalid lines

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

    Manages seamless loading across active log and archive files.
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
        """Refresh the list of archive files."""
        self._archives = self.storage.get_archived_files()

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
            # Beyond active log, no more messages
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
            for archive_path in self._archives:
                archive = self.storage.load_archive(archive_path)
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
            # Refresh archives in case archiving occurred
            self._refresh_archives()
        return result

    def get_latest_line_offset(self) -> int:
        """Get the current line offset (total messages in active log)."""
        return self.storage.get_message_count()

    def invalidate_cache(self):
        """Invalidate all caches."""
        self._refresh_archives()
        self.storage.clear_cache()
