"""Debug script to check visible range and widget creation."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer, QPoint

from app.ui.chat.list.agent_chat_list import AgentChatListWidget
from app.data.workspace import Workspace

import logging
logging.basicConfig(level=logging.ERROR)


def main():
    """Debug visible range calculation."""
    print("\n" + "=" * 70)
    print("DEBUG: Visible Range and Widget Creation")
    print("=" * 70)

    workspace_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "workspace")
    project_name = "demo"

    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)

    workspace = Workspace(workspace_path, project_name, load_data=True, defer_heavy_init=False)

    print("\n[1/4] Creating AgentChatListWidget...")
    widget = AgentChatListWidget(workspace)

    model_count = widget._model.rowCount()
    visible_count = len(widget._visible_widgets)
    viewport = widget.list_view.viewport()

    print(f"  Model: {model_count} rows")
    print(f"  Visible widgets: {visible_count}")
    print(f"  Viewport: {viewport.width()}x{viewport.height()}")

    scrollbar = widget.list_view.verticalScrollBar()
    print(f"  Scrollbar: value={scrollbar.value()}, max={scrollbar.maximum()}")

    # Check visible row range
    first_row, last_row = widget._get_visible_row_range()
    print(f"  Visible row range: {first_row} to {last_row}")

    # Check what's at various positions
    print("\n[2/4] Checking items at viewport positions:")
    for y in [0, 50, 100, 200, 500, 1000]:
        index = widget.list_view.indexAt(QPoint(0, y))
        if index.isValid():
            row = index.row()
            item = widget._model.get_item(row)
            if item:
                has_widget = row in widget._visible_widgets
                print(f"  y={y:4d}: row={row:2d}, {item.sender_name[:10]:10s} (widget={has_widget})")
        else:
            print(f"  y={y:4d}: no item")

    # Force refresh
    print("\n[3/4] Forcing refresh...")
    widget._refresh_visible_widgets()

    visible_count_after = len(widget._visible_widgets)
    print(f"  Visible widgets after refresh: {visible_count_after}")

    first_row, last_row = widget._get_visible_row_range()
    print(f"  Visible row range: {first_row} to {last_row}")

    # Scroll to bottom
    print("\n[4/4] Scrolling to bottom...")
    widget._user_at_bottom = True
    widget.list_view.scrollToBottom()

    def after_scroll():
        viewport = widget.list_view.viewport()
        scrollbar = widget.list_view.verticalScrollBar()

        visible_count = len(widget._visible_widgets)
        first_row, last_row = widget._get_visible_row_range()

        print(f"\n  After scroll:")
        print(f"    Viewport: {viewport.width()}x{viewport.height()}")
        print(f"    Scrollbar: value={scrollbar.value()}, max={scrollbar.maximum()}")
        print(f"    Visible widgets: {visible_count}")
        print(f"    Visible row range: {first_row} to {last_row}")

        # Force refresh after scroll
        widget._refresh_visible_widgets()

        visible_count_final = len(widget._visible_widgets)
        first_row, last_row = widget._get_visible_row_range()

        print(f"\n  After refresh:")
        print(f"    Visible widgets: {visible_count_final}")
        print(f"    Visible row range: {first_row} to {last_row}")

        # Check items near bottom
        print(f"\n  Items near bottom (last 5):")
        for row in range(max(0, model_count - 5), model_count):
            item = widget._model.get_item(row)
            if item:
                has_widget = row in widget._visible_widgets
                print(f"    [{row}] {item.sender_name[:10]:10s} (widget={has_widget})")

        QTimer.singleShot(500, app.quit)

    QTimer.singleShot(100, after_scroll)

    app.exec()


if __name__ == "__main__":
    main()
