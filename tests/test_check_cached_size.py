"""Check cached size values."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication

from app.ui.chat.list.agent_chat_list import AgentChatListWidget
from app.data.workspace import Workspace

import logging
logging.basicConfig(level=logging.ERROR)


def main():
    """Check cached size values."""
    print("\n" + "=" * 70)
    print("CHECKING CACHED SIZE VALUES")
    print("=" * 70)

    workspace_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "workspace")
    project_name = "demo"

    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)

    workspace = Workspace(workspace_path, project_name, load_data=True, defer_heavy_init=False)

    print("\nCreating AgentChatListWidget...")
    widget = AgentChatListWidget(workspace)

    model_count = widget._model.rowCount()
    print(f"Model: {model_count} rows")
    print(f"MIN_SIZING_WIDTH: {widget.MIN_SIZING_WIDTH}")
    print(f"Viewport width: {widget.list_view.viewport().width()}")

    # Force size hint calculation
    from PySide6.QtWidgets import QStyleOptionViewItem
    option = QStyleOptionViewItem()

    print("\nCalculating size hints (first 5):")
    total_height = 0

    for i in range(min(5, model_count)):
        index = widget._model.index(i, 0)
        item = widget._model.get_item(i)
        if item:
            size_hint = widget.get_item_size_hint(option, index)
            total_height += size_hint.height()

            # Check what's in cache
            cache_entry = widget._size_hint_cache.get(item.message_id)
            if cache_entry:
                for key, cached_size in cache_entry.items():
                    print(f"[{i}] {item.sender_name[:10]:10s} - "
                          f"returned: {size_hint.width()}x{size_hint.height()}, "
                          f"cached[{key}]: {cached_size.width()}x{cached_size.height()}")
            else:
                print(f"[{i}] {item.sender_name[:10]:10s} - "
                      f"returned: {size_hint.width()}x{size_hint.height()}, "
                      f"no cache")

    print(f"\nTotal height for 5 items: {total_height}")
    print(f"Estimated for 30 items: {total_height * 6}")

    scrollbar = widget.list_view.verticalScrollBar()
    print(f"\nActual scrollbar max: {scrollbar.maximum()}")


if __name__ == "__main__":
    main()
