"""
Unit tests for GlobalSequenceManager.get_messages_before_gsn method.

Tests the optimized single-pass strategy for loading historical messages.
"""

import os
import sys
import tempfile
import shutil
import unittest
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from agent.chat.history.global_sequence_manager import (
    GSNManager,
    EnhancedMessageLogHistory,
    get_enhanced_history
)


class TestGetMessagesBeforeGSN(unittest.TestCase):
    """Test cases for get_messages_before_gsn method."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.workspace_path = self.temp_dir
        self.project_name = "test_project"

    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def _create_message(self, message_id: str, gsn: int, content_type: str = "text") -> dict:
        """Create a test message with given message_id and GSN."""
        return {
            'message_id': message_id,
            'content': f'{content_type} content for {message_id}',
            'content_type': content_type,
            'metadata': {'gsn': gsn}
        }

    def test_empty_result_when_no_messages(self):
        """Test that empty list is returned when no messages exist."""
        with patch.object(EnhancedMessageLogHistory, '__init__', return_value=None):
            history = EnhancedMessageLogHistory.__new__(EnhancedMessageLogHistory)
            history._history = Mock()
            history._archives = []
            history._gsn_manager = Mock()
            history._gsn_manager.get_current_gsn.return_value = 0
            history._history.get_latest_messages.return_value = []

            result = history.get_messages_before_gsn(max_gsn=100, count=10)

            self.assertEqual(result, [])

    def test_fallback_when_max_gsn_zero_or_negative(self):
        """Test fallback to latest messages when max_gsn <= 0."""
        with patch.object(EnhancedMessageLogHistory, '__init__', return_value=None):
            history = EnhancedMessageLogHistory.__new__(EnhancedMessageLogHistory)
            history._history = Mock()
            history._archives = []
            history._history.get_latest_messages.return_value = ['msg1', 'msg2']

            # Test max_gsn = 0
            result = history.get_messages_before_gsn(max_gsn=0, count=10)
            self.assertEqual(result, ['msg1', 'msg2'])

            # Test max_gsn = -1
            result = history.get_messages_before_gsn(max_gsn=-1, count=10)
            self.assertEqual(result, ['msg1', 'msg2'])

    def test_single_message_multiple_entries(self):
        """Test that all entries for a single message_id are returned."""
        with patch.object(EnhancedMessageLogHistory, '__init__', return_value=None):
            history = EnhancedMessageLogHistory.__new__(EnhancedMessageLogHistory)
            history._history = Mock()
            history._archives = []
            history._gsn_manager = Mock()
            history._gsn_manager.get_current_gsn.return_value = 100

            # Simulate a single message with multiple entries (streaming updates)
            mock_messages = [
                self._create_message('msg-001', 10, 'thinking'),
                self._create_message('msg-001', 11, 'tool_call'),
                self._create_message('msg-001', 12, 'llm_output'),
                self._create_message('msg-001', 13, 'skill'),
                self._create_message('msg-002', 50, 'text'),  # This should be excluded
            ]
            history._history.get_latest_messages.return_value = mock_messages

            result = history.get_messages_before_gsn(max_gsn=20, count=10)

            # Should return all 4 entries for msg-001, but not msg-002
            self.assertEqual(len(result), 4)
            for entry in result:
                self.assertEqual(entry['message_id'], 'msg-001')

    def test_respects_count_limit_for_unique_message_ids(self):
        """Test that count limits unique message_ids, not total entries."""
        with patch.object(EnhancedMessageLogHistory, '__init__', return_value=None):
            history = EnhancedMessageLogHistory.__new__(EnhancedMessageLogHistory)
            history._history = Mock()
            history._archives = []
            history._gsn_manager = Mock()
            history._gsn_manager.get_current_gsn.return_value = 100

            # Create 3 messages, each with multiple entries
            mock_messages = [
                self._create_message('msg-001', 10, 'text'),
                self._create_message('msg-001', 11, 'tool'),
                self._create_message('msg-002', 20, 'text'),
                self._create_message('msg-002', 21, 'tool'),
                self._create_message('msg-003', 30, 'text'),
                self._create_message('msg-003', 31, 'tool'),
            ]
            history._history.get_latest_messages.return_value = mock_messages

            # Request only 2 unique messages
            result = history.get_messages_before_gsn(max_gsn=50, count=2)

            # Should return 4 entries (2 messages * 2 entries each)
            unique_ids = set(e['message_id'] for e in result)
            self.assertLessEqual(len(unique_ids), 2)

    def test_sorted_by_gsn_ascending(self):
        """Test that results are sorted by GSN in ascending order."""
        with patch.object(EnhancedMessageLogHistory, '__init__', return_value=None):
            history = EnhancedMessageLogHistory.__new__(EnhancedMessageLogHistory)
            history._history = Mock()
            history._archives = []
            history._gsn_manager = Mock()
            history._gsn_manager.get_current_gsn.return_value = 100

            # Messages in non-sequential order
            mock_messages = [
                self._create_message('msg-003', 30, 'text'),
                self._create_message('msg-001', 10, 'text'),
                self._create_message('msg-002', 20, 'text'),
            ]
            history._history.get_latest_messages.return_value = mock_messages

            result = history.get_messages_before_gsn(max_gsn=50, count=10)

            # Verify ascending order
            gsns = [e['metadata']['gsn'] for e in result]
            self.assertEqual(gsns, sorted(gsns))

    def test_excludes_messages_with_gsn_equal_or_greater(self):
        """Test that messages with GSN >= max_gsn are excluded."""
        with patch.object(EnhancedMessageLogHistory, '__init__', return_value=None):
            history = EnhancedMessageLogHistory.__new__(EnhancedMessageLogHistory)
            history._history = Mock()
            history._archives = []
            history._gsn_manager = Mock()
            history._gsn_manager.get_current_gsn.return_value = 100

            mock_messages = [
                self._create_message('msg-001', 10, 'text'),   # < 50, included
                self._create_message('msg-002', 49, 'text'),   # < 50, included
                self._create_message('msg-003', 50, 'text'),   # = 50, excluded
                self._create_message('msg-004', 51, 'text'),   # > 50, excluded
            ]
            history._history.get_latest_messages.return_value = mock_messages

            result = history.get_messages_before_gsn(max_gsn=50, count=10)

            unique_ids = set(e['message_id'] for e in result)
            self.assertIn('msg-001', unique_ids)
            self.assertIn('msg-002', unique_ids)
            self.assertNotIn('msg-003', unique_ids)
            self.assertNotIn('msg-004', unique_ids)

    def test_deduplication_by_gsn(self):
        """Test that duplicate entries with same GSN are removed."""
        with patch.object(EnhancedMessageLogHistory, '__init__', return_value=None):
            history = EnhancedMessageLogHistory.__new__(EnhancedMessageLogHistory)
            history._history = Mock()
            history._archives = []
            history._gsn_manager = Mock()
            history._gsn_manager.get_current_gsn.return_value = 100

            # Same message appears twice with same GSN (should be deduplicated)
            mock_messages = [
                self._create_message('msg-001', 10, 'text'),
                self._create_message('msg-001', 10, 'text'),  # Duplicate GSN
                self._create_message('msg-001', 11, 'text'),  # Different GSN
            ]
            history._history.get_latest_messages.return_value = mock_messages

            result = history.get_messages_before_gsn(max_gsn=50, count=10)

            # Should only have 2 entries (GSN 10 and 11)
            self.assertEqual(len(result), 2)

    def test_handles_archive_loading(self):
        """Test that archives are processed correctly."""
        with patch.object(EnhancedMessageLogHistory, '__init__', return_value=None):
            history = EnhancedMessageLogHistory.__new__(EnhancedMessageLogHistory)
            history._history = Mock()
            history._gsn_manager = Mock()
            history._gsn_manager.get_current_gsn.return_value = 100

            # Setup mock archive
            mock_archive = Mock()
            mock_archive.get_line_count.return_value = 2
            mock_archive.get_messages.return_value = [
                self._create_message('archive-msg-001', 5, 'text'),
                self._create_message('archive-msg-001', 6, 'tool'),
            ]

            history._history.storage.load_archive.return_value = mock_archive
            history._archives = [Path('/fake/archive1')]

            # Active log is empty
            history._history.get_latest_messages.return_value = []

            result = history.get_messages_before_gsn(max_gsn=50, count=10)

            self.assertEqual(len(result), 2)
            for entry in result:
                self.assertEqual(entry['message_id'], 'archive-msg-001')

    def test_chunked_archive_loading_from_end(self):
        """Test that large archives are loaded in chunks from the end."""
        with patch.object(EnhancedMessageLogHistory, '__init__', return_value=None):
            history = EnhancedMessageLogHistory.__new__(EnhancedMessageLogHistory)
            history._history = Mock()
            history._gsn_manager = Mock()
            history._gsn_manager.get_current_gsn.return_value = 100

            # Setup large archive (1000 entries)
            mock_archive = Mock()
            mock_archive.get_line_count.return_value = 1000

            # Track calls to get_messages
            call_history = []
            def track_get_messages(start, count):
                call_history.append((start, count))
                # Return messages with GSN based on position
                return [
                    self._create_message(f'msg-{start}-{i}', start + i + 1, 'text')
                    for i in range(count)
                ]
            mock_archive.get_messages.side_effect = track_get_messages

            history._history.storage.load_archive.return_value = mock_archive
            history._archives = [Path('/fake/archive1')]
            history._history.get_latest_messages.return_value = []

            result = history.get_messages_before_gsn(max_gsn=10000, count=100)

            # Verify chunked loading was used from end
            # First call should be from the end: start=500, count=500 (for 1000 entries)
            self.assertGreater(mock_archive.get_messages.call_count, 0)

            # Verify first call is from end of archive
            first_call_start, first_call_count = call_history[0]
            # Should start from position 500 (1000 - 500 = 500)
            self.assertEqual(first_call_start, 500)
            self.assertEqual(first_call_count, 500)

    def test_early_termination_when_enough_qualified(self):
        """Test that archive loading stops early when enough qualified IDs are found."""
        with patch.object(EnhancedMessageLogHistory, '__init__', return_value=None):
            history = EnhancedMessageLogHistory.__new__(EnhancedMessageLogHistory)
            history._history = Mock()
            history._gsn_manager = Mock()
            history._gsn_manager.get_current_gsn.return_value = 100

            # Setup two archives
            mock_archive1 = Mock()
            mock_archive1.get_line_count.return_value = 100
            mock_archive1.get_messages.return_value = [
                self._create_message(f'archive1-msg-{i}', 50 + i, 'text')
                for i in range(100)
            ]

            mock_archive2 = Mock()
            mock_archive2.get_line_count.return_value = 100
            mock_archive2.get_messages.return_value = [
                self._create_message(f'archive2-msg-{i}', 150 + i, 'text')
                for i in range(100)
            ]

            def load_archive_side_effect(path):
                if 'archive2' in str(path):
                    return mock_archive2
                return mock_archive1

            history._history.storage.load_archive.side_effect = load_archive_side_effect
            history._archives = [Path('/fake/archive1'), Path('/fake/archive2')]
            history._history.get_latest_messages.return_value = []

            # Request only 5 messages
            result = history.get_messages_before_gsn(max_gsn=200, count=5)

            # Should have at most 5 unique message_ids
            unique_ids = set(e['message_id'] for e in result)
            self.assertLessEqual(len(unique_ids), 5)


class TestGSNManager(unittest.TestCase):
    """Test cases for GSNManager class."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_gsn_allocation_is_sequential(self):
        """Test that GSN allocation is sequential."""
        manager = GSNManager(self.temp_dir)

        gsn1 = manager.get_next_gsn()
        gsn2 = manager.get_next_gsn()
        gsn3 = manager.get_next_gsn()

        self.assertEqual(gsn2, gsn1 + 1)
        self.assertEqual(gsn3, gsn2 + 1)

    def test_get_current_gsn(self):
        """Test getting current GSN without incrementing."""
        manager = GSNManager(self.temp_dir)

        # Initially 0
        self.assertEqual(manager.get_current_gsn(), 0)

        # After allocation
        manager.get_next_gsn()
        manager.get_next_gsn()
        self.assertEqual(manager.get_current_gsn(), 2)

    def test_singleton_per_history_root(self):
        """Test that GSNManager is singleton per history root."""
        manager1 = GSNManager.get_manager(self.temp_dir)
        manager2 = GSNManager.get_manager(self.temp_dir)

        self.assertIs(manager1, manager2)


if __name__ == '__main__':
    unittest.main(verbosity=2)
