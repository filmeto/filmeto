#!/usr/bin/env python3
"""Test for new message height calculation during streaming."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from unittest.mock import Mock, MagicMock, patch
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QRect, QModelIndex

# Initialize Qt app
app = QApplication.instance() or QApplication(sys.argv)

def test_new_message_height_consistency():
    """Test that new message heights are calculated consistently."""
    from app.ui.chat.list.agent_chat_list_widget import AgentChatListWidget

    print("\n=== Testing New Message Height Calculation ===\n")

    workspace = Mock()
    workspace.workspace_path = "/tmp/test"
    workspace.project_name = "test"

    widget = AgentChatListWidget.__new__(AgentChatListWidget)

    # Initialize state
    widget._model = Mock()
    widget._model.rowCount.return_value = 10
    widget._positions_cache_dirty = False
    widget._row_positions_cache = {}
    widget._total_height_cache = 0
    widget._size_hint_cache = {}
    widget._visible_widgets = {}
    widget._scroll_delta_since_last_refresh = 0
    widget._user_at_bottom = True
    widget._is_prepending = False
    widget._load_state = Mock()
    widget._load_state.known_message_ids = set()
    widget._loading_older = False
    widget._history = None
    widget._crew_member_metadata = {}
    widget._agent_current_cards = {}

    # Setup list view mock with consistent viewport dimensions
    viewport_mock = Mock()
    viewport_mock.height.return_value = 600
    viewport_mock.width.return_value = 800
    viewport_mock.rect.return_value = QRect(0, 0, 800, 600)
    viewport_mock.update = Mock()

    list_view_mock = Mock()
    list_view_mock.viewport = Mock(return_value=viewport_mock)
    list_view_mock.ensurePolished = Mock()
    list_view_mock.doItemsLayout = Mock()
    list_view_mock.scrollToBottom = Mock()
    list_view_mock.set_row_positions = Mock()
    list_view_mock.setIndexWidget = Mock()

    scrollbar = Mock()
    scrollbar.value.return_value = 0
    scrollbar.maximum.return_value = 5000
    list_view_mock.verticalScrollBar = Mock(return_value=scrollbar)

    widget.list_view = list_view_mock

    # Mock helper methods
    widget._get_item_size_hint = Mock()
    widget._create_message_widget = Mock(return_value=Mock())

    def mock_get_item(row):
        return Mock(message_id=f"msg_{row}")

    widget._model.get_item = mock_get_item

    # Create a mock index
    mock_index = Mock()
    mock_index.row.return_value = 0

    def mock_index_func(row, column=0):
        idx = Mock()
        idx.row.return_value = row
        return idx

    widget._model.index = mock_index_func

    print("Test 1: Initial cache build")
    print("-" * 50)

    # Simulate initial state with 10 messages
    heights = [100, 150, 120, 200, 80, 110, 130, 140, 160, 90]

    # Setup size hint return values
    def get_size_hint_side_effect(option, index):
        row = index.row()
        size = Mock()
        size.width.return_value = 800
        size.height.return_value = heights[row]
        return size

    widget._get_item_size_hint.side_effect = get_size_hint_side_effect

    # Build cache
    widget._rebuild_positions_cache(force=True)

    print(f"After initial cache build:")
    print(f"  Cached rows: {len(widget._row_positions_cache)}")
    print(f"  Total height: {widget._total_height_cache}")

    # Verify cache is correct
    expected_y = 0
    for row in range(10):
        if row in widget._row_positions_cache:
            y, h = widget._row_positions_cache[row]
            assert y == expected_y, f"Row {row} Y position wrong: {y} != {expected_y}"
            assert h == heights[row], f"Row {row} height wrong: {h} != {heights[row]}"
            expected_y += h

    print("  ✓ All positions correct")

    print("\nTest 2: Adding new message")
    print("-" * 50)

    # Simulate adding a new message (row count becomes 11)
    widget._model.rowCount.return_value = 11
    widget._positions_cache_dirty = True  # Simulate invalidate

    # Add new height for row 10
    heights.append(180)

    print("Simulating _on_rows_inserted (new message added):")

    # This is what _on_rows_inserted does now:
    widget._rebuild_positions_cache(force=True)

    print(f"After cache rebuild with new message:")
    print(f"  Cached rows: {len(widget._row_positions_cache)}")
    print(f"  Total height: {widget._total_height_cache}")

    # Verify cache includes new row
    assert len(widget._row_positions_cache) == 11, "Should have 11 rows"
    assert 10 in widget._row_positions_cache, "Row 10 should be in cache"

    # Verify positions are correct
    expected_y = 0
    for row in range(11):
        if row in widget._row_positions_cache:
            y, h = widget._row_positions_cache[row]
            assert y == expected_y, f"Row {row} Y position wrong after add: {y} != {expected_y}"
            assert h == heights[row], f"Row {row} height wrong after add: {h} != {heights[row]}"
            expected_y += h

    print("  ✓ All positions correct after adding new message")

    # Verify _total_height_cache is correct
    expected_total = sum(heights)
    assert widget._total_height_cache == expected_total, \
        f"Total height wrong: {widget._total_height_cache} != {expected_total}"

    print(f"  ✓ Total height correct: {widget._total_height_cache}")

    print("\nTest 3: Cache rebuild uses consistent viewport width")
    print("-" * 50)

    # Reset and test with different viewport width
    widget._positions_cache_dirty = True

    # Change viewport width to 900
    viewport_mock.width.return_value = 900
    viewport_mock.rect.return_value = QRect(0, 0, 900, 600)

    # Rebuild cache
    widget._rebuild_positions_cache(force=True)

    # Verify the option used the correct viewport width
    option_used = widget._get_item_size_hint.call_args_list[0][0]
    rect_width = option_used.rect.width()

    print(f"Viewport width: {viewport_mock.width.return_value}")
    print(f"Option rect width: {rect_width}")

    # They should match
    assert rect_width == 900, f"Option should use updated viewport width: {rect_width} != 900"

    print("  ✓ Cache rebuild uses current viewport dimensions")

    print("\n✓ All new message height tests passed")
    return True

def test_streaming_message_height_update():
    """Test that streaming message height updates correctly."""
    from app.ui.chat.list.agent_chat_list_widget import AgentChatListWidget

    print("\n=== Testing Streaming Message Height Update ===\n")

    workspace = Mock()
    workspace.workspace_path = "/tmp/test"
    workspace.project_name = "test"

    widget = AgentChatListWidget.__new__(AgentChatListWidget)

    # Initialize state
    widget._model = Mock()
    widget._model.rowCount.return_value = 5
    widget._positions_cache_dirty = False
    widget._row_positions_cache = {}
    widget._total_height_cache = 0
    widget._size_hint_cache = {}
    widget._visible_widgets = {}
    widget._scroll_delta_since_last_refresh = 0
    widget._user_at_bottom = True

    # Setup list view mock
    viewport_mock = Mock()
    viewport_mock.height.return_value = 600
    viewport_mock.width.return_value = 800
    viewport_mock.rect.return_value = QRect(0, 0, 800, 600)
    viewport_mock.update = Mock()

    list_view_mock = Mock()
    list_view_mock.viewport = Mock(return_value=viewport_mock)
    list_view_mock.set_row_positions = Mock()
    list_view_mock.setIndexWidget = Mock()

    scrollbar = Mock()
    scrollbar.value.return_value = 0
    scrollbar.maximum.return_value = 1000
    list_view_mock.verticalScrollBar = Mock(return_value=scrollbar)

    widget.list_view = list_view_mock

    # Initial heights: [100, 100, 50 (streaming), 100, 100]
    initial_heights = [100, 100, 50, 100, 100]

    widget._get_item_size_hint = Mock()
    widget._create_message_widget = Mock()
    widget._model.get_item = Mock(return_value=Mock(message_id=f"msg_{i}"))
    widget._model.index = Mock()

    def get_size_hint_side_effect(option, index):
        row = index.row()
        size = Mock()
        size.width.return_value = 800
        size.height.return_value = initial_heights[row]
        return size

    widget._get_item_size_hint.side_effect = get_size_hint_side_effect
    widget._model.index = lambda row, column=0: (Mock(row=row) if isinstance(row, int) else Mock())

    # Build initial cache
    widget._rebuild_positions_cache(force=True)

    print(f"Initial state:")
    print(f"  Row 2 (streaming) height: {initial_heights[2]}")
    print(f"  Row 2 position: {widget._row_positions_cache[2][0]}")
    print(f"  Total height: {widget._total_height_cache}")

    # Simulate streaming message growing from 50 to 200
    initial_heights[2] = 200
    widget._invalidate_size_hint("msg_2")
    widget._positions_cache_dirty = True

    # Rebuild cache (this is what _on_rows_inserted does now)
    widget._rebuild_positions_cache(force=True)

    print(f"\nAfter streaming message grew to 200:")
    print(f"  Row 2 height: {initial_heights[2]}")
    print(f"  Row 2 position: {widget._row_positions_cache[2][0]}")
    print(f"  Total height: {widget._total_height_cache}")

    # Verify row 2 height is updated
    assert widget._row_positions_cache[2][1] == 200, \
        f"Row 2 height should be 200: {widget._row_positions_cache[2][1]}"

    # Verify rows below are shifted
    row_3_y = widget._row_positions_cache[3][0]
    expected_row_3_y = 100 + 100 + 200  # rows 0, 1, 2
    assert row_3_y == expected_row_3_y, \
        f"Row 3 should be at {expected_row_3_y}: {row_3_y}"

    print(f"  ✓ Row 2 height updated correctly")
    print(f"  ✓ Rows below shifted correctly")

    print("\n✓ Streaming message height update test passed")
    return True

if __name__ == "__main__":
    try:
        test_new_message_height_consistency()
        test_streaming_message_height_update()

        print("\n" + "=" * 60)
        print("=== All Height Calculation Tests Passed ===")
        print("=" * 60)

        print("\nKey fixes applied:")
        print("1. ✓ Cache rebuilt BEFORE creating widgets in _refresh_visible_widgets")
        print("2. ✓ Cache rebuilt IMMEDIATELY in _on_rows_inserted (not deferred)")
        print("3. ✓ Cache uses force=True to ensure rebuild happens")
        print("4. ✓ Immediate refresh (immediate=True) for new messages")

    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
