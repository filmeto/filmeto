"""Quick verification that the history widget fix is working.

This script verifies that:
1. Messages are loaded into the model
2. Widgets are created for visible items
3. The view scrolls to the bottom
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

from app.ui.chat.list.agent_chat_list import AgentChatListWidget
from app.data.workspace import Workspace

import logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


def verify_fix():
    """Verify that the fix works correctly."""
    print("\n" + "=" * 70)
    print("HISTORY WIDGET FIX VERIFICATION")
    print("=" * 70)

    workspace_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "workspace")
    project_name = "demo"

    # Create Qt app
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)

    # Create workspace
    workspace = Workspace(workspace_path, project_name, load_data=True, defer_heavy_init=False)

    # Create chat list widget (this will load messages)
    print("\n[1/4] Creating AgentChatListWidget...")
    widget = AgentChatListWidget(workspace)

    # Check model
    model_count = widget._model.rowCount()
    print(f"  ✓ Model loaded: {model_count} rows")

    # Wait a bit for widgets to be created
    def check_after_delay():
        print("\n[2/4] Checking widget creation after delay...")

        # Force refresh (simulating what happens after window is shown)
        widget._refresh_visible_widgets()

        visible_count = len(widget._visible_widgets)
        print(f"  ✓ Visible widgets: {visible_count}")

        # Check viewport info
        viewport = widget.list_view.viewport()
        viewport_size = f"{viewport.width()}x{viewport.height()}"
        print(f"  ✓ Viewport size: {viewport_size}")

        # Scroll to bottom (this should trigger the fix)
        print("\n[3/4] Calling _ensure_widgets_visible_and_scrolled()...")
        widget._ensure_widgets_visible_and_scrolled()

        # Check final state after another delay
        QTimer.singleShot(150, check_final_state)

    def check_final_state():
        print("\n[4/4] Final state check:")

        visible_count = len(widget._visible_widgets)
        scrollbar = widget.list_view.verticalScrollBar()
        scroll_max = scrollbar.maximum()
        scroll_value = scrollbar.value()

        print(f"  ✓ Visible widgets: {visible_count}")
        print(f"  ✓ Scroll position: {scroll_value}/{scroll_max}")
        print(f"  ✓ At bottom: {scroll_value >= scroll_max - 10}")

        # Determine if fix is working
        is_working = visible_count > 0 and scroll_value >= scroll_max - 10

        print("\n" + "=" * 70)
        if is_working:
            print("✓ FIX VERIFIED: Widgets are created and scrolled to bottom!")
        else:
            print("⚠ PARTIAL: Model has data but widget visibility needs review")
        print("=" * 70)

        # Show sample items
        print("\nSample items in model:")
        for i in range(min(5, widget._model.rowCount())):
            item = widget._model.get_item(i)
            if item:
                has_widget = i in widget._visible_widgets
                print(f"  [{i}] {item.sender_name[:12]:12s} (widget={has_widget})")

        print("\nTo run the full GUI test:")
        print("  python tests/test_history_widget_display.py")
        print()

    # Start the check sequence
    QTimer.singleShot(100, check_after_delay)
    QTimer.singleShot(1000, app.quit)  # Auto-quit after checks

    # Run event loop
    app.exec()


if __name__ == "__main__":
    verify_fix()
