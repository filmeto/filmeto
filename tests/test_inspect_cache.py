"""Debug script to inspect cache contents."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication

from app.ui.chat.list.agent_chat_list import AgentChatListWidget
from app.data.workspace import Workspace

import logging
logging.basicConfig(level=logging.ERROR)


def main():
    """Inspect cache contents."""
    print("\n" + "=" * 70)
    print("CACHE INSPECTION")
    print("=" * 70)

    workspace_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "workspace")
    project_name = "demo"

    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)

    workspace = Workspace(workspace_path, project_name, load_data=True, defer_heavy_init=False)
    widget = AgentChatListWidget(workspace)

    model_count = widget._model.rowCount()
    print(f"\nModel: {model_count} rows")
    print(f"MIN_SIZING_WIDTH: {widget.MIN_SIZING_WIDTH}")

    # Inspect cache for first 3 items
    print("\nCache contents (first 3 items):")
    for i in range(min(3, model_count)):
        item = widget._model.get_item(i)
        if item:
            cache_entry = widget._size_hint_cache.get(item.message_id)
            if cache_entry:
                print(f"\n[{i}] {item.sender_name} (msg_id: {item.message_id[:8]}...)")
                print(f"    Cache keys: {list(cache_entry.keys())}")
                for key, size in cache_entry.items():
                    print(f"      Key={key}: {size.width()}x{size.height()}")

    # Check what get_item_size_hint returns
    print("\n" + "=" * 70)
    print("Testing get_item_size_hint directly:")
    print("=" * 70)

    from PySide6.QtWidgets import QStyleOptionViewItem
    option = QStyleOptionViewItem()

    for i in range(min(3, model_count)):
        index = widget._model.index(i, 0)
        item = widget._model.get_item(i)
        if item:
            size_hint = widget.get_item_size_hint(option, index)
            print(f"[{i}] {item.sender_name[:10]:10s} - {size_hint.width()}x{size_hint.height()}")

    # Check viewport width
    viewport = widget.list_view.viewport()
    viewport_width = viewport.width()
    viewport_height = viewport.height()
    print(f"\nViewport size: {viewport_width}x{viewport_height}")

    scrollbar = widget.list_view.verticalScrollBar()
    print(f"Scrollbar max: {scrollbar.maximum()}")


if __name__ == "__main__":
    main()
