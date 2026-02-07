"""Check all widgets status."""

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
    """Check all widgets status."""
    print("\n" + "=" * 70)
    print("CHECKING ALL WIDGETS STATUS")
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

    # Force refresh and scroll to bottom
    widget._refresh_visible_widgets()
    widget._user_at_bottom = True
    widget.list_view.scrollToBottom()

    def check():
        widget._refresh_visible_widgets()

        visible_count = len(widget._visible_widgets)
        print(f"\nVisible widgets: {visible_count}/{model_count}")

        # Check which items have widgets
        print("\nItems with widgets:")
        for row in range(model_count):
            has_widget = row in widget._visible_widgets
            if has_widget:
                item = widget._model.get_item(row)
                print(f"  [{row:2d}] {item.sender_name[:15]:15s} ✓")
            elif row < 5 or row >= model_count - 5:
                # Show first and last 5 regardless
                item = widget._model.get_item(row)
                print(f"  [{row:2d}] {item.sender_name[:15]:15s} ✗")

        # Count missing widgets
        missing = sum(1 for row in range(model_count) if row not in widget._visible_widgets)
        print(f"\nMissing widgets: {missing}")
        print(f"Widgets created: {model_count - missing}/{model_count}")

        QTimer.singleShot(500, app.quit)

    QTimer.singleShot(200, check)
    app.exec()


if __name__ == "__main__":
    main()
