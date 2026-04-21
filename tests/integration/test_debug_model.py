"""Debug script to check if model loads correctly."""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

os.environ['WORKSPACE_PATH'] = str(Path.cwd() / "workspace")

from PySide6.QtWidgets import QApplication
from app.ui.chat.list.agent_chat_list_model import QmlAgentChatListModel
from app.ui.chat.list.agent_chat_list_widget import QmlAgentChatListWidget
from app.data.workspace import Workspace

def main():
    app = QApplication(sys.argv)

    print("=== Creating QML Model ===")
    model = QmlAgentChatListModel()
    print(f"Model created: {model}")
    print(f"Initial row count: {model.rowCount()}")

    print("\n=== Creating Workspace ===")
    workspace_path = str(Path.cwd() / "workspace")
    workspace = Workspace(workspace_path, "demo", defer_heavy_init=True)
    print(f"Workspace created: {workspace.workspace_path}")

    print("\n=== Creating Widget ===")
    widget = QmlAgentChatListWidget(workspace, None)
    print(f"Widget created: {widget}")

    # Wait a bit for history to load
    import time
    time.sleep(2)

    print(f"\n=== After Loading ===")
    print(f"Model row count: {widget._model.rowCount()}")

    if widget._model.rowCount() > 0:
        print("\n=== Sample Items ===")
        for i in range(min(3, widget._model.rowCount())):
            item = widget._model.get_item(i)
            if item:
                is_user = item.get(QmlAgentChatListModel.IS_USER)
                sender = item.get(QmlAgentChatListModel.SENDER_NAME)
                content = item.get(QmlAgentChatListModel.CONTENT)
                print(f"  {i+1}. [{'USER' if is_user else sender}]: {content[:50]}...")
    else:
        print("  No items in model!")

    print(f"\n=== QML Status ===")
    print(f"QML widget status: {widget._quick_widget.status()}")
    if widget._quick_widget.status() == widget._quick_widget.Error:
        errors = widget._quick_widget.errors()
        for error in errors:
            print(f"  Error: {error.toString()}")

    print(f"\n=== QML Root Object ===")
    print(f"Root object: {widget._qml_root}")
    if widget._qml_root:
        print(f"Root object type: {widget._qml_root.metaObject().className()}")

if __name__ == "__main__":
    main()
