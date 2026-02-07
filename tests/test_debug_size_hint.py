"""Debug script to investigate size hint calculation issues."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QTimer

from app.ui.chat.list.agent_chat_list import AgentChatListWidget, ChatListItem
from app.data.workspace import Workspace
from app.ui.chat.card import AgentMessageCard, UserMessageCard

import logging
logging.basicConfig(level=logging.ERROR)


def debug_size_hints():
    """Debug size hint calculation."""
    print("\n" + "=" * 70)
    print("DEBUG: Size Hint Calculation")
    print("=" * 70)

    workspace_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "workspace")
    project_name = "demo"

    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)

    workspace = Workspace(workspace_path, project_name, load_data=True, defer_heavy_init=False)
    widget = AgentChatListWidget(workspace)

    model = widget._model
    row_count = model.rowCount()
    print(f"\nModel has {row_count} rows")

    viewport = widget.list_view.viewport()
    viewport_width = viewport.width()
    viewport_height = viewport.height()
    print(f"Viewport size: {viewport_width}x{viewport_height}")

    scrollbar = widget.list_view.verticalScrollBar()
    scroll_max = scrollbar.maximum()
    print(f"Scrollbar max: {scroll_max}")

    # Calculate expected total height
    print("\nChecking size hints for first 10 items:")
    total_height = 0

    for i in range(min(10, row_count)):
        item = model.get_item(i)
        if not item:
            continue

        # Get cached size hint
        cached = widget._size_hint_cache.get(item.message_id, {}).get(viewport_width)

        # Build sizing widget to get actual size
        from PySide6.QtWidgets import QStyleOptionViewItem, QStyle
        option = QStyleOptionViewItem()
        option.rect = viewport.rect()

        from PySide6.QtCore import QModelIndex
        index = model.index(i, 0)
        size_hint = widget.get_item_size_hint(option, index)

        total_height += size_hint.height()

        print(f"  [{i}] {item.sender_name[:10]:10s} - "
              f"size: {size_hint.width()}x{size_hint.height()}, "
              f"cached: {cached.height() if cached else 'None'}")

        # Check if widget exists
        has_widget = i in widget._visible_widgets
        if has_widget:
            actual_widget = widget._visible_widgets[i]
            actual_size = actual_widget.size()
            print(f"       actual widget: {actual_size.width()}x{actual_size.height()}")

    print(f"\nTotal height for first 10 items: {total_height}")
    print(f"Expected scrollbar max for 30 items: ~{total_height * 3}")

    # Check if issue is with sizing widgets
    print("\n" + "=" * 70)
    print("Testing widget creation directly:")
    print("=" * 70)

    # Get first item
    first_item = model.get_item(0)
    if first_item:
        print(f"\nCreating widget for: {first_item.sender_name}")

        # Create widget normally
        if first_item.is_user:
            test_widget = UserMessageCard(first_item.user_content)
        else:
            test_widget = AgentMessageCard(
                first_item.agent_message,
                first_item.agent_color,
                first_item.agent_icon,
                first_item.crew_member_metadata,
            )

        test_widget.setFixedWidth(viewport_width)
        test_widget.show()  # Actually show it

        # Process events
        app.processEvents()
        QTimer.singleShot(50, lambda: check_widget_size(test_widget))

        return test_widget


def check_widget_size(widget):
    """Check widget size after it's been shown."""
    size_hint = widget.sizeHint()
    size = widget.size()
    minimum = widget.minimumSize()
    minimum_hint = widget.minimumSizeHint()

    print(f"\nWidget size information:")
    print(f"  sizeHint(): {size_hint.width()}x{size_hint.height()}")
    print(f"  size(): {size.width()}x{size.height()}")
    print(f"  minimumSize(): {minimum.width()}x{minimum.height()}")
    print(f"  minimumSizeHint(): {minimum_hint.width()}x{minimum_hint.height()}")

    # Check with WA_DontShowOnScreen
    print("\n" + "=" * 70)
    print("Testing with WA_DontShowOnScreen:")
    print("=" * 70)

    widget.setAttribute(Qt.WA_DontShowOnScreen, True)
    widget.setFixedWidth(800)
    if widget.layout():
        widget.layout().activate()
    widget.adjustSize()

    size_hint2 = widget.sizeHint()
    size2 = widget.size()

    print(f"  With WA_DontShowOnScreen:")
    print(f"  sizeHint(): {size_hint2.width()}x{size_hint2.height()}")
    print(f"  size(): {size2.width()}x{size2.height()}")

    print("\nThe issue is likely that sizeHint() returns incorrect values")
    print("when widget is not properly shown/layed out.")

    QTimer.singleShot(100, QApplication.instance().quit)


if __name__ == "__main__":
    test_widget = debug_size_hints()
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
    app.exec()
