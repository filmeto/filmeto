"""Debug script to investigate the history widget display issue.

This script helps diagnose why only first few messages are visible
even though the model has more messages loaded.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication
from qasync import QEventLoop
from PySide6.QtCore import QTimer, QPoint

from app.data.workspace import Workspace
from app.ui.chat.list.agent_chat_list import AgentChatListWidget

def debug_widget_creation():
    """Debug widget creation and visibility."""
    print("\n" + "=" * 70)
    print("DEBUG: Widget Creation and Visibility")
    print("=" * 70)

    workspace_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "workspace")
    project_name = "demo"

    # Create Qt app
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)

    # Create workspace
    workspace = Workspace(workspace_path, project_name, load_data=True, defer_heavy_init=False)

    # Create chat list widget
    widget = AgentChatListWidget(workspace)

    # Check model
    model = widget._model
    row_count = model.rowCount()
    print(f"\n✓ Model has {row_count} rows")

    # Check visible widgets immediately after creation
    visible_count = len(widget._visible_widgets)
    print(f"✓ Visible widgets immediately: {visible_count}")

    # Force refresh visible widgets
    print("\nForcing refresh of visible widgets...")
    widget._refresh_visible_widgets()

    visible_count_after = len(widget._visible_widgets)
    print(f"✓ Visible widgets after refresh: {visible_count_after}")

    # Check viewport info
    viewport = widget.list_view.viewport()
    viewport_height = viewport.height()
    viewport_width = viewport.width()
    print(f"\nViewport size: {viewport_width}x{viewport_height}")

    # Check visible row range
    first_row, last_row = widget._get_visible_row_range()
    print(f"Visible row range: {first_row} to {last_row}")

    # Check scrollbar info
    scrollbar = widget.list_view.verticalScrollBar()
    max_value = scrollbar.maximum()
    current_value = scrollbar.value()
    print(f"Scrollbar: current={current_value}, max={max_value}")

    # Manually check what's at different positions
    print("\nChecking items at different positions:")
    for y in [0, 100, 200, 500, 1000]:
        index = widget.list_view.indexAt(QPoint(0, y))
        if index.isValid():
            row = index.row()
            item = model.get_item(row)
            if item:
                has_widget = row in widget._visible_widgets
                print(f"  y={y:4d}: row={row:2d}, {item.sender_name[:10]:10s} (widget={has_widget})")
        else:
            print(f"  y={y:4d}: no item")

    # Try to scroll to bottom
    print("\nScrolling to bottom...")
    widget._user_at_bottom = True
    widget.list_view.scrollToBottom()

    # Check again after scroll
    QTimer.singleShot(100, lambda: check_after_scroll(widget))

    return widget


def check_after_scroll(widget):
    """Check state after scrolling."""
    print("\n" + "=" * 70)
    print("After scrolling to bottom:")
    print("=" * 70)

    scrollbar = widget.list_view.verticalScrollBar()
    current_value = scrollbar.value()
    max_value = scrollbar.maximum()
    print(f"Scrollbar: current={current_value}, max={max_value}")

    # Refresh and check again
    widget._refresh_visible_widgets()
    visible_count = len(widget._visible_widgets)
    print(f"Visible widgets after scroll + refresh: {visible_count}")

    # Check visible row range
    first_row, last_row = widget._get_visible_row_range()
    print(f"Visible row range: {first_row} to {last_row}")

    # Check items near bottom
    print("\nChecking items near bottom:")
    model = widget._model
    row_count = model.rowCount()
    for row in range(max(0, row_count - 5), row_count):
        item = model.get_item(row)
        if item:
            has_widget = row in widget._visible_widgets
            print(f"  row={row:2d}: {item.sender_name[:10]:10s} (widget={has_widget})")

    print("\n" + "=" * 70)
    print("Diagnosis complete.")
    print("=" * 70)


def main():
    print("\n" + "=" * 70)
    print("HISTORY WIDGET DEBUG")
    print("=" * 70)

    widget = debug_widget_creation()

    print("\nNote: The widget needs to be shown for proper viewport sizing.")
    print("This script only tests without showing the window.")
    print("\nFor full GUI test, run: python tests/test_history_widget_display.py")


if __name__ == "__main__":
    main()
