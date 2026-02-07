"""Test script to clear cache and verify size hint fix."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

from app.ui.chat.list.agent_chat_list import AgentChatListWidget
from app.data.workspace import Workspace

import logging
logging.basicConfig(level=logging.ERROR)


def main():
    """Clear cache and test with fix."""
    print("\n" + "=" * 70)
    print("SIZE HINT FIX VERIFICATION (With Cache Clear)")
    print("=" * 70)

    workspace_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "workspace")
    project_name = "demo"

    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)

    workspace = Workspace(workspace_path, project_name, load_data=True, defer_heavy_init=False)

    # Create widget
    print("\n[1/5] Creating AgentChatListWidget...")
    widget = AgentChatListWidget(workspace)

    model_count = widget._model.rowCount()
    print(f"  ✓ Model: {model_count} rows")

    # Clear all caches
    print("\n[2/5] Clearing size hint cache...")
    widget._size_hint_cache.clear()
    print(f"  ✓ Cache cleared")

    # Clear and reload model
    print("\n[3/5] Reloading conversation with cleared cache...")
    widget._model.clear()
    widget._load_recent_conversation()

    def check_after_load():
        print("\n[4/5] Checking state after reload...")

        model_count = widget._model.rowCount()
        cache_size = len(widget._size_hint_cache)
        visible_count = len(widget._visible_widgets)

        print(f"  ✓ Model: {model_count} rows")
        print(f"  ✓ Cache entries: {cache_size}")
        print(f"  ✓ Visible widgets: {visible_count}")

        # Check scrollbar
        scrollbar = widget.list_view.verticalScrollBar()
        scroll_max = scrollbar.maximum()
        print(f"  ✓ Scrollbar max: {scroll_max}")

        # Check size hints for first few items
        print("\n  Size hints (first 5):")
        viewport = widget.list_view.viewport()
        viewport_width = viewport.width()

        for i in range(min(5, model_count)):
            item = widget._model.get_item(i)
            if item:
                cached = widget._size_hint_cache.get(item.message_id, {}).get(AgentChatListWidget.MIN_SIZING_WIDTH)
                if cached:
                    print(f"    [{i}] {item.sender_name[:10]:10s} - {cached.width()}x{cached.height()}")

        def final_check():
            print("\n[5/5] Final check after forcing refresh...")

            # Force refresh with actual viewport width
            widget._refresh_visible_widgets()

            visible_count = len(widget._visible_widgets)
            scrollbar = widget.list_view.verticalScrollBar()
            scroll_max = scrollbar.maximum()
            scroll_value = scrollbar.value()

            print(f"  ✓ Visible widgets: {visible_count}")
            print(f"  ✓ Scrollbar: {scroll_value}/{scroll_max}")

            # Calculate expected
            avg_height = scroll_max / model_count if model_count > 0 else 0
            print(f"\n  Analysis:")
            print(f"    - Messages: {model_count}")
            print(f"    - Scroll max: {scroll_max}")
            print(f"    - Avg height per message: {avg_height:.1f}")

            print("\n" + "=" * 70)
            if scroll_max < 10000 and avg_height < 500:
                print("✓ FIX SUCCESSFUL!")
                print("  Scroll bar size is reasonable (not exaggerated)")
                print("  Average height per message is normal")
            elif scroll_max > 15000:
                print("⚠ Scroll bar still large - cache may need more time to clear")
                print("  Try closing and reopening the test window")
            else:
                print("⚠ Intermediate state - check in actual GUI")
            print("=" * 70)

            QTimer.singleShot(500, app.quit)

        QTimer.singleShot(100, final_check)

    QTimer.singleShot(200, check_after_load)

    app.exec()


if __name__ == "__main__":
    main()
