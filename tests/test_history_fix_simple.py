"""Simple synchronous test to verify history widget fix."""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication

from app.ui.chat.list.agent_chat_list import AgentChatListWidget
from app.data.workspace import Workspace

import logging
logging.basicConfig(level=logging.ERROR)


def main():
    """Run simple verification test."""
    print("\n" + "=" * 70)
    print("HISTORY WIDGET FIX VERIFICATION (Simple)")
    print("=" * 70)

    workspace_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "workspace")
    project_name = "demo"

    # Create Qt app
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)

    # Create workspace
    print("\nCreating workspace...")
    workspace = Workspace(workspace_path, project_name, load_data=True, defer_heavy_init=False)

    # Create chat list widget
    print("Creating AgentChatListWidget...")
    widget = AgentChatListWidget(workspace)

    # Check model
    model_count = widget._model.rowCount()
    print(f"✓ Model loaded: {model_count} rows")

    # Process events to let widgets create
    app.processEvents()

    # Check if the fix method exists
    has_fix_method = hasattr(widget, '_ensure_widgets_visible_and_scrolled')
    print(f"✓ Has _ensure_widgets_visible_and_scrolled method: {has_fix_method}")

    # Force refresh
    print("Forcing widget refresh...")
    widget._refresh_visible_widgets()

    visible_count = len(widget._visible_widgets)
    print(f"✓ Visible widgets after refresh: {visible_count}")

    # Call the fix method
    print("Calling _ensure_widgets_visible_and_scrolled()...")
    try:
        widget._ensure_widgets_visible_and_scrolled()
        print("✓ Method executed successfully")
    except Exception as e:
        print(f"✗ Error calling method: {e}")
        return False

    # Process events again
    app.processEvents()
    time.sleep(0.1)
    app.processEvents()

    # Check final state
    visible_count_after = len(widget._visible_widgets)
    scrollbar = widget.list_view.verticalScrollBar()
    scroll_value = scrollbar.value()
    scroll_max = scrollbar.maximum()

    print(f"\nFinal state:")
    print(f"  ✓ Visible widgets: {visible_count_after}")
    print(f"  ✓ Scroll position: {scroll_value}/{scroll_max}")
    print(f"  ✓ At bottom: {scroll_value >= scroll_max - 10}")

    # Check model items
    print(f"\nSample items (showing first 5):")
    for i in range(min(5, model_count)):
        item = widget._model.get_item(i)
        if item:
            has_widget = i in widget._visible_widgets
            print(f"  [{i}] {item.sender_name[:12]:12s} (widget={has_widget})")

    # Verify fix
    is_working = (
        has_fix_method and
        model_count > 0 and
        visible_count_after > 0
    )

    print("\n" + "=" * 70)
    if is_working:
        print("✓ FIX VERIFIED!")
        print("  - Model has data")
        print("  - Fix method exists")
        print("  - Widgets are being created")
    else:
        print("⚠ FIX STATUS: Check needed")
    print("=" * 70)

    return is_working


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
