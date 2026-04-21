"""
Unit tests for agent/chat/history/agent_chat_storage.py

Tests message log storage functionality including:
- Constants: Storage constants
- MessageLogStorage: Active log storage
- MessageLogArchive: Archive reader
- MessageLogHistory: Combined history manager
"""

import pytest
import os
import json
import struct
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
from agent.chat.history.agent_chat_storage import (
    Constants,
    MessageLogStorage,
    MessageLogArchive,
    MessageLogHistory,
)


class TestConstants:
    """Tests for Constants class."""

    def test_max_messages_value(self):
        """Constants.MAX_MESSAGES should be 200."""
        assert Constants.MAX_MESSAGES == 200

    def test_archive_threshold_value(self):
        """Constants.ARCHIVE_THRESHOLD should be 100."""
        assert Constants.ARCHIVE_THRESHOLD == 100

    def test_current_dir_value(self):
        """Constants.CURRENT_DIR should be 'current'."""
        assert Constants.CURRENT_DIR == "current"

    def test_data_log_value(self):
        """Constants.DATA_LOG should be 'data.log'."""
        assert Constants.DATA_LOG == "data.log"

    def test_index_file_value(self):
        """Constants.INDEX_FILE should be 'index.idx'."""
        assert Constants.INDEX_FILE == "index.idx"

    def test_index_entry_size_value(self):
        """Constants.INDEX_ENTRY_SIZE should be 8."""
        assert Constants.INDEX_ENTRY_SIZE == 8


class TestMessageLogStorageInit:
    """Tests for MessageLogStorage initialization."""

    def test_init_creates_history_root(self):
        """MessageLogStorage creates history_root directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = MessageLogStorage(tmpdir)
            assert storage.history_root.exists()

    def test_init_creates_current_dir(self):
        """MessageLogStorage creates current directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = MessageLogStorage(tmpdir)
            assert storage.current_dir.exists()

    def test_init_creates_data_log(self):
        """MessageLogStorage creates empty data.log file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = MessageLogStorage(tmpdir)
            assert storage.data_log_path.exists()
            assert storage.data_log_path.stat().st_size == 0

    def test_init_creates_index_file(self):
        """MessageLogStorage creates empty index.idx file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = MessageLogStorage(tmpdir)
            assert storage.index_path.exists()
            assert storage.index_path.stat().st_size == 0


class TestMessageLogStorageAppendMessage:
    """Tests for MessageLogStorage.append_message method."""

    def test_append_message_returns_true(self):
        """append_message returns True on success."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = MessageLogStorage(tmpdir)
            message = {"id": "msg1", "content": "test"}
            result = storage.append_message(message)
            assert result is True

    def test_append_message_updates_line_count(self):
        """append_message updates cached line count."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = MessageLogStorage(tmpdir)
            storage.append_message({"id": "msg1"})
            storage.append_message({"id": "msg2"})
            assert storage._line_count == 2

    def test_append_message_writes_to_data_log(self):
        """append_message writes JSON to data.log."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = MessageLogStorage(tmpdir)
            message = {"id": "msg1", "content": "hello"}
            storage.append_message(message)

            with open(storage.data_log_path, "r") as f:
                line = f.readline()
                loaded = json.loads(line)
                assert loaded["id"] == "msg1"


class TestMessageLogStorageGetMessageCount:
    """Tests for MessageLogStorage.get_message_count method."""

    def test_get_message_count_returns_zero_empty(self):
        """get_message_count returns 0 for empty storage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = MessageLogStorage(tmpdir)
            assert storage.get_message_count() == 0

    def test_get_message_count_returns_correct_count(self):
        """get_message_count returns correct count after appends."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = MessageLogStorage(tmpdir)
            storage.append_message({"id": "1"})
            storage.append_message({"id": "2"})
            storage.append_message({"id": "3"})
            assert storage.get_message_count() == 3


class TestMessageLogStorageGetMessages:
    """Tests for MessageLogStorage.get_messages method."""

    def test_get_messages_returns_empty_for_empty_storage(self):
        """get_messages returns empty list for empty storage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = MessageLogStorage(tmpdir)
            messages = storage.get_messages(0, 10)
            assert messages == []

    def test_get_messages_returns_correct_range(self):
        """get_messages returns correct range of messages."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = MessageLogStorage(tmpdir)
            storage.append_message({"id": "1"})
            storage.append_message({"id": "2"})
            storage.append_message({"id": "3"})
            storage.append_message({"id": "4"})

            messages = storage.get_messages(1, 2)
            assert len(messages) == 2
            assert messages[0]["id"] == "2"
            assert messages[1]["id"] == "3"

    def test_get_messages_handles_out_of_range(self):
        """get_messages handles out of range requests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = MessageLogStorage(tmpdir)
            storage.append_message({"id": "1"})
            messages = storage.get_messages(10, 5)
            assert messages == []


class TestMessageLogStorageGetLatestMessages:
    """Tests for MessageLogStorage.get_latest_messages method."""

    def test_get_latest_messages_returns_most_recent(self):
        """get_latest_messages returns most recent messages."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = MessageLogStorage(tmpdir)
            storage.append_message({"id": "1"})
            storage.append_message({"id": "2"})
            storage.append_message({"id": "3"})

            messages = storage.get_latest_messages(2)
            assert len(messages) == 2
            # Most recent first
            assert messages[0]["id"] == "3"
            assert messages[1]["id"] == "2"


class TestMessageLogArchiveInit:
    """Tests for MessageLogArchive initialization."""

    def test_init_sets_paths(self):
        """MessageLogArchive sets data and index paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            archive_dir = Path(tmpdir) / "archive"
            archive_dir.mkdir()
            (archive_dir / Constants.DATA_LOG).write_bytes(b"")
            (archive_dir / Constants.INDEX_FILE).write_bytes(b"")

            archive = MessageLogArchive(archive_dir)
            assert archive.data_log_path == archive_dir / Constants.DATA_LOG
            assert archive.index_path == archive_dir / Constants.INDEX_FILE


class TestMessageLogArchiveGetLineCount:
    """Tests for MessageLogArchive.get_line_count method."""

    def test_get_line_count_from_index_size(self):
        """get_line_count calculates from index file size."""
        with tempfile.TemporaryDirectory() as tmpdir:
            archive_dir = Path(tmpdir) / "archive"
            archive_dir.mkdir()

            # Write 3 index entries (8 bytes each)
            index_data = struct.pack('<QQQ', 0, 100, 200)
            (archive_dir / Constants.INDEX_FILE).write_bytes(index_data)
            (archive_dir / Constants.DATA_LOG).write_bytes(b"line1\nline2\nline3\n")

            archive = MessageLogArchive(archive_dir)
            assert archive.get_line_count() == 3


class TestMessageLogHistoryInit:
    """Tests for MessageLogHistory initialization."""

    def test_init_creates_storage(self):
        """MessageLogHistory creates MessageLogStorage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            history = MessageLogHistory(tmpdir, "test_project")
            assert history.storage is not None

    def test_init_builds_correct_path(self):
        """MessageLogHistory builds correct history root path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            history = MessageLogHistory(tmpdir, "test_project")
            expected_root = os.path.join(
                tmpdir, "projects", "test_project", "agent", "history"
            )
            assert str(history.storage.history_root) == expected_root


class TestMessageLogHistoryAppendMessage:
    """Tests for MessageLogHistory.append_message method."""

    def test_append_message_calls_storage(self):
        """append_message calls storage.append_message."""
        with tempfile.TemporaryDirectory() as tmpdir:
            history = MessageLogHistory(tmpdir, "test_project")
            message = {"id": "msg1"}
            result = history.append_message(message)
            assert result is True

    def test_append_message_returns_false_on_failure(self):
        """append_message returns False on storage failure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            history = MessageLogHistory(tmpdir, "test_project")

            # Mock storage to fail
            history.storage.append_message = Mock(return_value=False)
            result = history.append_message({"id": "msg1"})
            assert result is False


class TestMessageLogHistoryGetLatestMessages:
    """Tests for MessageLogHistory.get_latest_messages method."""

    def test_get_latest_messages_returns_messages(self):
        """get_latest_messages returns messages from storage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            history = MessageLogHistory(tmpdir, "test_project")
            history.storage.append_message({"id": "1"})
            history.storage.append_message({"id": "2"})

            messages = history.get_latest_messages(2)
            assert len(messages) == 2


class TestMessageLogHistoryGetTotalCount:
    """Tests for MessageLogHistory.get_total_count method."""

    def test_get_total_count_returns_storage_count(self):
        """get_total_count returns storage count when no archives."""
        with tempfile.TemporaryDirectory() as tmpdir:
            history = MessageLogHistory(tmpdir, "test_project")
            history.storage.append_message({"id": "1"})
            history.storage.append_message({"id": "2"})

            count = history.get_total_count()
            assert count == 2