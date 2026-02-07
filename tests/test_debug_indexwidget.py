"""Debug script to check setIndexWidget functionality."""

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
    """Debug setIndexWidget."""
    print("\n" + "=" * 70)
    print("DEBUG: setIndexWidget and Index Location")
    print("=" * 70)

    workspace_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "workspace")
    project_name = "demo"

    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)

    workspace = Workspace(workspace_path, project_name, load_data=True, defer_heavy_init=False)

    print("\n[1/3] Creating AgentChatListWidget...")
    widget = AgentChatListWidget(workspace)

    model_count = widget._model.rowCount()
    print(f"  Model: {model_count} rows")

    # Force refresh to create widgets
    print("\n[2/3] Forcing refresh to create widgets...")
    widget._refresh_visible_widgets()

    visible_count = len(widget._visible_widgets)
    print(f"  Visible widgets: {visible_count}")

    # Check what indexAt returns for each row's expected position
    print("\n[3/3] Checking indexAt for each visible widget:")
    viewport = widget.list_view.viewport()

    for row in sorted(widget._visible_widgets.keys()):
        actual_widget = widget._visible_widgets[row]
        index = widget._model.index(row, 0)

        # Get the visual rect for this index
        visual_rect = widget.list_view.visualRect(index)
        print(f"\n  Row {row}:")
        print(f"    visualRect: {visual_rect}")
        print(f"    widget pos: {actual_widget.pos()}")
        print(f"    widget size: {actual_widget.size()}")

        # Check what indexAt returns for the top of this item
        index_at_top = widget.list_view.indexAt(QPoint(visual_rect.x(), visual_rect.y()))
        if index_at_top.isValid():
            print(f"    indexAt(top): row={index_at_top.row()}")
        else:
            print(f"    indexAt(top): invalid")

        # Check what indexAt returns for the bottom of this item
        bottom_y = visual_rect.y() + visual_rect.height() - 1
        if bottom_y >= 0:
            index_at_bottom = widget.list_view.indexAt(QPoint(visual_rect.x(), bottom_y))
            if index_at_bottom.isValid():
                print(f"    indexAt(bottom): row={index_at_bottom.row()}")
            else:
                print(f"    indexAt(bottom): invalid")

    # Check scrollbar
    scrollbar = widget.list_view.verticalScrollBar()
    print(f"\n  Scrollbar: value={scrollbar.value()}, max={scrollbar.maximum()}")
    print(f"  Viewport: {viewport.width()}x{viewport.height()}")

    # Check what _get_visible_row_range returns
    first_row, last_row = widget._get_visible_row_range()
    print(f"  Visible row range: {first_row} to {last_row}")

    # Check actual indexAt for viewport positions
    print(f"\n  Checking indexAt for viewport positions:")
    for y in [0, viewport.height()//2, viewport.height()-1]:
        index = widget.list_view.indexAt(QPoint(0, y))
        if index.isValid():
            row = index.row()
            item = widget._model.get_item(row)
            print(f"    y={y}: row={row} ({item.sender_name if item else 'N/A'})")
        else:
            print(f"    y={y}: invalid")

    QTimer.singleShot(500, app.quit)


if __name__ == "__main__":
    main()
