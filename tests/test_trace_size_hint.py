"""Trace size hint calculation."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication

from app.ui.chat.list.agent_chat_list import AgentChatListWidget
from app.data.workspace import Workspace

import logging
logging.basicConfig(level=logging.ERROR)


# Monkey patch to trace calls
original_get_item_size_hint = AgentChatListWidget.get_item_size_hint

def traced_get_item_size_hint(self, option, index):
    item = index.data(self._model.ITEM_ROLE)
    if item:
        print(f"  get_item_size_hint called: {item.sender_name[:10]}, viewport={self.list_view.viewport().width()}")

    result = original_get_item_size_hint(self, option, index)

    if item:
        print(f"    -> returning: {result.width()}x{result.height()}")
        cache_entry = self._size_hint_cache.get(item.message_id)
        if cache_entry:
            print(f"    -> cache keys: {list(cache_entry.keys())}")

    return result

AgentChatListWidget.get_item_size_hint = traced_get_item_size_hint


def main():
    """Trace size hint calls."""
    print("\n" + "=" * 70)
    print("TRACING SIZE HINT CALLS")
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
    print(f"\nModel: {model_count} rows")

    print("\nForcing get_item_size_hint calls...")
    from PySide6.QtWidgets import QStyleOptionViewItem
    option = QStyleOptionViewItem()

    for i in range(min(5, model_count)):
        print(f"\n[{i}] Calling get_item_size_hint:")
        index = widget._model.index(i, 0)
        size_hint = widget.get_item_size_hint(option, index)

    print("\n" + "=" * 70)
    print("Final cache state:")
    for i in range(min(3, model_count)):
        item = widget._model.get_item(i)
        if item:
            cache_entry = widget._size_hint_cache.get(item.message_id)
            if cache_entry:
                print(f"[{i}] {item.sender_name[:10]}: keys={list(cache_entry.keys())}")
            else:
                print(f"[{i}] {item.sender_name[:10]}: no cache")


if __name__ == "__main__":
    main()
